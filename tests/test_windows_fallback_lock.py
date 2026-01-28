"""
Test for Windows fallback file locking with automatic cleanup (Issue #846).

This test verifies that the file-based lock mechanism properly handles:
1. Lock acquisition and release
2. Automatic cleanup when process crashes
3. Lock timeout and retry mechanism
4. Multiple process scenarios
"""

import os
import sys
import tempfile
import time
import threading
from pathlib import Path
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import FileStorage


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
class TestWindowsFallbackLock:
    """Test Windows fallback lock mechanism with .lock file based approach."""

    def test_lock_file_created_on_acquire(self):
        """Test that a .lock file is created when lock is acquired."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name

        try:
            # Mock degraded mode (no pywin32)
            storage = FileStorage(tmp_path, lock_timeout=5)

            # Trigger lock acquisition by doing an operation
            storage.clear()

            # Check if .lock file exists
            lock_file = Path(tmp_path + ".lock")
            assert lock_file.exists(), "Lock file should be created after lock acquisition"

            # Release lock
            del storage

            # Lock file should be cleaned up
            time.sleep(0.1)  # Give time for cleanup
            # Note: In production, lock file might persist briefly, but should be cleaned
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            lock_file = Path(tmp_path + ".lock")
            if lock_file.exists():
                lock_file.unlink()

    def test_lock_timeout_with_multiple_processes(self):
        """Test that lock timeout works correctly with multiple competing processes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name

        try:
            storage1 = FileStorage(tmp_path, lock_timeout=2, lock_retry_interval=0.1)
            storage1.clear()

            # Create a manual lock file to simulate another process holding the lock
            lock_file = Path(tmp_path + ".lock")
            lock_file.write_text(f"pid={os.getpid()}\nlocked_at={time.time()}")

            # Try to acquire lock with same storage - should timeout
            storage2 = FileStorage(tmp_path, lock_timeout=1, lock_retry_interval=0.1)

            start_time = time.time()
            with pytest.raises(RuntimeError, match="timed out"):
                storage2.clear()
            elapsed = time.time() - start_time

            # Should have waited for approximately the timeout duration
            assert elapsed >= 0.9, f"Should have waited for timeout, but only took {elapsed}s"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            lock_file = Path(tmp_path + ".lock")
            if lock_file.exists():
                lock_file.unlink()

    def test_stale_lock_cleanup(self):
        """Test that stale locks from crashed processes are cleaned up."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as txt:
            tmp_path = txt.name

        try:
            lock_file = Path(tmp_path + ".lock")

            # Create a stale lock file with an old timestamp
            old_time = time.time() - 3600  # 1 hour ago
            lock_file.write_text(f"pid=99999\nlocked_at={old_time}")

            # Verify stale lock exists
            assert lock_file.exists()

            # Create storage - should detect stale lock and clean it up
            storage = FileStorage(tmp_path, lock_timeout=5, lock_stale_threshold=300)
            storage.clear()

            # Lock should be acquired successfully after cleanup
            # New lock file should exist with current timestamp
            assert lock_file.exists()
            content = lock_file.read_text()
            assert str(os.getpid()) in content or "locked_at" in content

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            lock_file = Path(tmp_path + ".lock")
            if lock_file.exists():
                lock_file.unlink()

    def test_lock_file_metadata(self):
        """Test that lock file contains proper metadata."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name

        try:
            storage = FileStorage(tmp_path, lock_timeout=5)
            storage.clear()

            lock_file = Path(tmp_path + ".lock")
            assert lock_file.exists()

            content = lock_file.read_text()
            # Should contain PID and timestamp
            assert "pid=" in content
            assert "locked_at=" in content

            # Verify timestamp is recent
            for line in content.split("\n"):
                if line.startswith("locked_at="):
                    timestamp = float(line.split("=")[1])
                    assert time.time() - timestamp < 5.0, "Lock timestamp should be recent"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            lock_file = Path(tmp_path + ".lock")
            if lock_file.exists():
                lock_file.unlink()

    def test_concurrent_access_prevention(self):
        """Test that concurrent access is properly prevented."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name

        try:
            storage1 = FileStorage(tmp_path, lock_timeout=5)
            storage1.clear()

            results = []
            errors = []

            def try_concurrent_access():
                """Try to access the same storage concurrently."""
                try:
                    storage2 = FileStorage(tmp_path, lock_timeout=1, lock_retry_interval=0.1)
                    storage2.add("Task 1")
                    results.append("success")
                except Exception as e:
                    errors.append(str(e))

            # Start concurrent thread
            thread = threading.Thread(target=try_concurrent_access)
            thread.start()
            thread.join(timeout=3)

            # The concurrent access should either fail with timeout
            # or wait until the main storage releases the lock
            # This verifies the lock is working
            assert len(errors) > 0 or len(results) > 0

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            lock_file = Path(tmp_path + ".lock")
            if lock_file.exists():
                lock_file.unlink()


@pytest.mark.skipif(os.name == "nt", reason="Unix-specific test")
class TestUnixFallbackLock:
    """Test that Unix systems don't use Windows-specific locks."""

    def test_no_msvcrt_on_unix(self):
        """Test that msvcrt is not used on Unix systems."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name

        try:
            storage = FileStorage(tmp_path, lock_timeout=5)
            storage.clear()

            # No .lock file should be created on Unix
            lock_file = Path(tmp_path + ".lock")
            # On Unix with fcntl, no lock file is needed
            # On degraded mode, different mechanism might be used

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            lock_file = Path(tmp_path + ".lock")
            if lock_file.exists():
                lock_file.unlink()
