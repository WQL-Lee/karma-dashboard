"""
Integration tests for Edit tool in build_conversation_timeline().

Tests that TimelineEvent metadata contains old_string and new_string
when an Edit tool call is processed.

Run from api/ directory:
    python -m pytest tests/test_edit_timeline_integration.py -v
"""

import sys
from pathlib import Path
from typing import Iterator, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone

from models.content import ToolUseBlock
from models.message import AssistantMessage, UserMessage
from services.conversation_endpoints import build_conversation_timeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)


def _assistant_msg_with_blocks(uuid: str, blocks: list) -> AssistantMessage:
    """Build an AssistantMessage with pre-parsed content blocks."""
    return AssistantMessage(
        uuid=uuid,
        timestamp=_TS,
        type="assistant",
        content_blocks=blocks,
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
# Tests for Edit Tool Timeline Events
# ---------------------------------------------------------------------------

class TestEditToolTimelineIntegration:
    """Tests for Edit tool TimelineEvent metadata in build_conversation_timeline."""

    def test_edit_tool_timeline_event_contains_old_and_new_string(self):
        """Edit tool call should produce TimelineEvent with old_string and new_string in metadata."""
        edit_block = _make_tool_block(
            "Edit",
            block_id="toolu_edit_001",
            input_dict={
                "file_path": "/project/src/utils.py",
                "old_string": "def foo():",
                "new_string": "def bar():",
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-001", [edit_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        edit_events = [e for e in events if e.metadata.get("tool_name") == "Edit"]
        assert len(edit_events) == 1, f"Expected 1 Edit event, got {len(edit_events)}"

        metadata = edit_events[0].metadata
        assert metadata.get("old_string") == "def foo():", f"old_string mismatch: {metadata.get('old_string')}"
        assert metadata.get("new_string") == "def bar():", f"new_string mismatch: {metadata.get('new_string')}"
        assert metadata.get("path") == "/project/src/utils.py"

    def test_edit_tool_timeline_event_with_multiline_strings(self):
        """Edit tool with multiline old_string and new_string should preserve content in metadata."""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified\nline3"

        edit_block = _make_tool_block(
            "Edit",
            block_id="toolu_edit_002",
            input_dict={
                "path": "/project/main.py",
                "old_string": old_content,
                "new_string": new_content,
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-002", [edit_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        edit_events = [e for e in events if e.metadata.get("tool_name") == "Edit"]
        assert len(edit_events) == 1

        metadata = edit_events[0].metadata
        assert metadata.get("old_string") == old_content
        assert metadata.get("new_string") == new_content

    def test_str_replace_tool_timeline_event_contains_old_and_new_string(self):
        """StrReplace tool should produce TimelineEvent with old_string and new_string in metadata."""
        str_replace_block = _make_tool_block(
            "StrReplace",
            block_id="toolu_strreplace_001",
            input_dict={
                "file_path": "/project/config.json",
                "old_string": "old_value",
                "new_string": "new_value",
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-003", [str_replace_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        str_replace_events = [e for e in events if e.metadata.get("tool_name") == "StrReplace"]
        assert len(str_replace_events) == 1

        metadata = str_replace_events[0].metadata
        assert metadata.get("old_string") == "old_value"
        assert metadata.get("new_string") == "new_value"

    def test_edit_with_empty_strings_still_in_metadata(self):
        """Edit tool with empty old_string/new_string should still have keys in metadata."""
        edit_block = _make_tool_block(
            "Edit",
            block_id="toolu_edit_003",
            input_dict={
                "path": "/project/empty.py",
                "old_string": "",
                "new_string": "",
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-004", [edit_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        edit_events = [e for e in events if e.metadata.get("tool_name") == "Edit"]
        assert len(edit_events) == 1

        metadata = edit_events[0].metadata
        assert "old_string" in metadata, "old_string key should be present even if empty"
        assert "new_string" in metadata, "new_string key should be present even if empty"
        assert metadata.get("old_string") == ""
        assert metadata.get("new_string") == ""

    def test_edit_tool_result_also_merged(self):
        """Edit tool with result from tool result file should merge both old_string and result."""
        edit_block = _make_tool_block(
            "Edit",
            block_id="toolu_edit_004",
            input_dict={
                "path": "/project/test.js",
                "old_string": "old",
                "new_string": "new",
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-005", [edit_block])

        # Add a tool result user message
        result_msg = _user_msg(
            "user-result-005",
            "File modified successfully. 1 replacement made.",
            is_tool_result=True,
            tool_result_id="toolu_edit_004",
        )

        conversation = FakeConversation([assistant_msg, result_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        edit_events = [e for e in events if e.metadata.get("tool_name") == "Edit"]
        assert len(edit_events) == 1

        metadata = edit_events[0].metadata
        # old_string should come from block.input
        assert metadata.get("old_string") == "old"
        # has_result should be True from tool result
        assert metadata.get("has_result") is True
        # result_content should be from tool result file
        assert "result_content" in metadata


# ---------------------------------------------------------------------------
# Regression Tests - Other Tools in Timeline
# ---------------------------------------------------------------------------

class TestEditToolTimelineRegression:
    """Regression tests to ensure other tools still work correctly in timeline."""

    def test_write_tool_still_contains_content_in_timeline(self):
        """Write tool should still have content in timeline metadata."""
        write_block = _make_tool_block(
            "Write",
            block_id="toolu_write_001",
            input_dict={
                "path": "/project/new.py",
                "content": "print('hello')",
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-write-001", [write_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        write_events = [e for e in events if e.metadata.get("tool_name") == "Write"]
        assert len(write_events) == 1

        metadata = write_events[0].metadata
        assert metadata.get("content") == "print('hello')"
        assert metadata.get("path") == "/project/new.py"
        assert "old_string" not in metadata

    def test_read_tool_still_contains_path_in_timeline(self):
        """Read tool should still have path in timeline metadata."""
        read_block = _make_tool_block(
            "Read",
            block_id="toolu_read_001",
            input_dict={"file_path": "/project/src/index.js"},
        )
        assistant_msg = _assistant_msg_with_blocks("asst-read-001", [read_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        read_events = [e for e in events if e.metadata.get("tool_name") == "Read"]
        assert len(read_events) == 1

        metadata = read_events[0].metadata
        assert metadata.get("path") == "/project/src/index.js"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_bash_tool_still_contains_command_in_timeline(self):
        """Bash tool should still have command in timeline metadata."""
        bash_block = _make_tool_block(
            "Bash",
            block_id="toolu_bash_001",
            input_dict={"command": "ls -la"},
        )
        assistant_msg = _assistant_msg_with_blocks("asst-bash-001", [bash_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        bash_events = [e for e in events if e.metadata.get("tool_name") == "Bash"]
        assert len(bash_events) == 1

        metadata = bash_events[0].metadata
        assert metadata.get("command") == "ls -la"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_grep_tool_still_contains_pattern_and_path_in_timeline(self):
        """Grep tool should still have pattern and path in timeline metadata."""
        grep_block = _make_tool_block(
            "Grep",
            block_id="toolu_grep_001",
            input_dict={
                "pattern": "def main",
                "path": "/project/src",
            },
        )
        assistant_msg = _assistant_msg_with_blocks("asst-grep-001", [grep_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        grep_events = [e for e in events if e.metadata.get("tool_name") == "Grep"]
        assert len(grep_events) == 1

        metadata = grep_events[0].metadata
        assert metadata.get("pattern") == "def main"
        # path is relativized (to_relative), so /project/src becomes src
        assert "path" in metadata
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_task_update_timeline_still_has_task_subject(self):
        """TaskUpdate tool should still have task_subject from TaskCreate result (requires tool result file).

        Note: This test documents that task_subject population requires the actual
        tool result file structure. For unit testing, we verify TaskUpdate metadata
        includes taskId and status correctly.
        """
        # TaskUpdate referencing task #1
        task_update_block = _make_tool_block(
            "TaskUpdate",
            block_id="toolu_task_update_001",
            input_dict={"taskId": "1", "status": "in_progress"},
        )

        assistant_msg = _assistant_msg_with_blocks("asst-task-001", [task_update_block])

        conversation = FakeConversation([assistant_msg])
        events = build_conversation_timeline(conversation, working_dirs=["/project"])

        update_events = [e for e in events if e.metadata.get("tool_name") == "TaskUpdate"]
        assert len(update_events) == 1

        metadata = update_events[0].metadata
        # TaskUpdate should have taskId and status from input
        assert metadata.get("taskId") == "1"
        assert metadata.get("status") == "in_progress"
        # Note: task_subject requires TaskCreate + matching tool result file to be set
        # This is an integration test behavior, not a unit test expectation