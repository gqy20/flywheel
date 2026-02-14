"""Regression tests for issue #3321: Symlink attack in load().

Issue: load() follows symlinks without validation, allowing an attacker
to leak file contents via diagnostic messages (e.g., JSON parse errors).

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_to_external_file(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks to files outside expected directory.

    Before fix: load() follows symlink and reads arbitrary file content
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a sensitive file outside the database directory
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    sensitive_file = outside_dir / "sensitive.json"
    sensitive_file.write_text('{"secret": "password123"}')

    # Create symlink to the sensitive file
    db = tmp_path / "todo.json"
    db.symlink_to(sensitive_file)

    storage = TodoStorage(str(db))

    # Should raise ValueError because db is a symlink
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_to_valid_json_file(tmp_path) -> None:
    """Issue #3321: load() should reject symlinks even to valid JSON files.

    Before fix: load() follows symlink and loads content
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a valid JSON file outside the database directory
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    external_json = outside_dir / "external.json"
    external_json.write_text('[{"id": 1, "text": "external todo", "done": false}]')

    # Create symlink to the external file
    db = tmp_path / "todo.json"
    db.symlink_to(external_json)

    storage = TodoStorage(str(db))

    # Should raise ValueError because db is a symlink
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_succeeds_with_regular_file(tmp_path) -> None:
    """Issue #3321: load() should still work with regular (non-symlink) files."""
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "test todo", "done": false}]')

    storage = TodoStorage(str(db))

    # Should succeed normally
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test todo"


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Issue #3321: load() should still return [] for nonexistent files."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list
    todos = storage.load()
    assert todos == []


def test_load_rejects_symlink_to_nonexistent_target(tmp_path) -> None:
    """Issue #3321: load() should reject broken symlinks too.

    A broken symlink could be used to probe for file existence via error messages.
    """
    # Create symlink to non-existent file
    db = tmp_path / "todo.json"
    db.symlink_to(tmp_path / "does_not_exist.json")

    storage = TodoStorage(str(db))

    # Should raise ValueError because db is a symlink
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_symlink_error_message_does_not_leak_target_path(tmp_path) -> None:
    """Issue #3321: Error message should not reveal symlink target path.

    This prevents leaking path information in diagnostic messages.
    """
    # Create a sensitive file with revealing path
    outside_dir = tmp_path / "secret_admin_credentials"
    outside_dir.mkdir()
    sensitive_file = outside_dir / "passwords.json"
    sensitive_file.write_text('{"admin": "secret123"}')

    # Create symlink with different name
    db = tmp_path / "todo.json"
    db.symlink_to(sensitive_file)

    storage = TodoStorage(str(db))

    # Error should mention symlink but not the target path
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_message = str(exc_info.value)
    assert "symlink" in error_message.lower()
    # Should not contain the sensitive path components
    assert "secret_admin_credentials" not in error_message
    assert "passwords.json" not in error_message
