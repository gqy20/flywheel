"""Regression tests for issue #2518: load() should validate file permissions.

Issue: load() does not validate file permissions before reading sensitive data.

The load() method should detect potentially tampered files by checking
if they have overly permissive permissions (world/group writable).

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_world_writable_file_strict(tmp_path) -> None:
    """Issue #2518: load() should reject world-writable files in strict mode.

    World-writable files (0o666) could indicate tampering.
    In strict mode, these should raise ValueError.

    Before fix: World-writable files are loaded without warning
    After fix: ValueError is raised for world-writable files in strict mode
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file with restrictive permissions first
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Make the file world-writable (0o666 - rw-rw-rw-)
    os.chmod(db, 0o666)

    # Verify the file is actually world-writable
    mode = db.stat().st_mode & 0o777
    assert mode == 0o666, f"Expected 0o666, got 0o{mode:o}"
    assert db.stat().st_mode & stat.S_IWOTH, "File should be world-writable"

    # Should raise ValueError in strict mode (validate_permissions=True, strict=True)
    with pytest.raises(ValueError, match=r"overly permissive|world-writable|permissions"):
        storage.load(validate_permissions=True, strict=True)


def test_load_rejects_group_writable_file_strict(tmp_path) -> None:
    """Issue #2518: load() should reject group-writable files in strict mode.

    Group-writable files (0o660) could allow unauthorized modification.
    In strict mode, these should raise ValueError.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Make the file group-writable (0o660)
    os.chmod(db, 0o660)

    # Verify the file is group-writable
    assert db.stat().st_mode & stat.S_IWGRP, "File should be group-writable"

    # Should raise ValueError in strict mode
    with pytest.raises(ValueError, match=r"overly permissive|group-writable|permissions"):
        storage.load(validate_permissions=True, strict=True)


def test_load_accepts_restrictive_permissions_strict(tmp_path) -> None:
    """Issue #2518: load() should accept files with 0o600 permissions.

    Files with owner-only read/write (0o600) are secure and should
    always be accepted, even in strict mode.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Verify file has restrictive permissions (should be 0o600 from save())
    mode = db.stat().st_mode & 0o777
    assert mode == 0o600, f"Expected 0o600, got 0o{mode:o}"

    # Should load successfully in strict mode
    loaded = storage.load(validate_permissions=True, strict=True)
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_load_warns_on_permissive_file_non_strict(tmp_path) -> None:
    """Issue #2518: load() should warn but not fail for permissive files in non-strict mode.

    When strict=False, the load should succeed but emit a warning.
    This maintains backward compatibility while providing security visibility.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Make the file world-writable (0o666)
    os.chmod(db, 0o666)

    # Should load with warning in non-strict mode
    # (The warning mechanism will be implementation-specific)
    loaded = storage.load(validate_permissions=True, strict=False)
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_load_skips_validation_when_disabled(tmp_path) -> None:
    """Issue #2518: load() should skip permission validation when validate_permissions=False.

    For backward compatibility, when validate_permissions is False or not specified,
    no permission checks should be performed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Make the file world-writable
    os.chmod(db, 0o666)

    # Should load without any checks when validation is disabled
    loaded = storage.load(validate_permissions=False)
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_load_default_behavior_no_validation(tmp_path) -> None:
    """Issue #2518: load() default behavior should not validate permissions.

    For maximum backward compatibility, the default behavior (no arguments)
    should NOT perform permission validation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Make the file world-writable
    os.chmod(db, 0o666)

    # Default behavior: no validation, should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
