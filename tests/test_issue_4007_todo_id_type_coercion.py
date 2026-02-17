"""Regression tests for issue #4007: Todo id type coercion.

The Todo constructor should enforce the int type contract for the id field.
When a float is passed, it should be coerced to int.
"""

import pytest

from flywheel.todo import Todo


class TestTodoIdTypeCoercion:
    """Test that Todo constructor coerces id to int."""

    def test_todo_with_float_id_coerces_to_int(self) -> None:
        """Todo(id=1.5, text='test') should store id as int 1."""
        todo = Todo(id=1.5, text="test")
        assert todo.id == 1
        assert isinstance(todo.id, int)

    def test_todo_with_int_id_preserves_int(self) -> None:
        """Todo(id=1, text='test').id should be int."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert isinstance(todo.id, int)

    def test_todo_with_string_numeric_id_in_from_dict(self) -> None:
        """Todo.from_dict({'id': '5', 'text': 'test'}).id == 5."""
        todo = Todo.from_dict({"id": "5", "text": "test"})
        assert todo.id == 5
        assert isinstance(todo.id, int)

    def test_todo_with_float_id_in_from_dict(self) -> None:
        """Todo.from_dict with float id should be coerced to int."""
        todo = Todo.from_dict({"id": 3.7, "text": "test"})
        assert todo.id == 3
        assert isinstance(todo.id, int)
