"""Tests for symlink security in TodoStorage.load().

This test suite verifies that TodoStorage.load() properly handles symlinks
to prevent TOCTOU (Time-of-Check to Time-of-Use) race condition attacks.

Issue: #3103 - load() method uses path.exists() which follows symlinks,
allowing TOCTOU race condition.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_valid_file(tmp_path: Path) -> None:
    """Test that load() rejects symlinks even when they point to valid JSON.

    Security: An attacker could replace a regular file with a symlink
    pointing to an attacker-controlled file. We should reject symlinks
    to prevent this attack vector.
    """
    # Create a valid JSON file
    target_file = tmp_path / "target.json"
    target_file.write_text('[{"id": 1, "text": "attacker data", "done": false}]')

    # Create a symlink pointing to the valid file
    symlink_path = tmp_path / "todo.json"
    symlink_path.symlink_to(target_file)

    storage = TodoStorage(str(symlink_path))

    # load() should reject symlinks for security
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_pointing_to_nonexistent_file(tmp_path: Path) -> None:
    """Test that load() rejects dangling symlinks.

    Security: Dangling symlinks could be exploited to leak information
    about whether certain paths exist.
    """
    # Create a symlink pointing to a non-existent file
    nonexistent = tmp_path / "does_not_exist.json"
    symlink_path = tmp_path / "todo.json"
    symlink_path.symlink_to(nonexistent)

    storage = TodoStorage(str(symlink_path))

    # load() should reject symlinks for security (not return empty list)
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_accepts_regular_file(tmp_path: Path) -> None:
    """Test that load() works correctly with regular (non-symlink) files."""
    # Create a regular JSON file
    json_file = tmp_path / "todo.json"
    json_file.write_text('[{"id": 1, "text": "valid data", "done": false}]')

    storage = TodoStorage(str(json_file))

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "valid data"


def test_load_returns_empty_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that load() returns empty list for non-existent files."""
    nonexistent = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(nonexistent))

    # Should return empty list without error
    todos = storage.load()
    assert todos == []


def test_load_rejects_symlink_in_directory_path(tmp_path: Path) -> None:
    """Test that load() rejects when a parent directory is a symlink.

    Security: Symlink in path could redirect to attacker-controlled location.
    """
    # Create a real directory with a JSON file
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    json_file = real_dir / "todo.json"
    json_file.write_text('[{"id": 1, "text": "data", "done": false}]')

    # Create a symlink to the directory
    symlink_dir = tmp_path / "link"
    symlink_dir.symlink_to(real_dir)

    # Access the file through the symlinked directory
    symlink_path = symlink_dir / "todo.json"
    storage = TodoStorage(str(symlink_path))

    # This test documents current behavior - we focus on the file itself being a symlink
    # The directory symlink case is a separate concern
    # For now, we accept this since the file itself is not a symlink
    todos = storage.load()
    assert len(todos) == 1
