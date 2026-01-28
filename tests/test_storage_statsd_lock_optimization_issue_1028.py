"""Tests for Statsd client lock optimization (Issue #1028).

This test suite verifies that the Statsd client initialization is optimized
to use functools.lru_cache or a more efficient pattern instead of explicit locks.
"""

import gc
import sys
import threading
import time
from unittest import mock

import pytest


class TestStatsdLockOptimization:
    """Test suite for Statsd client lock optimization (Issue #1028)."""

    def test_statsd_client_uses_lru_cache_or_module_level_init(self):
        """Test that statsd client uses lru_cache or module-level initialization.

        This test checks that the implementation avoids explicit locks in favor of
        functools.lru_cache or module-level initialization patterns.
        """
        # Arrange - import the storage module
        import flywheel.storage

        # Act - get the source code of get_statsd_client
        import inspect
        source = inspect.getsource(flywheel.storage.get_statsd_client)

        # Assert - verify the implementation does NOT use explicit locks
        # The new implementation should use functools.lru_cache or similar
        assert 'lru_cache' in source or \
               'Lock' not in source or \
               '_statsd_client_lock' not in source, \
            "Expected get_statsd_client to use lru_cache or avoid locks"

        # Verify that if lru_cache is used, it's properly imported
        if 'lru_cache' in source:
            assert 'functools' in str(dir(flywheel.storage)), \
                "functools should be imported when using lru_cache"

    def test_statsd_client_thread_safe_without_explicit_lock(self):
        """Test that statsd client is thread-safe without using explicit locks.

        This test verifies thread safety through concurrent calls.
        """
        # Arrange - reset the module to force re-initialization
        import flywheel.storage
        flywheel.storage._statsd_client = None

        # Mock statsd to be available
        mock_statsd_module = mock.MagicMock()
        mock_statsd_client = mock.MagicMock()
        mock_statsd_module.StatsClient.return_value = mock_statsd_client

        results = []
        errors = []

        def get_client_from_thread(thread_id):
            """Helper function to call get_statsd_client from a thread."""
            try:
                with mock.patch.dict('sys.modules', {'statsd': mock_statsd_module}):
                    with mock.patch.dict(
                        'os.environ',
                        {'FW_STATSD_HOST': 'localhost', 'FW_STATSD_PORT': '8125'}
                    ):
                        # Force reimport to get fresh environment
                        import importlib
                        importlib.reload(flywheel.storage)
                        client = flywheel.storage.get_statsd_client()
                        results.append((thread_id, id(client)))
            except Exception as e:
                errors.append((thread_id, e))

        # Act - create multiple threads that call get_statsd_client concurrently
        threads = []
        for i in range(10):
            t = threading.Thread(target=get_client_from_thread, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)

        # Assert - verify no errors occurred
        assert len(errors) == 0, f"Errors occurred in threads: {errors}"

        # Verify all threads got a client (could be None or a client instance)
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"

    def test_statsd_client_cached_after_initialization(self):
        """Test that statsd client is properly cached after first call.

        This verifies that the caching mechanism works correctly.
        """
        # Arrange
        import flywheel.storage

        # Save original state
        original_client = flywheel.storage._statsd_client

        try:
            # Reset to None
            flywheel.storage._statsd_client = None

            # Mock statsd
            mock_statsd_module = mock.MagicMock()
            mock_statsd_client = mock.MagicMock()
            mock_statsd_module.StatsClient.return_value = mock_statsd_client

            with mock.patch.dict('sys.modules', {'statsd': mock_statsd_module}):
                with mock.patch.dict(
                    'os.environ',
                    {'FW_STATSD_HOST': 'localhost', 'FW_STATSD_PORT': '8125'}
                ):
                    # Force reload
                    import importlib
                    importlib.reload(flywheel.storage)

                    # Act - call get_statsd_client twice
                    client1 = flywheel.storage.get_statsd_client()
                    client2 = flywheel.storage.get_statsd_client()

                    # Assert - both calls should return the same cached instance
                    assert client1 is client2, \
                        "Expected both calls to return the same cached instance"

                    # If a client was created, verify it's the expected type
                    if client1 is not None:
                        assert id(client1) == id(client2), \
                            "Client instances should be identical (same id)"
        finally:
            # Restore original state
            flywheel.storage._statsd_client = original_client

    def test_statsd_client_performance_no_lock_contention(self):
        """Test that statsd client initialization doesn't cause lock contention.

        This test measures performance to ensure there's no significant
        lock contention under concurrent access.
        """
        # Arrange
        import flywheel.storage

        # Save original state
        original_client = flywheel.storage._statsd_client

        try:
            # Reset to ensure initialization happens
            flywheel.storage._statsd_client = None

            # Mock statsd
            mock_statsd_module = mock.MagicMock()
            mock_statsd_client = mock.MagicMock()
            mock_statsd_module.StatsClient.return_value = mock_statsd_client

            call_times = []

            def timed_get_client(thread_id):
                """Helper to measure get_statsd_client call time."""
                with mock.patch.dict('sys.modules', {'statsd': mock_statsd_module}):
                    with mock.patch.dict(
                        'os.environ',
                        {'FW_STATSD_HOST': 'localhost', 'FW_STATSD_PORT': '8125'}
                    ):
                        start = time.perf_counter()
                        # Force reload per thread
                        import importlib
                        importlib.reload(flywheel.storage)
                        client = flywheel.storage.get_statsd_client()
                        end = time.perf_counter()
                        call_times.append((thread_id, end - start))

            # Act - call get_statsd_client from multiple threads
            threads = []
            for i in range(5):
                t = threading.Thread(target=timed_get_client, args=(i,))
                threads.append(t)

            # Start all threads
            for t in threads:
                t.start()

            # Wait for completion
            for t in threads:
                t.join(timeout=5)

            # Assert - verify all calls completed in reasonable time
            # With proper optimization, no call should take excessively long
            assert len(call_times) == 5, f"Expected 5 results, got {len(call_times)}"

            # Check that no single call took more than 1 second
            max_time = max(t for _, t in call_times)
            assert max_time < 1.0, \
                f"Expected all calls to complete quickly, but max was {max_time:.3f}s"

        finally:
            flywheel.storage._statsd_client = original_client

    def test_statsd_client_global_variable_type_ignore(self):
        """Test that global variables have proper type ignore comments if needed.

        This test verifies type ignore comments are present for static type checkers.
        """
        # Arrange - read the storage module source
        import flywheel.storage
        import inspect

        # Get the module source
        module_source = inspect.getsource(flywheel.storage)

        # Assert - check for type ignore comments near global variable declarations
        # This is a best practice when using module-level mutable state
        has_statsd_client_var = '_statsd_client' in module_source
        has_type_ignore = '# type: ignore' in module_source

        # If there's a global statsd_client variable, it should ideally have type ignore
        # or use a pattern that doesn't trigger type checker warnings
        if has_statsd_client_var:
            # Either type ignore is present, or the code uses lru_cache
            # (which doesn't require global mutable state)
            has_lru_cache = 'lru_cache' in module_source
            assert has_type_ignore or has_lru_cache, \
                "Global _statsd_client should have type: ignore or use lru_cache"
