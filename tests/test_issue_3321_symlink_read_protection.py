"""Regression tests for issue #3321: Symlink read protection in load().

Issue: load() follows symlinks without validation, could leak file content
via diagnostic messages (e.g., error messages could expose contents of
sensitive files if a symlink points to them).

Security impact: An attacker could create a symlink to a sensitive file
(e.g., /etc/passwd, ~/.ssh/id_rsa) and get its contents exposed in error
messages when load() fails to parse it as JSON.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_pointing_to_external_file(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks pointing to external files.

    Before fix: load() follows symlink and tries to parse external file as JSON
    After fix: load() should reject symlinks with a clear error message
    """
    # Create a sensitive file outside the expected directory
    sensitive_dir = tmp_path / "sensitive"
    sensitive_dir.mkdir()
    sensitive_file = sensitive_dir / "secret.txt"
    sensitive_file.write_text("SECRET DATA - should not be exposed")

    # Create a symlink in the data directory pointing to the sensitive file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(sensitive_file)

    storage = TodoStorage(str(db_symlink))

    # Attempt to load should reject the symlink
    # The error message should NOT contain the secret data
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink, but load() succeeded")
    except ValueError as e:
        error_msg = str(e)
        # Should indicate symlink is not allowed
        assert "symlink" in error_msg.lower(), f"Error should mention symlink: {error_msg}"
        # Must NOT expose the secret content
        assert "SECRET DATA" not in error_msg, f"Error should not expose file content: {error_msg}"


def test_load_rejects_symlink_pointing_to_valid_json_outside_directory(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks even to valid JSON outside directory.

    This tests the case where an attacker creates a symlink to a valid JSON file
    outside the expected directory.
    """
    # Create a valid JSON file in a different location
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_json = external_dir / "data.json"
    external_json.write_text('[{"id": 1, "text": "external data", "done": false}]')

    # Create a symlink pointing to the external file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(external_json)

    storage = TodoStorage(str(db_symlink))

    # Should reject symlink, not load the external data
    try:
        result = storage.load()
        # If it succeeded, it means we loaded external data via symlink - security issue!
        raise AssertionError(
            f"Expected ValueError for symlink, but load() returned: {result}"
        )
    except ValueError as e:
        error_msg = str(e)
        assert "symlink" in error_msg.lower(), f"Error should mention symlink: {error_msg}"


def test_load_succeeds_with_regular_file(tmp_path) -> None:
    """Issue #3321: load() should still work with regular files.

    This is a regression test to ensure the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="normal todo", done=False)]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"


def test_load_rejects_broken_symlink(tmp_path) -> None:
    """Issue #3321: load() should handle broken symlinks gracefully.

    A broken symlink (pointing to non-existent file) should still be rejected
    with a clear error message.
    """
    # Create a symlink to a non-existent target
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(tmp_path / "nonexistent.json")

    storage = TodoStorage(str(db_symlink))

    # Should reject the symlink (not follow it to a 404)
    try:
        storage.load()
        raise AssertionError("Expected ValueError for broken symlink")
    except ValueError as e:
        error_msg = str(e)
        # Either it detects it's a symlink or says file doesn't exist
        # Both are acceptable, as long as we don't crash or expose unexpected info
        assert (
            "symlink" in error_msg.lower()
            or "not exist" in error_msg.lower()
            or "no such file" in error_msg.lower()
        ), f"Unexpected error message: {error_msg}"


def test_load_rejects_symlink_to_large_file(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks even when size check exists.

    The current code has a size check, but it's after following symlinks.
    This test ensures symlinks are rejected BEFORE any file operations.
    """
    # Create a large file
    large_dir = tmp_path / "large"
    large_dir.mkdir()
    large_file = large_dir / "large.json"
    # Create content > 10MB limit
    large_content = "[" + ",".join([f'{{"id": {i}}}' for i in range(100000)]) + "]"
    large_file.write_text(large_content[:11 * 1024 * 1024])  # ~11MB

    # Create symlink to the large file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(large_file)

    storage = TodoStorage(str(db_symlink))

    # Should reject symlink before even checking size
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink to large file")
    except ValueError as e:
        error_msg = str(e)
        # The error should be about symlinks, not about file size
        # This proves we reject symlinks before following them
        assert "symlink" in error_msg.lower(), (
            f"Error should mention symlink (not just size): {error_msg}"
        )
