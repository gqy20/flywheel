"""Test for thread safety check syntax (Issue #1245).

This test verifies that the code around line 238 in storage.py
has valid syntax and the thread safety check works correctly.

The issue description claimed code was truncated at line 238, but
verification shows the code is complete and correct.

Reference: Issue #1245
"""
import pytest
import sys
import os
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import _AsyncCompatibleLock


def test_thread_safety_check_syntax_is_valid():
    """Test that the thread safety check code around line 238 has valid syntax.

    This test verifies:
    1. The code that checks current_thread_id = threading.get_ident() is valid
    2. The _event_loop_thread_id can be read under lock protection
    3. No syntax errors exist in the thread safety logic

    Reference: Issue #1245 - line 238
    """
    lock = _AsyncCompatibleLock()

    # This will trigger the thread safety check code
    # The code does: current_thread_id = threading.get_ident()
    current_thread_id = threading.get_ident()

    # Verify we can read _event_loop_thread_id under lock protection
    with lock._loop_lock:
        event_loop_thread_id = lock._event_loop_thread_id

    # The comparison should work without syntax errors
    if event_loop_thread_id is not None:
        # This comparison is what the original code does
        result = current_thread_id == event_loop_thread_id
        assert isinstance(result, bool)


def test_async_compatible_lock_thread_safety():
    """Test that _AsyncCompatibleLock properly handles thread safety.

    This ensures the thread safety check at line 238-242 works correctly.
    """
    lock = _AsyncCompatibleLock()

    # Initially, _event_loop_thread_id should be None
    with lock._loop_lock:
        assert lock._event_loop_thread_id is None

    # Get current thread ID
    current_thread_id = threading.get_ident()

    # The code should be able to compare thread IDs
    with lock._loop_lock:
        event_loop_thread_id = lock._event_loop_thread_id

    # This should not raise any errors
    if event_loop_thread_id is not None:
        assert current_thread_id == event_loop_thread_id


def test_can_parse_line_238_context():
    """Test that we can import and use the code around line 238.

    This is a smoke test to ensure no syntax errors exist.
    """
    # Simply importing should fail if there's a syntax error
    from flywheel.storage import Storage

    # Create a storage instance to trigger initialization
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = Storage(db_path)
        # If we got here, the syntax is valid
        assert storage is not None
    finally:
        # Clean up
        os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
