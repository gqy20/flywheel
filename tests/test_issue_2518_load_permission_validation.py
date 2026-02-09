"""Regression tests for issue #2518: load() should validate file permissions.

Issue: load() does not validate file permissions before reading sensitive data.

An attacker with file system access could modify permissions to make the file
world-writable, which may indicate tampering. This test FAILS before the fix
and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_world_writable_file_by_default(tmp_path) -> None:
    """Issue #2518: load() should reject files with world-writable permissions.

    A world-writable file (e.g., 0o666 or 0o644) is a security risk as it
    indicates potential tampering. load() should raise an error when
    validate_permissions=True (the default).

    Before fix: load() silently reads world-writable files
    After fix: load() raises ValueError for world-writable files
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo file with restrictive permissions
    todos = [Todo(id=1, text="sensitive data")]
    storage.save(todos)

    # Simulate an attacker making the file world-writable
    os.chmod(db, 0o644)  # rw-r--r--

    # load() should raise ValueError with validate_permissions=True
    with pytest.raises(ValueError, match=r"overly permissive|world-writable|permissions"):
        storage.load(validate_permissions=True)

    # But should still work without validation (backward compatibility)
    loaded = storage.load(validate_permissions=False)
    assert len(loaded) == 1
    assert loaded[0].text == "sensitive data"


def test_load_accepts_restrictive_permissions(tmp_path) -> None:
    """Issue #2518: load() should accept files with restrictive permissions (0o600)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo file with restrictive permissions
    todos = [Todo(id=1, text="secure data")]
    storage.save(todos)

    # Verify the file has 0o600 permissions (set by save())
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

    # load() with validate_permissions=True should succeed
    loaded = storage.load(validate_permissions=True)
    assert len(loaded) == 1
    assert loaded[0].text == "secure data"


def test_load_rejects_group_writable_file(tmp_path) -> None:
    """Issue #2518: load() should reject files with group-writable permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo file
    todos = [Todo(id=1, text="data")]
    storage.save(todos)

    # Make the file group-writable (0o660 - rw-rw----)
    os.chmod(db, 0o660)

    # load() with validate_permissions=True should raise ValueError
    with pytest.raises(ValueError, match=r"overly permissive|group-writable|permissions"):
        storage.load(validate_permissions=True)


def test_load_rejects_world_writable_anyone_can_write(tmp_path) -> None:
    """Issue #2518: load() should reject any file others can write to."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo file
    todos = [Todo(id=1, text="data")]
    storage.save(todos)

    # Test various world-writable modes
    dangerous_modes = [
        0o666,  # rw-rw-rw- (world readable and writable)
        0o644,  # rw-r--r-- (world readable)
        0o606,  # rw----rw- (world writable)
        0o642,  # rw-r---w- (others writable)
    ]

    for mode in dangerous_modes:
        os.chmod(db, mode)

        with pytest.raises(ValueError, match=r"overly permissive|permissions"):
            storage.load(validate_permissions=True)


def test_load_backward_compatibility_no_validation_by_default(tmp_path) -> None:
    """Issue #2518: load() should work without validation for backward compatibility.

    When validate_permissions is not specified or set to False, load() should
    work as before (without permission validation).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo file with insecure permissions
    todos = [Todo(id=1, text="data")]
    storage.save(todos)
    os.chmod(db, 0o644)

    # Without validate_permissions, should work (backward compatible)
    loaded = storage.load()  # No validate_permissions parameter
    assert len(loaded) == 1

    # Explicitly set to False
    loaded = storage.load(validate_permissions=False)
    assert len(loaded) == 1


def test_load_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Issue #2518: Permission validation should not affect nonexistent file handling."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list regardless of validate_permissions
    loaded = storage.load(validate_permissions=True)
    assert loaded == []

    loaded = storage.load(validate_permissions=False)
    assert loaded == []


def test_permission_check_happens_after_size_check(tmp_path) -> None:
    """Issue #2518: Permission validation should happen after size check for proper error ordering."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large file (over 10MB)
    large_content = "x" * (11 * 1024 * 1024)
    db.write_text(large_content)
    os.chmod(db, 0o644)

    # Should fail with size error, not permission error
    with pytest.raises(ValueError, match="too large"):
        storage.load(validate_permissions=True)
