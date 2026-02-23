"""Test for issue #5353: to_dict() return type missing generic annotations.

This test verifies that the type annotations are correct and consistent
between to_dict() and from_dict() methods.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_to_dict_has_proper_type_annotation() -> None:
    """Verify to_dict() returns dict[str, int | str | bool] (issue #5353)."""
    todo = Todo(id=1, text="test todo", done=False)
    result = todo.to_dict()

    # Verify the return type is a dict
    assert isinstance(result, dict)

    # Verify the keys and their types match expected schema
    assert "id" in result
    assert isinstance(result["id"], int)

    assert "text" in result
    assert isinstance(result["text"], str)

    assert "done" in result
    assert isinstance(result["done"], bool)

    assert "created_at" in result
    assert isinstance(result["created_at"], str)

    assert "updated_at" in result
    assert isinstance(result["updated_at"], str)


def test_from_dict_accepts_proper_type() -> None:
    """Verify from_dict() accepts dict[str, int | str | bool] (issue #5353)."""
    data: dict[str, int | str | bool] = {
        "id": 1,
        "text": "test todo",
        "done": True,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.text == "test todo"
    assert todo.done is True


def test_roundtrip_to_dict_from_dict_type_consistency() -> None:
    """Verify to_dict() -> from_dict() roundtrip has consistent types (issue #5353)."""
    original = Todo(id=42, text="roundtrip test", done=True)
    result = original.to_dict()

    # The result should be usable directly with from_dict
    restored = Todo.from_dict(result)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
