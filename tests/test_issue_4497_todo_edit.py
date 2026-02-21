"""Tests for Todo.edit() method (Issue #4497).

These tests verify that:
1. todo.edit(text='new') only updates text and updated_at
2. todo.edit(done=True) only updates done and updated_at
3. todo.edit(text='a', done=True) updates both fields and updated_at
4. todo.edit() with no args makes no changes and doesn't update updated_at
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEditText:
    """Tests for Todo.edit() with text parameter."""

    def test_edit_text_updates_text(self) -> None:
        """edit(text='new') should update text field."""
        todo = Todo(id=1, text="original")
        todo.edit(text="new text")

        assert todo.text == "new text"

    def test_edit_text_updates_updated_at(self) -> None:
        """edit(text='new') should update updated_at timestamp."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        todo.edit(text="new text")

        assert todo.updated_at > original_updated_at

    def test_edit_text_preserves_done_state(self) -> None:
        """edit(text='new') should not change done field."""
        todo = Todo(id=1, text="original", done=True)
        todo.edit(text="new text")

        assert todo.done is True

    def test_edit_text_strips_whitespace(self) -> None:
        """edit(text='  padded  ') should strip whitespace like rename()."""
        todo = Todo(id=1, text="original")
        todo.edit(text="  padded  ")

        assert todo.text == "padded"

    def test_edit_text_rejects_empty_string(self) -> None:
        """edit(text='') should raise ValueError."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.edit(text="")

        # State should remain unchanged
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_edit_text_rejects_whitespace_only(self) -> None:
        """edit(text='  ') should raise ValueError."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.edit(text="   ")

        # State should remain unchanged
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at


class TestTodoEditDone:
    """Tests for Todo.edit() with done parameter."""

    def test_edit_done_true_updates_done(self) -> None:
        """edit(done=True) should update done field to True."""
        todo = Todo(id=1, text="original", done=False)
        todo.edit(done=True)

        assert todo.done is True

    def test_edit_done_false_updates_done(self) -> None:
        """edit(done=False) should update done field to False."""
        todo = Todo(id=1, text="original", done=True)
        todo.edit(done=False)

        assert todo.done is False

    def test_edit_done_updates_updated_at(self) -> None:
        """edit(done=True) should update updated_at timestamp."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        todo.edit(done=True)

        assert todo.updated_at > original_updated_at

    def test_edit_done_preserves_text(self) -> None:
        """edit(done=True) should not change text field."""
        todo = Todo(id=1, text="original")
        todo.edit(done=True)

        assert todo.text == "original"


class TestTodoEditBoth:
    """Tests for Todo.edit() with both text and done parameters."""

    def test_edit_both_updates_both_fields(self) -> None:
        """edit(text='a', done=True) should update both fields."""
        todo = Todo(id=1, text="original", done=False)
        todo.edit(text="new text", done=True)

        assert todo.text == "new text"
        assert todo.done is True

    def test_edit_both_updates_updated_at_once(self) -> None:
        """edit(text='a', done=True) should update updated_at only once."""
        todo = Todo(id=1, text="original", done=False)
        original_updated_at = todo.updated_at

        todo.edit(text="new text", done=True)

        assert todo.updated_at > original_updated_at


class TestTodoEditNoArgs:
    """Tests for Todo.edit() with no arguments."""

    def test_edit_no_args_makes_no_changes(self) -> None:
        """edit() with no arguments should not change any field."""
        todo = Todo(id=1, text="original", done=True)
        todo.edit()

        assert todo.text == "original"
        assert todo.done is True

    def test_edit_no_args_does_not_update_updated_at(self) -> None:
        """edit() with no arguments should not update updated_at."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        todo.edit()

        assert todo.updated_at == original_updated_at
