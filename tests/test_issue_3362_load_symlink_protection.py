"""Regression tests for issue #3362: Symlink attack protection in load method.

Issue: The load method does not verify if the file is a regular file,
allowing reading of symlink targets or device files which could be
controlled by an attacker.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_file(tmp_path) -> None:
    """Issue #3362: load should reject symlink files.

    Before fix: load() follows symlinks and reads attacker-controlled file
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a target file that attacker wants us to read
    attack_target = tmp_path / "sensitive_data.txt"
    attack_target.write_text('[{"id": 1, "text": "stolen data", "done": false}]')

    # Create a symlink pointing to the sensitive file
    symlink_db = tmp_path / "todo.json"
    symlink_db.symlink_to(attack_target)

    storage = TodoStorage(str(symlink_db))

    # Before fix: load would follow symlink and return the stolen data
    # After fix: load should raise ValueError
    with pytest.raises(ValueError, match=r"symlink|regular file|not a file"):
        storage.load()


def test_load_rejects_device_file(tmp_path, monkeypatch) -> None:
    """Issue #3362: load should reject non-regular files like device files.

    This test uses monkeypatch to simulate a device file scenario.
    """
    # We can't actually create device files without root, so we mock is_file()
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "test", "done": false}]')

    storage = TodoStorage(str(db))

    # Mock is_file to return False (simulating device file)
    original_is_file = Path.is_file

    def mock_is_file(self):
        if self == storage.path:
            return False
        return original_is_file(self)

    monkeypatch.setattr(Path, "is_file", mock_is_file)

    # Should raise ValueError because path is not a regular file
    with pytest.raises(ValueError, match=r"not a regular file|not a file"):
        storage.load()


def test_load_accepts_regular_file(tmp_path) -> None:
    """Issue #3362: load should work normally with regular files."""
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "normal task", "done": false}]')

    storage = TodoStorage(str(db))

    # Should work normally with regular files
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal task"


def test_load_accepts_regular_file_via_symlink_check(tmp_path) -> None:
    """Issue #3362: Verify is_file() returns True for regular files.

    This test confirms our fix correctly identifies regular files.
    """
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "test", "done": false}]')

    storage = TodoStorage(str(db))

    # Verify the file is recognized as a regular file
    assert storage.path.is_file(), "Regular file should pass is_file() check"

    # load should work
    loaded = storage.load()
    assert len(loaded) == 1


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Issue #3362: load should still return empty list for nonexistent file."""
    nonexistent = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(nonexistent))

    # Should return empty list (not raise error)
    result = storage.load()
    assert result == []


def test_symlink_to_directory_is_rejected(tmp_path) -> None:
    """Issue #3362: load should reject symlink pointing to directory."""
    # Create a directory
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    # Create a symlink pointing to the directory
    symlink_db = tmp_path / "todo.json"
    symlink_db.symlink_to(target_dir)

    storage = TodoStorage(str(symlink_db))

    # Should raise ValueError (symlink, and also not a file)
    with pytest.raises(ValueError, match=r"symlink|not a regular file|not a file"):
        storage.load()
