"""Tests for from_dict() text stripping behavior (Issue #4426).

These tests verify that from_dict() strips text before assignment,
consistent with CLI.add() and rename() behavior.

Related:
- src/flywheel/todo.py:51 - rename() does text = text.strip()
- src/flywheel/cli.py:26 - CLI.add() does text = text.strip()
- src/flywheel/todo.py:98 - from_dict passes raw data['text'] without strip (BUG)
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFromDictTextStripping:
    """Tests for Issue #4426 - from_dict() should strip text before assignment."""

    def test_from_dict_strips_leading_trailing_whitespace(self) -> None:
        """from_dict() should strip leading and trailing whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  hello  "})
        assert todo.text == "hello"

    def test_from_dict_strips_leading_whitespace(self) -> None:
        """from_dict() should strip leading whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "   task"})
        assert todo.text == "task"

    def test_from_dict_strips_trailing_whitespace(self) -> None:
        """from_dict() should strip trailing whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "task   "})
        assert todo.text == "task"

    def test_from_dict_strips_tabs_and_newlines(self) -> None:
        """from_dict() should strip tabs and newlines from text."""
        todo = Todo.from_dict({"id": 1, "text": "\t\n  task  \n\t"})
        assert todo.text == "task"

    def test_from_dict_preserves_internal_whitespace(self) -> None:
        """from_dict() should preserve internal whitespace in text."""
        todo = Todo.from_dict({"id": 1, "text": "  hello world  "})
        assert todo.text == "hello world"

    def test_from_dict_raises_on_whitespace_only_text(self) -> None:
        """from_dict() should raise ValueError when text is only whitespace."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_raises_on_empty_text(self) -> None:
        """from_dict() should raise ValueError when text is empty string."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo.from_dict({"id": 1, "text": ""})


class TestFromDictRoundtrip:
    """Tests for save/load roundtrip behavior with stripped text."""

    def test_save_load_preserves_stripped_text(self, tmp_path) -> None:
        """Roundtrip save/load should preserve stripped text."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create todo with whitespace (simulating external JSON file edit)
        db.write_text('[{"id": 1, "text": "  padded task  ", "done": false}]', encoding="utf-8")

        # Load via storage (which uses from_dict)
        todos = storage.load()

        # Text should be stripped
        assert todos[0].text == "padded task"

    def test_to_dict_from_dict_preserves_text(self) -> None:
        """to_dict() then from_dict() should preserve the stripped text value."""
        original = Todo(id=1, text="hello world")
        data = original.to_dict()
        loaded = Todo.from_dict(data)

        assert loaded.text == "hello world"
