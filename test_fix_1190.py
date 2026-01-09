#!/usr/bin/env python
"""Quick verification script for Issue #1190 fix."""

import sys
import threading
import time

# Add src to path
sys.path.insert(0, '/home/runner/work/flywheel/flywheel/src')

from flywheel.storage import _AsyncCompatibleLock


def test_cross_thread_detection():
    """Test that cross-thread lock usage is detected."""
    lock = _AsyncCompatibleLock()

    # First, use the lock in the main thread to initialize the event loop
    print("Main thread: Acquiring lock...")
    with lock:
        print("Main thread: Lock acquired successfully")
        print(f"Main thread ID: {threading.get_ident()}")
        print(f"Event loop thread ID: {lock._event_loop_thread_id}")

    print("Main thread: Lock released")

    # Now try to use it from a different thread
    result = {"success": False, "error": None}

    def background_thread():
        try:
            print("Background thread: Trying to acquire lock...")
            with lock:
                result["success"] = True
                print("Background thread: Lock acquired (UNEXPECTED!)")
        except RuntimeError as e:
            result["error"] = str(e)
            print(f"Background thread: Got expected RuntimeError: {e}")
        except Exception as e:
            result["error"] = str(e)
            print(f"Background thread: Got unexpected error: {e}")

    bg_thread = threading.Thread(target=background_thread)
    start_time = time.time()
    bg_thread.start()
    bg_thread.join(timeout=5)
    elapsed = time.time() - start_time

    if bg_thread.is_alive():
        print(f"FAIL: Background thread hung for {elapsed:.2f}s - DEADLOCK!")
        return False

    if result["success"]:
        print("FAIL: Background thread was able to acquire lock from different thread")
        return False

    if result["error"] and ("thread" in result["error"].lower() or "event loop" in result["error"].lower()):
        print("PASS: Cross-thread usage was properly detected and prevented")
        return True

    print(f"FAIL: Unexpected error: {result['error']}")
    return False


if __name__ == "__main__":
    print("Testing Issue #1190 fix...")
    print("=" * 60)
    if test_cross_thread_detection():
        print("=" * 60)
        print("✓ Fix verification PASSED")
        sys.exit(0)
    else:
        print("=" * 60)
        print("✗ Fix verification FAILED")
        sys.exit(1)
