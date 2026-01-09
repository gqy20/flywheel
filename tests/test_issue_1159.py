"""Test for Issue #1159: Verify record_operation method is implemented correctly.

This test verifies that the IOMetrics.record_operation method is properly
implemented and functional. The issue report claimed the method was truncated
at line 244, but the actual implementation is complete at lines 280-350.
"""

import pytest
from flywheel.storage import IOMetrics


def test_record_operation_basic():
    """Test basic record_operation functionality."""
    metrics = IOMetrics()

    # Record a successful operation
    metrics.record_operation(
        operation_type='read',
        duration=0.5,
        retries=0,
        success=True
    )

    assert metrics.total_operation_count() == 1
    assert metrics.total_duration() == 0.5


def test_record_operation_with_error():
    """Test record_operation with failed operation."""
    metrics = IOMetrics()

    # Record a failed operation
    metrics.record_operation(
        operation_type='write',
        duration=0.3,
        retries=2,
        success=False,
        error_type='ENOENT'
    )

    assert metrics.total_operation_count() == 1
    assert metrics.total_duration() == 0.3


def test_record_operation_multiple():
    """Test recording multiple operations."""
    metrics = IOMetrics(max_operations=100)

    # Record multiple operations
    for i in range(10):
        metrics.record_operation(
            operation_type='flush',
            duration=0.1 * i,
            retries=0,
            success=True
        )

    assert metrics.total_operation_count() == 10
    assert metrics.total_duration() == 0.45  # Sum of 0, 0.1, 0.2, ..., 0.9


def test_record_operation_thread_safety():
    """Test that record_operation is thread-safe."""
    import threading

    metrics = IOMetrics(max_operations=1000)
    errors = []

    def record_ops(thread_id):
        try:
            for i in range(100):
                metrics.record_operation(
                    operation_type='read',
                    duration=0.01,
                    retries=0,
                    success=True
                )
        except Exception as e:
            errors.append((thread_id, e))

    # Create multiple threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=record_ops, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Should have 1000 operations (10 threads * 100 ops)
    assert metrics.total_operation_count() == 1000
    assert len(errors) == 0, f"Errors occurred: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
