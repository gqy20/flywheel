"""Regression tests for issue #1873: Path traversal via path parameter.

Issue: TodoStorage accepts paths without validation against '../' sequences,
allowing an attacker to read/write files outside the intended directory.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_path_traversal_with_parent_directory_sequences_raises_value_error(tmp_path) -> None:
    """Issue #1873: Paths with multiple '../' should be rejected.

    Before fix: TodoStorage("../../../etc/passwd") would allow escaping CWD
    After fix: Should raise ValueError with clear error message
    """
    with pytest.raises(ValueError, match=r"path|escape|outside|invalid"):
        TodoStorage("../../../etc/passwd")


def test_absolute_paths_are_allowed_for_user_flexibility(tmp_path) -> None:
    """Issue #1873: Absolute paths are allowed for user flexibility.

    The --db argument allows users to specify where to store their data.
    Absolute paths are legitimate - the user has full control via the CLI.

    The fix focuses on preventing '../' traversal in relative paths,
    not restricting absolute paths which are a user choice.
    """
    # Absolute paths work - users control where data is stored
    storage = TodoStorage(str(tmp_path / "safe.json"))
    assert storage.path.name == "safe.json"


def test_single_parent_directory_raises_value_error(tmp_path) -> None:
    """Issue #1873: Even a single '../' should be rejected.

    Before fix: TodoStorage("../outside.json") allowed escaping CWD
    After fix: Should raise ValueError
    """
    with pytest.raises(ValueError, match=r"path|escape|outside|invalid"):
        TodoStorage("../outside.json")


def test_safe_relative_path_works_normally(tmp_path) -> None:
    """Issue #1873: Safe relative paths within CWD should work normally.

    Before fix: Works as expected
    After fix: Should still work
    """
    # Safe filename in current directory
    storage = TodoStorage(str(tmp_path / "safe.json"))
    assert storage.path.name == "safe.json"


def test_subdirectory_path_works_normally(tmp_path) -> None:
    """Issue #1873: Paths to subdirectories within CWD should work.

    Before fix: Works as expected
    After fix: Should still work
    """
    # Safe path to subdirectory
    storage = TodoStorage(str(tmp_path / "subdir" / "safe.json"))
    # Path should be within tmp_path
    assert str(tmp_path) in str(storage.path)


def test_normalized_parent_directory_path_works(tmp_path) -> None:
    """Issue #1873: Paths that normalize to safe location should work.

    Before fix: Works as expected
    After fix: Should still work (after normalization)

    Example: 'subdir/../safe.json' normalizes to './safe.json' which is safe
    """
    # This path normalizes to safe.json within CWD
    storage = TodoStorage(str(tmp_path / "subdir" / ".." / "safe.json"))
    # After normalization, should be safe
    assert str(tmp_path) in str(storage.path.resolve())


def test_default_path_works_normally() -> None:
    """Issue #1873: Default path '.todo.json' should still work."""
    storage = TodoStorage()  # Default path
    assert storage.path.name == ".todo.json"


def test_current_directory_reference_works(tmp_path) -> None:
    """Issue #1873: Paths with explicit current directory './' should work."""
    storage = TodoStorage(str(tmp_path / "." / "safe.json"))
    assert str(tmp_path) in str(storage.path.resolve())
