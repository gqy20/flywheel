"""Test for mutable default tags issue (#501)."""
import pytest
from flywheel.todo import Todo


def test_tags_none_creates_empty_list():
    """Test that when tags is None, an empty list is created."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": None,
    }
    todo = Todo.from_dict(data)
    assert todo.tags == []
    assert isinstance(todo.tags, list)


def test_tags_with_values():
    """Test that tags with values works correctly."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["work", "urgent"],
    }
    todo = Todo.from_dict(data)
    assert todo.tags == ["work", "urgent"]


def test_tags_not_shared_between_instances():
    """Test that tags lists are not shared between instances (mutable default bug)."""
    # Create first todo with tags
    data1 = {
        "id": 1,
        "title": "Todo 1",
        "tags": None,
    }
    todo1 = Todo.from_dict(data1)

    # Create second todo with tags
    data2 = {
        "id": 2,
        "title": "Todo 2",
        "tags": None,
    }
    todo2 = Todo.from_dict(data2)

    # Add a tag to todo1
    todo1.tags.append("work")

    # Verify todo2 tags list is independent
    assert todo2.tags == []
    assert "work" not in todo2.tags

    # Verify todo1 has the tag
    assert todo1.tags == ["work"]


def test_tags_missing_key_creates_empty_list():
    """Test that when tags key is missing, an empty list is created."""
    data = {
        "id": 1,
        "title": "Test Todo",
    }
    todo = Todo.from_dict(data)
    assert todo.tags == []
    assert isinstance(todo.tags, list)


def test_multiple_instances_independence():
    """Test that multiple instances created from None tags have independent lists."""
    todos = [Todo.from_dict({"id": i, "title": f"Todo {i}", "tags": None}) for i in range(5)]

    # Add different tags to each todo
    for i, todo in enumerate(todos):
        todo.tags.append(f"tag{i}")

    # Verify all tags lists are independent
    for i, todo in enumerate(todos):
        assert todo.tags == [f"tag{i}"]
        assert len(todo.tags) == 1
