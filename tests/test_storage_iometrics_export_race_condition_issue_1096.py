"""Tests for IOMetrics race condition in export_to_dict (Issue #1096).

This test ensures that the export_to_dict method properly protects access to
self.operations throughout the entire method, including calculations and
total_duration() call.
"""

import asyncio
import pytest


class TestIOMetricsExportRaceConditionIssue1096:
    """Test suite for IOMetrics race condition in export_to_dict (Issue #1096)."""

    @pytest.mark.asyncio
    async def test_export_to_dict_all_calculations_inside_lock(self):
        """Test that all calculations in export_to_dict happen inside the lock.

        The bug is that operations_list is copied inside the lock, but
        successful_ops, failed_ops, total_retries calculations, and the
        total_duration() call happen outside the lock.

        While operations_list is safe (it's a copy), total_duration() can
        access self._durations which may be modified concurrently.

        This test checks the source code structure to ensure the lock
        context manager encompasses all calculations.
        """
        import inspect
        from flywheel.storage import IOMetrics

        # Get the source code of export_to_dict
        source = inspect.getsource(IOMetrics.export_to_dict)

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

        # Check if calculations happen after lock ends
        # The bug: successful_ops, failed_ops, total_retries calculated outside lock
        calculations_after_lock = False
        if lock_end_line is not None:
            for line in lines[lock_end_line:]:
                # Look for calculations that should be protected
                if any(pattern in line for pattern in [
                    'successful_ops',
                    'failed_ops',
                    'total_retries'
                ]):
                    calculations_after_lock = True
                    break

        # This should FAIL initially, demonstrating the bug
        assert not calculations_after_lock, \
            "Calculations happen after lock is released - race condition!"

    @pytest.mark.asyncio
    async def test_export_to_dict_total_duration_inside_lock(self):
        """Test that total_duration() call happens inside the lock.

        total_duration() accesses self._durations which can be modified
        concurrently, so it should be called inside the lock.
        """
        import inspect
        from flywheel.storage import IOMetrics

        # Get the source code
        source = inspect.getsource(IOMetrics.export_to_dict)
        lines = source.split('\n')

        # Find the lock block
        lock_start = None
        lock_indent = None

        for i, line in enumerate(lines):
            if 'async with self._lock:' in line:
                lock_start = i
                lock_indent = len(line) - len(line.lstrip())
                break

        assert lock_start is not None, "Lock not found in export_to_dict"

        # Find where lock block ends
        lock_end = None
        for i in range(lock_start + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Non-empty line
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= lock_indent:
                    lock_end = i
                    break

        # Find where total_duration() is called
        total_duration_line = None
        for i, line in enumerate(lines):
            if 'total_duration()' in line:
                total_duration_line = i
                break

        # total_duration() should be called inside the lock
        # This will FAIL initially because it's called in the return statement
        if total_duration_line is not None and lock_end is not None:
            assert total_duration_line < lock_end, \
                f"total_duration() called at line {total_duration_line} " \
                f"but lock ends at line {lock_end} - race condition!"

    @pytest.mark.asyncio
    async def test_concurrent_record_and_export_to_dict_safe(self):
        """Test that concurrent record_operation and export_to_dict don't cause corruption.

        This test creates concurrent operations that would expose the race condition
        if calculations are not properly protected.
        """
        from flywheel.storage import IOMetrics

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
        successful_exports = 0

        async def record_operations():
            """Continuously record operations."""
            for i in range(100):
                try:
                    await metrics.record_operation(
                        "write",
                        duration=0.2,
                        retries=i % 3,  # Some retries
                        success=(i % 2 == 0)  # Some failures
                    )
                except Exception as e:
                    errors.append(f"record_operation error: {e}")

        async def export_data():
            """Continuously call export_to_dict."""
            nonlocal successful_exports
            for i in range(50):
                try:
                    data = metrics.export_to_dict()

                    # Verify data consistency
                    total_ops = data['successful_operations'] + data['failed_operations']
                    assert total_ops == data['total_operation_count'], \
                        f"Inconsistent counts: {total_ops} vs {data['total_operation_count']}"

                    successful_exports += 1
                except Exception as e:
                    errors.append(f"export_to_dict error: {e}")

        # Run both concurrently
        await asyncio.gather(
            record_operations(),
            export_data()
        )

        # Should not have any errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert successful_exports > 0, "export_to_dict should have run successfully"
