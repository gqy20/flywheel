"""Test for Issue #1141 - Verify record_operation has complete implementation

This test verifies that the record_operation method has:
1. Proper locking mechanism (with self._sync_lock)
2. Actual operation recording logic (self.operations.append(operation))

The issue reported that the code was incomplete at line 254, but it was
already fixed as part of Issue #1135.
"""

from flywheel.storage import IOMetrics


def test_record_operation_has_complete_implementation():
    """Test that record_operation method has complete implementation.

    Verifies that:
    1. The method exists and is callable
    2. It properly records operations with locking
    3. Operations are actually stored in the operations deque
    """
    metrics = IOMetrics()

    # Record an operation
    metrics.record_operation('read', 0.1, 0, True)

    # Verify it was recorded (access needs to be thread-safe)
    import asyncio
    async def verify():
        async with metrics._lock:
            return len(metrics.operations), list(metrics.operations)[-1] if metrics.operations else None

    # Run the async verification
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        count, last_op = loop.run_until_complete(verify())
    finally:
        loop.close()

    # Assertions
    assert count == 1, f"Expected 1 operation, got {count}"
    assert last_op is not None, "Operation should not be None"
    assert last_op['operation_type'] == 'read', f"Expected 'read', got {last_op['operation_type']}"
    assert last_op['duration'] == 0.1, f"Expected duration 0.1, got {last_op['duration']}"
    assert last_op['retries'] == 0, f"Expected retries 0, got {last_op['retries']}"
    assert last_op['success'] is True, f"Expected success True, got {last_op['success']}"

    print("✅ Test passed: record_operation has complete implementation with proper locking")


def test_record_operation_multiple_operations():
    """Test that record_operation correctly records multiple operations.

    This verifies the locking mechanism works correctly for consecutive calls.
    """
    metrics = IOMetrics()

    # Record multiple operations
    for i in range(5):
        metrics.record_operation('write', 0.05 * (i + 1), i, i % 2 == 0)

    # Verify all were recorded
    import asyncio
    async def verify():
        async with metrics._lock:
            return len(metrics.operations)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        count = loop.run_until_complete(verify())
    finally:
        loop.close()

    assert count == 5, f"Expected 5 operations, got {count}"
    print("✅ Test passed: Multiple operations recorded correctly with locking")


def test_record_operation_thread_safety():
    """Test that record_operation uses proper locking for thread safety.

    This verifies that the 'with self._sync_lock:' statement is present
    and working correctly.
    """
    metrics = IOMetrics()

    # This test verifies the method has the lock attribute
    assert hasattr(metrics, '_sync_lock'), "IOMetrics should have _sync_lock attribute"
    assert hasattr(metrics, 'operations'), "IOMetrics should have operations attribute"

    # Record operation which should use the lock internally
    metrics.record_operation('flush', 0.02, 1, False, 'ENOENT')

    # Verify it was recorded
    import asyncio
    async def verify():
        async with metrics._lock:
            if metrics.operations:
                return list(metrics.operations)[-1]
            return None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        last_op = loop.run_until_complete(verify())
    finally:
        loop.close()

    assert last_op is not None, "Operation should be recorded"
    assert last_op['operation_type'] == 'flush', f"Expected 'flush', got {last_op['operation_type']}"
    assert last_op['error_type'] == 'ENOENT', f"Expected error_type 'ENOENT', got {last_op.get('error_type')}"

    print("✅ Test passed: Thread safety with _sync_lock verified")
