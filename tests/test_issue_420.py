"""Test for consistent directory security across all OS (Issue #420).

This test verifies that _secure_all_parent_directories is called on ALL
operating systems, not just Unix-like systems.

The original bug was that the code had:
    if os.name != 'nt':  # Unix-like systems
        self._secure_all_parent_directories(self.path.parent)

This skipped directory security on Windows, which could leave parent
directories with insecure permissions.

The fix ensures _secure_all_parent_directories is called unconditionally
on all operating systems.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from flywheel.storage import Storage


def test_secure_all_parent_directories_called_on_all_os():
    """Test that _secure_all_parent_directories is called on all OS.

    This test verifies the fix for issue #420 by checking that
    _secure_all_parent_directories is called regardless of the
    operating system.

    The test mocks _secure_all_parent_directories and verifies it's
    called during Storage initialization, even when os.name == 'nt'.

    Ref: Issue #420
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test" / "todos.json"

        # Mock _secure_all_parent_directories to track if it was called
        with patch.object(Storage, '_secure_all_parent_directories') as mock_secure:
            # Create storage
            storage = Storage(str(storage_path))

            # Verify _secure_all_parent_directories was called exactly once
            assert mock_secure.called, (
                "_secure_all_parent_directories was NOT called during Storage "
                "initialization. This is the bug from issue #420 - directory "
                "security is being skipped."
            )

            # Verify it was called with the parent directory
            assert mock_secure.call_count == 1, (
                f"_secure_all_parent_directories was called {mock_secure.call_count} "
                f"times. Expected 1."
            )

            # Verify the argument
            call_args = mock_secure.call_args[0]
            assert call_args[0] == storage_path.parent, (
                f"_secure_all_parent_directories was called with "
                f"{call_args[0]}, expected {storage_path.parent}"
            )


def test_secure_all_parent_directories_called_even_on_windows():
    """Test that _secure_all_parent_directories is called even on Windows.

    This test specifically verifies the fix for issue #420 by simulating
    a Windows environment (os.name == 'nt') and ensuring that
    _secure_all_parent_directories is still called.

    The original bug had code like:
        if os.name != 'nt':  # Unix-like systems
            self._secure_all_parent_directories(self.path.parent)

    This test ensures that conditional check has been removed.

    Ref: Issue #420
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "windows_test" / "todos.json"

        # Mock os.name to simulate Windows
        with patch('os.name', 'nt'):
            # Mock _secure_all_parent_directories to track if it was called
            with patch.object(Storage, '_secure_all_parent_directories') as mock_secure:
                # Create storage
                storage = Storage(str(storage_path))

                # CRITICAL: Verify _secure_all_parent_directories was called
                # even though we're simulating Windows (os.name == 'nt')
                assert mock_secure.called, (
                    "_secure_all_parent_directories was NOT called during Storage "
                    "initialization on Windows (os.name == 'nt'). This is the bug "
                    "from issue #420 - directory security is being skipped on Windows."
                )

                # Verify it was called exactly once
                assert mock_secure.call_count == 1, (
                    f"_secure_all_parent_directories was called {mock_secure.call_count} "
                    f"times on Windows. Expected 1."
                )


def test_no_conditional_skip_for_windows():
    """Test that there's no conditional skip for Windows in Storage.__init__.

    This test verifies that the fix for issue #420 has been properly applied
    by checking the source code for the problematic pattern.

    Ref: Issue #420
    """
    import inspect

    # Get the source code of Storage.__init__
    source = inspect.getsource(Storage.__init__)

    # Check that the problematic pattern is NOT present
    # The old buggy code had: if os.name != 'nt':  # Unix-like systems
    #                       self._secure_all_parent_directories(self.path.parent)

    # Look for the pattern where _secure_all_parent_directories is
    # conditionally called based on os.name != 'nt'
    assert "if os.name != 'nt'" not in source or \
           "self._secure_all_parent_directories" not in source.split("if os.name != 'nt'")[0], (
        "Found conditional OS check that may skip _secure_all_parent_directories. "
        "This is the bug from issue #420. The method should be called unconditionally "
        "on all operating systems."
    )

    # Verify that _secure_all_parent_directories IS called in __init__
    assert "_secure_all_parent_directories" in source, (
        "_secure_all_parent_directories is not called in Storage.__init__ at all. "
        "This would be a regression."
    )


if __name__ == "__main__":
    # Run tests
    test_secure_all_parent_directories_called_on_all_os()
    print("✓ test_secure_all_parent_directories_called_on_all_os passed")

    test_secure_all_parent_directories_called_even_on_windows()
    print("✓ test_secure_all_parent_directories_called_even_on_windows passed")

    test_no_conditional_skip_for_windows()
    print("✓ test_no_conditional_skip_for_windows passed")

    print("\nAll tests for issue #420 passed!")
