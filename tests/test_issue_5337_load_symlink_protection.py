"""Regression tests for issue #5337: Symlink attack protection in load().

Issue: The load() method does not validate that the file is a regular file
(not a symlink) before reading. An attacker could create a symlink at the
expected database path pointing to a sensitive file, causing the application
to read and potentially expose its contents.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_fails_when_path_is_symlink(tmp_path: Path) -> None:
    """Issue #5337: load() should raise ValueError when path is a symlink.

    Security: An attacker could create a symlink at the expected database path
    pointing to a sensitive file. Without this check, the application would
    read the symlink target file instead.
    """
    # Create a target file with sensitive content
    attack_target = tmp_path / "sensitive_data.txt"
    attack_target.write_text("sensitive secret data")

    # Create a symlink at the database path pointing to the target
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    storage = TodoStorage(str(db_symlink))

    # Should raise ValueError when path is a symlink
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        storage.load()


def test_load_fails_when_path_is_symlink_to_directory(tmp_path: Path) -> None:
    """Issue #5337: load() should raise ValueError when path is a symlink to a directory."""
    # Create a target directory with some files
    attack_dir = tmp_path / "sensitive_directory"
    attack_dir.mkdir()
    (attack_dir / "secret.txt").write_text("more secrets")

    # Create a symlink at the database path pointing to the directory
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_dir)

    storage = TodoStorage(str(db_symlink))

    # Should raise ValueError when path is a symlink
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        storage.load()


def test_load_succeeds_with_regular_file(tmp_path: Path) -> None:
    """Issue #5337: load() should still work with regular files (no regression)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save some todos
    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]
    storage.save(todos)

    # Then load them back
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_returns_empty_list_for_nonexistent_path(tmp_path: Path) -> None:
    """Issue #5337: load() should return [] for non-existent paths (no regression)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list for non-existent file
    loaded = storage.load()
    assert loaded == []


def test_load_error_message_mentions_security(tmp_path: Path) -> None:
    """Issue #5337: Error message should clearly indicate the security concern."""
    # Create a target file with sensitive content
    attack_target = tmp_path / "sensitive.txt"
    attack_target.write_text("secret")

    # Create a symlink at the database path
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    storage = TodoStorage(str(db_symlink))

    # The error message should indicate the security concern
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    # Should mention either "security" or "symlink" clearly
    assert "security" in error_msg or "symlink" in error_msg
