"""Regression tests for issue #6546: Target path symlink attack protection.

Issue: os.replace follows symlinks, potentially allowing symlink attack on the
target file path. If self.path is a symlink, os.replace will replace the target
file, not the symlink itself.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_raises_error_when_target_path_is_symlink(tmp_path) -> None:
    """Issue #6546: save() should reject writing to a symlink target path.

    If the database path is a symlink pointing to another file, save() should
    raise ValueError to prevent an attacker from redirecting writes to arbitrary
    locations via symlink manipulation.

    Before fix: save() follows symlink and writes to attacker-controlled location
    After fix: save() raises ValueError with 'symlink' in message
    """
    # Create a target file that attacker wants us to overwrite
    attack_target = tmp_path / "sensitive_data.txt"
    attack_target.write_text("original sensitive content")

    # Create a symlink at the db path pointing to the attack target
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    # Verify symlink is set up correctly
    assert db_symlink.is_symlink()
    assert db_symlink.resolve() == attack_target

    storage = TodoStorage(str(db_symlink))
    todos = [Todo(id=1, text="test")]

    # Before fix: This would overwrite attack_target
    # After fix: This should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        storage.save(todos)

    # Error message should mention 'symlink' for clarity
    assert "symlink" in str(exc_info.value).lower()

    # Verify the attack target was NOT modified
    assert attack_target.read_text() == "original sensitive content"


def test_save_to_regular_file_still_works(tmp_path) -> None:
    """Issue #6546: Normal save to regular file should still work after fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]

    # Should succeed normally
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_save_to_nonexistent_path_still_works(tmp_path) -> None:
    """Issue #6546: Creating new file at nonexistent path should still work."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Should succeed - parent directory created, file created
    storage.save(todos)

    # Verify file was created
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_raises_error_when_target_path_is_dangling_symlink(tmp_path) -> None:
    """Issue #6546: save() should also reject dangling symlinks.

    A dangling symlink (pointing to nonexistent target) should also be rejected
    for consistency and security.
    """
    # Create a symlink pointing to a nonexistent file
    attack_target = tmp_path / "nonexistent.txt"
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    # Verify it's a dangling symlink
    assert db_symlink.is_symlink()
    assert not db_symlink.exists()  # exists() returns False for dangling symlinks

    storage = TodoStorage(str(db_symlink))
    todos = [Todo(id=1, text="test")]

    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        storage.save(todos)

    assert "symlink" in str(exc_info.value).lower()
