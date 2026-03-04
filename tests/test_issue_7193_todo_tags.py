"""Tests for Todo tags/categories field (Issue #7193).

These tests verify that:
1. Todo has a tags field as immutable tuple
2. Empty tuple is default, tags are preserved via serialization
3. Tags are normalized (stripped, lowercase) on creation
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_tags_field_with_default_empty_tuple() -> None:
    """Todo should have tags field defaulting to empty tuple."""
    todo = Todo(id=1, text="buy milk")

    assert hasattr(todo, "tags")
    assert todo.tags == ()
    assert isinstance(todo.tags, tuple)


def test_todo_tags_stored_as_immutable_tuple() -> None:
    """Todo tags should be stored as immutable tuple."""
    todo = Todo(id=1, text="buy milk", tags=["work", "urgent"])

    assert isinstance(todo.tags, tuple)
    assert todo.tags == ("work", "urgent")


def test_todo_tags_normalized_lowercase() -> None:
    """Todo tags should be normalized to lowercase."""
    todo = Todo(id=1, text="buy milk", tags=["Work", "URGENT", "Personal"])

    assert todo.tags == ("work", "urgent", "personal")


def test_todo_tags_normalized_stripped() -> None:
    """Todo tags should have whitespace stripped."""
    todo = Todo(id=1, text="buy milk", tags=[" work ", "  urgent  ", "\tpersonal\n"])

    assert todo.tags == ("work", "urgent", "personal")


def test_todo_tags_normalized_combined() -> None:
    """Todo tags should be both stripped and lowercased."""
    todo = Todo(id=1, text="buy milk", tags=[" Work ", "URGENT"])

    assert todo.tags == ("work", "urgent")


def test_todo_to_dict_preserves_tags() -> None:
    """to_dict should include tags as list for JSON serialization."""
    todo = Todo(id=1, text="buy milk", tags=["work", "urgent"])
    data = todo.to_dict()

    assert "tags" in data
    assert data["tags"] == ["work", "urgent"]
    assert isinstance(data["tags"], list)  # JSON serializable


def test_todo_to_dict_with_empty_tags() -> None:
    """to_dict should include empty tags list."""
    todo = Todo(id=1, text="buy milk")
    data = todo.to_dict()

    assert "tags" in data
    assert data["tags"] == []


def test_todo_from_dict_preserves_tags() -> None:
    """from_dict should restore tags from list."""
    data = {"id": 1, "text": "buy milk", "tags": ["work", "urgent"]}
    todo = Todo.from_dict(data)

    assert todo.tags == ("work", "urgent")
    assert isinstance(todo.tags, tuple)


def test_todo_from_dict_without_tags() -> None:
    """from_dict should default to empty tuple if tags missing."""
    data = {"id": 1, "text": "buy milk"}
    todo = Todo.from_dict(data)

    assert todo.tags == ()


def test_todo_from_dict_normalizes_tags() -> None:
    """from_dict should normalize tags (strip and lowercase)."""
    data = {"id": 1, "text": "buy milk", "tags": [" Work ", "URGENT"]}
    todo = Todo.from_dict(data)

    assert todo.tags == ("work", "urgent")


def test_todo_tags_roundtrip_via_serialization() -> None:
    """Tags should survive to_dict -> from_dict round-trip."""
    original = Todo(id=1, text="buy milk", tags=["work", "urgent"])
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.tags == ("work", "urgent")
