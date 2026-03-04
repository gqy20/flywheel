"""Regression tests for Issue #7193: Add tags/categories field to Todo.

These tests verify that:
1. Todo has tags field as immutable tuple
2. Empty tuple is default, tags are preserved via serialization
3. Tags are normalized (stripped, lowercase) on creation
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_tags_field_as_tuple() -> None:
    """Todo should have tags field that stores tags as immutable tuple."""
    todo = Todo(id=1, text="Buy milk", tags=("work", "urgent"))
    assert todo.tags == ("work", "urgent")
    assert isinstance(todo.tags, tuple)


def test_todo_tags_default_is_empty_tuple() -> None:
    """Todo tags should default to empty tuple."""
    todo = Todo(id=1, text="Buy milk")
    assert todo.tags == ()
    assert isinstance(todo.tags, tuple)


def test_todo_tags_normalized_lowercase() -> None:
    """Todo tags should be normalized to lowercase."""
    todo = Todo(id=1, text="Buy milk", tags=("WORK", "UrGeNt"))
    assert todo.tags == ("work", "urgent")


def test_todo_tags_normalized_stripped() -> None:
    """Todo tags should have whitespace stripped."""
    todo = Todo(id=1, text="Buy milk", tags=("  work  ", "  urgent  "))
    assert todo.tags == ("work", "urgent")


def test_todo_to_dict_includes_tags_as_list() -> None:
    """Todo.to_dict() should include tags as list for JSON serialization."""
    todo = Todo(id=1, text="Buy milk", tags=("work", "urgent"))
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] == ["work", "urgent"]
    assert isinstance(data["tags"], list)


def test_todo_from_dict_preserves_tags() -> None:
    """Todo.from_dict() should preserve tags from deserialization."""
    data = {"id": 1, "text": "Buy milk", "tags": ["work", "urgent"]}
    todo = Todo.from_dict(data)
    assert todo.tags == ("work", "urgent")
    assert isinstance(todo.tags, tuple)


def test_todo_from_dict_tags_default_empty() -> None:
    """Todo.from_dict() should default tags to empty tuple if not present."""
    data = {"id": 1, "text": "Buy milk"}
    todo = Todo.from_dict(data)
    assert todo.tags == ()


def test_todo_tags_roundtrip_via_dict() -> None:
    """Tags should be preserved through to_dict/from_dict round-trip."""
    original = Todo(id=1, text="Buy milk", tags=("work", "urgent"))
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags == ("work", "urgent")


def test_todo_tags_normalized_on_creation() -> None:
    """Tags should be normalized during __post_init__."""
    # Create with mixed case and whitespace
    todo = Todo(id=1, text="Buy milk", tags=("  WORK  ", "  UrGeNt  ", "  PERSONAL  "))
    assert todo.tags == ("work", "urgent", "personal")


def test_todo_tags_empty_after_normalization() -> None:
    """Empty or whitespace-only tags should be filtered out."""
    todo = Todo(id=1, text="Buy milk", tags=("work", "", "  ", "urgent"))
    # Empty strings after stripping should be filtered out
    assert todo.tags == ("work", "urgent")
