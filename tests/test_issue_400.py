"""Test for Issue #400 - Windows directory creation should use atomic security.

The issue is that _create_and_secure_directories creates directories using mkdir()
which inherits insecure ACLs on Windows, then immediately calls _secure_directory().
This creates a time window where directories exist with insecure permissions.

The fix uses CreateDirectory with a security descriptor parameter to make
directory creation atomic with security on Windows.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows atomic directory creation test only applicable on Windows"
)


class TestWindowsAtomicDirectoryCreation:
    """Test that Windows directory creation is atomic with security (Issue #400)."""

    def test_win32file_createdirectory_is_used(self):
        """Test that win32file.CreateDirectory is used instead of mkdir() on Windows.

        This verifies that the implementation uses the atomic CreateDirectory API
        rather than mkdir() followed by SetFileSecurity().
        """
        # Mock win32security and related modules
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock(), 'win32file': MagicMock()}):
            import win32security
            import win32con
            import win32api
            import win32file

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
            win32con.NameFullyQualifiedDN = 1  # Mock constant

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

            # Track CreateDirectory calls
            create_directory_calls = []

            def track_create_directory(path, security_descriptor):
                create_directory_calls.append({
                    'path': path,
                    'security_descriptor': security_descriptor
                })
                # Return True to indicate success
                return True

            win32file.CreateDirectory.side_effect = track_create_directory

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage with nested directories
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use a nested path to test parent directory creation
                storage_path = Path(tmpdir) / "subdir1" / "subdir2" / "test_todos.json"

                # Track if mkdir was called (which would indicate vulnerability)
                mkdir_called = []
                original_mkdir = Path.mkdir

                def track_mkdir(self, *args, **kwargs):
                    mkdir_called.append({
                        'path': self,
                        'args': args,
                        'kwargs': kwargs
                    })
                    # Don't actually call mkdir - we want CreateDirectory to be used
                    raise NotImplementedError("mkdir should not be called on Windows")

                with patch.object(Path, 'mkdir', track_mkdir):
                    # This should use CreateDirectory, not mkdir
                    Storage(str(storage_path))

                # VERIFY: CreateDirectory was called instead of mkdir
                assert len(create_directory_calls) > 0, (
                    "Issue #400: win32file.CreateDirectory should be used on Windows "
                    "for atomic directory creation with security descriptor."
                )

                # Verify that CreateDirectory was called with security descriptors
                for call_info in create_directory_calls:
                    assert call_info['security_descriptor'] is not None, (
                        "Issue #400: CreateDirectory should be called with a security descriptor"
                    )

                # Verify mkdir was NOT called (or only called on Unix)
                assert len(mkdir_called) == 0, (
                    f"Issue #400: mkdir() should not be called on Windows. "
                    f"Found {len(mkdir_called)} mkdir() calls. "
                    "Use win32file.CreateDirectory() for atomic security."
                )

    def test_security_descriptor_passed_to_createdirectory(self):
        """Test that CreateDirectory is called with a proper security descriptor.

        This verifies that the security descriptor passed to CreateDirectory
        contains all the necessary security settings.
        """
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock(), 'win32file': MagicMock()}):
            import win32security
            import win32con
            import win32api
            import win32file

            # Define Windows security constants
            win32security.SE_DACL_PROTECTED = 0x1000
            win32security.DACL_SECURITY_INFORMATION = 0x4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
            win32security.ACL_REVISION = 2

            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
            win32con.SYNCHRONIZE = 0x00100000
            win32con.NameFullyQualifiedDN = 1

            # Mock LookupAccountName
            mock_sid = MagicMock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock API functions
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Track security descriptor creation and method calls
            sd_instances = []
            original_sd = win32security.SECURITY_DESCRIPTOR

            def track_sd():
                mock_sd = MagicMock()
                sd_instances.append(mock_sd)

                # Track method calls on the security descriptor
                sd_calls = []

                def track_method(method_name, *args, **kwargs):
                    sd_calls.append({
                        'method': method_name,
                        'args': args,
                        'kwargs': kwargs
                    })

                mock_sd.SetSecurityDescriptorOwner.side_effect = lambda *args, **kwargs: track_method('SetSecurityDescriptorOwner', *args, **kwargs)
                mock_sd.SetSecurityDescriptorDacl.side_effect = lambda *args, **kwargs: track_method('SetSecurityDescriptorDacl', *args, **kwargs)
                mock_sd.SetSecurityDescriptorSacl.side_effect = lambda *args, **kwargs: track_method('SetSecurityDescriptorSacl', *args, **kwargs)
                mock_sd.SetSecurityDescriptorControl.side_effect = lambda *args, **kwargs: track_method('SetSecurityDescriptorControl', *args, **kwargs)

                mock_sd._calls = sd_calls  # Attach calls to the mock for inspection
                return mock_sd

            win32security.SECURITY_DESCRIPTOR.side_effect = track_sd

            # Mock ACL
            mock_dacl = MagicMock()
            win32security.ACL.return_value = mock_dacl

            # Track CreateDirectory calls and capture security descriptors
            create_directory_calls = []

            def track_create_directory(path, security_descriptor):
                create_directory_calls.append({
                    'path': path,
                    'security_descriptor': security_descriptor
                })
                return True

            win32file.CreateDirectory.side_effect = track_create_directory

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage with nested directories
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"

                Storage(str(storage_path))

                # VERIFY: CreateDirectory was called with security descriptors
                assert len(create_directory_calls) > 0, (
                    "Issue #400: CreateDirectory should be called with security descriptor"
                )

                # Verify security descriptors were properly configured
                for call_info in create_directory_calls:
                    sd = call_info['security_descriptor']
                    assert sd is not None, (
                        "Issue #400: Security descriptor should not be None"
                    )

                    # Check that the security descriptor had the proper methods called
                    # (SetSecurityDescriptorOwner, SetSecurityDescriptorDacl, etc.)
                    if hasattr(sd, '_calls'):
                        methods_called = [call['method'] for call in sd._calls]
                        assert 'SetSecurityDescriptorOwner' in methods_called, (
                            "Issue #400: Security descriptor should have owner set"
                        )
                        assert 'SetSecurityDescriptorDacl' in methods_called, (
                            "Issue #400: Security descriptor should have DACL set"
                        )
                        assert 'SetSecurityDescriptorControl' in methods_called, (
                            "Issue #400: Security descriptor should have control set (SE_DACL_PROTECTED)"
                        )

    def test_all_parent_directories_created_atomically(self):
        """Test that all parent directories are created atomically.

        When creating a nested directory path, all intermediate directories
        should be created using CreateDirectory with security descriptors.
        """
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock(), 'win32file': MagicMock()}):
            import win32security
            import win32con
            import win32api
            import win32file

            # Define Windows security constants
            win32security.SE_DACL_PROTECTED = 0x1000
            win32security.DACL_SECURITY_INFORMATION = 0x4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
            win32security.ACL_REVISION = 2

            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
            win32con.SYNCHRONIZE = 0x00100000
            win32con.NameFullyQualifiedDN = 1

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

            # Track CreateDirectory calls
            create_directory_calls = []

            def track_create_directory(path, security_descriptor):
                create_directory_calls.append({
                    'path': path,
                    'security_descriptor': security_descriptor
                })
                return True

            win32file.CreateDirectory.side_effect = track_create_directory

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage with deeply nested directories
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create 3 levels of nesting
                storage_path = Path(tmpdir) / "level1" / "level2" / "level3" / "test_todos.json"

                Storage(str(storage_path))

                # VERIFY: All parent directories were created using CreateDirectory
                # Should have created level1, level2, and level3
                assert len(create_directory_calls) == 3, (
                    f"Issue #400: Expected 3 CreateDirectory calls (one for each parent directory), "
                    f"got {len(create_directory_calls)}. "
                    "All parent directories should be created atomically."
                )

                # Verify each call had a security descriptor
                for call_info in create_directory_calls:
                    assert call_info['security_descriptor'] is not None, (
                        "Issue #400: Each CreateDirectory call should include a security descriptor"
                    )
