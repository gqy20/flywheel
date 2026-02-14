"""Regression tests for issue #3362: load() should reject symlinks and non-regular files.

Issue: The load() method only checks exists() but doesn't verify the path is a regular
file. This could allow reading symlinks pointing to attacker-controlled files or device files.

Security concern: If path is a symlink, an attacker could redirect read operations to
sensitive files outside the expected storage location.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_to_regular_file(tmp_path) -> None:
    """Issue #3362: load() should reject paths that are symlinks.

    Before fix: load() follows symlink and reads target file content
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a real file with content
    real_file = tmp_path / "real_todo.json"
    real_file.write_text('[{"id": 1, "text": "sensitive data", "done": false}]', encoding="utf-8")

    # Create a symlink pointing to the real file
    symlink_path = tmp_path / "symlink_todo.json"
    symlink_path.symlink_to(real_file)

    storage = TodoStorage(str(symlink_path))

    # Should raise ValueError because path is a symlink
    with pytest.raises(ValueError, match=r"symlink|regular file"):
        storage.load()


def test_load_rejects_symlink_to_directory(tmp_path) -> None:
    """Issue #3362: load() should reject paths that are symlinks to directories."""
    # Create a directory
    real_dir = tmp_path / "real_directory"
    real_dir.mkdir()

    # Create a symlink pointing to the directory
    symlink_path = tmp_path / "symlink_to_dir"
    symlink_path.symlink_to(real_dir)

    storage = TodoStorage(str(symlink_path))

    # Should raise ValueError because path is a symlink
    with pytest.raises(ValueError, match=r"symlink|regular file"):
        storage.load()


def test_load_accepts_regular_file(tmp_path) -> None:
    """Issue #3362: load() should accept regular files (non-symlinks).

    This test verifies that normal functionality is preserved after the fix.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a regular file with valid content
    todos = [Todo(id=1, text="normal todo", done=False)]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"
    assert loaded[0].done is False


def test_load_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Issue #3362: load() should still return empty list for nonexistent paths.

    This verifies that the fix doesn't break the existing behavior for missing files.
    """
    nonexistent = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(nonexistent))

    # Should return empty list, not raise error
    result = storage.load()
    assert result == []


def test_load_regular_file_via_absolute_path(tmp_path) -> None:
    """Issue #3362: load() should work with absolute paths to regular files."""
    db = tmp_path / "absolute_todo.json"
    storage = TodoStorage(str(db.resolve()))  # Use absolute path

    todos = [Todo(id=1, text="absolute path test")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "absolute path test"


def test_symlink_in_parent_directory_is_allowed(tmp_path) -> None:
    """Issue #3362: Symlinks in parent directories should still be allowed.

    Only the final path component (the file itself) should be checked.
    """
    # Create a real directory with a file
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()

    db_in_real_dir = real_dir / "todo.json"
    db_in_real_dir.write_text('[{"id": 1, "text": "data in linked dir", "done": false}]', encoding="utf-8")

    # Create a symlink to the parent directory (not the file)
    symlink_dir = tmp_path / "symlink_dir"
    symlink_dir.symlink_to(real_dir)

    # Access file through the symlinked directory
    db_via_symlink = symlink_dir / "todo.json"
    storage = TodoStorage(str(db_via_symlink))

    # This should work - only the final component is checked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "data in linked dir"


def test_load_error_message_is_clear(tmp_path) -> None:
    """Issue #3362: Error message should clearly indicate the security issue."""
    real_file = tmp_path / "target.json"
    real_file.write_text('[{"id": 1, "text": "data"}]', encoding="utf-8")

    symlink_path = tmp_path / "symlink.json"
    symlink_path.symlink_to(real_file)

    storage = TodoStorage(str(symlink_path))

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Error message should mention symlink or security concern
    error_msg = str(exc_info.value).lower()
    assert "symlink" in error_msg or "regular file" in error_msg or "symbolic link" in error_msg
