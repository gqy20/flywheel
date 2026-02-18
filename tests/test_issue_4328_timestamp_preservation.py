"""Tests for timestamp preservation in Todo.from_dict (Issue #4328).

Bug: __post_init__ silently converts falsy created_at/updated_at to new timestamps

The issue is in from_dict lines 100-101:
    created_at=str(data.get("created_at") or ""),

The `or ""` pattern treats all falsy values (None, 0, False, "") as "missing",
causing __post_init__ to generate new timestamps and overwrite original values.

Root cause: `data.get("created_at") or ""` converts 0/False/None to "" before
passing to the constructor, which then gets replaced by __post_init__.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_explicit_created_at_string() -> None:
    """from_dict should preserve explicit created_at timestamp exactly.

    This is the core bug: passing an explicit timestamp should preserve it,
    not convert it via str() and lose information.
    """
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "2023-01-01T00:00:00",
    })

    assert todo.created_at == "2023-01-01T00:00:00"


def test_from_dict_preserves_explicit_updated_at_string() -> None:
    """from_dict should preserve explicit updated_at timestamp exactly."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "updated_at": "2023-12-31T23:59:59",
    })

    assert todo.updated_at == "2023-12-31T23:59:59"


def test_from_dict_generates_timestamp_when_created_at_missing() -> None:
    """from_dict should generate a new timestamp when created_at is not provided.

    This is the correct existing behavior - missing keys should result in
    auto-generated timestamps.
    """
    todo = Todo.from_dict({"id": 1, "text": "test"})

    # Should have generated a timestamp (not empty)
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format


def test_from_dict_with_none_created_at() -> None:
    """from_dict with explicit None should convert to string "None".

    When created_at is explicitly None, str(None) = "None" which is truthy.
    This is preserved as-is, consistent with how other non-string values are handled.
    The string "None" is different from missing/empty, so __post_init__ won't replace it.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})

    # str(None) = "None" which is truthy, so it's preserved
    assert todo.created_at == "None"


def test_from_dict_handles_empty_string_created_at() -> None:
    """from_dict with empty string should let __post_init__ generate timestamp.

    Empty string is falsy, so __post_init__ should generate a new timestamp.
    This is consistent behavior - empty string means 'generate a new one'.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": ""})

    # __post_init__ should have generated a new timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format


def test_from_dict_preserves_both_timestamps() -> None:
    """from_dict should preserve both timestamps when both are provided."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-12-31T23:59:59",
    })

    assert todo.created_at == "2023-01-01T00:00:00"
    assert todo.updated_at == "2023-12-31T23:59:59"


# Regression tests for the actual bug: falsy values getting converted
def test_from_dict_with_integer_zero_created_at() -> None:
    """from_dict with created_at=0 should convert to "0", not generate timestamp.

    Bug: `data.get("created_at") or ""` converts 0 to "" which triggers __post_init__
    to generate a new timestamp, overwriting the original value.

    Fix: Preserve the str(0) = "0" value and let __post_init__ not replace it
    since "0" is a truthy string.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0})

    # str(0) = "0" which is truthy, so should be preserved
    assert todo.created_at == "0"


def test_from_dict_with_false_created_at() -> None:
    """from_dict with created_at=False should convert to "False", not generate timestamp.

    Bug: `data.get("created_at") or ""` converts False to "" which triggers __post_init__
    to generate a new timestamp.

    Fix: Preserve str(False) = "False" which is truthy.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False})

    # str(False) = "False" which is truthy, so should be preserved
    assert todo.created_at == "False"


def test_from_dict_with_integer_zero_updated_at() -> None:
    """from_dict with updated_at=0 should convert to "0", not generate timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": 0})

    assert todo.updated_at == "0"


def test_from_dict_with_false_updated_at() -> None:
    """from_dict with updated_at=False should convert to "False", not generate timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": False})

    assert todo.updated_at == "False"
