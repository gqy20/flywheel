"""Tests for Todo.__repr__ method (Issue #2087)."""

from flywheel.todo import Todo


def test_repr_with_all_fields() -> None:
    """Test repr output includes all relevant fields."""
    todo = Todo(id=1, text="buy milk", done=False)
    repr_str = repr(todo)

    assert "Todo" in repr_str
    assert "id=1" in repr_str
    assert "text=" in repr_str
    assert "done=False" in repr_str


def test_repr_with_minimal_fields() -> None:
    """Test repr works with minimal required fields."""
    todo = Todo(id=42, text="single task")
    repr_str = repr(todo)

    assert "Todo" in repr_str
    assert "id=42" in repr_str
    assert "text=" in repr_str
    assert "done=False" in repr_str


def test_repr_truncates_long_text() -> None:
    """Test repr truncates long text to keep output concise."""
    long_text = "a" * 60
    todo = Todo(id=1, text=long_text)
    repr_str = repr(todo)

    # Repr should be concise (< 80 chars)
    assert len(repr_str) < 80
    # Should indicate truncation
    assert "..." in repr_str


def test_repr_is_concise() -> None:
    """Test repr output is concise for normal todos."""
    todo = Todo(id=1, text="normal length task", done=True)
    repr_str = repr(todo)

    # Normal todo repr should be under 80 chars
    assert len(repr_str) < 80


def test_repr_with_unicode() -> None:
    """Test repr handles unicode characters properly."""
    todo = Todo(id=1, text="buy milk 🥛 and émojis")
    repr_str = repr(todo)

    assert "Todo" in repr_str
    assert "id=1" in repr_str
    # Text should be properly escaped/repr'd
    assert "text=" in repr_str


def test_repr_with_special_chars() -> None:
    """Test repr handles special characters like quotes and newlines."""
    todo = Todo(id=1, text='text with "quotes" and\nnewlines')
    repr_str = repr(todo)

    assert "Todo" in repr_str
    # Should use repr() for text which escapes special chars
    assert "text=" in repr_str
