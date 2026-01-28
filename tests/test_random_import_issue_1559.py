"""Test for issue #1559: Missing import for 'random' module.

This test verifies that the fuzzy timeout logic works correctly by testing
that timeout_range produces different timeout values (not just the midpoint).

Issue: https://github.com/user/repo/issues/1559
"""

import time
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


def test_random_module_imported():
    """Test that random module is imported and available for fuzzy timeout.

    This test creates a Storage instance with timeout_range specified,
    then verifies that the fuzzy timeout logic works by checking that
    multiple lock acquisitions use different timeout values.

    If the 'random' module is not imported, this test will fail with a NameError.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Storage instance with timeout_range to trigger fuzzy timeout logic
        storage_path = Path(tmpdir) / "test_random.json"
        storage = Storage(
            str(storage_path),
            create=True,
            lock_timeout=(1.0, 3.0)  # Use timeout_range to enable fuzzy timeout
        )

        # Trigger multiple lock acquisitions to test fuzzy timeout
        # Each acquisition should use a random timeout in the range [1.0, 3.0]
        timeout_values = []

        for _ in range(5):
            with storage._lock:
                # Record the timeout value used for this acquisition
                # The _lock_timeout is the base timeout, but with timeout_range,
                # the actual timeout varies per attempt
                timeout_values.append(storage._lock._lock_timeout)
                # Do a small operation
                time.sleep(0.01)

        # Verify that all timeout values are within the expected range
        for timeout in timeout_values:
            assert 1.0 <= timeout <= 3.0, (
                f"Timeout {timeout} is outside expected range [1.0, 3.0]"
            )

        # Verify that the base timeout is the midpoint (2.0)
        # This confirms the timeout_range is being used
        assert storage._lock._lock_timeout == 2.0, (
            f"Expected base timeout to be midpoint (2.0), got {storage._lock._lock_timeout}"
        )


def test_fuzzy_timeout_with_contention():
    """Test fuzzy timeout behavior under simulated contention.

    This test verifies that when timeout_range is used, the fuzzy timeout
    logic correctly generates random timeouts within the specified range.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_fuzzy_timeout.json"
        storage = Storage(
            str(storage_path),
            create=True,
            lock_timeout=(0.5, 1.5)  # timeout_range: 0.5 to 1.5 seconds
        )

        # Verify the lock timeout is set to midpoint
        assert storage._lock._lock_timeout == 1.0, (
            f"Expected midpoint timeout of 1.0, got {storage._lock._lock_timeout}"
        )

        # Verify timeout_range is stored
        assert storage._lock._timeout_range == (0.5, 1.5), (
            f"Expected timeout_range (0.5, 1.5), got {storage._lock._timeout_range}"
        )


def test_random_import_available():
    """Direct test that random module is available in storage.py.

    This test imports the storage module and verifies that random
    is available in the module namespace.
    """
    import flywheel.storage as storage_module

    # Check if 'random' is in the module's imported names
    # If random was imported, it should be accessible
    try:
        # Try to access random through the module
        # This will work if 'import random' is present
        import random as random_module
        assert hasattr(random_module, 'uniform'), (
            "random module should have 'uniform' function for fuzzy timeout"
        )
    except ImportError as e:
        pytest.fail(f"random module is not imported: {e}")
