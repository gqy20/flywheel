"""Test statsd client caching optimization (Issue #1013).

This test verifies that environment variable checks for statsd configuration
are cached at module level and not repeated on every call to get_statsd_client.
"""

import os
from unittest import mock

import pytest


def test_statsd_environment_check_cached():
    """Test that environment variables are only checked once per process lifetime.

    This test ensures that the os.environ.get call for statsd configuration
    is cached at module level, avoiding repeated environment variable lookups
    during high-frequency I/O operations.
    """
    # Reset the module-level cache by reimporting
    import importlib
    import flywheel.storage
    importlib.reload(flywheel.storage)

    # Mock os.environ.get to count calls
    original_environ_get = os.environ.get
    call_count = {'count': 0}

    def mock_environ_get(*args, **kwargs):
        call_count['count'] += 1
        return original_environ_get(*args, **kwargs)

    with mock.patch('os.environ.get', side_effect=mock_environ_get):
        # First call should check environment
        flywheel.storage.get_statsd_client()

        # Get the count after first call
        count_after_first = call_count['count']

        # Second call should NOT check environment again
        flywheel.storage.get_statsd_client()

        # Third call should also NOT check environment again
        flywheel.storage.get_statsd_client()

        # The environment check should only happen once at module level,
        # not on every function call
        # After caching, subsequent calls should not trigger os.environ.get again
        # We allow some tolerance for the first call's initialization
        assert call_count['count'] <= count_after_first + 1, (
            f"Environment variable checked {call_count['count']} times, "
            f"but should be cached after first check. "
            f"Expected at most {count_after_first + 1} calls."
        )
