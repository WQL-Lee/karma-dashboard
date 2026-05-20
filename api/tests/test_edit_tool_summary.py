"""
Unit tests for get_tool_summary() with Edit/StrReplace tool support.

Covers:
- Edit tool old_string and new_string extraction
- StrReplace alias behavior (same as Edit)
- Regression tests for other tools (Write, Read, Delete, Bash, etc.)

Run from api/ directory:
    python -m pytest tests/test_edit_tool_summary.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.content import ToolUseBlock
from utils import get_tool_summary


# =============================================================================
# Test Data
# =============================================================================

_TS = "2026-01-08T12:00:00Z"


def _make_block(name: str, tool_id: str = "toolu_test", input_dict: dict = None) -> ToolUseBlock:
    """Create a ToolUseBlock for testing."""
    return ToolUseBlock(
        type="tool_use",
        id=tool_id,
        name=name,
        input=input_dict or {},
    )


# =============================================================================
# Tests for Edit Tool
# =============================================================================

class TestGetToolSummaryEdit:
    """Tests for Edit tool old_string and new_string extraction."""

    def test_edit_with_old_and_new_string(self):
        """Edit with both old_string and new_string should be in metadata."""
        block = _make_block(
            "Edit",
            input_dict={
                "file_path": "/project/src/utils.py",
                "old_string": "def foo():",
                "new_string": "def bar():",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Edit file"
        assert "/project/src/utils.py" in summary or "src/utils.py" in summary
        assert metadata.get("old_string") == "def foo():"
        assert metadata.get("new_string") == "def bar():"
        assert metadata.get("path") == "/project/src/utils.py"

    def test_edit_with_only_old_string(self):
        """Edit with only old_string should work (new_string is empty)."""
        block = _make_block(
            "Edit",
            input_dict={
                "path": "/project/test.py",
                "old_string": "original content",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Edit file"
        assert metadata.get("old_string") == "original content"
        assert metadata.get("new_string") == ""
        assert metadata.get("path") == "/project/test.py"

    def test_edit_with_only_new_string(self):
        """Edit with only new_string should work (old_string is empty)."""
        block = _make_block(
            "Edit",
            input_dict={
                "path": "/project/test.py",
                "new_string": "new content only",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Edit file"
        assert metadata.get("old_string") == ""
        assert metadata.get("new_string") == "new content only"
        assert metadata.get("path") == "/project/test.py"

    def test_edit_with_empty_strings(self):
        """Edit with empty old_string and new_string should have empty strings in metadata."""
        block = _make_block(
            "Edit",
            input_dict={
                "path": "/project/test.py",
                "old_string": "",
                "new_string": "",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Edit file"
        assert metadata.get("old_string") == ""
        assert metadata.get("new_string") == ""

    def test_edit_with_file_path_key(self):
        """Edit using file_path key (alternative to path) should map to path."""
        block = _make_block(
            "Edit",
            input_dict={
                "file_path": "/project/config.json",
                "old_string": "old_value",
                "new_string": "new_value",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Edit file"
        assert metadata.get("path") == "/project/config.json"
        assert metadata.get("old_string") == "old_value"
        assert metadata.get("new_string") == "new_value"

    def test_edit_multiline_strings(self):
        """Edit with multiline old_string and new_string should preserve content."""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified\nline3"

        block = _make_block(
            "Edit",
            input_dict={
                "path": "/project/main.py",
                "old_string": old_content,
                "new_string": new_content,
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert metadata.get("old_string") == old_content
        assert metadata.get("new_string") == new_content

    def test_edit_with_special_characters(self):
        """Edit with special regex characters in old_string should be preserved."""
        old_string = "function (.*) { return $1; }"
        new_string = "function (.*) { return $2; }"

        block = _make_block(
            "Edit",
            input_dict={
                "path": "/project/test.js",
                "old_string": old_string,
                "new_string": new_string,
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert metadata.get("old_string") == old_string
        assert metadata.get("new_string") == new_string


class TestGetToolSummaryStrReplace:
    """Tests for StrReplace alias (should behave identically to Edit)."""

    def test_str_replace_with_old_and_new_string(self):
        """StrReplace with both old_string and new_string should be in metadata."""
        block = _make_block(
            "StrReplace",
            input_dict={
                "file_path": "/project/src/app.ts",
                "old_string": "export default",
                "new_string": "export",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Edit file"
        assert metadata.get("old_string") == "export default"
        assert metadata.get("new_string") == "export"
        assert metadata.get("path") == "/project/src/app.ts"

    def test_str_replace_alias_behaves_like_edit(self):
        """StrReplace should produce identical results to Edit with same input."""
        input_dict = {
            "path": "/project/file.py",
            "old_string": "old",
            "new_string": "new",
        }

        edit_block = _make_block("Edit", input_dict=input_dict.copy())
        str_replace_block = _make_block("StrReplace", input_dict=input_dict.copy())

        edit_result = get_tool_summary(edit_block, working_dirs=["/project"])
        str_replace_result = get_tool_summary(str_replace_block, working_dirs=["/project"])

        # Both should return same title, summary keys, and metadata keys
        assert edit_result[0] == str_replace_result[0]  # title
        assert edit_result[1] == str_replace_result[1]  # summary
        assert edit_result[2].keys() == str_replace_result[2].keys()  # metadata keys
        assert edit_result[2]["old_string"] == str_replace_result[2]["old_string"]
        assert edit_result[2]["new_string"] == str_replace_result[2]["new_string"]


# =============================================================================
# Regression Tests - Other Tools Unchanged
# =============================================================================

class TestGetToolSummaryRegression:
    """Regression tests to ensure other tools work correctly after Edit fix."""

    def test_read_tool_unchanged(self):
        """Read tool should still have path in metadata (no old_string/new_string)."""
        block = _make_block(
            "Read",
            input_dict={"file_path": "/project/src/index.js"},
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Read file"
        assert "path" in metadata
        assert metadata.get("path") == "/project/src/index.js"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_write_tool_unchanged(self):
        """Write tool should still have path and content in metadata."""
        block = _make_block(
            "Write",
            input_dict={
                "file_path": "/project/src/new.py",
                "content": "print('hello')",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Write file"
        assert metadata.get("path") == "/project/src/new.py"
        assert metadata.get("content") == "print('hello')"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_delete_tool_unchanged(self):
        """Delete tool should still have path in metadata."""
        block = _make_block(
            "Delete",
            input_dict={"file_path": "/project/temp.txt"},
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Delete file"
        assert metadata.get("path") == "/project/temp.txt"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_bash_tool_unchanged(self):
        """Bash tool should still have command in metadata."""
        block = _make_block(
            "Bash",
            input_dict={"command": "ls -la /project"},
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Run command"
        assert metadata.get("command") == "ls -la /project"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_glob_tool_unchanged(self):
        """Glob tool should still have pattern in metadata."""
        block = _make_block(
            "Glob",
            input_dict={"pattern": "**/*.py"},
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Search files"
        assert metadata.get("pattern") == "**/*.py"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_grep_tool_unchanged(self):
        """Grep tool should still have pattern and path in metadata."""
        block = _make_block(
            "Grep",
            input_dict={
                "pattern": "def main",
                "path": "/project/src",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Search content"
        assert metadata.get("pattern") == "def main"
        # path is relativized (to_relative), so /project/src becomes src
        assert "path" in metadata
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_ls_tool_unchanged(self):
        """LS tool should still have path in metadata."""
        block = _make_block(
            "LS",
            input_dict={"target_directory": "/project/src"},
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "List directory"
        assert metadata.get("path") == "/project/src"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_task_tool_unchanged(self):
        """Task tool should still have description and subagent_type in metadata."""
        block = _make_block(
            "Task",
            input_dict={
                "description": "Analyze the codebase",
                "subagent_type": "research",
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Spawn subagent"
        assert metadata.get("description") == "Analyze the codebase"
        assert metadata.get("subagent_type") == "research"
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_todowrite_tool_unchanged(self):
        """TodoWrite tool should still have todos in metadata."""
        block = _make_block(
            "TodoWrite",
            input_dict={
                "todos": [{"content": "Test", "status": "in_progress"}],
                "merge": False,
            },
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        # Title is "Set N todo(s)" for merge=False, "Update todos" for merge=True
        assert "todo" in title.lower()
        assert "todos" in metadata
        assert "old_string" not in metadata
        assert "new_string" not in metadata

    def test_websearch_tool_unchanged(self):
        """WebSearch tool should still have search_term in metadata."""
        block = _make_block(
            "WebSearch",
            input_dict={"search_term": "python async tutorial"},
        )

        title, summary, metadata = get_tool_summary(block, working_dirs=["/project"])

        assert title == "Web search"
        # WebSearch uses search_term key, not query
        assert metadata.get("search_term") == "python async tutorial"
        assert "old_string" not in metadata
        assert "new_string" not in metadata