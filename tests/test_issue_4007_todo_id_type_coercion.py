"""Tests for Todo id type coercion (Issue #4007).

These tests verify that:
1. Todo constructor coerces float id values to int
2. Todo.id is always an int type
3. Direct construction behaves consistently with from_dict
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_id_coerces_float_to_int() -> None:
    """Todo(id=1.5, text='test') should store id as int 1."""
    todo = Todo(id=1.5, text="test")
    assert todo.id == 1
    assert isinstance(todo.id, int)


def test_todo_id_is_int_type_for_int_input() -> None:
    """isinstance(Todo(id=1, text='x').id, int) should be True."""
    todo = Todo(id=1, text="x")
    assert isinstance(todo.id, int)
    assert todo.id == 1


def test_todo_id_coerces_string_number_via_from_dict() -> None:
    """Todo.from_dict({'id': '5', 'text': 'test'}).id should equal 5."""
    todo = Todo.from_dict({"id": "5", "text": "test"})
    assert todo.id == 5
    assert isinstance(todo.id, int)


def test_todo_id_coerces_float_zero_to_int() -> None:
    """Todo(id=0.0, text='test') should store id as int 0."""
    todo = Todo(id=0.0, text="test")
    assert todo.id == 0
    assert isinstance(todo.id, int)


def test_todo_id_preserves_negative_int() -> None:
    """Todo should preserve negative int values."""
    todo = Todo(id=-1, text="test")
    assert todo.id == -1
    assert isinstance(todo.id, int)


def test_todo_id_coerces_large_float_to_int() -> None:
    """Todo should truncate large float values to int."""
    todo = Todo(id=123.456, text="test")
    assert todo.id == 123
    assert isinstance(todo.id, int)


def test_direct_construction_matches_from_dict_behavior() -> None:
    """Direct construction with float id should match from_dict behavior."""
    direct_todo = Todo(id=1.5, text="test")
    from_dict_todo = Todo.from_dict({"id": 1.5, "text": "test"})

    assert direct_todo.id == from_dict_todo.id
    assert isinstance(direct_todo.id, int)
    assert isinstance(from_dict_todo.id, int)
