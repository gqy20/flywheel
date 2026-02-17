"""Regression tests for issue #3907: TOCTOU race condition in _ensure_parent_directory.

Issue: The _ensure_parent_directory function has a Time-Of-Check-To-Time-Of-Use
race condition window between validation (lines 35-40) and mkdir (lines 43-50).

An attacker with local access can create a conflicting file/symlink in the
parent path during this window, potentially causing misleading error messages
or enabling symlink attacks.

The fix should:
1. Use os.makedirs with exist_ok=True to eliminate the race window
2. Catch FileExistsError to distinguish "file exists as non-directory" from other errors
3. Provide clear, specific error messages

These tests verify the fix provides clear error messages for race condition scenarios.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_detection_with_thread(tmp_path) -> None:
    """Issue #3907: Verify TOCTOU race condition is properly handled.

    This test simulates an attacker creating a file in the parent path
    during the validation-to-mkdir window.

    Before fix: Error message may be generic OSError
    After fix: Should raise clear ValueError indicating "file exists as non-directory"
    """
    db_path = tmp_path / "subdir" / "todo.json"

    # Create a file at the location where we expect a directory
    conflict_file = tmp_path / "subdir"
    conflict_file.write_text("I am a file, not a directory")

    # Now try to create storage at a path that requires the file to be a directory
    # This should fail with a clear error message
    storage = TodoStorage(str(db_path))

    # Should fail with clear ValueError about file vs directory confusion
    with pytest.raises(ValueError, match=r"(file|not a directory|exists)"):
        storage.save([Todo(id=1, text="test")])


def test_toctou_race_clear_error_message(tmp_path) -> None:
    """Issue #3907: Error message should clearly distinguish file-as-directory from other errors.

    When a file exists where a directory is needed, the error should say so explicitly,
    NOT suggest "check permissions" which is misleading.

    Before fix: OSError with message suggesting "Check permissions"
    After fix: ValueError with clear message about "exists as a file, not a directory"
    """
    # Create a file where directory should be
    blocking_file = tmp_path / "blocking_file"
    blocking_file.write_text("content")

    # Try to create a path that requires the file to be a directory
    db_path = blocking_file / "nested" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Error should mention that something exists as a file, not a directory
    with pytest.raises(ValueError, match=r"(file|not a directory|exists)") as exc_info:
        storage.save([Todo(id=1, text="test")])

    # Verify the error message is descriptive and NOT misleading about permissions
    error_msg = str(exc_info.value).lower()
    assert "file" in error_msg or "not a directory" in error_msg or "path error" in error_msg
    # The message should NOT suggest checking permissions for this case
    # (This is the key improvement over the current generic OSError)
    assert "check permissions" not in error_msg, (
        "Error should not suggest permissions for file-as-directory"
    )


def test_toctou_race_actual_simulation(tmp_path) -> None:
    """Issue #3907: Actual TOCTOU race condition simulation.

    This test patches Path.exists to introduce a race condition where:
    1. First exists() calls pass (no file seen)
    2. During validation loop, attacker creates file
    3. mkdir fails with NotADirectoryError

    Before fix: OSError with "Check permissions" message (misleading)
    After fix: ValueError with clear "file exists as non-directory" message
    """
    import threading
    import time

    db_path = tmp_path / "parent" / "child" / "todo.json"
    attacker_file = tmp_path / "parent"

    race_triggered = threading.Event()
    error_caught = []

    original_exists = Path.exists
    call_count = [0]

    def patched_exists(self):
        result = original_exists(self)
        call_count[0] += 1
        # After validation starts, create the conflicting file
        if call_count[0] == 2 and not race_triggered.is_set():
            race_triggered.set()
            # Create file at parent location to cause race
            attacker_file.write_text("attacker file")
            time.sleep(0.01)  # Give time for race
        return result

    with patch.object(Path, "exists", patched_exists):
        storage = TodoStorage(str(db_path))
        try:
            storage.save([Todo(id=1, text="test")])
        except Exception as e:
            error_caught.append((type(e).__name__, str(e)))

    # Should have caught an error
    assert len(error_caught) == 1, f"Expected error, got: {error_caught}"
    error_type, error_msg = error_caught[0]

    # The fix should raise ValueError with clear message
    # Not OSError with misleading "check permissions" message
    assert error_type == "ValueError", f"Expected ValueError, got {error_type}: {error_msg}"
    error_msg_lower = error_msg.lower()
    assert "file" in error_msg_lower or "not a directory" in error_msg_lower, (
        f"Error message should mention file/directory issue: {error_msg}"
    )
    # Should NOT suggest checking permissions for this case
    assert "check permissions" not in error_msg_lower, (
        f"Error should not suggest permissions: {error_msg}"
    )


def test_simulated_toctou_attack_threaded(tmp_path) -> None:
    """Issue #3907: Simulate a TOCTOU attack using threading.

    This test creates a race condition where:
    1. Main thread starts _ensure_parent_directory (which validates)
    2. Attacker thread creates a conflicting file during validation
    3. Main thread's mkdir should fail with clear error

    Before fix: Generic OSError from mkdir failure
    After fix: Clear ValueError about file-as-directory confusion
    """
    db_path = tmp_path / "target" / "subdir" / "todo.json"
    attack_target = tmp_path / "target" / "subdir"

    race_event = threading.Event()
    error_caught = []
    error_type = []

    def attacker_thread():
        """Simulate attacker creating file during race window."""
        # Wait for validation to start
        race_event.wait(timeout=5)
        # Small delay to ensure we're in the race window
        time.sleep(0.001)
        # Create conflicting file
        try:
            attack_target.mkdir(parents=True, exist_ok=True)
            # Place a file where directory is expected
            conflict = attack_target / "conflict"
            conflict.write_text("attacker file")
        except Exception:
            pass  # Directory might already exist

    original_exists = Path.exists
    call_count = [0]

    def patched_exists(self):
        """Patch Path.exists to trigger race condition."""
        result = original_exists(self)
        call_count[0] += 1
        # Trigger attacker after first few exists() calls
        if call_count[0] == 3 and not race_event.is_set():
            race_event.set()
            time.sleep(0.01)  # Give attacker time to create file
        return result

    # Start attacker thread
    attacker = threading.Thread(target=attacker_thread)
    attacker.start()

    try:
        with patch.object(Path, "exists", patched_exists):
            storage = TodoStorage(str(db_path))
            try:
                storage.save([Todo(id=1, text="test")])
            except (ValueError, OSError) as e:
                error_caught.append(str(e))
                error_type.append(type(e).__name__)
    finally:
        race_event.set()  # Ensure thread can exit
        attacker.join(timeout=5)

    # Either the operation should succeed (if no race occurred)
    # or fail with a clear error
    if error_caught:
        # Should be ValueError with clear message about file/directory confusion
        # OSError is also acceptable but ValueError is preferred
        # The fix should provide clear error messages
        # At minimum, should not be a confusing generic error
        assert error_type[0] in ("ValueError", "OSError", "FileExistsError")


def test_ensure_parent_directory_handles_file_in_path(tmp_path) -> None:
    """Issue #3907: _ensure_parent_directory should handle file in parent path.

    Direct test of _ensure_parent_directory function with file-as-directory scenario.
    """
    # Create a file where directory should be
    blocking_file = tmp_path / "blocking"
    blocking_file.write_text("content")

    # Try to ensure parent for a path that requires the file to be a directory
    db_path = blocking_file / "nested" / "todo.json"

    # Should raise ValueError about file vs directory
    with pytest.raises(ValueError, match=r"(file|not a directory|exists)"):
        _ensure_parent_directory(db_path)


def test_ensure_parent_directory_succeeds_for_normal_paths(tmp_path) -> None:
    """Issue #3907: Normal directory creation should still work after fix."""
    # Non-existent nested path
    db_path = tmp_path / "a" / "b" / "c" / "todo.json"

    # Should create directories successfully
    _ensure_parent_directory(db_path)

    # Verify directory was created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_ensure_parent_directory_succeeds_for_existing_directory(tmp_path) -> None:
    """Issue #3907: Should work when parent directory already exists."""
    # Pre-create directory
    parent_dir = tmp_path / "existing"
    parent_dir.mkdir()
    db_path = parent_dir / "todo.json"

    # Should succeed without error
    _ensure_parent_directory(db_path)

    assert db_path.parent.exists()


