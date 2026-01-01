"""Test for Issue #361: _lock_range should be initialized in __init__."""

import tempfile
import os
from pathlib import Path

from flywheel.storage import Storage


def test_lock_range_initialized():
    """Test that _lock_range is initialized in __init__ to prevent AttributeError.

    This test verifies that _lock_range exists even before any file lock operations.
    Without initialization, calling _release_file_lock without first calling
    _acquire_file_lock would raise AttributeError.

    Issue: #361
    """
    # Create a temporary storage path
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"

        # Create Storage instance
        storage = Storage(str(storage_path))

        # _lock_range should be initialized even without any lock operations
        # This prevents AttributeError if _release_file_lock is called
        # before _acquire_file_lock (e.g., in exception handling paths)
        assert hasattr(storage, '_lock_range'), \
            "_lock_range attribute should exist after initialization"

        # Verify it's initialized to 0 (safe default value)
        # This matches the value set in _acquire_file_lock for Unix systems
        assert storage._lock_range == 0, \
            "_lock_range should be initialized to 0"

        # Cleanup
        storage.close()
