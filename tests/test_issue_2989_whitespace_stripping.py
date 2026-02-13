"""Test for issue #2989: Todo.__init__ should strip whitespace from text.

This test file ensures that whitespace handling is consistent across:
- Todo.__init__
- Todo.rename()
- TodoApp.add()
- Todo.from_dict()
"""

import tempfile

from flywheel.cli import TodoApp
from flywheel.todo import Todo


class TestTodoInitStripsWhitespace:
    """Bug #2989: Todo.__init__ should strip whitespace from text."""

    def test_todo_init_strips_leading_whitespace(self) -> None:
        """Todo constructor should strip leading whitespace."""
        todo = Todo(id=1, text="  hello")
        assert todo.text == "hello", f"Expected 'hello', got {todo.text!r}"

    def test_todo_init_strips_trailing_whitespace(self) -> None:
        """Todo constructor should strip trailing whitespace."""
        todo = Todo(id=1, text="hello  ")
        assert todo.text == "hello", f"Expected 'hello', got {todo.text!r}"

    def test_todo_init_strips_both_whitespace(self) -> None:
        """Todo constructor should strip both leading and trailing whitespace."""
        todo = Todo(id=1, text="  hello  ")
        assert todo.text == "hello", f"Expected 'hello', got {todo.text!r}"

    def test_todo_init_strips_tabs(self) -> None:
        """Todo constructor should strip tabs."""
        todo = Todo(id=1, text="\thello\t")
        assert todo.text == "hello", f"Expected 'hello', got {todo.text!r}"

    def test_todo_init_strips_mixed_whitespace(self) -> None:
        """Todo constructor should strip mixed whitespace."""
        todo = Todo(id=1, text=" \t hello \n ")
        assert todo.text == "hello", f"Expected 'hello', got {todo.text!r}"


class TestTodoFromDictStripsWhitespace:
    """Bug #2989: Todo.from_dict should strip whitespace from text."""

    def test_from_dict_strips_whitespace(self) -> None:
        """Todo.from_dict should strip whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  padded  "})
        assert todo.text == "padded", f"Expected 'padded', got {todo.text!r}"


class TestTodoAppAddStripsWhitespace:
    """Verify TodoApp.add() strips whitespace (existing behavior)."""

    def test_app_add_strips_whitespace(self) -> None:
        """TodoApp.add() should strip whitespace from text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/.todo.json"
            app = TodoApp(db_path=db_path)
            todo = app.add("  padded  ")
            assert todo.text == "padded", f"Expected 'padded', got {todo.text!r}"


class TestTodoRenameStripsWhitespace:
    """Verify Todo.rename() strips whitespace (existing behavior)."""

    def test_rename_strips_whitespace(self) -> None:
        """Todo.rename() should strip whitespace from text."""
        todo = Todo(id=1, text="original")
        todo.rename("  renamed  ")
        assert todo.text == "renamed", f"Expected 'renamed', got {todo.text!r}"
