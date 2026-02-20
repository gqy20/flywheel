"""Regression tests for issue #4650: Symlink protection in load().

Issue: load() uses path.stat() which follows symlinks before checking file size,
allowing a symlink race attack where an attacker can read arbitrary files.

These tests verify that load() properly rejects symlinks to prevent such attacks.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_outside_file(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks to prevent reading arbitrary files.

    Before fix: load() follows symlink and reads target file content
    After fix: load() raises ValueError when db path is a symlink
    """
    # Create a legitimate todo file
    legit_db = tmp_path / "legit.json"
    legit_db.write_text('[{"id": 1, "text": "legit todo", "done": false}]')

    # Create a symlink pointing to the legitimate file
    symlink_db = tmp_path / "symlink.json"
    symlink_db.symlink_to(legit_db)

    storage = TodoStorage(str(symlink_db))

    # Should raise ValueError because we're loading from a symlink
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink path")
    except ValueError as e:
        assert "symlink" in str(e).lower(), f"Expected symlink error, got: {e}"


def test_load_rejects_symlink_pointing_to_sensitive_file(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks even if target is not a todo file.

    This prevents attackers from reading sensitive files like /etc/passwd
    by creating a symlink to them.
    """
    # Create a file that simulates a sensitive system file
    sensitive_file = tmp_path / "sensitive_data.txt"
    sensitive_file.write_text("secret: password123")

    # Create a symlink pointing to the sensitive file
    symlink_db = tmp_path / "malicious.json"
    symlink_db.symlink_to(sensitive_file)

    storage = TodoStorage(str(symlink_db))

    # Should raise ValueError because we're loading from a symlink
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink path")
    except ValueError as e:
        assert "symlink" in str(e).lower(), f"Expected symlink error, got: {e}"


def test_load_succeeds_for_regular_file(tmp_path) -> None:
    """Issue #4650: load() should work normally for regular files (not symlinks)."""
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "test todo", "done": false}]')

    storage = TodoStorage(str(db))
    todos = storage.load()

    assert len(todos) == 1
    assert todos[0].text == "test todo"
    assert todos[0].done is False


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Issue #4650: load() should return empty list for nonexistent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    todos = storage.load()
    assert todos == []


def test_load_uses_lstat_not_stat(tmp_path) -> None:
    """Issue #4650: Verify load() uses lstat() to avoid following symlinks.

    This test verifies that the implementation uses os.lstat() instead of
    path.stat() to prevent TOCTOU race conditions.
    """
    # Create a valid todo file
    real_db = tmp_path / "real.json"
    real_db.write_text('[{"id": 1, "text": "real todo", "done": false}]')

    # Create a symlink to it
    symlink_db = tmp_path / "link.json"
    symlink_db.symlink_to(real_db)

    storage = TodoStorage(str(symlink_db))

    # If using stat(), this would load the real file content
    # If using lstat(), this should reject the symlink
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink path")
    except ValueError as e:
        # Verify the error message mentions symlink
        assert "symlink" in str(e).lower()
