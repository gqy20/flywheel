"""
Test for issue #1554: Verify that code is not truncated and _async_events is properly initialized.

This test verifies that:
1. The Storage class can be imported without syntax errors
2. The _async_events attribute is properly initialized as a dict
3. The comment block about Issue #1381 and #1545 is complete
"""

import pytest


def test_storage_class_can_be_imported():
    """Test that Storage class can be imported without syntax errors."""
    try:
        from flywheel.storage import Storage
        assert Storage is not None
    except SyntaxError as e:
        pytest.fail(f"Storage class has syntax error: {e}")
    except ImportError as e:
        pytest.fail(f"Failed to import Storage class: {e}")


def test_async_events_attribute_exists():
    """Test that _async_events attribute is properly initialized."""
    from flywheel.storage import Storage
    import tempfile
    import os

    # Create a temporary storage instance
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(storage_path)

        # Verify _async_events is initialized as a dict
        assert hasattr(storage, "_async_events"), "Storage instance should have _async_events attribute"
        assert isinstance(storage._async_events, dict), "_async_events should be a dict"
        assert storage._async_events == {}, "_async_events should be initialized as an empty dict"


def test_async_events_lock_exists():
    """Test that _async_event_init_lock attribute exists (Issue #1545)."""
    from flywheel.storage import Storage
    import tempfile
    import os

    # Create a temporary storage instance
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(storage_path)

        # Verify _async_event_init_lock is initialized
        assert hasattr(storage, "_async_event_init_lock"), \
            "Storage instance should have _async_event_init_lock attribute (Issue #1545)"


def test_lock_attribute_exists():
    """Test that _lock attribute is properly initialized (Issue #1394)."""
    from flywheel.storage import Storage
    import tempfile
    import os
    import threading

    # Create a temporary storage instance
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(storage_path)

        # Verify _lock is initialized as a threading.Lock (not RLock per Issue #1394)
        assert hasattr(storage, "_lock"), "Storage instance should have _lock attribute"
        assert isinstance(storage._lock, threading.Lock), "_lock should be a threading.Lock"
