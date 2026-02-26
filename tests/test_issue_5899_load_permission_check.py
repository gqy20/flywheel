"""Regression tests for issue #5899: load() should warn on overly permissive file.

Issue: load() reads files without checking if permissions are too loose.
The save() method sets 0o600 (owner read/write only), but if the file
is modified externally to have group/other read permissions, sensitive
todo data could be exposed.

This test verifies that load() emits a warning when file permissions
are too permissive (group or other readable).
"""

from __future__ import annotations

import os
import stat
import warnings

from flywheel.storage import TodoStorage


def test_load_warns_on_group_readable_file(tmp_path) -> None:
    """Issue #5899: load() should warn when file is group readable (0o640).

    Before fix: load() silently reads file with overly permissive permissions
    After fix: load() emits UserWarning about insecure permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with group-readable permissions (insecure)
    db.write_text('[]', encoding="utf-8")
    os.chmod(db, 0o640)  # rw-r-----

    # Verify permissions were set correctly
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o640, f"Setup failed: expected 0o640, got {oct(file_mode)}"

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        storage.load()

        # Should have at least one warning about permissions
        permission_warnings = [
            w
            for w in caught_warnings
            if "permission" in str(w.message).lower()
            or "insecure" in str(w.message).lower()
        ]
        assert len(permission_warnings) >= 1, (
            f"Expected warning about insecure permissions, got: "
            f"{[str(w.message) for w in caught_warnings]}"
        )


def test_load_warns_on_world_readable_file(tmp_path) -> None:
    """Issue #5899: load() should warn when file is world readable (0o644)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with world-readable permissions (insecure)
    db.write_text('[]', encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r--

    # Verify permissions were set correctly
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o644, f"Setup failed: expected 0o644, got {oct(file_mode)}"

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        storage.load()

        permission_warnings = [
            w
            for w in caught_warnings
            if "permission" in str(w.message).lower()
            or "insecure" in str(w.message).lower()
        ]
        assert len(permission_warnings) >= 1, (
            f"Expected warning about insecure permissions, got: "
            f"{[str(w.message) for w in caught_warnings]}"
        )


def test_load_no_warning_on_secure_permissions(tmp_path) -> None:
    """Issue #5899: load() should NOT warn when file has secure permissions (0o600)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with secure permissions
    db.write_text('[]', encoding="utf-8")
    os.chmod(db, 0o600)  # rw-------

    # Verify permissions were set correctly
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o600, f"Setup failed: expected 0o600, got {oct(file_mode)}"

    # load() should NOT emit a warning
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        storage.load()

        permission_warnings = [
            w
            for w in caught_warnings
            if "permission" in str(w.message).lower()
            or "insecure" in str(w.message).lower()
        ]
        assert len(permission_warnings) == 0, (
            f"Should not warn on secure permissions, got: "
            f"{[str(w.message) for w in permission_warnings]}"
        )


def test_load_no_warning_on_nonexistent_file(tmp_path) -> None:
    """Issue #5899: load() should NOT warn when file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File doesn't exist - should return empty list without warning
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        result = storage.load()

        assert result == []
        permission_warnings = [
            w
            for w in caught_warnings
            if "permission" in str(w.message).lower()
            or "insecure" in str(w.message).lower()
        ]
        assert len(permission_warnings) == 0
