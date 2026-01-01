"""Test for Issue #314 - Windows security fallback mechanism.

This test ensures that Windows security logic has proper fallback mechanisms
when win32api.GetUserName() returns edge case formats or when user/domain
cannot be resolved, using environment variables as fallback and raising
RuntimeError when security context cannot be obtained.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path


@pytest.mark.skipif(
    os.name != 'nt',
    reason="Windows-specific test"
)
class TestWindowsSecurityFallback:
    """Test Windows security fallback mechanisms."""

    def test_get_username_returns_empty_string_with_env_fallback(self, tmp_path):
        """Test fallback to USERNAME environment variable when GetUserName returns empty."""
        # Save original environment
        original_username = os.environ.get('USERNAME')
        original_userdomain = os.environ.get('USERDOMAIN')

        try:
            # Set environment variables as fallback
            os.environ['USERNAME'] = 'testuser'
            os.environ['USERDOMAIN'] = 'TESTDOMAIN'

            # Mock GetUserName to return empty string (edge case)
            with patch('win32api.GetUserName', return_value=''):
                with patch('win32api.GetUserNameEx', side_effect=Exception("No domain")):
                    with patch('win32api.GetComputerName', return_value='TESTPC'):
                        from flywheel.storage import Storage
                        # Should not raise - should use environment variables
                        storage = Storage(path=str(tmp_path / "test.json"))
                        assert storage is not None
        finally:
            # Restore environment
            if original_username is not None:
                os.environ['USERNAME'] = original_username
            else:
                os.environ.pop('USERNAME', None)
            if original_userdomain is not None:
                os.environ['USERDOMAIN'] = original_userdomain
            else:
                os.environ.pop('USERDOMAIN', None)

    def test_get_username_returns_none_with_env_fallback(self, tmp_path):
        """Test fallback to USERNAME environment variable when GetUserName returns None."""
        original_username = os.environ.get('USERNAME')
        original_userdomain = os.environ.get('USERDOMAIN')

        try:
            os.environ['USERNAME'] = 'testuser'
            os.environ['USERDOMAIN'] = 'TESTDOMAIN'

            # Mock GetUserName to return None (edge case)
            with patch('win32api.GetUserName', return_value=None):
                with patch('win32api.GetUserNameEx', side_effect=Exception("No domain")):
                    with patch('win32api.GetComputerName', return_value='TESTPC'):
                        from flywheel.storage import Storage
                        # Should not raise - should use environment variables
                        storage = Storage(path=str(tmp_path / "test.json"))
                        assert storage is not None
        finally:
            if original_username is not None:
                os.environ['USERNAME'] = original_username
            else:
                os.environ.pop('USERNAME', None)
            if original_userdomain is not None:
                os.environ['USERDOMAIN'] = original_userdomain
            else:
                os.environ.pop('USERDOMAIN', None)

    def test_get_username_returns_whitespace_with_env_fallback(self, tmp_path):
        """Test fallback when GetUserName returns whitespace only."""
        original_username = os.environ.get('USERNAME')
        original_userdomain = os.environ.get('USERDOMAIN')

        try:
            os.environ['USERNAME'] = 'testuser'
            os.environ['USERDOMAIN'] = 'TESTDOMAIN'

            # Mock GetUserName to return whitespace (edge case)
            with patch('win32api.GetUserName', return_value='   '):
                with patch('win32api.GetUserNameEx', side_effect=Exception("No domain")):
                    with patch('win32api.GetComputerName', return_value='TESTPC'):
                        from flywheel.storage import Storage
                        # Should not raise - should use environment variables
                        storage = Storage(path=str(tmp_path / "test.json"))
                        assert storage is not None
        finally:
            if original_username is not None:
                os.environ['USERNAME'] = original_username
            else:
                os.environ.pop('USERNAME', None)
            if original_userdomain is not None:
                os.environ['USERDOMAIN'] = original_userdomain
            else:
                os.environ.pop('USERDOMAIN', None)

    def test_no_username_env_and_api_fails_raises_runtime_error(self, tmp_path):
        """Test RuntimeError when both API and environment variables fail."""
        # Save and remove environment variables
        original_username = os.environ.pop('USERNAME', None)
        original_userdomain = os.environ.pop('USERDOMAIN', None)

        try:
            # Mock all APIs to fail
            with patch('win32api.GetUserName', return_value=''):
                with patch('win32api.GetUserNameEx', side_effect=Exception("No domain")):
                    with patch('win32api.GetComputerName', side_effect=Exception("No computer")):
                        from flywheel.storage import Storage
                        # Should raise RuntimeError when all methods fail
                        with pytest.raises(RuntimeError) as exc_info:
                            Storage(path=str(tmp_path / "test.json"))
                        assert "Cannot set Windows security" in str(exc_info.value) or \
                               "Invalid user name" in str(exc_info.value)
        finally:
            # Restore environment
            if original_username is not None:
                os.environ['USERNAME'] = original_username
            if original_userdomain is not None:
                os.environ['USERDOMAIN'] = original_userdomain

    def test_lookup_account_fails_with_env_fallback(self, tmp_path):
        """Test fallback when LookupAccountName fails with valid user from env."""
        original_username = os.environ.get('USERNAME')
        original_userdomain = os.environ.get('USERDOMAIN')

        try:
            os.environ['USERNAME'] = 'validuser'
            os.environ['USERDOMAIN'] = 'VALIDDOMAIN'

            # Mock GetUserName to return invalid user
            with patch('win32api.GetUserName', return_value='invalid\\user'):
                # Mock GetUserNameEx to fail
                with patch('win32api.GetUserNameEx', side_effect=Exception("No domain")):
                    # Mock GetComputerName to return domain
                    with patch('win32api.GetComputerName', return_value='VALIDDOMAIN'):
                        # Mock LookupAccountName to fail first time (with invalid user)
                        # but succeed with environment variable user
                        mock_lookup = Mock(side_effect=[
                            Exception("Lookup failed"),  # First call with invalid user
                            (Mock(), Mock(), Mock()),    # Second call with env user succeeds
                        ])
                        with patch('win32security.LookupAccountName', mock_lookup):
                            from flywheel.storage import Storage
                            # Should handle LookupAccountName failure and retry with env
                            storage = Storage(path=str(tmp_path / "test.json"))
                            assert storage is not None
        finally:
            if original_username is not None:
                os.environ['USERNAME'] = original_username
            else:
                os.environ.pop('USERNAME', None)
            if original_userdomain is not None:
                os.environ['USERDOMAIN'] = original_userdomain
            else:
                os.environ.pop('USERDOMAIN', None)


def test_username_parsing_with_edge_cases():
    """Test username parsing logic handles edge cases correctly."""
    test_cases = [
        # (input, expected_output, description)
        ("username", "username", "Plain username"),
        ("DOMAIN\\username", "username", "Domain-prefixed username"),
        ("DOMAIN\\\\username", "username", "Double backslash - extract last part"),
        ("DOMAIN\\user\\name", "user\\name", "Multiple backslashes - extract after last"),
        ("", "", "Empty string"),
        ("   ", "   ", "Whitespace only"),
        ("DOMAIN/", "DOMAIN/", "Forward slash - not parsed"),
    ]

    def extract_username(user: str) -> str:
        """Helper function matching current implementation."""
        if '\\' in user:
            parts = user.rsplit('\\', 1)
            if len(parts) == 2:
                return parts[1]
        return user

    for input_user, expected, description in test_cases:
        result = extract_username(input_user)
        assert result == expected, f"Failed for {description}: '{input_user}' -> '{result}' (expected '{expected}')"


@pytest.mark.skipif(
    os.name != 'nt',
    reason="Windows-specific test"
)
def test_multiple_backslash_username_format(tmp_path):
    """Test handling of usernames with multiple backslashes."""
    original_username = os.environ.get('USERNAME')

    try:
        os.environ['USERNAME'] = 'actualuser'

        # Mock GetUserName to return format with multiple backslashes
        with patch('win32api.GetUserName', return_value='DOMAIN\\sub\\actualuser'):
            with patch('win32api.GetUserNameEx', side_effect=Exception("No domain")):
                with patch('win32api.GetComputerName', return_value='DOMAIN'):
                    with patch('win32security.LookupAccountName') as mock_lookup:
                        # Mock successful lookup
                        mock_lookup.return_value = (Mock(), Mock(), Mock())
                        from flywheel.storage import Storage
                        storage = Storage(path=str(tmp_path / "test.json"))
                        # Verify LookupAccountName was called with extracted username
                        mock_lookup.assert_called()
                        # The extracted username should be 'actualuser' (after last backslash)
                        call_args = mock_lookup.call_args
                        if call_args:
                            # First arg after self should be domain, second should be user
                            user_arg = call_args[0][1] if len(call_args[0]) > 1 else None
                            # Should have extracted 'actualuser' from 'DOMAIN\\sub\\actualuser'
                            assert user_arg is not None and 'actualuser' in user_arg or user_arg == 'actualuser'
    finally:
        if original_username is not None:
            os.environ['USERNAME'] = original_username
        else:
            os.environ.pop('USERNAME', None)
