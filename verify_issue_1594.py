#!/usr/bin/env python
"""
Manual verification script for Issue #1594
Tests that _lock_timeout is always initialized correctly.
"""
import sys
sys.path.insert(0, 'src')

from flywheel.storage import _AsyncCompatibleLock

def test_with_timeout_range():
    """Test with timeout_range only."""
    lock = _AsyncCompatibleLock(timeout_range=(5.0, 15.0), lock_timeout=None)
    assert hasattr(lock, '_lock_timeout'), "Missing _lock_timeout attribute"
    assert lock._lock_timeout == 10.0, f"Expected 10.0, got {lock._lock_timeout}"
    print("✓ Test with timeout_range: PASS")

def test_with_lock_timeout():
    """Test with lock_timeout only."""
    lock = _AsyncCompatibleLock(timeout_range=None, lock_timeout=7.5)
    assert hasattr(lock, '_lock_timeout'), "Missing _lock_timeout attribute"
    assert lock._lock_timeout == 7.5, f"Expected 7.5, got {lock._lock_timeout}"
    print("✓ Test with lock_timeout: PASS")

def test_with_defaults():
    """Test with default values."""
    lock = _AsyncCompatibleLock(timeout_range=None, lock_timeout=None)
    assert hasattr(lock, '_lock_timeout'), "Missing _lock_timeout attribute"
    assert lock._lock_timeout == lock._DEFAULT_LOCK_TIMEOUT, \
        f"Expected {lock._DEFAULT_LOCK_TIMEOUT}, got {lock._lock_timeout}"
    print("✓ Test with defaults: PASS")

def test_accessible():
    """Test that _lock_timeout is accessible."""
    lock = _AsyncCompatibleLock(timeout_range=(3.0, 9.0), lock_timeout=None)
    try:
        timeout = lock._lock_timeout
        assert timeout == 6.0, f"Expected 6.0, got {timeout}"
        print("✓ Test accessibility: PASS")
    except AttributeError as e:
        print(f"✗ Test accessibility: FAIL - {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Verifying Issue #1594: _lock_timeout initialization...")
    print()

    try:
        test_with_timeout_range()
        test_with_lock_timeout()
        test_with_defaults()
        test_accessible()

        print()
        print("=" * 60)
        print("All tests PASSED! Issue #1594 does NOT exist in current code.")
        print("=" * 60)
        print()
        print("The _lock_timeout attribute is correctly initialized in all cases:")
        print("  1. With timeout_range: set to midpoint")
        print("  2. With lock_timeout: set to provided value")
        print("  3. With neither: set to _DEFAULT_LOCK_TIMEOUT (10.0)")
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"Test FAILED: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"Unexpected error: {e}")
        print("=" * 60)
        sys.exit(1)
