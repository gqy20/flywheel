"""Regression tests for issue #5514: load() should verify file permissions.

Issue: The load() function does not validate JSON file permissions, allowing
an attacker who can modify file permissions to leak sensitive information.

The save() function sets restrictive permissions (0o600 - owner read/write only),
but load() does not verify that these permissions are still in place.

Security risk: An attacker could change file permissions to 0o644 (world-readable)
after the file is saved, allowing other users on the system to read sensitive data.

Acceptance criteria:
- load() warns when file has overly permissive permissions (group/other readable)
- Backward compatible: warns instead of refusing to load
"""

from __future__ import annotations

import json
import os
import stat
import warnings
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_warns_on_world_readable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file is world-readable.

    Create a file with 0o644 permissions (world-readable) and verify
    that load() emits a warning about insecure permissions.
    """
    db = tmp_path / "todo.json"

    # Create a world-readable file (simulating attacker modification)
    db.write_text(json.dumps([{"id": 1, "text": "sensitive data", "done": False}]))
    os.chmod(db, 0o644)  # rw-r--r-- (world-readable)

    # Verify the file is actually world-readable
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode & stat.S_IROTH, "Test setup failed: file should be world-readable"

    storage = TodoStorage(str(db))

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Should have loaded successfully
    assert len(todos) == 1
    assert todos[0].text == "sensitive data"

    # Should have emitted a warning about permissions
    assert len(w) == 1, f"Expected 1 warning, got {len(w)}"
    assert "permission" in str(w[0].message).lower(), f"Warning message should mention permissions: {w[0].message}"


def test_load_warns_on_group_readable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file is group-readable.

    Create a file with 0o640 permissions (group-readable) and verify
    that load() emits a warning about insecure permissions.
    """
    db = tmp_path / "todo.json"

    # Create a group-readable file
    db.write_text(json.dumps([{"id": 1, "text": "secret", "done": False}]))
    os.chmod(db, 0o640)  # rw-r----- (group-readable)

    # Verify the file is actually group-readable
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode & stat.S_IRGRP, "Test setup failed: file should be group-readable"

    storage = TodoStorage(str(db))

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Should have loaded successfully
    assert len(todos) == 1
    assert todos[0].text == "secret"

    # Should have emitted a warning about permissions
    assert len(w) == 1, f"Expected 1 warning, got {len(w)}"
    assert "permission" in str(w[0].message).lower(), f"Warning message should mention permissions: {w[0].message}"


def test_load_no_warning_on_secure_file(tmp_path) -> None:
    """Issue #5514: load() should NOT warn when file has secure permissions.

    Create a file with 0o600 permissions (owner read/write only) and verify
    that load() does not emit a warning.
    """
    db = tmp_path / "todo.json"

    # Create a secure file (0o600 - owner read/write only)
    db.write_text(json.dumps([{"id": 1, "text": "data", "done": False}]))
    os.chmod(db, 0o600)  # rw------- (owner only)

    storage = TodoStorage(str(db))

    # load() should NOT emit a warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    # Should have loaded successfully
    assert len(todos) == 1
    assert todos[0].text == "data"

    # Should NOT have emitted any warnings about permissions
    permission_warnings = [warning for warning in w if "permission" in str(warning.message).lower()]
    assert len(permission_warnings) == 0, f"Unexpected warnings: {[str(x.message) for x in permission_warnings]}"


def test_load_no_warning_on_nonexistent_file(tmp_path) -> None:
    """Issue #5514: load() should not warn when file doesn't exist.

    The permission check only applies to existing files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # load() on nonexistent file should return empty list without warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

    assert todos == []
    assert len(w) == 0, f"Unexpected warnings: {[str(x.message) for x in w]}"
