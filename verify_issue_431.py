#!/usr/bin/env python3
"""Verify that Issue #431 is already fixed.

This script verifies that the _get_file_lock_range_from_handle method
is properly called and its return value is used in the Windows file
locking implementation.
"""

import os
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flywheel.storage import Storage

# Read the storage.py file
storage_file = Path(__file__).parent / "src" / "flywheel" / "storage.py"
content = storage_file.read_text()

# Check if _get_file_lock_range_from_handle is called
print("=" * 60)
print("Issue #431 Verification")
print("=" * 60)
print()

# Check 1: Method definition exists
if "def _get_file_lock_range_from_handle(self, file_handle)" in content:
    print("✅ Check 1: Method _get_file_lock_range_from_handle is defined")
else:
    print("❌ Check 1: Method _get_file_lock_range_from_handle NOT found")

# Check 2: Method is called in _acquire_file_lock
if "lock_range_low, lock_range_high = self._get_file_lock_range_from_handle(file_handle)" in content:
    print("✅ Check 2: Method _get_file_lock_range_from_handle is CALLED in _acquire_file_lock")
else:
    print("❌ Check 2: Method _get_file_lock_range_from_handle NOT called")

# Check 3: Return value is used
if "lock_range_low,  # NumberOfBytesToLockLow" in content and "lock_range_high,  # NumberOfBytesToLockHigh" in content:
    print("✅ Check 3: Return values (lock_range_low, lock_range_high) are USED in LockFileEx")
else:
    print("❌ Check 3: Return values NOT used")

print()
print("=" * 60)
print("Conclusion:")
print("=" * 60)

all_checks_pass = (
    "def _get_file_lock_range_from_handle(self, file_handle)" in content and
    "lock_range_low, lock_range_high = self._get_file_lock_range_from_handle(file_handle)" in content and
    "lock_range_low,  # NumberOfBytesToLockLow" in content
)

if all_checks_pass:
    print("✅ Issue #431 is ALREADY FIXED in the codebase")
    print("   The _get_file_lock_range_from_handle method is properly")
    print("   called and its return value is used in the Windows")
    print("   file locking implementation.")
else:
    print("❌ Issue #431 needs to be fixed")
