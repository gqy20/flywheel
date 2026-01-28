"""Test for issue #1130: asyncio.run() should not be called in running event loop"""

import asyncio
import pytest
from flywheel.storage import PersistentStorageJSON


def test_record_operation_in_async_context_should_raise_error():
    """Test that record_operation raises RuntimeError when called from async context"""

    storage = PersistentStorageJSON(
        max_operations=100,
        persistence_path="/tmp/test_storage_1130.json"
    )

    async def call_in_async_context():
        # This should raise RuntimeError, not try to call asyncio.run()
        storage.record_operation(
            operation_type="read",
            duration=0.1,
            retries=0,
            success=True,
            error_type=None
        )

    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        with pytest.raises(RuntimeError) as exc_info:
            loop.run_until_complete(call_in_async_context())

        # Verify the error message mentions the async context issue
        assert "async context" in str(exc_info.value).lower() or "record_operation_async" in str(exc_info.value)
    finally:
        loop.close()


def test_record_operation_in_sync_context_works():
    """Test that record_operation works correctly in sync context"""

    storage = PersistentStorageJSON(
        max_operations=100,
        persistence_path="/tmp/test_storage_1130_sync.json"
    )

    # This should work fine in sync context
    storage.record_operation(
        operation_type="read",
        duration=0.1,
        retries=0,
        success=True,
        error_type=None
    )

    # Verify the operation was recorded
    assert storage.total_operation_count() == 1
