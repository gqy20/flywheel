"""Regression tests for issue #5899: load() should warn on insecure file permissions.

Issue: load() method reads files without verifying file permissions.
If a file was externally modified to have overly permissive permissions
(e.g., group or world readable), sensitive data could leak.

The save() method sets 0o600 permissions, but load() should warn if
permissions have been relaxed externally.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import json
import logging
import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_warns_on_group_readable_file(tmp_path, caplog) -> None:
    """Issue #5899: load() should warn when file has group read permission.

    Create a file with 0o640 permissions (group readable) and verify
    that load() emits a warning about insecure permissions.
    """
    db = tmp_path / "todo.json"

    # Create a valid todo file
    todos = [Todo(id=1, text="sensitive task")]
    data = [todo.to_dict() for todo in todos]
    db.write_text(json.dumps(data), encoding="utf-8")

    # Set overly permissive permissions (group readable)
    os.chmod(db, 0o640)  # rw-r-----

    storage = TodoStorage(str(db))

    # Load should succeed but emit a warning
    with caplog.at_level(logging.WARNING, logger="flywheel.storage"):
        loaded = storage.load()

    # Data should still load correctly
    assert len(loaded) == 1
    assert loaded[0].text == "sensitive task"

    # A warning should have been logged about insecure permissions
    assert any("insecure" in record.message.lower() for record in caplog.records), (
        f"Expected warning about insecure permissions, got: {[r.message for r in caplog.records]}"
    )


def test_load_warns_on_world_readable_file(tmp_path, caplog) -> None:
    """Issue #5899: load() should warn when file has world read permission.

    Create a file with 0o644 permissions (world readable) and verify
    that load() emits a warning about insecure permissions.
    """
    db = tmp_path / "todo.json"

    # Create a valid todo file
    todos = [Todo(id=1, text="secret task")]
    data = [todo.to_dict() for todo in todos]
    db.write_text(json.dumps(data), encoding="utf-8")

    # Set overly permissive permissions (world readable)
    os.chmod(db, 0o644)  # rw-r--r--

    storage = TodoStorage(str(db))

    # Load should succeed but emit a warning
    with caplog.at_level(logging.WARNING, logger="flywheel.storage"):
        loaded = storage.load()

    # Data should still load correctly
    assert len(loaded) == 1
    assert loaded[0].text == "secret task"

    # A warning should have been logged about insecure permissions
    assert any("insecure" in record.message.lower() for record in caplog.records), (
        f"Expected warning about insecure permissions, got: {[r.message for r in caplog.records]}"
    )


def test_load_no_warning_on_secure_file(tmp_path, caplog) -> None:
    """Issue #5899: load() should NOT warn when file has secure 0o600 permissions.

    Create a file with 0o600 permissions (owner only) and verify
    that load() does NOT emit a warning.
    """
    db = tmp_path / "todo.json"

    # Create a valid todo file
    todos = [Todo(id=1, text="private task")]
    data = [todo.to_dict() for todo in todos]
    db.write_text(json.dumps(data), encoding="utf-8")

    # Set secure permissions (owner read/write only)
    os.chmod(db, 0o600)  # rw-------

    storage = TodoStorage(str(db))

    # Load should succeed without warnings
    with caplog.at_level(logging.WARNING, logger="flywheel.storage"):
        loaded = storage.load()

    # Data should load correctly
    assert len(loaded) == 1
    assert loaded[0].text == "private task"

    # No warning should have been logged
    insecure_warnings = [r for r in caplog.records if "insecure" in r.message.lower()]
    assert len(insecure_warnings) == 0, (
        f"Expected no warnings, got: {[r.message for r in insecure_warnings]}"
    )


def test_load_no_warning_on_nonexistent_file(tmp_path, caplog) -> None:
    """Issue #5899: load() should NOT warn when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load should return empty list without warnings
    with caplog.at_level(logging.WARNING, logger="flywheel.storage"):
        loaded = storage.load()

    assert loaded == []
    assert len(caplog.records) == 0, (
        f"Expected no warnings, got: {[r.message for r in caplog.records]}"
    )
