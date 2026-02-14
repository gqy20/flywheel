"""Regression tests for issue #3321: Symlink read protection in load().

Issue: load() follows symlinks without validation, which could leak file content
via diagnostic messages (e.g., JSON decode errors that include file content).

Security risk: An attacker could create a symlink at the storage path pointing
to a sensitive file (e.g., /etc/passwd, ~/.ssh/id_rsa), and load() would read
its content. While JSON parsing would fail, the error message could leak sensitive
information.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_external_file(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks pointing to external files.

    Security: Prevent reading arbitrary files via symlink attacks.
    This protects against data exfiltration through diagnostic messages.
    """
    # Create a sensitive file outside the storage directory
    sensitive_dir = tmp_path / "sensitive"
    sensitive_dir.mkdir()
    sensitive_file = sensitive_dir / "secret.json"
    sensitive_file.write_text('{"secret": "password123"}')

    # Create a symlink at the storage path pointing to the sensitive file
    db_path = tmp_path / "todo.json"
    db_path.symlink_to(sensitive_file)

    storage = TodoStorage(str(db_path))

    # load() should reject the symlink and raise ValueError
    # Before fix: load() follows symlink and reads the sensitive file
    # After fix: load() rejects symlink with clear error message
    try:
        storage.load()
        raise AssertionError("load() should have raised ValueError for symlink")
    except ValueError as e:
        error_msg = str(e)
        assert "symlink" in error_msg.lower(), f"Error should mention symlink: {error_msg}"


def test_load_rejects_symlink_even_to_valid_json(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks even if they point to valid JSON.

    The security concern is that allowing symlinks opens up attack vectors
    regardless of whether the target file is valid JSON.
    """
    # Create a valid JSON file outside the storage directory
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_json = external_dir / "data.json"
    external_json.write_text('[{"id": 1, "text": "external todo", "done": false}]')

    # Create a symlink pointing to the external JSON file
    db_path = tmp_path / "todo.json"
    db_path.symlink_to(external_json)

    storage = TodoStorage(str(db_path))

    # load() should reject the symlink even though the JSON is valid
    try:
        storage.load()
        raise AssertionError("load() should have raised ValueError for symlink")
    except ValueError as e:
        error_msg = str(e)
        assert "symlink" in error_msg.lower(), f"Error should mention symlink: {error_msg}"


def test_load_accepts_regular_file(tmp_path) -> None:
    """Issue #3321: load() should still work correctly with regular files.

    This ensures the fix doesn't break normal operation.
    """
    db_path = tmp_path / "todo.json"
    db_path.write_text('[{"id": 1, "text": "test todo", "done": false}]')

    storage = TodoStorage(str(db_path))
    todos = storage.load()

    assert len(todos) == 1
    assert todos[0].text == "test todo"
    assert todos[0].done is False


def test_load_empty_file_still_works(tmp_path) -> None:
    """Issue #3321: load() should return empty list when file doesn't exist.

    This ensures the fix doesn't change behavior for non-existent files.
    """
    db_path = tmp_path / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should return empty list, not raise an error
    todos = storage.load()
    assert todos == []
