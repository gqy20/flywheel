"""Regression tests for issue #5337: Symlink attack protection in load().

Issue: The load() method does not validate that the file is a regular file
(not a symlink) before reading. An attacker could create a symlink at the
expected database path pointing to a sensitive file, causing the application
to read and potentially expose its contents through error messages or other
channels.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_fails_when_path_is_symlink(tmp_path: Path) -> None:
    """Issue #5337: load() should reject symlinks for security.

    Before fix: load() follows symlink and reads target file
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a target file with sensitive content (simulating attack target)
    attack_target = tmp_path / "sensitive_data.txt"
    attack_target.write_text("SECRET: password123")

    # Create a symlink at the database path pointing to the attack target
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    storage = TodoStorage(str(db_symlink))

    # load() should fail with clear error message about symlink security
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_fails_when_path_is_symlink_to_directory(tmp_path: Path) -> None:
    """Issue #5337: load() should reject symlinks even if pointing to directory.

    A symlink to a directory would cause an error anyway when trying to read,
    but we should still catch it early with a clear security error.
    """
    # Create a target directory
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    # Create a symlink at the database path pointing to the directory
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target_dir)

    storage = TodoStorage(str(db_symlink))

    # load() should fail with clear error message about symlink security
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_fails_when_path_is_symlink_to_json_file(tmp_path: Path) -> None:
    """Issue #5337: load() should reject symlinks even if pointing to valid JSON.

    Even if the symlink points to a valid JSON file (which load() could parse),
    we must reject it to prevent symlink attacks.
    """
    # Create a target JSON file with valid content
    target_json = tmp_path / "real_data.json"
    target_json.write_text('[]')

    # Create a symlink at the database path pointing to the target JSON
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target_json)

    storage = TodoStorage(str(db_symlink))

    # load() should fail with clear error message about symlink security
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_returns_empty_list_for_nonexistent_path(tmp_path: Path) -> None:
    """Issue #5337: Non-existent path should return empty list (no regression)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list without error
    result = storage.load()
    assert result == []


def test_load_works_for_regular_file(tmp_path: Path) -> None:
    """Issue #5337: Normal file reading should continue to work after fix."""
    db = tmp_path / "todo.json"

    # Create a valid todo file
    todos = [Todo(id=1, text="test todo", done=False)]
    storage = TodoStorage(str(db))
    storage.save(todos)

    # load() should work normally for regular files
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
    assert loaded[0].done is False


def test_load_works_for_regular_file_with_existing_data(tmp_path: Path) -> None:
    """Issue #5337: load() should work correctly with pre-existing data."""
    db = tmp_path / "existing.json"

    # Pre-create a file with valid JSON
    db.write_text('[{"id": 1, "text": "existing todo", "done": true}]')

    storage = TodoStorage(str(db))
    loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].id == 1
    assert loaded[0].text == "existing todo"
    assert loaded[0].done is True
