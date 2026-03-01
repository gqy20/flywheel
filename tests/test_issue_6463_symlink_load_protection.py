"""Regression tests for issue #6463: Symlink attack protection in load().

Issue: The load() method follows symlinks without validation, allowing arbitrary
file read if an attacker can create a symlink at the .todo.json path.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_fails_when_db_is_symlink_to_other_file(tmp_path) -> None:
    """Issue #6463: load() should reject symlinks to prevent arbitrary file read.

    Attack scenario: Attacker creates symlink at .todo.json pointing to
    sensitive files like /etc/passwd. Without protection, load() would
    read and attempt to parse the sensitive file.

    Before fix: load() follows symlink and reads target file
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a sensitive file that attacker wants to read
    sensitive_file = tmp_path / "sensitive_data.txt"
    sensitive_file.write_text("SECRET: password=supersecret123\n")

    # Create a symlink pointing to the sensitive file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(sensitive_file)

    # Verify the symlink was created correctly
    assert db_symlink.is_symlink()

    storage = TodoStorage(str(db_symlink))

    # Before fix: load() would read the sensitive file content
    # After fix: load() should raise ValueError
    try:
        storage.load()
        # If we get here, the fix is NOT in place
        raise AssertionError(
            "load() should have raised ValueError for symlink path. "
            "The vulnerability still exists!"
        )
    except ValueError as e:
        # Expected: load() should reject symlinks
        error_msg = str(e).lower()
        assert "symlink" in error_msg or "symbolic link" in error_msg, (
            f"Error message should mention symlink for security clarity: {e}"
        )


def test_load_fails_when_db_is_symlink_to_json_file(tmp_path) -> None:
    """Issue #6463: load() should reject symlinks even if target is valid JSON.

    This ensures we don't just reject based on JSON parsing errors,
    but actually check for symlinks before reading.
    """
    # Create a valid JSON file
    json_file = tmp_path / "real_data.json"
    json_file.write_text('[{"id": 1, "text": "legitimate data", "done": false}]')

    # Create a symlink pointing to the JSON file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(json_file)

    assert db_symlink.is_symlink()

    storage = TodoStorage(str(db_symlink))

    # Even though the target is valid JSON, symlink should be rejected
    try:
        storage.load()
        raise AssertionError("load() should have raised ValueError for symlink path")
    except ValueError as e:
        error_msg = str(e).lower()
        assert "symlink" in error_msg or "symbolic link" in error_msg


def test_load_succeeds_with_regular_file(tmp_path) -> None:
    """Issue #6463: load() should still work with regular (non-symlink) files."""
    db = tmp_path / "todo.json"

    # Create a valid todo file
    todos = [Todo(id=1, text="test todo", done=False)]
    storage = TodoStorage(str(db))
    storage.save(todos)

    # Verify load works correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
    assert loaded[0].done is False


def test_load_succeeds_when_file_does_not_exist(tmp_path) -> None:
    """Issue #6463: load() should return empty list for non-existent files."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list without error
    loaded = storage.load()
    assert loaded == []


def test_load_symlink_error_message_is_clear(tmp_path) -> None:
    """Issue #6463: Error message should clearly indicate security concern."""
    sensitive_file = tmp_path / "secret.txt"
    sensitive_file.write_text("secret data")

    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(sensitive_file)

    storage = TodoStorage(str(db_symlink))

    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink")
    except ValueError as e:
        error_msg = str(e)
        # Error message should:
        # 1. Mention symlink/symbolic link
        # 2. Indicate it's a security issue
        # 3. Be clear to the user
        assert "symlink" in error_msg.lower() or "symbolic link" in error_msg.lower()
        # Should mention security or not allowed
        assert "security" in error_msg.lower() or "not allowed" in error_msg.lower()
