"""Regression tests for issue #6546: Target path symlink attack protection.

Issue: os.replace follows symlinks, potentially allowing symlink attack on the target file path.
If self.path is a symlink, os.replace(temp_path, self.path) replaces the target file,
not the symlink itself.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_rejects_symlink_at_target_path(tmp_path: Path) -> None:
    """Issue #6546: save() should reject if target path is a symlink.

    Before fix: save() follows symlink and writes to attacker-controlled location
    After fix: save() raises ValueError when target path is a symlink
    """
    # Create a target file that attacker wants us to overwrite
    attack_target = tmp_path / "sensitive_data.txt"
    attack_target.write_text("original sensitive content")

    # Create the database path as a symlink pointing to the attack target
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    storage = TodoStorage(str(db_symlink))
    todos = [Todo(id=1, text="malicious todo")]

    # After fix: should raise ValueError with 'symlink' in message
    with pytest.raises(ValueError, match="symlink"):
        storage.save(todos)

    # Verify the attack target was NOT overwritten
    assert attack_target.read_text() == "original sensitive content"


def test_save_rejects_symlink_at_target_path_even_if_target_does_not_exist(tmp_path: Path) -> None:
    """Issue #6546: save() should reject symlink even if target doesn't exist."""
    # Create a symlink pointing to a non-existent file
    non_existent = tmp_path / "does_not_exist.txt"
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(non_existent)

    storage = TodoStorage(str(db_symlink))
    todos = [Todo(id=1, text="test todo")]

    # After fix: should raise ValueError with 'symlink' in message
    with pytest.raises(ValueError, match="symlink"):
        storage.save(todos)


def test_normal_save_to_regular_file_still_works(tmp_path: Path) -> None:
    """Issue #6546: Normal save to regular file should continue to work."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first todo"), Todo(id=2, text="second todo", done=True)]

    # Should succeed normally
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True
