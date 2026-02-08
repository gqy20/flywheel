"""Regression test for issue #2221: from_dict treats falsy timestamp values incorrectly.

Bug: Using `or ""` fallback causes False, 0, None to become empty string.
Fix: Use dict.get(key, default) instead of dict.get(key) or default.
"""

from flywheel.todo import Todo


def test_from_dict_preserves_false_as_timestamp_string() -> None:
    """Issue #2221: created_at=False should be preserved as 'False' string, not ''."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": False})
    assert todo.created_at == "False", f"Expected 'False' but got {todo.created_at!r}"


def test_from_dict_preserves_zero_as_timestamp_string() -> None:
    """Issue #2221: updated_at=0 should be preserved as '0' string, not ''."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": 0})
    assert todo.updated_at == "0", f"Expected '0' but got {todo.updated_at!r}"


def test_from_dict_preserves_none_as_timestamp_string() -> None:
    """Issue #2221: None should be preserved as 'None' string, not ''."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None, "updated_at": None})
    assert todo.created_at == "None", f"Expected 'None' but got {todo.created_at!r}"
    assert todo.updated_at == "None", f"Expected 'None' but got {todo.updated_at!r}"


def test_from_dict_with_both_falsy_timestamps() -> None:
    """Issue #2221: Both timestamps can be falsy and should be preserved."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": False, "updated_at": 0})
    assert todo.created_at == "False", f"Expected 'False' but got {todo.created_at!r}"
    assert todo.updated_at == "0", f"Expected '0' but got {todo.updated_at!r}"


def test_from_dict_with_missing_timestamps_auto_fills_iso() -> None:
    """Missing timestamp keys should auto-fill with ISO timestamp via __post_init__."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # Missing keys result in empty string, which __post_init__ fills with ISO timestamp
    assert todo.created_at != "", f"Expected ISO timestamp but got {todo.created_at!r}"
    assert todo.updated_at != "", f"Expected ISO timestamp but got {todo.updated_at!r}"


def test_from_dict_with_actual_timestamp_string_preserved() -> None:
    """Actual timestamp strings should pass through unchanged."""
    ts = "2025-01-01T12:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ts, "updated_at": ts})
    assert todo.created_at == ts, f"Expected {ts!r} but got {todo.created_at!r}"
    assert todo.updated_at == ts, f"Expected {ts!r} but got {todo.updated_at!r}"
