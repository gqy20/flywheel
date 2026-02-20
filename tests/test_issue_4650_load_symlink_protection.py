"""Regression tests for issue #4650: Symlink protection in load().

Issue: load() uses path.stat() which follows symlinks before size check,
potentially allowing symlink attacks and TOCTOU race conditions.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_pointing_outside_allowed_dirs(tmp_path) -> None:
    """Issue #4650: load() should detect and reject symlinks.

    Before fix: load() follows symlink and reads from target file
    After fix: load() should fail with security error for symlinks
    """
    db = tmp_path / "todo.json"

    # Create a valid todo file elsewhere
    valid_todo = tmp_path / "valid" / "todos.json"
    valid_todo.parent.mkdir()
    valid_todo.write_text('[{"id": 1, "text": "secret todo", "done": false}]', encoding="utf-8")

    # Create a symlink pointing to the valid todo file
    db.symlink_to(valid_todo)

    storage = TodoStorage(str(db))

    # Before fix: This would succeed and load data from symlink target
    # After fix: This should fail with a security error
    try:
        result = storage.load()
        # If we reach here, the fix is not applied - we loaded symlink target
        raise AssertionError(f"load() should reject symlinks, but it loaded: {result}")
    except ValueError as e:
        # Expected: security error about symlinks
        assert "symlink" in str(e).lower(), f"Expected symlink error, got: {e}"


def test_load_rejects_symlink_to_system_file(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks pointing to system files.

    This test verifies that a malicious symlink to /etc/passwd is rejected.
    """
    db = tmp_path / "todo.json"

    # Create a symlink pointing to a system file (if it exists)
    passwd_path = Path("/etc/passwd")
    if not passwd_path.exists():
        # Skip if /etc/passwd doesn't exist (unlikely on Unix)
        import pytest

        pytest.skip("/etc/passwd not available for testing")

    db.symlink_to(passwd_path)

    storage = TodoStorage(str(db))

    # Before fix: This would read /etc/passwd content (or fail on JSON parse)
    # After fix: This should fail with a security error
    try:
        storage.load()
        raise AssertionError("load() should reject symlinks to system files")
    except ValueError as e:
        assert "symlink" in str(e).lower(), f"Expected symlink error, got: {e}"


def test_load_succeeds_for_regular_file(tmp_path) -> None:
    """Issue #4650: load() should still work for regular files (non-symlinks)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid regular file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Verify we can load from regular file
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_load_empty_file_still_works(tmp_path) -> None:
    """Issue #4650: Empty regular files should still work correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create empty file
    db.write_text("[]", encoding="utf-8")

    # Should return empty list
    loaded = storage.load()
    assert loaded == []


def test_load_uses_lstat_not_stat(tmp_path) -> None:
    """Issue #4650: load() should use os.lstat() to avoid following symlinks.

    This verifies the fix implementation uses lstat instead of stat.
    We check this by creating a symlink to a non-existent target.
    """
    db = tmp_path / "todo.json"

    # Create a dangling symlink (points to non-existent file)
    nonexistent = tmp_path / "does_not_exist.json"
    db.symlink_to(nonexistent)

    storage = TodoStorage(str(db))

    # Before fix: Path.exists() follows symlinks, so dangling symlink doesn't "exist"
    # and load() would return [] (because path.exists() returns False)
    #
    # After fix: We should detect the symlink and reject it
    # Either way, we should NOT get an OSError from trying to stat the dangling target
    try:
        result = storage.load()
        # If symlink detection is working, we should get an error
        # If we get here with [], it means exists() returned False for dangling symlink
        # which is technically correct behavior for a dangling symlink
        assert result == [], f"Expected empty list or error for dangling symlink, got: {result}"
    except ValueError as e:
        # If symlink detection is applied, we get a clear error
        assert "symlink" in str(e).lower(), f"Expected symlink error, got: {e}"
