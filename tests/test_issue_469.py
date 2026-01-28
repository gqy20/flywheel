"""Test for Issue #469: Windows file lock range calculation is incorrect.

The issue is that the lock range (0, 0xFFFFFFFF) is claimed to represent 0 to 4GB,
but actually represents 0 to 0xFFFFFFFF00000000 bytes (approx 16 Exabytes).

In Windows LockFileEx API, the lock range is specified as:
- low: NumberOfBytesToLockLow (lower 32 bits of the byte count)
- high: NumberOfBytesToLockHigh (upper 32 bits of the byte count)

The actual locked range = low + (high << 32)

So (0, 0xFFFFFFFF) locks:
- 0 + (0xFFFFFFFF << 32) = 0xFFFFFFFF00000000 bytes (approx 16 EB)

To lock 4GB (0xFFFFFFFF bytes):
- We need (0xFFFFFFFF, 0) which equals 0xFFFFFFFF + (0 << 32) = 0xFFFFFFFF bytes

Or to lock "a very large range" from byte 0:
- We should use (0xFFFFFFFF, 0xFFFFFFFF) for maximum range
- Or (0, 0xFFFFFFFF) if we want to lock ~16EB starting from offset 0

This test verifies that the lock range calculation is correct.
"""
import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_file_lock_range_calculation():
    """Test that Windows file lock range is calculated correctly.

    According to the issue, the lock range (0, 0xFFFFFFFF) is claimed to
    represent 0 to 4GB, but actually represents ~16 Exabytes.

    The comment says: "This represents a range from 0 to 4GB"
    But the math shows: (0, 0xFFFFFFFF) = 0 + (0xFFFFFFFF << 32) bytes

    This test verifies the actual range matches the documented behavior.
    """
    with TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Get the lock range that would be used for file locking
        # We need to create a file handle to test this
        with storage_path.open('w') as f:
            lock_range = storage._get_file_lock_range_from_handle(f)

        # The lock range should be a tuple of (low, high) on Windows
        assert isinstance(lock_range, tuple), f"Expected tuple, got {type(lock_range)}"
        assert len(lock_range) == 2, f"Expected 2 elements, got {len(lock_range)}"

        low, high = lock_range

        # Calculate the actual byte range this represents
        # Range = low + (high << 32)
        actual_range_bytes = low + (high << 32)

        # According to the comment in the code, this should represent "0 to 4GB"
        # 4GB = 0xFFFFFFFF bytes = 4294967295 bytes
        expected_4gb = 0xFFFFFFFF  # 4294967295 bytes

        # The issue: (0, 0xFFFFFFFF) actually represents ~16 Exabytes, not 4GB
        # 16 EB = 0xFFFFFFFF00000000 bytes = 18446744065119617024 bytes
        incorrect_range = 0 + (0xFFFFFFFF << 32)

        # Test case 1: If the intention is to lock 4GB (0xFFFFFFFF bytes)
        # Then the correct lock range should be (0xFFFFFFFF, 0)
        # Because: 0xFFFFFFFF + (0 << 32) = 0xFFFFFFFF bytes
        correct_4gb_low = 0xFFFFFFFF
        correct_4gb_high = 0
        correct_4gb_range = correct_4gb_low + (correct_4gb_high << 32)

        # Test case 2: If the intention is to lock "a very large range"
        # Then either:
        # a) Use (0xFFFFFFFF, 0xFFFFFFFF) for maximum 64-bit range (~16 EB at offset 0xFFFFFFFF)
        # b) Use (0, 0xFFFFFFFF) to lock from offset 0 for ~16 EB
        # But the comment MUST be accurate

        # Verify the current implementation
        if (low, high) == (0, 0xFFFFFFFF):
            # Current implementation uses (0, 0xFFFFFFFF)
            # This locks from offset 0 for ~16 Exabytes
            assert actual_range_bytes == incorrect_range

            # The bug: The comment says "0 to 4GB" but it's actually ~16 EB
            # This test will fail until the bug is fixed
            assert False, (
                f"Bug detected: Lock range (0, 0xFFFFFFFF) locks {actual_range_bytes} bytes "
                f"(~16 Exabytes), but the comment claims it locks 4GB. "
                f"Either change to ({correct_4gb_low}, {correct_4gb_high}) for 4GB, "
                f"or fix the comment to accurately reflect the ~16 EB range."
            )

        elif (low, high) == (0xFFFFFFFF, 0):
            # Correct implementation for 4GB
            assert actual_range_bytes == expected_4gb
            assert actual_range_bytes == correct_4gb_range

        elif (low, high) == (0xFFFFFFFF, 0xFFFFFFFF):
            # Maximum range (not recommended, but valid)
            # This locks from offset 0xFFFFFFFF for ~16 EB
            max_range = 0xFFFFFFFF + (0xFFFFFFFF << 32)
            assert actual_range_bytes == max_range

        else:
            # Unknown lock range configuration
            pytest.fail(f"Unexpected lock range: ({low}, {high})")


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_file_lock_range_4gb_correctness():
    """Test that verifies the correct lock range for 4GB.

    This test documents what the correct lock range should be if we
    want to lock the first 4GB of the file.
    """
    with TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Get the lock range that would be used for file locking
        with storage_path.open('w') as f:
            lock_range = storage._get_file_lock_range_from_handle(f)

        low, high = lock_range

        # For locking 4GB (0xFFFFFFFF bytes):
        # - low = 0xFFFFFFFF (lower 32 bits)
        # - high = 0 (upper 32 bits)
        # - Actual range = 0xFFFFFFFF + (0 << 32) = 0xFFFFFFFF bytes = 4GB
        correct_4gb_low = 0xFFFFFFFF
        correct_4gb_high = 0

        # The current buggy implementation
        buggy_low = 0
        buggy_high = 0xFFFFFFFF

        # Verify the bug exists
        if (low, high) == (buggy_low, buggy_high):
            # Calculate what the buggy range actually locks
            buggy_range = buggy_low + (buggy_high << 32)
            expected_4gb = 0xFFFFFFFF

            # This assertion demonstrates the bug
            assert buggy_range != expected_4gb, (
                f"Buggy implementation: ({buggy_low}, {buggy_high}) locks "
                f"{buggy_range} bytes (~{buggy_range / (1024**6):.1f} EB), "
                f"not {expected_4gb} bytes (4 GB)"
            )

            # This will fail until the bug is fixed
            assert False, (
                f"Issue #469: Current implementation uses ({low}, {high}) which locks "
                f"{buggy_range} bytes, but should use ({correct_4gb_low}, {correct_4gb_high}) "
                f"to lock 4GB ({expected_4gb} bytes)"
            )

        elif (low, high) == (correct_4gb_low, correct_4gb_high):
            # Correct implementation
            actual_range = low + (high << 32)
            expected_4gb = 0xFFFFFFFF
            assert actual_range == expected_4gb
        else:
            pytest.fail(f"Unexpected lock range: ({low}, {high})")


@pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
def test_unix_file_lock_range_is_placeholder():
    """Test that Unix file lock range is a placeholder (ignored by fcntl)."""
    with TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # On Unix, the lock range should be a placeholder (ignored by fcntl.flock)
        with storage_path.open('w') as f:
            lock_range = storage._get_file_lock_range_from_handle(f)

        # Unix should return 0 (placeholder, ignored by fcntl)
        assert lock_range == 0, f"Unix lock range should be 0, got {lock_range}"
