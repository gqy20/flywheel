#!/usr/bin/env python
"""Standalone test to demonstrate issue #1381 bug."""

import asyncio
import sys
import threading
import time

# Add src to path
sys.path.insert(0, 'src')

from flywheel.storage import _AsyncCompatibleLock


def test_sync_async_lock_bug():
    """Demonstrate that sync and async locks don't mutually exclude."""
    lock = _AsyncCompatibleLock()
    results = []
    sync_acquired = threading.Event()
    async_allowed = threading.Event()

    def sync_worker():
        """Hold sync lock and check if async can acquire."""
        with lock:
            results.append("sync_acquired")
            sync_acquired.set()
            time.sleep(0.2)
            if async_allowed.is_set():
                results.append("BUG_DETECTED: async acquired while sync held")

    async def async_worker():
        """Try to acquire async lock while sync is held."""
        await asyncio.sleep(0.1)
        async with lock:
            results.append("async_acquired")
            async_allowed.set()

    # Start sync thread
    sync_thread = threading.Thread(target=sync_worker)
    sync_thread.start()
    sync_acquired.wait(timeout=1.0)

    # Run async in new thread
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_worker())
        finally:
            loop.close()

    async_thread = threading.Thread(target=run_async)
    async_thread.start()

    sync_thread.join(timeout=2.0)
    async_thread.join(timeout=2.0)

    print(f"Results: {results}")

    if "BUG_DETECTED" in str(results):
        print("\n❌ TEST FAILED: Bug confirmed!")
        print("async lock was acquired while sync lock was held.")
        print("threading.RLock and asyncio.Lock are independent.")
        return False
    else:
        print("\n✅ TEST PASSED: Locks properly exclude each other.")
        return True


if __name__ == "__main__":
    success = test_sync_async_lock_bug()
    sys.exit(0 if success else 1)
