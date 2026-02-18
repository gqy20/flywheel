"""Test for issue #4092: toggle method to switch completion status."""

import time

from flywheel.todo import Todo


def test_toggle_from_false_to_true():
    """Toggle should change done=False to done=True."""
    todo = Todo(id=1, text="Test todo", done=False)
    assert todo.done is False

    todo.toggle()

    assert todo.done is True


def test_toggle_from_true_to_false():
    """Toggle should change done=True to done=False."""
    todo = Todo(id=1, text="Test todo", done=True)
    assert todo.done is True

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_timestamp():
    """Toggle should update the updated_at timestamp."""
    todo = Todo(id=1, text="Test todo", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(0.01)
    todo.toggle()

    assert todo.updated_at != original_updated_at
