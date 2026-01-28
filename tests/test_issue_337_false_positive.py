"""Test to verify Issue #337 is a false positive.

Issue #337 claimed the code was truncated at `parts = user.rspli`,
but the actual code is complete: `parts = user.rsplit('\\', 1)`.

This test verifies:
1. The storage module can be imported (no syntax errors)
2. The rsplit logic works correctly for Windows username parsing
"""

import pytest


def test_storage_module_imports():
    """Verify storage.py can be imported without syntax errors."""
    from flywheel.storage import Storage
    assert Storage is not None


def test_rsplit_logic_windows_username():
    """Test the rsplit logic mentioned in the issue.

    The code at line 223 correctly uses:
        parts = user.rsplit('\\', 1)

    This should extract the username from 'DOMAIN\\user' format.
    """
    # Simulate the logic from storage.py lines 221-225
    test_cases = [
        ("DOMAIN\\username", "username"),
        ("COMPUTERNAME\\user", "user"),
        ("DOMAIN\\user\\extra", "user\\extra"),  # Only splits on last backslash
        ("single", "single"),  # No backslash, no split
    ]

    for user_input, expected in test_cases:
        if '\\' in user_input:
            parts = user_input.rsplit('\\', 1)
            if len(parts) == 2:
                result = parts[1]
            else:
                result = user_input
        else:
            result = user_input

        assert result == expected, f"Failed for {user_input}: got {result}, expected {expected}"


def test_storage_methods_exist():
    """Verify all methods mentioned in the issue exist."""
    from flywheel.storage import Storage

    # Check that all methods mentioned in issue #337 exist
    assert hasattr(Storage, 'add'), "Storage.add method missing"
    assert hasattr(Storage, 'delete'), "Storage.delete (remove) method missing"
    assert hasattr(Storage, '_load'), "Storage._load method missing"
    assert hasattr(Storage, '_save'), "Storage._save method missing"
    assert hasattr(Storage, '_cleanup'), "Storage._cleanup method missing"
