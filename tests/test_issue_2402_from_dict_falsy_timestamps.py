"""Tests for Todo.from_dict with falsy timestamp values (Issue #2402).

These tests verify that:
1. from_dict uses str(data.get("created_at", "")) instead of str(data.get("created_at") or "")
2. The fix preserves the string "0" when explicitly provided
3. The fix converts integer 0 to string "0" (not empty string)
4. Missing keys still default to empty string (which __post_init__ then fills)

Bug: str(data.get('created_at') or '') converts falsy values (0, False, None)
to empty string BEFORE str() is applied, losing the original value.

Fix: str(data.get('created_at', '')) only uses default when key is MISSING,
not when the value is falsy.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_string_zero_timestamp() -> None:
    """from_dict should preserve '0' as a valid timestamp string value.

    This is the key bug fix: '0' is a truthy string, so '0' or '' = '0'.
    However, the issue is about data.get() or '' pattern which is problematic
    for other falsy values (integer 0, False, None).
    """
    data = {
        "id": 1,
        "text": "test todo",
        "created_at": "0",
        "updated_at": "0"
    }
    todo = Todo.from_dict(data)

    # Should preserve '0' as a valid timestamp
    assert todo.created_at == "0", f"Expected '0', got {todo.created_at!r}"
    assert todo.updated_at == "0", f"Expected '0', got {todo.updated_at!r}"


def test_from_dict_converts_integer_zero_to_string_zero() -> None:
    """from_dict should convert integer 0 to string '0', not empty string.

    Bug: str(0 or '') = str('') = '', then __post_init__ overwrites it.
    Fix: str(data.get('created_at', '')) = str(0) = '0' when key exists with value 0.
    """
    data = {
        "id": 1,
        "text": "test todo",
        "created_at": 0,
        "updated_at": 0
    }
    todo = Todo.from_dict(data)

    # Integer 0 should convert to string '0' (not empty string)
    # This is the fix - previously it became '' and was overwritten by __post_init__
    assert todo.created_at == "0", f"Expected '0' (str of int 0), got {todo.created_at!r}"
    assert todo.updated_at == "0", f"Expected '0' (str of int 0), got {todo.updated_at!r}"


def test_from_dict_defaults_missing_timestamps_to_empty_string() -> None:
    """from_dict should default missing timestamps to empty string.

    When created_at/updated_at keys are MISSING, they should default to ''.
    The __post_init__ will then fill them with current timestamps.

    Fix: data.get('created_at', '') returns '' when key is missing.
    """
    data = {
        "id": 1,
        "text": "test todo"
    }
    todo = Todo.from_dict(data)

    # Missing keys should default to empty string
    # Then __post_init__ fills them with timestamps
    assert todo.created_at != "", "created_at should be set by __post_init__"
    assert todo.updated_at != "", "updated_at should be set by __post_init__"


def test_from_dict_converts_none_to_string_none() -> None:
    """from_dict should convert None to string 'None', not empty string.

    Bug: str(None or '') = str('') = '', then __post_init__ overwrites it.
    Fix: str(data.get('created_at', '')) = str(None) = 'None' when key exists with value None.
    """
    data = {
        "id": 1,
        "text": "test todo",
        "created_at": None,
        "updated_at": None
    }
    todo = Todo.from_dict(data)

    # None should convert to string 'None' (not empty string)
    assert todo.created_at == "None", f"Expected 'None', got {todo.created_at!r}"
    assert todo.updated_at == "None", f"Expected 'None', got {todo.updated_at!r}"


def test_from_dict_converts_false_to_string_false() -> None:
    """from_dict should convert False to string 'False', not empty string.

    Bug: str(False or '') = str('') = '', then __post_init__ overwrites it.
    Fix: str(data.get('created_at', '')) = str(False) = 'False' when key exists with value False.
    """
    data = {
        "id": 1,
        "text": "test todo",
        "created_at": False,
        "updated_at": False
    }
    todo = Todo.from_dict(data)

    # False should convert to string 'False' (not empty string)
    assert todo.created_at == "False", f"Expected 'False', got {todo.created_at!r}"
    assert todo.updated_at == "False", f"Expected 'False', got {todo.updated_at!r}"


def test_from_dict_preserves_valid_timestamp_strings() -> None:
    """from_dict should preserve valid ISO timestamp strings."""
    data = {
        "id": 1,
        "text": "test todo",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-02T12:30:45+00:00"
    }
    todo = Todo.from_dict(data)

    assert todo.created_at == "2025-01-01T00:00:00+00:00"
    assert todo.updated_at == "2025-01-02T12:30:45+00:00"
