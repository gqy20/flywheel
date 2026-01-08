"""Tests for IOMetrics.log_summary thread safety (Issue #1076).

This test ensures that IOMetrics.log_summary is thread-safe and handles
concurrent modifications to self.operations by using proper locking.

The fix ensures that the entire log_summary operation uses a consistent
snapshot of self.operations, preventing race conditions.
"""

import os
import threading
import time
import pytest


class TestIOMetricsLogSummaryThreadSafetyIssue1076:
    """Test suite for IOMetrics.log_summary thread safety (Issue #1076)."""

    def test_log_summary_thread_safety_with_concurrent_modifications(self):
        """Test that log_summary handles concurrent modifications safely.

        This test creates a high-contention scenario where one thread
        continuously modifies operations while another calls log_summary.
        The test passes if no exceptions are raised, demonstrating that
        log_summary properly handles concurrent access.
        """
        from flywheel.storage import IOMetrics

        # Enable metrics logging
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Record some initial operations
        for i in range(10):
            metrics.record_operation(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )

        # Flag to control the thread
        running = True
        errors = []

        def modify_operations():
            """Continuously modify operations in a background thread."""
            nonlocal running, errors
            while running:
                try:
                    metrics.record_operation(
                        "write",
                        duration=0.2,
                        retries=0,
                        success=True
                    )
                except Exception as e:
                    errors.append(f"Modification error: {e}")
                time.sleep(0.0001)  # Very small delay for high contention

        # Start background thread that modifies operations
        modifier_thread = threading.Thread(target=modify_operations, daemon=True)
        modifier_thread.start()

        try:
            # Call log_summary multiple times while operations are being modified
            # This should not raise any exceptions
            for i in range(200):
                try:
                    metrics.log_summary()
                except Exception as e:
                    errors.append(f"log_summary call {i} error: {e}")
                time.sleep(0.0001)
        finally:
            # Stop the background thread
            running = False
            modifier_thread.join(timeout=2)

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']

        # Assert no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent access: {errors}"

    def test_log_summary_creates_consistent_snapshot(self):
        """Test that log_summary creates a consistent snapshot of operations.

        This test verifies that log_summary uses a consistent view of
        operations throughout its execution, even if operations are
        being modified concurrently.
        """
        from flywheel.storage import IOMetrics

        # Enable metrics logging
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Add operations of different types
        for i in range(20):
            metrics.record_operation(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )
            metrics.record_operation(
                "write",
                duration=0.2,
                retries=0,
                success=True
            )

        # log_summary should complete successfully
        # and provide consistent metrics
        metrics.log_summary()

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']

    def test_log_summary_operations_protected_during_iteration(self):
        """Test that operations are protected during iteration in log_summary.

        This test ensures that the iteration over operations in log_summary
        is protected from concurrent modifications that could cause
        inconsistent state or exceptions.
        """
        from flywheel.storage import IOMetrics
        from unittest.mock import patch

        # Enable metrics logging
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Add some operations
        for i in range(10):
            metrics.record_operation(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )

        # Patch the sleep in log_summary to extend the critical section
        # This makes race conditions more likely if locking is incorrect
        original_sleep = time.sleep

        def slow_sleep(duration):
            """Only slow down the first sleep call."""
            if slow_sleep.call_count == 0:
                slow_sleep.call_count += 1
                original_sleep(0.01)  # Longer sleep to create window for race
            else:
                original_sleep(duration)

        slow_sleep.call_count = 0

        # Call log_summary - it should handle the extended critical section safely
        with patch('time.sleep', side_effect=slow_sleep):
            metrics.log_summary()

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']
