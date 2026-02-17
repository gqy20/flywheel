"""Regression tests for issue #4007: Todo constructor float id coercion.

Bug: Todo constructor accepts float id values silently, breaking type contract.
Fix: Add type coercion in __post_init__ to ensure id is always an int.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_constructor_coerces_float_id_to_int() -> None:
    """Bug #4007: Todo(id=1.5, text='test') should store id as int 1."""
    todo = Todo(id=1.5, text="test")
    assert todo.id == 1
    assert isinstance(todo.id, int)


def test_todo_constructor_preserves_int_id() -> None:
    """Bug #4007: Todo(id=1, text='test').id should remain int type."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert isinstance(todo.id, int)


def test_todo_from_dict_coerces_string_id() -> None:
    """Bug #4007: from_dict({'id': '5', ...}) should convert string to int 5."""
    todo = Todo.from_dict({"id": "5", "text": "test"})
    assert todo.id == 5
    assert isinstance(todo.id, int)


def test_todo_from_dict_coerces_float_id() -> None:
    """Bug #4007: from_dict({'id': 3.7, ...}) should convert float to int 3."""
    todo = Todo.from_dict({"id": 3.7, "text": "test"})
    assert todo.id == 3
    assert isinstance(todo.id, int)


def test_todo_constructor_coerces_string_numeric_id() -> None:
    """Bug #4007: Todo(id='42', text='test') should coerce string to int 42."""
    todo = Todo(id="42", text="test")
    assert todo.id == 42
    assert isinstance(todo.id, int)
