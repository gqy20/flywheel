#!/usr/bin/env python
"""手动运行测试来验证 Issue #1181"""
import sys
import asyncio
sys.path.insert(0, 'src')

from flywheel.storage import _AsyncCompatibleLock


def test_exit_without_enter_should_not_raise():
    """Test that __exit__ without __enter__ doesn't raise RuntimeError."""
    print("Test 1: __exit__ without __enter__")
    lock = _AsyncCompatibleLock()

    try:
        lock.__exit__(None, None, None)
        print("  PASS: No error raised")
        return True
    except RuntimeError as e:
        if "Lock is not acquired" in str(e) or "not acquired" in str(e).lower():
            print(f"  FAIL: Unsafe lock release error: {e}")
            return False
        raise


def test_normal_context_manager_usage():
    """Test that normal context manager usage still works correctly."""
    print("Test 2: Normal context manager usage")
    lock = _AsyncCompatibleLock()

    try:
        with lock:
            # Lock should be held here
            if not lock._lock.locked():
                print("  FAIL: Lock should be held inside context")
                return False

        # Lock should be released here
        if lock._lock.locked():
            print("  FAIL: Lock should be released after context")
            return False

        print("  PASS: Normal usage works correctly")
        return True
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Issue #1181: Unsafe lock release in __exit__")
    print("=" * 60)
    print()

    result1 = test_exit_without_enter_should_not_raise()
    print()
    result2 = test_normal_context_manager_usage()
    print()

    print("=" * 60)
    if result1 and result2:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
