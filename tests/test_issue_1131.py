"""Test for issue #1131: asyncio.run() in running event loop causes RuntimeError"""

import asyncio
import pytest

from flywheel.storage import Storage


def test_total_operation_count_in_running_event_loop():
    """Test that total_operation_count works when called from a running event loop."""
    storage = Storage()

    # Simulate being in an already running event loop
    # (e.g., in Jupyter Notebook or async web framework)
    async def call_in_event_loop():
        # This should not raise RuntimeError
        count = storage.total_operation_count()
        assert isinstance(count, int)
        assert count >= 0

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(call_in_event_loop())
    finally:
        loop.close()


def test_total_operation_count_standalone():
    """Test that total_operation_count works in normal sync context."""
    storage = Storage()
    count = storage.total_operation_count()
    assert isinstance(count, int)
    assert count >= 0
