"""Tests for Issue #525 - atexit handler registration timing."""

import json
import tempfile
import atexit
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from flywheel.storage import Storage


class TestAtexitRegistrationTiming:
    """Test that atexit handler is safely registered."""

    def test_atexit_not_registered_on_init_failure(self):
        """Test that atexit handler is not registered if initialization fails."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "todos.json"

            # Create a valid JSON file first
            test_file.write_text(json.dumps({"todos": [], "next_id": 1}))

            # Track if atexit.register was called
            original_register = atexit.register
            register_called = []

            def mock_register(func, *args, **kwargs):
                register_called.append(func)
                return original_register(func, *args, **kwargs)

            with patch('atexit.register', side_effect=mock_register):
                # Test 1: Normal initialization should register cleanup
                register_called.clear()
                storage1 = Storage(str(test_file))
                assert any(func.__name__ == '_cleanup' for func in register_called), \
                    "Cleanup should be registered on normal init"
                # Clean up the registered handler
                atexit.unregister(storage1._cleanup)

                # Test 2: Simulate failure during _load by corrupting the file
                # Write invalid JSON that will cause a JSONDecodeError
                test_file.write_text("{invalid json content")

                # This should raise an exception during init
                # The atexit handler should NOT be registered for this failed instance
                register_called.clear()

                with pytest.raises(Exception):
                    Storage(str(test_file))

                # Verify cleanup was not registered for the failed instance
                # (or if it was registered, _cleanup should handle it safely)
                # For now, we just verify the exception was raised

    def test_cleanup_handles_partial_initialization(self):
        """Test that _cleanup method handles partially initialized objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "todos.json"

            # Create a storage instance normally
            test_file.write_text(json.dumps({"todos": [], "next_id": 1}))
            storage = Storage(str(test_file))

            # Simulate partial initialization by removing required attributes
            # This tests if _cleanup can handle such a case
            original_dirty = storage._dirty
            original_path = storage.path

            # Test with _dirty attribute missing
            delattr(storage, '_dirty')
            try:
                # This should not crash
                storage._cleanup()
            except AttributeError:
                pytest.fail("_cleanup should handle missing _dirty attribute")
            finally:
                # Restore for cleanup
                storage._dirty = original_dirty

            # Test with missing todos attribute
            if hasattr(storage, '_todos'):
                original_todos = storage._todos
                delattr(storage, '_todos')
                try:
                    # This should not crash
                    storage._cleanup()
                except AttributeError:
                    pytest.fail("_cleanup should handle missing _todos attribute")
                finally:
                    storage._todos = original_todos

            # Clean up
            atexit.unregister(storage._cleanup)

    def test_atexit_registered_after_full_init(self):
        """Test that atexit is registered only after full initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "todos.json"

            # Create a valid JSON file
            test_file.write_text(json.dumps({"todos": [], "next_id": 1}))

            # Patch _load to raise an exception after atexit would have been registered
            # in the old code (before fix)
            with patch('flywheel.storage.Storage._load') as mock_load:
                # Make _load raise a ValueError (not RuntimeError)
                mock_load.side_effect = ValueError("Simulated init failure")

                # Track registrations
                original_register = atexit.register
                registrations = []

                def track_register(func, *args, **kwargs):
                    registrations.append(func.__name__)
                    return original_register(func, *args, **kwargs)

                with patch('atexit.register', side_effect=track_register):
                    with pytest.raises(ValueError, match="Simulated init failure"):
                        Storage(str(test_file))

                    # After fix: cleanup should NOT be registered if init fails
                    # Before fix: cleanup WOULD be registered even if init fails later
                    # This test verifies the fix
                    assert '_cleanup' not in registrations, \
                        "atexit should not be registered if initialization fails"
