"""Regression tests for issue #1986: Race condition with stale temp files.

Issue: If a temp file already exists from a previous crash, the atomic
rename operation could fail or behave unexpectedly. The fix should clean
up stale temp files before writing.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_with_stale_temp_file_from_crash(tmp_path) -> None:
    """Issue #1986: save() should succeed even if a stale temp file exists.

    A previous process crash could leave a temp file. The save() operation
    should clean up or work around stale temp files.

    Before fix: stale temp file may cause save to fail or corrupt data
    After fix: stale temp files are cleaned up before write
    """
    db = tmp_path / "todo.json"

    # Create a stale temp file simulating a previous crash
    stale_temp = tmp_path / ".todo.json.12345.tmp"
    stale_temp.write_text('{"stale": "data from crashed process"}')

    # Try to save new data - this should succeed
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="new todo"), Todo(id=2, text="another todo")]

    # This should NOT raise an exception
    storage.save(todos)

    # Verify the correct data was saved
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "new todo"
    assert loaded[1].text == "another todo"

    # Verify stale temp file was cleaned up
    assert not stale_temp.exists(), "Stale temp file should be cleaned up"


def test_save_succeeds_with_multiple_stale_temp_files(tmp_path) -> None:
    """Issue #1986: Multiple stale temp files should all be cleaned up."""
    db = tmp_path / "todo.json"

    # Create multiple stale temp files
    stale_files = [
        tmp_path / ".todo.json.old1.tmp",
        tmp_path / ".todo.json.old2.tmp",
        tmp_path / ".todo.json.abc123.tmp",
    ]

    for stale_file in stale_files:
        stale_file.write_text('{"stale": "data"}')

    # Save should succeed
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="clean save")])

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "clean save"

    # Verify all stale files matching our pattern were cleaned up
    # (Note: we only clean up files matching our temp file pattern)
    remaining_stale = [f for f in stale_files if f.exists()]
    assert len(remaining_stale) == 0, f"Stale temp files not cleaned up: {remaining_stale}"


def test_save_cleans_only_related_temp_files(tmp_path) -> None:
    """Issue #1986: Cleanup should only affect temp files for this storage."""
    db = tmp_path / "todo.json"

    # Create a stale temp file for this storage
    relevant_stale = tmp_path / ".todo.json.old.tmp"
    relevant_stale.write_text('{"relevant": "stale"}')

    # Create temp files for OTHER files (should NOT be cleaned up)
    other_stale = tmp_path / ".other.json.old.tmp"
    other_stale.write_text('{"other": "should remain"}')

    # Save should clean up only its own temp files
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Our stale file should be cleaned
    assert not relevant_stale.exists()

    # Other file's temp should NOT be cleaned
    assert other_stale.exists(), "Should not clean up temp files for other storage files"


def test_temp_file_cleanup_on_replace_failure(tmp_path) -> None:
    """Issue #1986: Temp file should be cleaned up if os.replace fails.

    Before fix: if os.replace fails, temp file is orphaned
    After fix: temp file is cleaned up in exception handler
    """
    db = tmp_path / "todo.json"

    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    # Track created temp files
    temp_files_created = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    # Simulate os.replace failure
    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("flywheel.storage.os.replace", side_effect=OSError("Simulated replace failure")),
        pytest.raises(OSError, match="Simulated replace failure"),
    ):
        storage.save(todos)

    # All temp files should be cleaned up even when os.replace fails
    for temp_file in temp_files_created:
        assert not temp_file.exists(), f"Temp file not cleaned up after failure: {temp_file}"


def test_atomic_write_with_race_condition_simulation(tmp_path) -> None:
    """Issue #1986: Simulate race condition with concurrent processes.

    This test simulates the scenario where:
    1. Process A creates a temp file
    2. Process A crashes before os.replace
    3. Process B tries to write to the same file

    Process B should succeed.
    """
    db = tmp_path / "todo.json"

    # Simulate stale temp from crashed process
    # We use the actual prefix pattern that TodoStorage uses
    crashed_temp = tmp_path / ".todo.json.crashed_pid.tmp"
    crashed_temp.write_text('{"from": "crashed process"}')

    # New process tries to save
    storage = TodoStorage(str(db))
    new_todos = [
        Todo(id=1, text="recovered data"),
        Todo(id=2, text="new data"),
    ]

    # Should succeed without errors
    storage.save(new_todos)

    # Verify correct data was saved
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "recovered data"
    assert loaded[1].text == "new data"

    # Verify crashed temp was cleaned up
    assert not crashed_temp.exists()


def test_save_creates_unique_temp_names(tmp_path) -> None:
    """Issue #1986: Verify temp file names are unique (already fixed via mkstemp).

    This is a sanity check that tempfile.mkstemp is being used and
    produces unique names.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track all temp file names created
    temp_names = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_names.append(Path(path).name)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=tracking_mkstemp):
        # Do multiple saves
        for i in range(5):
            storage.save([Todo(id=i, text=f"todo {i}")])

    # All temp names should be unique
    assert len(temp_names) == 5, f"Expected 5 temp files, got {len(temp_names)}"
    assert len(set(temp_names)) == 5, f"Temp names should be unique: {temp_names}"

    # All should start with the correct prefix and end with .tmp
    for name in temp_names:
        assert name.startswith(".todo.json."), f"Temp file should have correct prefix: {name}"
        assert name.endswith(".tmp"), f"Temp file should end with .tmp: {name}"
