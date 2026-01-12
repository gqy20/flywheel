#!/usr/bin/env python3
"""
Verification script for issue #1554.
Checks that the Storage class is properly defined and _async_events is initialized.
"""

import sys
import tempfile
import os

def main():
    print("=" * 60)
    print("Verifying Issue #1554: Code truncation check")
    print("=" * 60)

    # Test 1: Import the module
    print("\n[Test 1] Attempting to import Storage class...")
    try:
        from flywheel.storage import Storage
        print("✓ Successfully imported Storage class")
    except SyntaxError as e:
        print(f"✗ Syntax error in storage.py: {e}")
        return 1
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        return 1

    # Test 2: Create instance and check attributes
    print("\n[Test 2] Creating Storage instance...")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        try:
            storage = Storage(storage_path)
            print("✓ Successfully created Storage instance")
        except Exception as e:
            print(f"✗ Failed to create instance: {e}")
            return 1

        # Test 3: Check _async_events attribute
        print("\n[Test 3] Checking _async_events attribute...")
        if not hasattr(storage, "_async_events"):
            print("✗ Missing _async_events attribute")
            return 1
        print(f"✓ _async_events exists: {type(storage._async_events)}")

        if not isinstance(storage._async_events, dict):
            print(f"✗ _async_events is not a dict: {type(storage._async_events)}")
            return 1
        print(f"✓ _async_events is a dict")

        # Test 4: Check _async_event_init_lock attribute (Issue #1545)
        print("\n[Test 4] Checking _async_event_init_lock attribute (Issue #1545)...")
        if not hasattr(storage, "_async_event_init_lock"):
            print("✗ Missing _async_event_init_lock attribute")
            return 1
        print(f"✓ _async_event_init_lock exists: {type(storage._async_event_init_lock)}")

        # Test 5: Check _lock attribute (Issue #1394)
        print("\n[Test 5] Checking _lock attribute (Issue #1394)...")
        import threading
        if not hasattr(storage, "_lock"):
            print("✗ Missing _lock attribute")
            return 1
        print(f"✓ _lock exists: {type(storage._lock)}")

        if not isinstance(storage._lock, threading.Lock):
            print(f"✗ _lock is not a threading.Lock: {type(storage._lock)}")
            return 1
        print(f"✓ _lock is a threading.Lock (not RLock per Issue #1394)")

    print("\n" + "=" * 60)
    print("✓ All tests passed! Code is complete and correct.")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
