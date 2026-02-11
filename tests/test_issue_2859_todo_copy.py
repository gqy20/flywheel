"""Tests for Todo.copy() method - Issue #2859."""


from flywheel.todo import Todo


def test_todo_copy_creates_independent_instance():
    """Test that copy() creates a new instance with identical values."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy()

    # Should be a different instance
    assert copy is not original
    # But with the same values
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done


def test_todo_copy_with_text_override():
    """Test that copy(text=...) returns new Todo with updated text."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy(text="updated task")

    assert copy is not original
    assert copy.text == "updated task"
    # Original should be unchanged
    assert original.text == "original task"
    # Other fields should match
    assert copy.id == original.id
    assert copy.done == original.done


def test_todo_copy_with_done_override():
    """Test that copy(done=...) returns new Todo with updated done status."""
    original = Todo(id=1, text="task", done=False)
    copy = original.copy(done=True)

    assert copy is not original
    assert copy.done is True
    # Original should be unchanged
    assert original.done is False
    # Other fields should match
    assert copy.id == original.id
    assert copy.text == original.text


def test_todo_copy_with_multiple_overrides():
    """Test copy with multiple fields overridden."""
    original = Todo(id=1, text="original", done=False)
    copy = original.copy(text="updated", done=True)

    assert copy is not original
    assert copy.text == "updated"
    assert copy.done is True
    # Original should be unchanged
    assert original.text == "original"
    assert original.done is False


def test_todo_copy_preserves_timestamps():
    """Test that copy preserves created_at and updates updated_at."""
    original = Todo(id=1, text="task")
    original_created = original.created_at
    original_updated = original.updated_at

    copy = original.copy()

    # Timestamps should be preserved from original
    assert copy.created_at == original_created
    assert copy.updated_at == original_updated


def test_todo_copy_with_override_updates_timestamp():
    """Test that copy with any override updates the updated_at timestamp."""
    original = Todo(id=1, text="task")
    original_updated = original.updated_at

    # Copy with override should update timestamp
    copy = original.copy(text="updated")
    assert copy.updated_at != original_updated


def test_todo_copy_unchanged_does_not_update_timestamp():
    """Test that copy without overrides does not change updated_at."""
    original = Todo(id=1, text="task")
    original_updated = original.updated_at

    copy = original.copy()
    assert copy.updated_at == original_updated
