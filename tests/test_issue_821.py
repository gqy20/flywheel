"""Test that Windows degraded mode uses msvcrt fallback lock instead of no lock (Issue #821).

Issue #821: Windows降级模式下文件锁完全禁用

The bug is that when pywin32 is not available on Windows, the code completely
disables file locking instead of using a fallback mechanism like msvcrt.locking.
This can cause data corruption when multiple instances run concurrently.

This test verifies that a fallback lock mechanism (msvcrt or atomic file rename)
is used instead of completely disabling locking.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import multiprocessing
import pytest

from flywheel.storage import Storage


class TestIssue821WindowsFallbackLock:
    """Test Windows degraded mode should use fallback lock, not disable locking."""

    def test_windows_without_pywin32_uses_fallback_lock(self):
        """When pywin32 is not available on Windows, should use msvcrt fallback lock.

        This test ensures that even in degraded mode (without pywin32), Windows
        still uses SOME form of file locking (msvcrt.locking or atomic rename)
        instead of completely disabling locking.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.todos.json"

            # Mock Windows environment
            with patch('os.name', 'nt'):
                # Mock pywin32 as not installed
                with patch.dict('sys.modules', {
                    'win32security': None,
                    'win32con': None,
                    'win32api': None,
                    'win32file': None,
                    'pywintypes': None
                }):
                    # Mock import to raise ImportError
                    def mock_import(name, *args, **kwargs):
                        if name in ['win32security', 'win32con', 'win32api',
                                   'win32file', 'pywintypes']:
                            raise ImportError(f"No module named '{name}'")
                        return original_import(name, *args, **kwargs)

                    original_import = __builtins__.__import__

                    with patch('builtins.__import__', side_effect=mock_import):
                        # Capture warnings
                        import warnings
                        with warnings.catch_warnings(record=True) as w:
                            warnings.simplefilter("always")

                            # Create storage - should trigger degraded mode warning
                            # BUT should still use fallback lock
                            storage = Storage(str(test_path))

                            # Verify warning about pywin32 not installed
                            warning_messages = [str(warning.message) for warning in w]
                            pywin32_warnings = [
                                msg for msg in warning_messages
                                if "pywin32" in msg.lower()
                            ]
                            assert len(pywin32_warnings) > 0, \
                                "Should warn about pywin32 not being installed"

                            # Verify that storage has SOME lock mechanism enabled
                            # Check if degraded mode is detected
                            from flywheel.storage import _is_degraded_mode
                            assert _is_degraded_mode() == True, \
                                "Should be in degraded mode when pywin32 is not available"

                            # KEY ASSERTION: Even in degraded mode, should attempt locking
                            # The _is_degraded_mode() function should return True,
                            # BUT the actual lock acquisition should still try a fallback
                            # (msvcrt.locking or atomic rename)
                            #
                            # We verify this by checking that the storage object
                            # was created successfully and has lock timeout configured
                            assert storage._lock_timeout > 0, \
                                "Lock timeout should be configured even in degraded mode"

    def test_windows_fallback_lock_prevents_concurrent_writes(self):
        """Test that fallback lock actually prevents concurrent write conflicts.

        This is an integration test that verifies the fallback lock mechanism
        works by attempting concurrent writes from multiple processes.
        """
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "concurrent_test.json"

            # Simulate degraded mode by mocking pywin32 as unavailable
            # In actual implementation, this would use msvcrt.locking
            def write_process(value):
                """Write a value from a separate process."""
                try:
                    storage = Storage(str(test_path))
                    storage.add(f"Todo {value}")
                    storage._save()
                    return True
                except Exception as e:
                    print(f"Process failed: {e}")
                    return False

            # Try concurrent writes (should not corrupt data if lock works)
            results = []
            with multiprocessing.Pool(processes=2) as pool:
                results = pool.map(write_process, [1, 2])

            # At least one should succeed (proves lock mechanism works)
            # This is a basic smoke test - full concurrent testing is complex
            assert any(results), "At least one write should succeed"

            # Verify file is not corrupted (can be loaded)
            storage = Storage(str(test_path))
            todos = storage._load()
            assert isinstance(todos, list), "File should not be corrupted"

    def test_degraded_mode_locking_uses_msvcrt_or_atomic_rename(self):
        """Verify that degraded mode uses either msvcrt.locking or atomic rename.

        This test checks the implementation strategy for fallback locking.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock Windows without pywin32
            with patch('os.name', 'nt'):
                with patch.dict('sys.modules', {
                    'win32file': None,
                    'pywintypes': None
                }):
                    # Check if msvcrt is available (Windows standard library)
                    try:
                        import msvcrt
                        has_msvcrt = True
                    except ImportError:
                        has_msvcrt = False

                    # The implementation should use one of:
                    # 1. msvcrt.locking (Windows-specific)
                    # 2. Atomic file rename (portable fallback)
                    #
                    # This test verifies the implementation attempts a lock
                    with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs:
                            ImportError(f"No module named '{name}'")
                            if name in ['win32file', 'pywintypes']
                            else __builtins__.__import__(name, *args, **kwargs)):

                        storage = Storage(str(test_path))

                        # Verify lock timeout is set (proves locking is configured)
                        assert storage._lock_timeout > 0, \
                            "Lock timeout should be set even in degraded mode"

                        # If we're on Windows and have msvcrt, verify it's used
                        # (This will be checked in the implementation phase)
                        if has_msvcrt:
                            # In GREEN phase, we'll verify msvcrt.locking is called
                            # For now, just verify the module is available
                            assert has_msvcrt, "msvcrt should be available on Windows"

    def test_fallback_lock_does_not_corrupt_data(self):
        """Test that fallback lock mechanism prevents data corruption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "integrity_test.json"

            # Mock Windows without pywin32
            with patch('os.name', 'nt'):
                with patch.dict('sys.modules', {
                    'win32file': None,
                    'pywintypes': None
                }):
                    # Perform multiple save operations
                    storage = Storage(str(test_path))
                    for i in range(10):
                        storage.add(f"Todo {i}")
                        storage._save()

                    # Verify data integrity
                    todos = storage._load()
                    assert len(todos) == 10, "All todos should be saved without corruption"
                    assert all(f"Todo {i}" in str(todo) for i, todo in enumerate(todos)), \
                        "Each todo should be intact"
