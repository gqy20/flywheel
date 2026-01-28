"""Test for issue #1136: IOMetrics.record_operation 定义了内部函数但从未调用

验证测试：确认 record_operation 方法确实调用了 _record_with_lock 内部函数。

注意：经检查，代码在第 247 行已经包含 `asyncio.run(_record_with_lock())` 调用，
因此 issue 中描述的问题实际上已经存在。这个测试作为验证测试，确认功能正常工作。
"""

import pytest
from flywheel.storage import PersistentStorageJSON


def test_record_operation_actually_records_operations():
    """Test that record_operation actually records operations to the deque.

    This test verifies that the internal _record_with_lock function is being called
    and operations are actually being appended to the operations deque.
    """

    storage = PersistentStorageJSON(
        max_operations=100,
        persistence_path="/tmp/test_storage_1136.json"
    )

    # Initially, no operations should be recorded
    assert storage.total_operation_count() == 0

    # Call record_operation multiple times
    storage.record_operation(
        operation_type="read",
        duration=0.1,
        retries=0,
        success=True,
        error_type=None
    )

    storage.record_operation(
        operation_type="write",
        duration=0.2,
        retries=1,
        success=False,
        error_type="ENOENT"
    )

    storage.record_operation(
        operation_type="flush",
        duration=0.05,
        retries=0,
        success=True,
        error_type=None
    )

    # Verify operations were actually recorded
    count = storage.total_operation_count()
    assert count == 3, f"Expected 3 operations, but got {count}"

    # Verify we can export the metrics (this internally accesses the operations deque)
    metrics = storage.get_metrics()
    assert metrics['total_operations'] == 3


def test_record_operation_in_sync_context_multiple_calls():
    """Test multiple calls to record_operation in sync context work correctly."""

    storage = PersistentStorageJSON(
        max_operations=100,
        persistence_path="/tmp/test_storage_1136_multiple.json"
    )

    # Call record_operation 10 times
    for i in range(10):
        storage.record_operation(
            operation_type="read",
            duration=0.01 * i,
            retries=0,
            success=True,
            error_type=None
        )

    # Verify all operations were recorded
    assert storage.total_operation_count() == 10
