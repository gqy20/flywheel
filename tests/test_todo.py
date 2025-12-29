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
