"""Regression tests for issue #5899: load() should warn on overly permissive file permissions.

Issue: The load() method reads files without checking if permissions are too loose.
While save() sets 0o600 permissions, external processes could modify the file to have
looser permissions (e.g., 0o644), potentially exposing sensitive todo data.

The fix: load() should check file permissions and emit a warning when group or other
read permissions are present (permissions more permissive than 0o600).

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
import warnings

from flywheel.storage import TodoStorage


def test_load_warns_on_group_readable_file(tmp_path) -> None:
    """Issue #5899: load() should warn when file has group read permission.

    Before fix: No warning is emitted
    After fix: A UserWarning is emitted for files with group/other permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with group-readable permissions (0o640)
    db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o640)  # rw-r-----

    # Verify file was created with correct permissions
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o640, f"Setup failed: expected 0o640, got {oct(file_mode)}"

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        storage.load()

        # After fix: There should be at least one warning about permissions
        permission_warnings = [
            warning
            for warning in w
            if "permission" in str(warning.message).lower()
            or "insecure" in str(warning.message).lower()
        ]

        assert len(permission_warnings) > 0, (
            "Expected a warning about insecure file permissions when loading "
            "a file with 0o640 permissions (group-readable). "
            f"Got {len(w)} warnings: {[str(x.message) for x in w]}"
        )


def test_load_warns_on_world_readable_file(tmp_path) -> None:
    """Issue #5899: load() should warn when file has world/other read permission."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with world-readable permissions (0o644)
    db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r--

    # Verify file was created with correct permissions
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o644, f"Setup failed: expected 0o644, got {oct(file_mode)}"

    # load() should emit a warning about insecure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        storage.load()

        permission_warnings = [
            warning
            for warning in w
            if "permission" in str(warning.message).lower()
            or "insecure" in str(warning.message).lower()
        ]

        assert len(permission_warnings) > 0, (
            "Expected a warning about insecure file permissions when loading "
            "a file with 0o644 permissions (world-readable)."
        )


def test_load_no_warning_on_secure_permissions(tmp_path) -> None:
    """Issue #5899: load() should NOT warn when file has secure 0o600 permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with secure permissions (0o600)
    db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")
    os.chmod(db, 0o600)  # rw-------

    # Verify file was created with correct permissions
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o600, f"Setup failed: expected 0o600, got {oct(file_mode)}"

    # load() should NOT emit a warning for secure permissions
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        storage.load()

        permission_warnings = [
            warning
            for warning in w
            if "permission" in str(warning.message).lower()
            or "insecure" in str(warning.message).lower()
        ]

        assert len(permission_warnings) == 0, (
            f"Should NOT warn about secure 0o600 permissions. "
            f"Got warnings: {[str(x.message) for x in permission_warnings]}"
        )


def test_load_no_warning_on_nonexistent_file(tmp_path) -> None:
    """Issue #5899: load() should NOT warn when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, so no permission check needed
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = storage.load()

        assert result == [], "Should return empty list for nonexistent file"

        permission_warnings = [
            warning
            for warning in w
            if "permission" in str(warning.message).lower()
            or "insecure" in str(warning.message).lower()
        ]

        assert len(permission_warnings) == 0, (
            "Should NOT warn about permissions for nonexistent file."
        )
