"""Test for Issue #1017 - Thread-safe statsd client initialization.

This test verifies that the statsd client initialization is thread-safe
and prevents race conditions when multiple threads call get_statsd_client()
simultaneously.
"""
import os
import sys
import threading
from unittest.mock import patch, MagicMock

import pytest

# Add src to path so we can import flywheel modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import get_statsd_client, _statsd_client


class TestStatsdThreadSafety:
    """Test thread-safe initialization of statsd client."""

    def test_concurrent_initialization_returns_same_instance(self):
        """Test that concurrent calls to get_statsd_client return the same instance."""
        # Reset the global client
        import flywheel.storage
        flywheel.storage._statsd_client = None

        # Mock statsd module
        mock_statsd = MagicMock()
        mock_client = MagicMock()
        mock_statsd.StatsClient.return_value = mock_client

        instances = []
        errors = []

        def get_client():
            try:
                client = get_statsd_client()
                instances.append(client)
            except Exception as e:
                errors.append(e)

        # Set environment variable for statsd host
        with patch.dict(os.environ, {'FW_STATSD_HOST': 'localhost'}):
            with patch.dict('sys.modules', {'statsd': mock_statsd}):
                # Create multiple threads that will try to initialize the client simultaneously
                threads = []
                num_threads = 50

                # Use a barrier to make all threads start at the same time
                barrier = threading.Barrier(num_threads)

                def get_client_with_barrier():
                    barrier.wait()  # Wait for all threads to be ready
                    get_client()

                for _ in range(num_threads):
                    t = threading.Thread(target=get_client_with_barrier)
                    threads.append(t)

                # Start all threads
                for t in threads:
                    t.start()

                # Wait for all threads to complete
                for t in threads:
                    t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all threads got the same client instance
        assert len(instances) == num_threads, \
            f"Expected {num_threads} instances, got {len(instances)}"

        # All instances should be the same object (same identity)
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, \
                "Not all threads received the same client instance"

        # Verify StatsClient was called only once
        assert mock_statsd.StatsClient.call_count == 1, \
            f"StatsClient was called {mock_statsd.StatsClient.call_count} times, expected 1"

    def test_thread_safety_with_multiple_rapid_calls(self):
        """Test that rapid successive calls from multiple threads are safe."""
        # Reset the global client
        import flywheel.storage
        flywheel.storage._statsd_client = None

        # Mock statsd module
        mock_statsd = MagicMock()
        mock_client = MagicMock()
        mock_statsd.StatsClient.return_value = mock_client

        call_count = {'count': 0}
        lock = threading.Lock()

        def track_calls():
            with lock:
                call_count['count'] += 1

        # Set environment variable for statsd host
        with patch.dict(os.environ, {'FW_STATSD_HOST': 'localhost'}):
            with patch.dict('sys.modules', {'statsd': mock_statsd}):
                # Make many rapid calls from multiple threads
                threads = []
                num_threads = 100
                calls_per_thread = 10

                def rapid_calls():
                    for _ in range(calls_per_thread):
                        client = get_statsd_client()
                        track_calls()

                for _ in range(num_threads):
                    t = threading.Thread(target=rapid_calls)
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

        # Verify total number of successful calls
        expected_calls = num_threads * calls_per_thread
        assert call_count['count'] == expected_calls, \
            f"Expected {expected_calls} calls, got {call_count['count']}"

        # Verify StatsClient was called only once despite many get_statsd_client calls
        assert mock_statsd.StatsClient.call_count == 1, \
            f"StatsClient was called {mock_statsd.StatsClient.call_count} times, expected 1"
