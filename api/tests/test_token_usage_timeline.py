"""
Unit and integration tests for token usage metadata in build_conversation_timeline().

Commit f488298 adds token usage metadata (input_tokens, output_tokens,
cache_creation_input_tokens, cache_read_input_tokens, cost_usd) to every
timeline event that originates from an AssistantMessage with usage populated.

Run from api/ directory:
    python -m pytest tests/test_token_usage_timeline.py -v
"""

import sys
from pathlib import Path
from typing import Iterator, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone

from models.content import ToolUseBlock, ThinkingBlock, TextBlock
from models.message import AssistantMessage, UserMessage
from models.usage import TokenUsage
from services.conversation_endpoints import build_conversation_timeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)


def _assistant_msg_with_blocks(
    uuid: str,
    blocks: list,
    usage: TokenUsage | None = None,
    model: str | None = "claude-sonnet-4-6",
) -> AssistantMessage:
    """Build an AssistantMessage with pre-parsed content blocks and optional usage."""
    return AssistantMessage(
        uuid=uuid,
        timestamp=_TS,
        type="assistant",
        content_blocks=blocks,
        usage=usage,
        model=model,
    )


def _user_msg(
    uuid: str, content: str, *, is_tool_result: bool = False, tool_result_id: str | None = None
) -> UserMessage:
    """Build a UserMessage directly without going through JSONL parsing."""
    return UserMessage(
        uuid=uuid,
        timestamp=_TS,
        type="user",
        content=content,
        is_tool_result=is_tool_result,
        tool_result_id=tool_result_id,
    )


def _make_tool_block(
    name: str, block_id: str = "toolu_test", input_dict: dict = None
) -> ToolUseBlock:
    """Create a ToolUseBlock for testing."""
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name=name,
        input=input_dict or {},
    )


class FakeConversation:
    """Minimal ConversationEntity for testing — satisfies MessageSource protocol."""

    def __init__(self, messages: List):
        self._messages = messages
        self.cwd = "/fake/project"

    def iter_messages(self) -> Iterator:
        return iter(self._messages)


# ---------------------------------------------------------------------------
# Shared assertions
# ---------------------------------------------------------------------------

_TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "cost_usd",
)


def _assert_token_keys_present(metadata: dict) -> None:
    """Assert all 5 token keys are present in metadata."""
    for key in _TOKEN_KEYS:
        assert key in metadata, f"Expected '{key}' in metadata"


def _assert_token_keys_absent(metadata: dict) -> None:
    """Assert no token keys are present in metadata."""
    for key in _TOKEN_KEYS:
        assert key not in metadata, f"Unexpected '{key}' in metadata"


# ---------------------------------------------------------------------------
# 1. Unit Tests - Token Metadata by Event Type
# ---------------------------------------------------------------------------


