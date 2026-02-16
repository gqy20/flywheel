"""Regression tests for issue #3662: Symlink protection in load().

Issue: load() follows symlinks without validation, allowing read of arbitrary file content.

Security vulnerability: An attacker could create a symlink at the database path
pointing to a sensitive file (e.g., /etc/passwd), and load() would read and
attempt to parse it as JSON, potentially exposing sensitive file content.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_file(tmp_path) -> None:
    """Issue #3662: load() should reject symlinks pointing to regular files.

    Security: An attacker could create a symlink at the database path
    pointing to a sensitive file, and load() would read its contents.

    Before fix: load() follows symlink and reads target file content
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a target file that looks like valid JSON (simulating sensitive data)
    attack_target = tmp_path / "sensitive_data.json"
    attack_target.write_text('{"secret": "SENSITIVE DATA - should not be accessible via load()"}')

    # Create a symlink at the database path pointing to the target file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    storage = TodoStorage(str(db_symlink))

    # Before fix: load() would read the symlink target content without error
    # After fix: load() should raise ValueError for symlinks
    import pytest
    with pytest.raises(ValueError, match=r"(?i)symlink"):
        storage.load()


def test_load_rejects_symlink_pointing_to_directory(tmp_path) -> None:
    """Issue #3662: load() should reject symlinks pointing to directories.

    Before fix: load() would attempt to read directory (causing IsADirectoryError)
    After fix: load() raises ValueError with clear message about symlinks
    """
    # Create a target directory
    attack_dir = tmp_path / "sensitive_directory"
    attack_dir.mkdir()

    # Create a symlink at the database path pointing to the directory
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_dir)

    storage = TodoStorage(str(db_symlink))

    # load() should reject symlinks before attempting to read
    # The fix should catch symlinks and raise ValueError, not IsADirectoryError
    import pytest
    with pytest.raises(ValueError, match=r"(?i)symlink"):
        storage.load()


def test_load_succeeds_for_regular_file(tmp_path) -> None:
    """Issue #3662: load() should still work correctly for regular files.

    This is a regression test to ensure the symlink check doesn't break
    normal file loading.
    """
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "test todo", "done": false}]')

    storage = TodoStorage(str(db))
    todos = storage.load()

    assert len(todos) == 1
    assert todos[0].id == 1
    assert todos[0].text == "test todo"
    assert todos[0].done is False


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Issue #3662: load() should return empty list for nonexistent files.

    This verifies the symlink check doesn't break the existing behavior.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    todos = storage.load()
    assert todos == []


def test_load_rejects_broken_symlink(tmp_path) -> None:
    """Issue #3662: load() should reject symlinks even if target doesn't exist.

    Before fix: load() would fail with FileNotFoundError or return empty
    After fix: load() raises ValueError for symlinks
    """
    # Create a symlink pointing to a nonexistent file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(tmp_path / "nonexistent_target.json")

    storage = TodoStorage(str(db_symlink))

    # load() should reject symlinks even if broken
    # The fix should catch symlinks and raise ValueError, not FileNotFoundError
    import pytest
    with pytest.raises(ValueError, match=r"(?i)symlink"):
        storage.load()
