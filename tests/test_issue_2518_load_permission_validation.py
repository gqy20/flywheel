"""Regression tests for issue #2518: load() should validate file permissions before reading sensitive data.

Issue: The load() method does not validate file permissions before reading sensitive data.
An attacker with file access could modify permissions to make world-writable files.

Fix: Add optional permission validation in load() method with strict=False by default.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
import warnings

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_world_writable_file_strict_mode(tmp_path) -> None:
    """Issue #2518: File with world-writable permissions (0o644) should be rejected in strict mode.

    Before fix: load() accepts world-writable files without validation
    After fix: load() raises ValueError for permissive files when strict=True
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with valid content
    storage.save([Todo(id=1, text="test")])

    # Make file world-writable (0o644 = rw-r--r--)
    os.chmod(db, 0o644)

    # Verify file actually has the permissions we set
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o644, f"Failed to set test file permissions: {oct(file_mode)}"

    # In strict mode, should raise ValueError
    with pytest.raises(ValueError, match="overly permissive permissions"):
        storage.load(strict=True)


def test_load_rejects_group_writable_file_strict_mode(tmp_path) -> None:
    """Issue #2518: File with group-writable permissions (0o660) should be rejected in strict mode."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with valid content
    storage.save([Todo(id=1, text="test")])

    # Make file group-writable (0o660 = rw-rw----)
    os.chmod(db, 0o660)

    # Verify file actually has the permissions we set
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o660, f"Failed to set test file permissions: {oct(file_mode)}"

    # In strict mode, should raise ValueError
    with pytest.raises(ValueError, match="overly permissive permissions"):
        storage.load(strict=True)


def test_load_accepts_restrictive_permissions_strict_mode(tmp_path) -> None:
    """Issue #2518: File with restrictive permissions (0o600) should always be accepted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with valid content - TodoStorage.save() creates files with 0o600
    storage.save([Todo(id=1, text="test", done=False)])

    # Verify file has restrictive permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"Expected 0o600, got: {oct(file_mode)}"

    # In strict mode, restrictive permissions should succeed
    todos = storage.load(strict=True)
    assert len(todos) == 1
    assert todos[0].text == "test"
    assert todos[0].done is False


def test_load_warns_on_permissive_permissions_default_mode(tmp_path) -> None:
    """Issue #2518: File with permissive permissions should emit warning in default mode (strict=False)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with valid content
    storage.save([Todo(id=1, text="test")])

    # Make file world-writable
    os.chmod(db, 0o644)

    # In default mode (strict=False), should emit warning but succeed
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()  # strict=False is default

        # Should have emitted a warning
        assert len(w) == 1
        assert "overly permissive permissions" in str(w[0].message).lower()

    # Load should still succeed
    assert len(todos) == 1
    assert todos[0].text == "test"


def test_load_no_warning_for_restrictive_permissions_default_mode(tmp_path) -> None:
    """Issue #2518: File with restrictive permissions should not emit warning in default mode."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with valid content - TodoStorage.save() creates files with 0o600
    storage.save([Todo(id=1, text="test")])

    # Verify file has restrictive permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"Expected 0o600, got: {oct(file_mode)}"

    # In default mode, should not emit warning for restrictive permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()  # strict=False is default

        # Should NOT have emitted a warning
        assert len(w) == 0

    # Load should succeed
    assert len(todos) == 1
    assert todos[0].text == "test"


def test_load_handles_missing_file_gracefully_with_strict(tmp_path) -> None:
    """Issue #2518: load() should return empty list for non-existent files even with strict=True."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Non-existent file should return empty list regardless of strict mode
    todos = storage.load(strict=True)
    assert todos == []
