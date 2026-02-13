"""Tests for symlink security in TodoStorage.load().

This test suite verifies that TodoStorage.load() properly handles symlinks
to prevent TOCTOU (Time-of-Check to Time-of-Use) race condition attacks.

The vulnerability was that load() used path.exists() which follows symlinks,
allowing an attacker to replace a regular file with a symlink between the
existence check and the read_text() call.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_to_file(tmp_path: Path) -> None:
    """Test that load() rejects symlinks pointing to regular files.

    This prevents TOCTOU attacks where a file is replaced with a symlink
    between the existence check and the read operation.
    """
    # Create a target file with legitimate-looking data
    target_file = tmp_path / "target.json"
    target_file.write_text(
        json.dumps([{"id": 1, "text": "attacker data", "done": False}]),
        encoding="utf-8",
    )

    # Create a symlink pointing to the target file
    symlink_path = tmp_path / "todo.json"
    symlink_path.symlink_to(target_file)

    storage = TodoStorage(str(symlink_path))

    # load() should raise an error when encountering a symlink
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_to_nonexistent_target(tmp_path: Path) -> None:
    """Test that load() rejects dangling symlinks (pointing to non-existent targets)."""
    # Create a symlink pointing to a non-existent file
    nonexistent = tmp_path / "nonexistent.json"
    symlink_path = tmp_path / "todo.json"
    symlink_path.symlink_to(nonexistent)

    storage = TodoStorage(str(symlink_path))

    # load() should raise an error for dangling symlinks
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_accepts_regular_file(tmp_path: Path) -> None:
    """Test that load() works correctly with regular files (not symlinks)."""
    # Create a regular file with valid data
    regular_file = tmp_path / "todo.json"
    regular_file.write_text(
        json.dumps([{"id": 1, "text": "legitimate todo", "done": False}]),
        encoding="utf-8",
    )

    storage = TodoStorage(str(regular_file))

    # load() should work normally for regular files
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "legitimate todo"


def test_load_returns_empty_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that load() returns empty list for non-existent files."""
    nonexistent = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(nonexistent))

    # load() should return empty list for non-existent files
    loaded = storage.load()
    assert loaded == []


def test_load_works_through_symlinked_parent_directory(tmp_path: Path) -> None:
    """Test that load() works when a parent directory is a symlink.

    Note: This test documents current behavior. While traversing symlinked
    directories could theoretically be exploited, it's a common use case
    (e.g., /home being a symlink). The primary security concern addressed
    is the final path component being a symlink.

    If stricter symlink checking is needed for parent directories, that
    would be a separate security enhancement.
    """
    # Create a real directory with a file
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    real_file = real_dir / "todo.json"
    real_file.write_text(
        json.dumps([{"id": 1, "text": "data in real dir", "done": False}]),
        encoding="utf-8",
    )

    # Create a symlink pointing to the real directory
    symlink_dir = tmp_path / "symlink_dir"
    symlink_dir.symlink_to(real_dir)

    # The file path goes through the symlinked directory
    file_via_symlink = symlink_dir / "todo.json"
    storage = TodoStorage(str(file_via_symlink))

    # load() works through symlinked parent directories (documented behavior)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "data in real dir"