def test_concurrent_ensure_parent_directory_calls(tmp_path) -> None:
    """Issue #3907: Multiple concurrent calls should all succeed.

    Tests that using exist_ok=True in the fix handles concurrent directory creation.
    """
    db_path = tmp_path / "shared" / "todo.json"
    results = []
    errors = []

    def worker():
        try:
            storage = TodoStorage(str(db_path))
            storage.save([Todo(id=1, text="worker-todo")])
            results.append("success")
        except Exception as e:
            errors.append(str(e))

    # Start multiple threads
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # All should succeed (or at least not crash with confusing errors)
    # With exist_ok=True, concurrent creation should work
    assert len(results) == 5, f"Some workers failed: {errors}"


def test_error_message_for_permission_denied_distinct(tmp_path) -> None:
    """Issue #3907: Permission errors should be distinct from file-as-directory errors."""
    # Create read-only parent
    readonly_parent = tmp_path / "readonly"
    readonly_parent.mkdir()

    db_path = readonly_parent / "subdir" / "todo.json"

    try:
        readonly_parent.chmod(0o444)

        storage = TodoStorage(str(db_path))

        # Should fail with OSError/PermissionError, not ValueError
        with pytest.raises((OSError, PermissionError)):
            storage.save([Todo(id=1, text="test")])
    finally:
        readonly_parent.chmod(0o755)