class TestTokenMetadataOnToolCallEvents:
    """Token metadata on ToolUseBlock timeline events."""

    def test_tool_call_event_contains_all_token_fields(self):
        """ToolUseBlock event has all 5 token fields with correct values."""
        usage = TokenUsage(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_input_tokens=200,
            cache_read_input_tokens=300,
        )
        bash_block = _make_tool_block("Bash", "toolu_bash_001", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks("asst-001", [bash_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1, f"Expected 1 Bash event, got {len(tool_events)}"

        metadata = tool_events[0].metadata
        _assert_token_keys_present(metadata)
        assert metadata["input_tokens"] == 1000
        assert metadata["output_tokens"] == 500
        assert metadata["cache_creation_input_tokens"] == 200
        assert metadata["cache_read_input_tokens"] == 300
        # cost_usd calculated for claude-sonnet-4-6
        assert metadata["cost_usd"] is not None
        assert metadata["cost_usd"] > 0

    def test_tool_call_event_cost_usd_null_without_model(self):
        """cost_usd is None when msg.model is None (but usage is populated)."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        bash_block = _make_tool_block("Bash", "toolu_bash_002", {"command": "ls"})
        # model=None via explicit None override
        assistant_msg = AssistantMessage(
            uuid="asst-002",
            timestamp=_TS,
            type="assistant",
            content_blocks=[bash_block],
            usage=usage,
            model=None,
        )

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        _assert_token_keys_present(metadata)
        assert metadata["input_tokens"] == 1000
        assert metadata["cost_usd"] is None, "cost_usd should be None when model is None"

    def test_tool_call_event_no_usage_fields_absent(self):
        """Events without usage have no token keys at all."""
        bash_block = _make_tool_block("Bash", "toolu_bash_003", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks("asst-003", [bash_block], usage=None)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        _assert_token_keys_absent(tool_events[0].metadata)


class TestTokenMetadataOnThinkingEvents:
    """Token metadata on ThinkingBlock timeline events."""

    def test_thinking_event_contains_token_metadata(self):
        """ThinkingBlock event has all token fields."""
        usage = TokenUsage(
            input_tokens=800,
            output_tokens=400,
            cache_creation_input_tokens=100,
            cache_read_input_tokens=50,
        )
        thinking_block = ThinkingBlock(
            type="thinking",
            thinking="Let me think through this problem step by step...",
        )
        assistant_msg = _assistant_msg_with_blocks("asst-thinking-001", [thinking_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        thinking_events = [e for e in events if e.event_type == "thinking"]
        assert len(thinking_events) == 1, f"Expected 1 thinking event, got {len(thinking_events)}"

        metadata = thinking_events[0].metadata
        _assert_token_keys_present(metadata)
        assert metadata["input_tokens"] == 800
        assert metadata["output_tokens"] == 400

    def test_thinking_event_no_usage_no_token_keys(self):
        """Thinking without usage has no token keys."""
        thinking_block = ThinkingBlock(
            type="thinking",
            thinking="Simple thought.",
        )
        assistant_msg = _assistant_msg_with_blocks(
            "asst-thinking-002", [thinking_block], usage=None
        )

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        thinking_events = [e for e in events if e.event_type == "thinking"]
        assert len(thinking_events) == 1
        _assert_token_keys_absent(thinking_events[0].metadata)


class TestTokenMetadataOnResponseEvents:
    """Token metadata on TextBlock (>50 chars) timeline events."""

    def test_response_event_contains_token_metadata(self):
        """TextBlock (>50 chars) event has all token fields."""
        usage = TokenUsage(input_tokens=1200, output_tokens=600)
        text_block = TextBlock(
            type="text",
            text="This is a detailed response that exceeds fifty characters in length and should trigger response event creation.",
        )
        assistant_msg = _assistant_msg_with_blocks("asst-text-001", [text_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        response_events = [e for e in events if e.event_type == "response"]
        assert len(response_events) == 1, f"Expected 1 response event, got {len(response_events)}"

        metadata = response_events[0].metadata
        _assert_token_keys_present(metadata)
        assert metadata["input_tokens"] == 1200
        assert metadata["output_tokens"] == 600

    def test_response_event_short_text_no_event(self):
        """TextBlock with <=50 chars produces no response event."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        text_block = TextBlock(
            type="text",
            text="Short reply.",  # <= 50 chars
        )
        assistant_msg = _assistant_msg_with_blocks("asst-text-002", [text_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        response_events = [e for e in events if e.event_type == "response"]
        assert len(response_events) == 0, "Short text should not produce a response event"

    def test_response_event_no_usage_no_token_keys(self):
        """Response without usage has no token keys."""
        text_block = TextBlock(
            type="text",
            text="This is a detailed response that exceeds fifty characters in length and should trigger response event creation.",
        )
        assistant_msg = _assistant_msg_with_blocks(
            "asst-text-003", [text_block], usage=None
        )

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        response_events = [e for e in events if e.event_type == "response"]
        assert len(response_events) == 1
        _assert_token_keys_absent(response_events[0].metadata)


# ---------------------------------------------------------------------------
# 2. Edge Cases
# ---------------------------------------------------------------------------


class TestTokenUsageEdgeCases:
    """Edge cases for token usage propagation."""

    def test_zero_usage_all_events_have_zero_values(self):
        """All zeros in usage produces input_tokens=0, output_tokens=0, etc."""
        usage = TokenUsage()  # all defaults to 0
        bash_block = _make_tool_block("Bash", "toolu_zero_001", {"command": "true"})
        assistant_msg = _assistant_msg_with_blocks("asst-zero-001", [bash_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        _assert_token_keys_present(metadata)
        assert metadata["input_tokens"] == 0
        assert metadata["output_tokens"] == 0
        assert metadata["cache_creation_input_tokens"] == 0
        assert metadata["cache_read_input_tokens"] == 0
        assert metadata["cost_usd"] == 0.0

    def test_cache_only_usage_propagates_cache_fields(self):
        """cache_read_input_tokens is propagated correctly when only cache is used."""
        usage = TokenUsage(
            input_tokens=0,
            output_tokens=100,
            cache_read_input_tokens=5000,
        )
        bash_block = _make_tool_block("Bash", "toolu_cache_001", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks("asst-cache-001", [bash_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        assert metadata["cache_read_input_tokens"] == 5000
        assert metadata["input_tokens"] == 0
        assert metadata["cost_usd"] is not None
        # Cache reads cost 10% of input price; 5000 tokens at $3/M = $0.0015,
        # plus 100 output tokens at $15/M = $0.0015, total ~$0.003
        assert 0.002 < metadata["cost_usd"] < 0.005

    def test_single_message_multiple_blocks_share_same_token_metadata(self):
        """All blocks in same AssistantMessage share identical token data."""
        usage = TokenUsage(input_tokens=1500, output_tokens=750)
        bash_block = _make_tool_block("Bash", "toolu_multi_001", {"command": "ls"})
        thinking_block = ThinkingBlock(type="thinking", thinking="Considering the options carefully.")
        text_block = TextBlock(
            type="text",
            text="After careful consideration, I have determined the optimal approach for this task implementation.",
        )
        assistant_msg = _assistant_msg_with_blocks(
            "asst-multi-001",
            [bash_block, thinking_block, text_block],
            usage=usage,
        )

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        thinking_events = [e for e in events if e.event_type == "thinking"]
        response_events = [e for e in events if e.event_type == "response"]

        assert len(tool_events) == 1
        assert len(thinking_events) == 1
        assert len(response_events) == 1

        # All should share the same token values from the same usage object
        for event in [tool_events[0], thinking_events[0], response_events[0]]:
            assert event.metadata["input_tokens"] == 1500
            assert event.metadata["output_tokens"] == 750
            assert event.metadata["cost_usd"] is not None


# ---------------------------------------------------------------------------
# 3. Merge Priority
# ---------------------------------------------------------------------------


class TestMergePriority:
    """Verify token_metadata merge order: tool metadata takes priority."""

    def test_token_metadata_does_not_override_tool_name(self):
        """tool_name is preserved after merge (tool metadata wins)."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        bash_block = _make_tool_block("Bash", "toolu_merge_001", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks("asst-merge-001", [bash_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        assert tool_events[0].metadata["tool_name"] == "Bash"
        # Token data also present
        assert tool_events[0].metadata["input_tokens"] == 1000

    def test_token_metadata_does_not_override_has_result(self):
        """has_result key wins over any conflicting token metadata."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        bash_block = _make_tool_block("Bash", "toolu_result_001", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks("asst-result-001", [bash_block], usage=usage)
        result_msg = _user_msg(
            "user-result-001",
            "file1.txt\nfile2.txt",
            is_tool_result=True,
            tool_result_id="toolu_result_001",
        )

        conversation = FakeConversation([assistant_msg, result_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        assert "has_result" in metadata
        assert metadata["has_result"] is True
        assert metadata["input_tokens"] == 1000

    def test_token_metadata_does_not_override_result_content(self):
        """result_content is preserved after token metadata merge."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        bash_block = _make_tool_block("Bash", "toolu_content_001", {"command": "cat foo.txt"})
        assistant_msg = _assistant_msg_with_blocks("asst-content-001", [bash_block], usage=usage)
        result_msg = _user_msg(
            "user-content-001",
            "Hello World",
            is_tool_result=True,
            tool_result_id="toolu_content_001",
        )

        conversation = FakeConversation([assistant_msg, result_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        assert "result_content" in metadata
        assert metadata["result_content"] == "Hello World"
        assert metadata["input_tokens"] == 1000

    def test_tool_metadata_can_override_token_fields(self):
        """Sanity check: merge order is {**token_metadata, **tool_metadata}."""
        usage = TokenUsage(input_tokens=999, output_tokens=888)
        bash_block = _make_tool_block("Bash", "toolu_override_001", {"command": "echo 999"})
        assistant_msg = _assistant_msg_with_blocks("asst-override-001", [bash_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        assert tool_events[0].metadata.get("command") == "echo 999"
        assert tool_events[0].metadata["input_tokens"] == 999


# ---------------------------------------------------------------------------
# 4. Regression Tests
# ---------------------------------------------------------------------------


class TestRegression:
    """Regression tests to ensure existing functionality is not broken."""

    def test_tool_call_still_has_tool_name_tool_id(self):
        """tool_name and tool_id still present after token metadata addition."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        bash_block = _make_tool_block("Bash", "toolu_reg_001", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks("asst-reg-001", [bash_block], usage=usage)

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        assert "tool_name" in metadata
        assert metadata["tool_name"] == "Bash"
        assert "tool_id" in metadata
        assert metadata["tool_id"] == "toolu_reg_001"

    def test_tool_call_still_has_result_merged(self):
        """has_result and result_content still work correctly."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        bash_block = _make_tool_block("Bash", "toolu_reg_result_001", {"command": "ls"})
        assistant_msg = _assistant_msg_with_blocks(
            "asst-reg-result-001", [bash_block], usage=usage
        )
        result_msg = _user_msg(
            "user-reg-result-001",
            "total 0\n-rw-r-- 1 user user 0 Jan  1 00:00 file.txt",
            is_tool_result=True,
            tool_result_id="toolu_reg_result_001",
        )

        conversation = FakeConversation([assistant_msg, result_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        assert metadata.get("has_result") is True
        assert "result_content" in metadata

    def test_subagent_tool_call_still_has_agent_id_agent_slug(self):
        """agent_id and agent_slug still added for subagent messages."""
        usage = TokenUsage(input_tokens=200, output_tokens=100)
        bash_block = _make_tool_block("Bash", "toolu_subagent_001", {"command": "ls"})
        assistant_msg = AssistantMessage(
            uuid="asst-subagent-001",
            timestamp=_TS,
            type="assistant",
            content_blocks=[bash_block],
            usage=usage,
            model="claude-sonnet-4-6",
            agent_id="agent-123",
            slug="my-session",
        )

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        tool_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(tool_events) == 1
        metadata = tool_events[0].metadata

        assert metadata.get("agent_id") == "agent-123"
        assert metadata.get("agent_slug") == "my-session"
        assert metadata["input_tokens"] == 200

    def test_user_prompt_event_does_not_get_token_metadata(self):
        """UserMessage does not receive token metadata (only AssistantMessage does)."""
        user_msg = _user_msg("user-prompt-001", "Please help me with this task")

        conversation = FakeConversation([user_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        for event in events:
            _assert_token_keys_absent(event.metadata)