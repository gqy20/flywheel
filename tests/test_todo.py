"""Tests for Todo model."""

from flywheel.todo import Priority, Status, Todo


def test_todo_creation():
    """Test creating a todo."""
    todo = Todo(
        id=1,
        title="Test todo",
        description="Test description",
        priority=Priority.HIGH,
        status=Status.TODO,
    )

    assert todo.id == 1
    assert todo.title == "Test todo"
    assert todo.description == "Test description"
    assert todo.priority == Priority.HIGH
    assert todo.status == Status.TODO


def test_todo_to_dict():
    """Test converting todo to dictionary."""
    todo = Todo(id=1, title="Test", priority=Priority.HIGH)
    data = todo.to_dict()

    assert data["id"] == 1
    assert data["title"] == "Test"
    assert data["priority"] == "high"


def test_todo_from_dict():
    """Test creating todo from dictionary."""
    data = {
        "id": 1,
        "title": "Test",
        "description": "Description",
        "status": "todo",
        "priority": "high",
        "tags": ["work"],
    }
    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test"
    assert todo.status == Status.TODO
    assert todo.priority == Priority.HIGH
    assert todo.tags == ["work"]


def test_todo_defaults():
    """Test todo default values."""
    todo = Todo(id=1, title="Test")

    assert todo.description == ""
    assert todo.status == Status.TODO
    assert todo.priority == Priority.MEDIUM
    assert todo.due_date is None
    assert todo.tags == []
    assert todo.completed_at is None
    assert todo.created_at is not None


def test_todo_from_dict_invalid_due_date():
    """Test creating todo from dictionary with invalid due_date format."""
    data = {
        "id": 1,
        "title": "Test",
        "due_date": "invalid-date-format",
    }

    try:
        Todo.from_dict(data)
        assert False, "Should have raised ValueError for invalid due_date"
    except ValueError as e:
        assert "Invalid ISO 8601 date format for 'due_date'" in str(e)
        assert "invalid-date-format" in str(e)


def test_todo_from_dict_valid_due_date():
    """Test creating todo from dictionary with valid due_date format."""
    data = {
        "id": 1,
        "title": "Test",
        "due_date": "2026-01-15T10:30:00",
    }
    todo = Todo.from_dict(data)

    assert todo.due_date == "2026-01-15T10:30:00"
