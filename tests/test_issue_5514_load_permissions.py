"""Regression tests for issue #5514: load() should warn on insecure file permissions.

Issue: load() does not validate JSON file permissions. An attacker who can modify
file permissions could make sensitive data world-readable (e.g., 0o644), allowing
other users on the system to read the todo data.

The save() method sets 0o600 (owner read/write only) permissions, but load()
does not verify that the file maintains these secure permissions. If file
permissions are accidentally or maliciously changed to be more permissive,
the user should be warned.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
import warnings
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_warns_on_world_readable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file has overly permissive permissions.

    Before fix: load() silently reads files with insecure permissions
    After fix: load() emits a warning when file permissions are too permissive
    """
    db = tmp_path / "todo.json"

    # Create a file with insecure permissions (world-readable)
    db.write_text('[{"id": 1, "text": "secret task"}]', encoding="utf-8")

    # Set permissions to 0o644 (rw-r--r--) - world-readable
    os.chmod(db, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    storage = TodoStorage(str(db))

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Verify data was loaded correctly
    assert len(todos) == 1
    assert todos[0].text == "secret task"

    # Verify a warning was issued
    assert len(w) >= 1, "Expected a warning about insecure file permissions"
    assert any("permission" in str(warning.message).lower() for warning in w), (
        f"Expected warning about permissions, got: {[str(warning.message) for warning in w]}"
    )


def test_load_warns_on_group_readable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file is readable by group (0o640)."""
    db = tmp_path / "todo.json"

    # Create a file with group-readable permissions
    db.write_text('[{"id": 1, "text": "task"}]', encoding="utf-8")

    # Set permissions to 0o640 (rw-r-----) - group-readable
    os.chmod(db, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)

    storage = TodoStorage(str(db))

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Verify data was loaded correctly
    assert len(todos) == 1

    # Verify a warning was issued
    assert len(w) >= 1, "Expected a warning about insecure file permissions"


def test_load_no_warning_on_secure_permissions(tmp_path) -> None:
    """Issue #5514: load() should NOT warn when file has secure 0o600 permissions."""
    db = tmp_path / "todo.json"

    # Create a file with secure permissions
    db.write_text('[{"id": 1, "text": "task"}]', encoding="utf-8")

    # Set permissions to 0o600 (rw-------) - owner only
    os.chmod(db, stat.S_IRUSR | stat.S_IWUSR)

    storage = TodoStorage(str(db))

    # load() should NOT emit a warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Verify data was loaded correctly
    assert len(todos) == 1

    # Verify NO warning was issued about permissions
    permission_warnings = [warning for warning in w if "permission" in str(warning.message).lower()]
    assert len(permission_warnings) == 0, (
        f"Expected no permission warning for secure file, got: {[str(w.message) for w in permission_warnings]}"
    )


def test_load_no_warning_on_nonexistent_file(tmp_path) -> None:
    """Issue #5514: load() should NOT warn when file doesn't exist (returns empty list)."""
    db = tmp_path / "nonexistent.json"

    storage = TodoStorage(str(db))

    # load() should return empty list without warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Verify empty list was returned
    assert todos == []

    # Verify NO warnings were issued
    assert len(w) == 0, f"Expected no warnings for nonexistent file, got: {[str(warning.message) for warning in w]}"
