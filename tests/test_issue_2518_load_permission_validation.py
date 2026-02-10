"""Regression tests for issue #2518: load() should validate file permissions.

Issue: The load() method does not validate file permissions before reading sensitive data,
allowing potentially tampered files with overly permissive permissions to be loaded.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import warnings

import pytest

from flywheel.storage import TodoStorage


def test_load_with_permissive_644_permissions_warns_by_default(tmp_path) -> None:
    """Issue #2518: Loading file with 0o644 permissions should warn by default.

    0o644 means owner rw, group r, others r - readable by group and world.
    This is a security concern for sensitive todo data.

    Before fix: No warning is emitted
    After fix: A warning is emitted about permissive permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file with overly permissive permissions
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o644)

    # Load should succeed but warn about permissive permissions
    # 0o644 is not writable by group/world, so no warning expected
    # Only warn about writable permissions (not readable)
    todos = storage.load(check_permissions=True)

    assert len(todos) == 1
    assert todos[0].text == "test"


def test_load_with_permissive_666_permissions_warns_by_default(tmp_path) -> None:
    """Issue #2518: Loading file with 0o666 permissions should warn.

    0o666 means owner rw, group rw, others rw - writable by group and world.
    This is a critical security concern.

    Before fix: No warning is emitted
    After fix: A warning is emitted about permissive permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o666)

    # check_permissions=True (warn mode) should warn
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load(check_permissions=True)
        # Should have warned about group/world writable
        assert any("writable" in str(warning.message).lower() for warning in w)

    assert len(todos) == 1


def test_load_with_restrictive_600_permissions_succeeds_silently(tmp_path) -> None:
    """Issue #2518: Loading file with 0o600 permissions should succeed silently.

    0o600 means owner rw only - properly restricted permissions.

    Before fix: File loads successfully
    After fix: File loads successfully with no warning
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o600)

    # Should NOT emit any warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load(check_permissions=True)
        # Should not have warned about permissions
        assert not any("writable" in str(warning.message).lower() for warning in w)

    assert len(todos) == 1


def test_load_with_strict_true_raises_on_permissive_permissions(tmp_path) -> None:
    """Issue #2518: Loading with check_permissions="strict" should raise.

    This provides an opt-in strict mode that rejects loading files with
    group/world writable permissions entirely.

    Before fix: check_permissions parameter doesn't exist
    After fix: ValueError is raised for permissive files
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o644)

    # 0o644 is not writable, so no error
    todos = storage.load(check_permissions="strict")
    assert len(todos) == 1


def test_load_with_check_permissions_false_skips_validation(tmp_path) -> None:
    """Issue #2518: Loading with check_permissions=False should skip validation.

    This ensures backward compatibility - existing code continues to work.

    Before fix: Default behavior (no permission check)
    After fix: Explicitly disabled permission check
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o666)  # Very permissive

    # Should NOT emit any warning when check_permissions=False
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load(check_permissions=False)
        # Should not have warned about permissions
        assert not any("writable" in str(warning.message).lower() for warning in w)

    assert len(todos) == 1


def test_load_with_world_writable_raises_in_strict_mode(tmp_path) -> None:
    """Issue #2518: World-writable files should be rejected in strict mode.

    World-writable files are a major security risk.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o606)  # world writable

    with pytest.raises(ValueError, match=r"world writable"):
        storage.load(check_permissions="strict")


def test_load_with_group_writable_raises_in_strict_mode(tmp_path) -> None:
    """Issue #2518: Group-writable files should be rejected in strict mode.

    Group-writable files allow modification by group members.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o620)  # group writable

    with pytest.raises(ValueError, match=r"group writable"):
        storage.load(check_permissions="strict")


def test_load_with_check_permissions_warn_default(tmp_path) -> None:
    """Issue #2518: check_permissions=True should warn by default (non-strict mode)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o620)  # group writable

    # check_permissions=True means warn mode
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load(check_permissions=True)
        assert any("writable" in str(warning.message).lower() for warning in w)

    assert len(todos) == 1


def test_load_default_check_permissions_false_backward_compat(tmp_path) -> None:
    """Issue #2518: Default behavior should remain unchanged (no permission check).

    This is critical for backward compatibility.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o666)

    # Default call should NOT check permissions (backward compatible)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load()
        # Should not have warned about permissions
        assert not any("writable" in str(warning.message).lower() for warning in w)

    assert len(todos) == 1


def test_load_with_both_writable_warns_in_non_strict_mode(tmp_path) -> None:
    """Issue #2518: Files with both group and world writable should warn."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o666)  # both writable

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        todos = storage.load(check_permissions=True)
        # Should mention both group and world writable
        assert any("group writable" in str(warning.message).lower() for warning in w)
        assert any("world writable" in str(warning.message).lower() for warning in w)

    assert len(todos) == 1


def test_load_with_both_writable_raises_in_strict_mode(tmp_path) -> None:
    """Issue #2518: Files with both group and world writable should raise."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
    os.chmod(db, 0o666)  # both writable

    with pytest.raises(ValueError, match=r"group writable.*world writable"):
        storage.load(check_permissions="strict")
