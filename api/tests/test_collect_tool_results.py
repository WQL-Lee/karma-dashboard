"""
Unit tests for collect_tool_results function.

Tests:
1. Read tool content is NOT truncated (returns full content)
2. Other tools are truncated to 500 chars (or 2000 for AskUserQuestion)
3. Read tool can read from tool_results_dir when available
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from typing import Iterator, List

from models.content import ToolUseBlock
from models.message import AssistantMessage, UserMessage
from utils import collect_tool_results


_TS = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)


def _user_msg(
    uuid: str,
    content: str,
    *,
    is_tool_result: bool = False,
    tool_result_id: str | None = None,
) -> UserMessage:
    return UserMessage(
        uuid=uuid,
        timestamp=_TS,
        type="user",
        content=content,
        is_tool_result=is_tool_result,
        tool_result_id=tool_result_id,
    )


def _assistant_msg_with_blocks(uuid: str, blocks: list) -> AssistantMessage:
    return AssistantMessage(
        uuid=uuid,
        timestamp=_TS,
        type="assistant",
        content_blocks=blocks,
    )


def _read_block(block_id: str, file_path: str = "/test/file.txt") -> ToolUseBlock:
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name="Read",
        input={"file_path": file_path},
    )


def _write_block(block_id: str, file_path: str = "/test/output.txt") -> ToolUseBlock:
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name="Write",
        input={"file_path": file_path, "content": "test"},
    )


def _bash_block(block_id: str, command: str = "echo test") -> ToolUseBlock:
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name="Bash",
        input={"command": command},
    )


class FakeConversation:
    def __init__(self, messages: List):
        self._messages = messages

    def iter_messages(self) -> Iterator:
        return iter(self._messages)


class TestReadToolNotTruncated:
    """Read tool should return full content without truncation."""

    def test_read_tool_returns_full_content(self):
        """Read tool result should NOT be truncated to 500 chars."""
        block_id = "toolu_read_001"
        # Create content longer than 500 chars
        long_content = "x" * 1000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_read_block(block_id)]),
            _user_msg(
                "user-result-001",
                long_content,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert results[block_id].content == long_content
        assert len(results[block_id].content) == 1000

    def test_read_tool_with_very_long_content(self):
        """Read tool should handle very long content (several KB)."""
        block_id = "toolu_read_002"
        # Create content much longer than 500 chars
        long_content = "line\n" * 2000  # ~8KB

        messages = [
            _assistant_msg_with_blocks("asst-001", [_read_block(block_id)]),
            _user_msg(
                "user-result-001",
                long_content,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert results[block_id].content == long_content
        # Content should not be truncated
        assert len(results[block_id].content) == len(long_content)


class TestOtherToolsTruncated:
    """Other tools (Write, Bash, etc.) should still be truncated."""

    def test_write_tool_truncated_to_500(self):
        """Write tool result should be truncated to 500 chars."""
        block_id = "toolu_write_001"
        long_content = "x" * 1000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_write_block(block_id)]),
            _user_msg(
                "user-result-001",
                long_content,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert len(results[block_id].content) == 500

    def test_bash_tool_truncated_to_500(self):
        """Bash tool result should be truncated to 500 chars."""
        block_id = "toolu_bash_001"
        long_content = "x" * 1000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_bash_block(block_id)]),
            _user_msg(
                "user-result-001",
                long_content,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert len(results[block_id].content) == 500


class TestReadToolWithFileFallback:
    """Read tool should use file content when tool_results_dir provided."""

    def test_read_tool_uses_jsonl_content_when_no_file(self):
        """Read tool should use JSONL content when no file exists."""
        block_id = "toolu_read_003"
        jsonl_content = "content from JSONL"

        messages = [
            _assistant_msg_with_blocks("asst-001", [_read_block(block_id)]),
            _user_msg(
                "user-result-001",
                jsonl_content,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation, tool_results_dir=Path("/nonexistent"))

        assert block_id in results
        assert results[block_id].content == jsonl_content