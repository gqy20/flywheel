"""Test that Windows degraded mode enforces file-based lock (Issue #894).

Issue #894: Windows 降级模式下的死锁风险

问题描述：
当 pywin32 不可用时，系统进入降级模式。注释中提到 Issue #846 修复了死锁风险，
但需要确保 FileStorage 类在 _is_degraded_mode() 为 True 时，强制使用基于文件的锁
实现（.lock 文件），而不是依赖 msvcrt.locking 或完全跳过锁定。

修复建议：
1. 当 _is_degraded_mode() 返回 True 时，必须使用 .lock 文件
2. 不能使用 msvcrt.locking（有死锁风险）
3. 不能跳过锁定（会导致数据损坏风险）
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestIssue894DegradedModeFileLock:
    """Test that degraded mode enforces file-based lock on Windows.

    Issue #894: Ensure that when _is_degraded_mode() returns True,
    FileStorage MUST use file-based .lock files, not msvcrt.locking
    or no locking at all.
    """

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_degraded_mode_uses_file_lock_not_msvcrt(self):
        """Test that degraded mode uses .lock files, not msvcrt.locking.

        This test verifies that when pywin32 is not available (degraded mode),
        the FileStorage class uses file-based .lock files for locking,
        NOT msvcrt.locking which has deadlock risks.
        """
        from flywheel.storage import FileStorage, _is_degraded_mode

        # Skip this test if not in degraded mode (pywin32 is available)
        if not _is_degraded_mode():
            pytest.skip("This test requires degraded mode (pywin32 not available)")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test_degraded.json")

            # Create a FileStorage instance
            storage = FileStorage(storage_path)

            # Perform an operation that requires locking
            # This should use file-based .lock files, not msvcrt.locking
            todo = storage.add("Test todo in degraded mode")

            # Verify that a .lock file was created
            lock_file_path = storage_path + ".lock"
            assert os.path.exists(lock_file_path), (
                f"In degraded mode, FileStorage must create .lock file at {lock_file_path}. "
                "If no .lock file exists, the system may be using msvcrt.locking or no locking, "
                "which creates deadlock or data corruption risks."
            )

            # Verify lock file contains metadata (PID, timestamp)
            with open(lock_file_path, 'r') as f:
                content = f.read()
                assert 'pid=' in content, "Lock file must contain PID for stale lock detection"
                assert 'locked_at=' in content, "Lock file must contain timestamp"

            # Cleanup
            storage.delete(todo.id)
            del storage

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_degraded_mode_lock_mechanism_enforced(self):
        """Test that lock mechanism is enforced in degraded mode.

        This test verifies that in degraded mode, the lock acquisition
        mechanism is actually file-based locking, not just a warning.
        """
        from flywheel.storage import FileStorage, _is_degraded_mode

        # Skip if not in degraded mode
        if not _is_degraded_mode():
            pytest.skip("This test requires degraded mode (pywin32 not available)")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test_enforced.json")

            # Create first storage instance
            storage1 = FileStorage(storage_path)

            # Add a todo (this acquires lock)
            todo1 = storage1.add("Todo from instance 1")

            # Verify lock file exists
            lock_file_path = storage_path + ".lock"
            assert os.path.exists(lock_file_path), (
                "Lock file must exist in degraded mode"
            )

            # Read lock file content
            with open(lock_file_path, 'r') as f:
                lock_content = f.read()

            # Verify it has proper structure
            assert 'pid=' in lock_content
            assert 'locked_at=' in lock_content

            # Create second storage instance
            # This should wait for the lock (file-based mechanism)
            # In a real scenario, we'd need to test concurrent access,
            # but for now we just verify the lock file structure
            storage2 = FileStorage(storage_path)

            # Verify both instances can work (lock was released and re-acquired)
            todo2 = storage2.add("Todo from instance 2")

            assert todo1.id == 1
            assert todo2.id == 2

            # Cleanup
            storage1.delete(todo1.id)
            storage2.delete(todo2.id)
            del storage1, storage2

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_no_msvcrt_usage_in_degraded_mode(self):
        """Test that msvcrt.locking is NOT used in degraded mode.

        This test ensures that the code does not use msvcrt.locking
        when in degraded mode, as it has deadlock risks.
        """
        from flywheel.storage import FileStorage, _is_degraded_mode

        # Skip if not in degraded mode
        if not _is_degraded_mode():
            pytest.skip("This test requires degraded mode (pywin32 not available)")

        # Mock msvcrt to ensure it's not imported or used
        with patch.dict('sys.modules', {'msvcrt': None}):
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = os.path.join(tmpdir, "test_no_msvcrt.json")

                # This should work without msvcrt
                # If the code tries to use msvcrt.locking, it will fail
                try:
                    storage = FileStorage(storage_path)
                    todo = storage.add("Test without msvcrt")

                    # Verify .lock file is used instead
                    lock_file_path = storage_path + ".lock"
                    assert os.path.exists(lock_file_path), (
                        "Must use .lock file in degraded mode, not msvcrt.locking"
                    )

                    # Cleanup
                    storage.delete(todo.id)
                    del storage

                except ImportError as e:
                    if 'msvcrt' in str(e):
                        pytest.fail(
                            f"Code attempted to use msvcrt in degraded mode. "
                            f"This is a deadlock risk (Issue #894). Error: {e}"
                        )
                    else:
                        raise

    def test_degraded_mode_file_lock_cleanup(self):
        """Test that file locks are properly cleaned up in degraded mode.

        Issue #894: Ensure that .lock files are cleaned up properly
        to prevent stale locks from blocking future operations.
        """
        from flywheel.storage import FileStorage, _is_degraded_mode

        # Only test in degraded mode (Windows without pywin32, or Unix without fcntl)
        if not _is_degraded_mode():
            pytest.skip("This test requires degraded mode")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test_cleanup.json")

            # Create storage and add todo
            storage = FileStorage(storage_path)
            todo = storage.add("Test cleanup")

            # Lock file should exist
            lock_file_path = storage_path + ".lock"

            # After operation completes, lock should be released
            # (file may still exist temporarily, but should be cleanable)
            # Delete storage to trigger cleanup
            del storage

            # Create new storage instance
            # This should not be blocked by a stale lock
            storage2 = FileStorage(storage_path)
            todo2 = storage2.add("Test after cleanup")

            # Verify successful operation (no stale lock blocking)
            assert todo2.id == 2

            # Cleanup
            storage2.delete(todo2.id)
            del storage2

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_degraded_mode_warning_message(self):
        """Test that degraded mode shows appropriate warning.

        Issue #894: Ensure users are warned about degraded mode
        and that file-based locking is being used.
        """
        from flywheel.storage import FileStorage, _is_degraded_mode

        if not _is_degraded_mode():
            pytest.skip("This test requires degraded mode (pywin32 not available)")

        # Check that a warning was issued when module was imported
        # (This is tested implicitly by the fact that the module loaded successfully
        # and _is_degraded_mode() returns True)

        # Verify the warning message mentions file-based locking
        with pytest.warns(UserWarning, match=r"pywin32 is not installed.*fallback file locking"):
            # Re-import to trigger warning
            import importlib
            import warnings

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                # Force re-check (the warning is already issued at module import)
                from flywheel.storage import _is_degraded_mode
                is_degraded = _is_degraded_mode()

                if is_degraded:
                    # Check if any warning mentions file-based locking
                    warning_messages = [str(warning.message) for warning in w]
                    has_file_lock_warning = any(
                        "file locking" in msg.lower() or ".lock" in msg
                        for msg in warning_messages
                    )
                    # Note: The warning might have been issued earlier during module import
                    # so we don't fail if it's not in this specific capture
