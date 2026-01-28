"""Tests for IOMetrics race condition in log_summary (Issue #1086).

This test ensures that the log_summary method properly protects access to
self.operations throughout the entire method, not just during calculation.
"""

import asyncio
import os
import pytest


class TestIOMetricsRaceConditionIssue1086:
    """Test suite for IOMetrics race condition in log_summary (Issue #1086)."""

    @pytest.mark.asyncio
    async def test_log_summary_lock_held_during_entire_method(self):
        """Test that log_summary holds lock throughout all operations access.

        The bug is that the lock is released before the logging statements,
        which means self.operations can be accessed outside the lock.

        This test checks the source code structure to ensure the lock
        context manager encompasses all access to self.operations.
        """
        import inspect
        from flywheel.storage import IOMetrics

        # Get the source code of log_summary
        source = inspect.getsource(IOMetrics.log_summary)

        # The bug: logging happens after the lock is released
        # We need to check if "async with self._lock:" properly covers
        # all access to self.operations

        # Split into lines and find the lock context
        lines = source.split('\n')

        lock_indent = None
        lock_end_line = None

        for i, line in enumerate(lines):
            if 'async with self._lock:' in line:
                lock_indent = len(line) - len(line.lstrip())
                # Find where this block ends
                for j in range(i + 1, len(lines)):
                    current_indent = len(lines[j]) - len(lines[j].lstrip())
                    if lines[j].strip() and current_indent <= lock_indent:
                        lock_end_line = j
                        break
                break

        # Check if there's any access to self.operations after lock ends
        operations_access_after_lock = False
        if lock_end_line is not None:
            for line in lines[lock_end_line:]:
                if 'self.operations' in line and 'for' not in line:
                    operations_access_after_lock = True
                    break

        # This should FAIL initially, demonstrating the bug
        assert not operations_access_after_lock, \
            "self.operations is accessed after lock is released - race condition!"

    @pytest.mark.asyncio
    async def test_concurrent_record_and_log_summary_safe(self):
        """Test that concurrent record_operation and log_summary don't cause data corruption.

        This test creates concurrent operations that would expose the race condition
        if the lock is not held throughout log_summary.
        """
        from flywheel.storage import IOMetrics

        # Enable metrics logging
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Record initial operations
        for i in range(50):
            await metrics.record_operation(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )

        # Track any errors
        errors = []
        successful_runs = 0

        async def record_operations():
            """Continuously record operations."""
            for i in range(100):
                try:
                    await metrics.record_operation(
                        "write",
                        duration=0.2,
                        retries=0,
                        success=True
                    )
                except Exception as e:
                    errors.append(f"record_operation error: {e}")

        async def log_summaries():
            """Continuously call log_summary."""
            nonlocal successful_runs
            for i in range(50):
                try:
                    metrics.log_summary()
                    successful_runs += 1
                except Exception as e:
                    errors.append(f"log_summary error: {e}")

        # Run both concurrently
        await asyncio.gather(
            record_operations(),
            log_summaries()
        )

        # Should not have any errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert successful_runs > 0, "log_summary should have run successfully"

    @pytest.mark.asyncio
    async def test_log_summary_all_operations_access_inside_lock(self):
        """Test that all access to self.operations in log_summary is inside the lock.

        This is a structural test that verifies the code organization.
        """
        import inspect
        from flywheel.storage import IOMetrics

        # Get the source code
        source = inspect.getsource(IOMetrics.log_summary)
        lines = source.split('\n')

        # Find the lock block
        lock_start = None
        lock_indent = None

        for i, line in enumerate(lines):
            if 'async with self._lock:' in line:
                lock_start = i
                lock_indent = len(line) - len(line.lstrip())
                break

        assert lock_start is not None, "Lock not found in log_summary"

        # Find where lock block ends
        lock_end = None
        for i in range(lock_start + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Non-empty line
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= lock_indent:
                    lock_end = i
                    break

        # Check all self.operations access
        operations_access_lines = []
        for i, line in enumerate(lines):
            if 'self.operations' in line and '#' not in line.split('self.operations')[0]:
                operations_access_lines.append(i)

        # All operations access should be inside the lock block
        # This will FAIL initially because logging happens after lock
        for line_num in operations_access_lines:
            if lock_end is not None and line_num >= lock_end:
                # Found access to self.operations outside lock
                assert False, f"Line {line_num} accesses self.operations outside lock: {lines[line_num].strip()}"
