#!/usr/bin/env python3
"""Quick test to verify the fix for issue #1406."""

import sys
import time
import threading
from flywheel.storage import _AsyncCompatibleLock


def test_basic_lock_usage():
    """Test basic lock usage still works."""
    print("Test 1: Basic lock usage...")
    lock = _AsyncCompatibleLock()
    with lock:
        print("  ✓ Lock acquired and released successfully")
    return True


def test_lock_timeout_works():
    """Test that lock timeout mechanism works."""
    print("\nTest 2: Lock timeout mechanism...")
    lock = _AsyncCompatibleLock()

    # Hold the lock in a thread
    def hold_lock():
        with lock:
            print("  Lock held by thread...")
            time.sleep(2)
            print("  Thread releasing lock...")

    holder = threading.Thread(target=hold_lock)
    holder.start()
    time.sleep(0.3)  # Let holder acquire

    # Try to acquire from main thread - should succeed after ~2 seconds
    print("  Trying to acquire lock...")
    start = time.time()
    try:
        with lock:
            elapsed = time.time() - start
            print(f"  ✓ Lock acquired after {elapsed:.2f}s (expected ~2s)")
            if elapsed < 1.5:
                print(f"  ⚠ Warning: Expected to wait at least 1.5s, got {elapsed:.2f}s")
            return True
    except TimeoutError as e:
        elapsed = time.time() - start
        print(f"  ⚠ TimeoutError after {elapsed:.2f}s: {e}")
        return False
    finally:
        holder.join()


def test_timeout_too_short():
    """Test that timeout raises TimeoutError when lock is held too long."""
    print("\nTest 3: Timeout with very short timeout...")
    lock = _AsyncCompatibleLock(lock_timeout=0.5)

    # Hold the lock
    lock.acquire()

    try:
        # Try to acquire with very short timeout - should fail
        start = time.time()
        try:
            with lock:
                pass
            print("  ✗ Should have timed out but didn't")
            return False
        except TimeoutError as e:
            elapsed = time.time() - start
            print(f"  ✓ TimeoutError after {elapsed:.2f}s: {e}")
            if 0.4 <= elapsed <= 0.7:
                print(f"  ✓ Timeout duration is correct (expected ~0.5s)")
            return True
    finally:
        lock.release()


def test_default_timeout_constant():
    """Test that the default timeout constant is set correctly."""
    print("\nTest 4: Default timeout constant...")
    lock = _AsyncCompatibleLock()
    if hasattr(lock, '_DEFAULT_LOCK_TIMEOUT'):
        print(f"  ✓ _DEFAULT_LOCK_TIMEOUT = {lock._DEFAULT_LOCK_TIMEOUT}s")
        if lock._DEFAULT_LOCK_TIMEOUT == 10.0:
            print("  ✓ Default timeout is 10.0 seconds as expected")
            return True
        else:
            print(f"  ✗ Expected 10.0s, got {lock._DEFAULT_LOCK_TIMEOUT}s")
            return False
    else:
        print("  ✗ _DEFAULT_LOCK_TIMEOUT constant not found")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing fix for Issue #1406: Lock timeout in __enter__")
    print("=" * 60)

    results = []
    results.append(("Basic lock usage", test_basic_lock_usage()))
    results.append(("Lock timeout mechanism", test_lock_timeout_works()))
    results.append(("Short timeout", test_timeout_too_short()))
    results.append(("Default timeout constant", test_default_timeout_constant()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✅ All tests passed! Issue #1406 is fixed.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
