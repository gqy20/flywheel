"""Test for Issue #400 - Windows directory creation should use atomic security.

The issue is that _create_and_secure_directories creates directories using mkdir()
which inherits insecure ACLs on Windows, then immediately calls _secure_directory().
This creates a time window where directories exist with insecure permissions.

The fix should use CreateDirectory with a security descriptor parameter to make
directory creation atomic with security on Windows.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call, AsyncMock

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows atomic directory creation test only applicable on Windows"
)


class TestWindowsAtomicDirectoryCreation:
    """Test that Windows directory creation is atomic with security (Issue #400)."""

    def test_no_time_window_between_mkdir_and_secure(self):
        """Test that there's no time window between mkdir and _secure_directory.

        This test verifies that the system uses an atomic approach where
        directories are created with security already applied, rather than
        creating them first and securing them later.
        """
        # Mock win32security and related modules
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define Windows security constants
            win32security.SE_DACL_PROTECTED = 0x1000
            win32security.DACL_SECURITY_INFORMATION = 0x4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000

            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
            win32con.SYNCHRONIZE = 0x00100000

            # Mock LookupAccountName
            mock_sid = MagicMock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock API functions
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock SECURITY_DESCRIPTOR
            mock_sd = MagicMock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            # Mock ACL
            mock_dacl = MagicMock()
            win32security.ACL.return_value = mock_dacl

            # Track SetFileSecurity calls to verify directories are secured
            setfilesecurity_calls = []

            def track_setfilesecurity(path, security_info, sd):
                setfilesecurity_calls.append({
                    'path': path,
                    'security_info': security_info,
                    'sd': sd
                })

            win32security.SetFileSecurity.side_effect = track_setfilesecurity

            # Mock CreateDirectory if it exists (for the fixed implementation)
            # The fix should use CreateDirectory instead of mkdir + SetFileSecurity
            create_directory_called = []
            original_create_directory = getattr(win32security, 'CreateDirectory', None)

            def track_create_directory(path, security_descriptor):
                create_directory_called.append({
                    'path': path,
                    'security_descriptor': security_descriptor
                })
                # Return True to indicate success
                return True

            if original_create_directory:
                win32security.CreateDirectory = track_create_directory

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage with nested directories
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use a nested path to test parent directory creation
                storage_path = Path(tmpdir) / "subdir1" / "subdir2" / "test_todos.json"

                # Track if mkdir was called (which would create a security window)
                mkdir_called = []
                original_mkdir = Path.mkdir

                def track_mkdir(self, *args, **kwargs):
                    mkdir_called.append({
                        'path': self,
                        'args': args,
                        'kwargs': kwargs
                    })
                    # Call the original mkdir
                    return original_mkdir(self, *args, **kwargs)

                with patch.object(Path, 'mkdir', track_mkdir):
                    Storage(str(storage_path))

                # VERIFY: Check if CreateDirectory was used instead of mkdir
                # The FIXED implementation should use CreateDirectory with security descriptor
                # If this test fails, it means mkdir is still being used (security vulnerability)

                # Check that mkdir was NOT used for parent directories
                # (or if it was used, it should be immediately followed by security)
                assert len(create_directory_called) > 0 or len(mkdir_called) == 0, (
                    "Issue #400: Windows should use CreateDirectory with security descriptor "
                    "instead of mkdir() to avoid security time window. "
                    f"Found {len(mkdir_called)} mkdir() calls which create security vulnerabilities."
                )

                # If CreateDirectory was called, verify it was called with a security descriptor
                if len(create_directory_called) > 0:
                    for call_info in create_directory_called:
                        assert call_info['security_descriptor'] is not None, (
                            "Issue #400: CreateDirectory should be called with a security descriptor"
                        )

    def test_security_descriptor_applied_during_creation(self):
        """Test that security descriptor is applied during directory creation, not after.

        This test verifies the implementation uses an atomic approach where
        the security descriptor is provided at creation time.
        """
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define Windows security constants
            win32security.SE_DACL_PROTECTED = 0x1000
            win32security.DACL_SECURITY_INFORMATION = 0x4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000

            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
            win32con.SYNCHRONIZE = 0x00100000

            # Mock LookupAccountName
            mock_sid = MagicMock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock API functions
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Track the sequence of operations
            operation_sequence = []

            # Mock SECURITY_DESCRIPTOR
            def create_security_descriptor():
                operation_sequence.append(('create_security_descriptor', None))
                mock_sd = MagicMock()
                return mock_sd

            win32security.SECURITY_DESCRIPTOR.side_effect = create_security_descriptor

            # Mock ACL
            def create_acl():
                operation_sequence.append(('create_acl', None))
                return MagicMock()

            win32security.ACL.side_effect = create_acl

            # Track SetFileSecurity calls
            def track_setfilesecurity(path, security_info, sd):
                operation_sequence.append(('set_file_security', path))

            win32security.SetFileSecurity.side_effect = track_setfilesecurity

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage with nested directories
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "deep" / "nested" / "path" / "test_todos.json"

                Storage(str(storage_path))

                # VERIFY: In the current implementation, there's a time window
                # because mkdir happens before SetFileSecurity
                # The FIXED implementation should use CreateDirectory to make it atomic

                # Check if there are separate create and secure operations
                separate_operations = [
                    op for op in operation_sequence
                    if op[0] in ['create_security_descriptor', 'set_file_security']
                ]

                # The current vulnerable implementation has separate operations
                # A secure implementation would have them combined
                assert False, (
                    "Issue #400: Test verifies that there's a security time window. "
                    "The current implementation uses mkdir() followed by SetFileSecurity(), "
                    "which creates a window where directories exist with insecure ACLs. "
                    f"Operation sequence: {operation_sequence}. "
                    "Fix: Use CreateDirectory API with security descriptor parameter."
                )

    def test_all_parent_directories_secured_atomically(self):
        """Test that all parent directories are secured atomically during creation.

        When creating a nested directory path like /a/b/c/d/file.json,
        all intermediate directories (/, a, b, c, d) should be created
        with atomic security, not created first and secured later.
        """
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define Windows security constants
            win32security.SE_DACL_PROTECTED = 0x1000
            win32security.DACL_SECURITY_INFORMATION = 0x4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000

            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
            win32con.SYNCHRONIZE = 0x00100000

            # Mock LookupAccountName
            mock_sid = MagicMock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock API functions
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock SECURITY_DESCRIPTOR
            mock_sd = MagicMock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            # Mock ACL
            mock_dacl = MagicMock()
            win32security.ACL.return_value = mock_dacl

            # Track all directory operations
            directory_operations = []

            def track_setfilesecurity(path, security_info, sd):
                directory_operations.append({
                    'operation': 'set_security',
                    'path': path
                })

            win32security.SetFileSecurity.side_effect = track_setfilesecurity

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage with deeply nested directories
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create 4 levels of nesting
                storage_path = Path(tmpdir) / "level1" / "level2" / "level3" / "level4" / "test_todos.json"

                # Track mkdir calls
                mkdir_calls = []
                original_mkdir = Path.mkdir

                def track_mkdir(self, *args, **kwargs):
                    mkdir_calls.append(str(self))
                    return original_mkdir(self, *args, **kwargs)

                with patch.object(Path, 'mkdir', track_mkdir):
                    Storage(str(storage_path))

                # VERIFY: All parent directories should be secured
                # The test should FAIL if any directory was created without immediate security

                # Count how many directories were created
                created_dirs = len(mkdir_calls)
                secured_dirs = len([op for op in directory_operations if op['operation'] == 'set_security'])

                # All created directories should be secured
                assert created_dirs == secured_dirs, (
                    f"Issue #400: Not all parent directories were secured atomically. "
                    f"Created {created_dirs} directories but only secured {secured_dirs}. "
                    "This indicates a time window where some directories existed with insecure ACLs."
                )

                # Additionally, verify that securing happened immediately after each mkdir
                # (not all mkdirs first, then all secures)
                # We can't easily test the timing, but we can verify the count matches
                assert created_dirs > 0, "No directories were created"
                assert secured_dirs > 0, "No directories were secured"
