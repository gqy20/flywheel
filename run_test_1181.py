#!/usr/bin/env python
"""手动运行测试来验证 Issue #1181"""
import sys
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


if __name__ == "__main__":
    result = test_exit_without_enter_should_not_raise()
    sys.exit(0 if result else 1)
