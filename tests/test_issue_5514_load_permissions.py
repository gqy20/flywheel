"""Regression tests for issue #5514: load() should validate JSON file permissions.

Issue: load() does not validate file permissions before reading. An attacker
could modify file permissions to make it world-readable, potentially leaking
sensitive information. The save() method correctly sets 0o600 permissions,
but load() should warn if permissions have been changed.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import warnings

from flywheel.storage import TodoStorage


def test_load_warns_on_world_readable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file has world-readable permissions.

    A file with 0o644 permissions is readable by everyone on the system,
    which could leak sensitive todo data.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with overly permissive permissions (world-readable)
    db.write_text('[{"id": 1, "text": "secret data", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r-- (world-readable)

    # load() should emit a security warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

        # Should have warned about insecure permissions
        security_warnings = [x for x in w if "permission" in str(x.message).lower()]
        assert len(security_warnings) > 0, (
            "load() should warn about world-readable file permissions"
        )

    # Data should still load (backward compatibility - warn, don't reject)
    assert len(todos) == 1
    assert todos[0].text == "secret data"


def test_load_warns_on_group_readable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file has group-readable permissions.

    A file with 0o640 permissions is readable by the group, which could
    leak sensitive todo data to other users in the same group.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with group-readable permissions
    db.write_text('[{"id": 1, "text": "confidential", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o640)  # rw-r----- (group-readable)

    # load() should emit a security warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

        # Should have warned about insecure permissions
        security_warnings = [x for x in w if "permission" in str(x.message).lower()]
        assert len(security_warnings) > 0, (
            "load() should warn about group-readable file permissions"
        )

    # Data should still load (backward compatibility)
    assert len(todos) == 1


def test_load_accepts_secure_permissions(tmp_path) -> None:
    """Issue #5514: load() should NOT warn for properly secured files (0o600).

    Files with 0o600 permissions (owner read/write only) are secure.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with secure permissions (same as save() uses)
    db.write_text('[{"id": 1, "text": "secure data", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o600)  # rw------- (owner only)

    # load() should NOT warn for secure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

        # Should NOT have warned about permissions
        permission_warnings = [x for x in w if "permission" in str(x.message).lower()]
        assert len(permission_warnings) == 0, (
            f"load() should not warn about secure permissions, but got: {[str(x.message) for x in permission_warnings]}"
        )

    # Data should load normally
    assert len(todos) == 1
    assert todos[0].text == "secure data"


def test_load_warns_on_world_writable_file(tmp_path) -> None:
    """Issue #5514: load() should warn when file has world-writable permissions.

    A file with write permissions for others is a serious security risk.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with world-writable permissions
    db.write_text('[{"id": 1, "text": "data", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o606)  # rw----rw- (world-writable)

    # load() should emit a security warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()

        # Should have warned about insecure permissions
        security_warnings = [x for x in w if "permission" in str(x.message).lower()]
        assert len(security_warnings) > 0, (
            "load() should warn about world-writable file permissions"
        )

    assert len(todos) == 1
