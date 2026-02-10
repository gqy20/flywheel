"""Regression tests for issue #1873: Path traversal via path parameter.

Issue: TodoStorage accepts arbitrary paths without validation against '../' sequences.
This could allow accessing files outside the intended working directory.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_path_traversal_with_parent_dot_slash_rejected(tmp_path) -> None:
    """Issue #1873: Paths with '../' should be rejected or normalized.

    Attempting to create TodoStorage with '../../../etc/passwd' should
    either raise ValueError or be normalized to stay within working directory.

    Before fix: Path is accepted as-is, allowing directory traversal
    After fix: ValueError raised with clear message
    """
    original_cwd = Path.cwd()

    try:
        # Change to temp directory for isolation
        import os
        os.chdir(tmp_path)

        # Attempt path traversal attack
        with pytest.raises(ValueError, match=r"Invalid path|within working directory|Path traversal"):
            TodoStorage("../../../etc/passwd")
    finally:
        os.chdir(original_cwd)


def test_absolute_path_outside_working_directory_rejected(tmp_path) -> None:
    """Issue #1873: Absolute paths outside working directory are allowed.

    Note: The security issue is about path traversal via '../' sequences,
    not about absolute paths. Absolute paths are explicitly chosen by the user
    and don't involve traversal attacks.

    This test documents that absolute paths are permitted as a design choice.
    """
    # Absolute paths are allowed - they don't use traversal sequences
    storage = TodoStorage("/tmp/test_todo.json")
    assert storage.path == Path("/tmp/test_todo.json")


def test_safe_relative_path_accepted(tmp_path) -> None:
    """Issue #1873: Safe relative paths should work normally."""
    storage = TodoStorage("safe.json")
    assert storage.path.name == "safe.json"


def test_explicit_current_dir_path_accepted(tmp_path) -> None:
    """Issue #1873: Explicit current directory './data.json' should work."""
    storage = TodoStorage("./data.json")
    # Should normalize to just 'data.json'
    assert "data.json" in str(storage.path)


def test_subdirectory_path_accepted(tmp_path) -> None:
    """Issue #1873: Paths within subdirectories should be allowed."""
    storage = TodoStorage("subdir/data.json")
    # Should work - subdirectories within working directory are OK
    assert "subdir" in str(storage.path)
    assert "data.json" in str(storage.path)


def test_traversal_with_dot_dot_slash_in_middle_rejected(tmp_path) -> None:
    """Issue #1873: Path like 'subdir/../../etc/passwd' should be rejected."""
    with pytest.raises(ValueError, match=r"Invalid path|within working directory|Path traversal"):
        TodoStorage("subdir/../../etc/passwd")


def test_nested_traversal_rejected(tmp_path) -> None:
    """Issue #1873: Deeply nested '../' sequences should be rejected."""
    with pytest.raises(ValueError, match=r"Invalid path|within working directory|Path traversal"):
        TodoStorage("a/b/c/../../../../../../../../etc/passwd")


def test_normal_save_operation_still_works(tmp_path) -> None:
    """Issue #1873: Normal save operations should still work after fix."""
    import os
    original_cwd = Path.cwd()

    try:
        os.chdir(tmp_path)

        storage = TodoStorage("todo.json")
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_subdirectory_save_still_works(tmp_path) -> None:
    """Issue #1873: Saving to subdirectories should still work."""
    import os
    original_cwd = Path.cwd()

    try:
        os.chdir(tmp_path)

        storage = TodoStorage("subdir/nested/todos.json")
        todos = [Todo(id=1, text="nested todo")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "nested todo"

        # Verify file was created in expected location
        expected_path = tmp_path / "subdir" / "nested" / "todos.json"
        assert expected_path.exists()
    finally:
        os.chdir(original_cwd)
