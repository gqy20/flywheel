#!/usr/bin/env python3
"""Quick verification script for issue #1624 fix."""

import sys

# Mock aiofiles as unavailable
sys.modules['aiofiles'] = None  # This will cause ImportError

# Remove from sys.modules if it was already imported
if 'flywheel.storage' in sys.modules:
    del sys.modules['flywheel.storage']

# Import storage module
from flywheel import storage

# Check that aiofiles has 'open' method
print(f"HAS_AIOFILES: {storage.HAS_AIOFILES}")
print(f"aiofiles type: {type(storage.aiofiles)}")
print(f"aiofiles has 'open': {hasattr(storage.aiofiles, 'open')}")
print(f"aiofiles.open is callable: {callable(storage.aiofiles.open)}")

# Try to access the open method
try:
    open_method = storage.aiofiles.open
    print(f"✅ SUCCESS: aiofiles.open is accessible: {open_method}")
except AttributeError as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print("\n✅ All checks passed! Issue #1624 is fixed.")
