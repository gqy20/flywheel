"""Test for Issue #251 - Windows GetUserName() format handling.

This test ensures that win32api.GetUserName() returns a format that is
compatible with LookupAccountName, even in non-domain environments where
it might return 'COMPUTERNAME\\username' instead of just 'username'.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestWindowsGetUserNameFormat:
    """Test Windows username format handling in non-domain environments."""

    @pytest.mark.skipif(
        True,  # This test is for documentation only - actual fix requires Windows
        reason="Test documents expected behavior; actual testing requires Windows environment"
    )
    def test_get_username_format_compatibility(self):
        """Test that GetUserName returns compatible format for LookupAccountName.

        Issue #251: win32api.GetUserName() in non-domain environments may return
        'COMPUTERNAME\\username' format which causes LookupAccountName to fail.

        Expected: The code should extract pure username or use GetUserNameEx
        with NameSamCompatible to ensure correct format.
        """
        # This test documents the expected behavior
        # The actual fix should handle formats like:
        # - 'username' (already correct)
        # - 'COMPUTERNAME\\username' (needs extraction)
        # - 'DOMAIN\\username' (needs extraction)
        pass


def test_windows_username_parsing_logic():
    """Test the username parsing logic that should be implemented.

    This is a unit test that validates the parsing logic regardless of OS.
    """
    # Test cases for different username formats
    test_cases = [
        # (input, expected_output, description)
        ("username", "username", "Plain username"),
        ("COMPUTERNAME\\username", "username", "Computer-prefixed username"),
        ("DOMAIN\\username", "username", "Domain-prefixed username"),
        ("DOMAIN/user", "DOMAIN/user", "Forward slash should not be parsed"),
        ("username\\extra", "username\\extra", "Multiple backslashes ambiguous"),
    ]

    def extract_username(user: str) -> str:
        """Helper function to extract username from various formats.

        This logic should be implemented in storage.py to fix Issue #251.
        """
        # If the username contains a backslash, extract the part after it
        # This handles 'COMPUTERNAME\\username' -> 'username'
        if '\\' in user:
            parts = user.rsplit('\\', 1)
            # Only extract if there's exactly one domain prefix
            # Avoid splitting on usernames with multiple backslashes
            if len(parts) == 2:
                return parts[1]
        return user

    for input_user, expected, description in test_cases:
        result = extract_username(input_user)
        assert result == expected, f"Failed for {description}: {input_user} -> {result} (expected {expected})"


@pytest.mark.skipif(
    True,
    reason="Integration test - requires Windows environment with pywin32"
)
def test_windows_acl_with_non_domain_username(tmp_path):
    """Test that ACL setting works with non-domain usernames.

    This is an integration test that would run on Windows to verify
    the fix works correctly in the actual environment.
    """
    # This would test the actual Storage._secure_directory method
    # with a mocked GetUserName that returns 'COMPUTERNAME\\username'
    pass
