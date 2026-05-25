"""
Unit tests for collect_tool_results function.

Tests:
1. Read tool content is NOT truncated (returns full content)
2. Write, Bash, Edit, Shell tools are NOT truncated (return full content)
3. AskUserQuestion results are truncated to 2000 chars
4. Read tool can read from tool_results_dir when available
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


def _generic_block(block_id: str, tool_name: str = "Bash") -> ToolUseBlock:
    """Generic tool block for testing AskUserQuestion truncation."""
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name=tool_name,
        input={"command": "test"},
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


def _edit_block(block_id: str, file_path: str = "/test/file.txt") -> ToolUseBlock:
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name="Edit",
        input={"file_path": file_path, "old_string": "old", "new_string": "new"},
    )


def _shell_block(block_id: str, command: str = "echo test") -> ToolUseBlock:
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name="Shell",
        input={"command": command},
    )


def _notebook_edit_block(block_id: str) -> ToolUseBlock:
    return ToolUseBlock(
        type="tool_use",
        id=block_id,
        name="NotebookEdit",
        input={"file_path": "/test/notebook.ipynb", "cell_index": 0},
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


class TestWriteToolNotTruncated:
    """Write tool should return full content without truncation."""

    def test_write_tool_returns_full_content(self):
        """Write tool result should NOT be truncated."""
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
        assert results[block_id].content == long_content
        assert len(results[block_id].content) == 1000

    def test_write_tool_with_very_long_content(self):
        """Write tool should handle multi-KB content without truncation."""
        block_id = "toolu_write_002"
        long_content = "x" * 5000  # 5KB

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
        assert results[block_id].content == long_content
        assert len(results[block_id].content) == 5000


class TestBashToolNotTruncated:
    """Bash tool should return full content without truncation."""

    def test_bash_tool_returns_full_content(self):
        """Bash tool result should NOT be truncated."""
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
        assert results[block_id].content == long_content
        assert len(results[block_id].content) == 1000

    def test_bash_tool_with_very_long_output(self):
        """Bash tool with output exceeding 5000 chars should not be truncated."""
        block_id = "toolu_bash_002"
        long_output = "output\n" * 2000  # ~12KB

        messages = [
            _assistant_msg_with_blocks("asst-001", [_bash_block(block_id)]),
            _user_msg(
                "user-result-001",
                long_output,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert results[block_id].content == long_output
        assert len(results[block_id].content) == len(long_output)


class TestEditToolNotTruncated:
    """Edit tool should return full content without truncation."""

    def test_edit_tool_returns_full_content(self):
        """Edit tool result should NOT be truncated."""
        block_id = "toolu_edit_001"
        long_content = "x" * 1000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_edit_block(block_id)]),
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


class TestShellToolNotTruncated:
    """Shell tool should return full content without truncation."""

    def test_shell_tool_returns_full_content(self):
        """Shell tool result should NOT be truncated."""
        block_id = "toolu_shell_001"
        long_content = "x" * 1000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_shell_block(block_id)]),
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


class TestNotebookEditToolNotTruncated:
    """NotebookEdit tool should return full content without truncation."""

    def test_notebook_edit_tool_returns_full_content(self):
        """NotebookEdit tool result should NOT be truncated."""
        block_id = "toolu_nb_001"
        long_content = "x" * 1000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_notebook_edit_block(block_id)]),
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


class TestAskUserQuestionTruncated:
    """AskUserQuestion results should be truncated to 2000 chars."""

    def test_ask_user_question_truncated_to_2000(self):
        """AskUserQuestion result should be truncated to 2000 chars.

        Note: AskUserQuestion is only detected for non-Read tools.
        The detection is based on "has answered your questions" (lowercase) in first 60 chars.
        """
        block_id = "toolu_ask_001"
        # Create content with the detection phrase at the start (lowercase 'has')
        long_content = "has answered your questions about the project setup. " + "x" * 3000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_generic_block(block_id, "Bash")]),
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
        assert len(results[block_id].content) == 2000

    def test_ask_user_question_not_truncated_when_under_2000(self):
        """AskUserQuestion content under 2000 chars should not be truncated."""
        block_id = "toolu_ask_002"
        # Content with detection phrase (lowercase 'has') but under 2000 chars
        short_content = "has answered your questions. " + "x" * 100

        messages = [
            _assistant_msg_with_blocks("asst-001", [_generic_block(block_id, "Bash")]),
            _user_msg(
                "user-result-001",
                short_content,
                is_tool_result=True,
                tool_result_id=block_id,
            ),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert len(results[block_id].content) == len(short_content)


class TestAskUserQuestionDetection:
    """Test AskUserQuestion detection logic (first 60 chars check)."""

    def test_ask_user_detected_by_has_answered_string(self):
        """AskUserQuestion is detected by 'has answered your questions' (lowercase) in first 60 chars."""
        block_id = "toolu_ask_003"
        # Content with the detection phrase (lowercase 'has')
        content = "has answered your questions about the project setup. " + "x" * 2000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_generic_block(block_id, "Bash")]),
            _user_msg("user-result-001", content, is_tool_result=True, tool_result_id=block_id),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert len(results[block_id].content) == 2000  # truncated

    def test_ask_user_not_detected_if_phrase_after_60_chars(self):
        """If 'has answered your questions' appears after 60 chars, NOT treated as AskUserQuestion."""
        block_id = "toolu_ask_004"
        # Place detection phrase beyond 60 char limit
        content = "x" * 65 + "has answered your questions" + "y" * 3000

        messages = [
            _assistant_msg_with_blocks("asst-001", [_generic_block(block_id, "Bash")]),
            _user_msg("user-result-001", content, is_tool_result=True, tool_result_id=block_id),
        ]

        conversation = FakeConversation(messages)
        results = collect_tool_results(conversation)

        assert block_id in results
        assert len(results[block_id].content) == len(content)  # NOT truncated


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