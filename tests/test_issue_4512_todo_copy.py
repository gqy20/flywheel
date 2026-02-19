"""Test for Todo.copy() method - Issue #4512.

Tests for:
- todo.copy() returns a new Todo instance with all fields identical
- todo.copy(text='new text') returns a new instance with only text updated
- copy() automatically updates updated_at timestamp
- copy() does not modify the original object
"""


def test_copy_returns_new_instance_with_same_fields():
    """Test that copy() returns a different object with same field values."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries", done=True)
    copied = original.copy()

    # Different objects
    assert copied is not original
    # Same field values (except timestamps which are dynamically updated)
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_copy_with_text_override():
    """Test that copy(text='x') only updates the text field."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries", done=True)
    copied = original.copy(text="Buy milk")

    assert copied.text == "Buy milk"
    assert copied.id == original.id
    assert copied.done == original.done


def test_copy_with_done_override():
    """Test that copy(done=False) only updates the done field."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries", done=True)
    copied = original.copy(done=False)

    assert copied.done is False
    assert copied.text == original.text
    assert copied.id == original.id


def test_copy_updates_updated_at_timestamp():
    """Test that copy() automatically updates the updated_at timestamp."""
    import time

    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries")
    original_timestamp = original.updated_at

    # Small delay to ensure timestamps differ
    time.sleep(0.01)

    copied = original.copy()
    assert copied.updated_at != original_timestamp
    assert copied.updated_at > original_timestamp


def test_copy_preserves_created_at():
    """Test that copy() preserves created_at from original."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries")
    copied = original.copy(text="New text")

    assert copied.created_at == original.created_at


def test_copy_does_not_modify_original():
    """Test that copy() does not modify the original object."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries", done=False)
    original_updated_at = original.updated_at

    _ = original.copy(text="Buy milk", done=True)

    # Original should be unchanged
    assert original.text == "Buy groceries"
    assert original.done is False
    assert original.updated_at == original_updated_at


def test_copy_with_multiple_overrides():
    """Test copy() with multiple field overrides."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries", done=False)
    copied = original.copy(text="Buy milk", done=True)

    assert copied.text == "Buy milk"
    assert copied.done is True
    assert copied.id == original.id


def test_copy_with_id_override():
    """Test that copy() allows overriding the id field."""
    from flywheel.todo import Todo

    original = Todo(id=1, text="Buy groceries")
    copied = original.copy(id=2)

    assert copied.id == 2
    assert copied.text == original.text
