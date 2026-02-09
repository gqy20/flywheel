"""Regression tests for issue #2518: load() should validate file permissions.

Issue: load() reads sensitive data without checking if file permissions
are overly permissive (world/group writable).

An attacker with file access could modify permissions to make sensitive
data files world-writable, potentially allowing further tampering.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_world_writable_file_by_default(tmp_path) -> None:
    """Issue #2518: load() should reject world-writable files by default.

    A file that is writable by anyone (world-writable) is a security risk
    as it could be tampered with by other users on the system.

    Before fix: load() silently accepts world-writable files
    After fix: load() raises ValueError for world-writable files
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    storage.save([Todo(id=1, text="test")])

    # Make it world-writable (0o646 = rw-r--rw-)
    os.chmod(db, 0o646)

    # Should raise ValueError due to world-writable permissions
    with pytest.raises(ValueError, match=r"world-writable|security risk"):
        storage.load()


def test_load_rejects_group_writable_file_in_strict_mode(tmp_path) -> None:
    """Issue #2518: load() should reject group-writable files in strict mode.

    Group-writable files could be tampered with by other group members.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    storage.save([Todo(id=1, text="test")])

    # Make it group-writable (0o660 = rw-rw----)
    os.chmod(db, 0o660)

    # Should raise ValueError in strict mode
    with pytest.raises(ValueError, match=r"overly permissive|permissions"):
        storage.load(strict_permissions=True)


def test_load_accepts_restrictive_permissions(tmp_path) -> None:
    """Issue #2518: load() should accept files with proper permissions (0o600).

    Files with owner-only read/write (0o600) should always be accepted.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    storage.save([Todo(id=1, text="test")])

    # Ensure it has restrictive permissions (0o600 = rw-------)
    os.chmod(db, 0o600)

    # Should load successfully in both modes
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test"

    # Also verify strict mode accepts it
    todos = storage.load(strict_permissions=True)
    assert len(todos) == 1


def test_load_strict_mode_rejects_world_readable(tmp_path) -> None:
    """Issue #2518: load() strict mode should reject world-readable files.

    In strict mode, even world-readable (but not writable) files should be rejected.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    storage.save([Todo(id=1, text="test")])

    # Make it world-readable but not writable (0o644 = rw-r--r--)
    os.chmod(db, 0o644)

    # Should raise ValueError in strict mode
    with pytest.raises(ValueError, match=r"overly permissive|permissions"):
        storage.load(strict_permissions=True)


def test_load_non_strict_mode_warns_on_world_readable(tmp_path) -> None:
    """Issue #2518: load() should warn but not error in non-strict mode.

    In non-strict mode (default), world-readable files should trigger a warning
    but still load to maintain backward compatibility.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    storage.save([Todo(id=1, text="test")])

    # Make it world-readable but not writable (0o644)
    os.chmod(db, 0o644)

    # In default (non-strict) mode, this should succeed
    # Note: The exact behavior depends on implementation - it may warn or succeed
    # For now, we test that it at least doesn't crash
    todos = storage.load(strict_permissions=False)
    assert len(todos) == 1
