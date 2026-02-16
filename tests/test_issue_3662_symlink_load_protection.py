"""Regression tests for issue #3662: Symlink protection in load().

Issue: The load() method follows symlinks without validation, allowing read
of arbitrary file content if the database file is a symlink.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_to_file(tmp_path: Path) -> None:
    """Issue #3662: load() should reject when path is a symlink.

    Security: An attacker could create a symlink at .todo.json pointing
    to sensitive files like /etc/passwd or ~/.ssh/id_rsa to read their content.
    """
    # Create a sensitive file that attacker wants to exfiltrate
    sensitive_file = tmp_path / "secret.txt"
    sensitive_file.write_text("SENSITIVE DATA: api_key=super_secret_12345")

    # Create a symlink from database path to sensitive file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(sensitive_file)

    storage = TodoStorage(str(db_symlink))

    # Before fix: load() would follow symlink and attempt to read sensitive file
    # After fix: load() should raise ValueError
    with pytest.raises(ValueError, match="symlink|Symlinks not allowed"):
        storage.load()


def test_load_rejects_symlink_to_json_file(tmp_path: Path) -> None:
    """Issue #3662: load() should reject symlinks even if target is valid JSON.

    Even if the symlink points to a valid JSON file, we should still reject it
    to prevent any potential confusion or directory traversal attacks.
    """
    # Create a valid JSON file in a different location
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    json_file = other_dir / "data.json"
    json_file.write_text(json.dumps([{"id": 1, "text": "test", "done": False}]))

    # Create a symlink to the JSON file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(json_file)

    storage = TodoStorage(str(db_symlink))

    # Should reject symlink even if target is valid JSON
    with pytest.raises(ValueError, match="symlink|Symlinks not allowed"):
        storage.load()


def test_load_succeeds_with_regular_file(tmp_path: Path) -> None:
    """Issue #3662: load() should still work with regular (non-symlink) files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo", done=True)]
    storage.save(todos)

    # load() should work normally
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "test todo"
    assert loaded[1].text == "another todo"
    assert loaded[1].done is True


def test_load_empty_file_succeeds(tmp_path: Path) -> None:
    """Issue #3662: load() should handle empty files (no symlink check needed)."""
    db = tmp_path / "todo.json"
    db.write_text("[]")
    storage = TodoStorage(str(db))

    # load() should work with empty file
    loaded = storage.load()
    assert loaded == []


def test_load_nonexistent_file_returns_empty(tmp_path: Path) -> None:
    """Issue #3662: load() should return empty list for nonexistent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # load() should return empty list, not raise error
    loaded = storage.load()
    assert loaded == []


def test_symlink_error_message_is_clear(tmp_path: Path) -> None:
    """Issue #3662: Error message should clearly indicate symlink is not allowed."""
    target = tmp_path / "target.txt"
    target.write_text("content")

    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target)

    storage = TodoStorage(str(db_symlink))

    try:
        storage.load()
        pytest.fail("Expected ValueError to be raised")
    except ValueError as e:
        error_msg = str(e).lower()
        # Error message should mention symlink
        assert "symlink" in error_msg, f"Error message should mention symlink: {e}"
