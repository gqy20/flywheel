"""Tests for issue #614 - sanitization of due_date field.

This test suite ensures that the due_date field is properly sanitized
to prevent injection attacks when data is rendered or executed by storage backends.

Security Issue: The 'due_date' field is passed directly from user input without
sanitization in cli.py line 157. This could lead to injection attacks if the
due_date is used in storage backends vulnerable to injection.
"""

import pytest
from unittest.mock import Mock, patch
from argparse import Namespace

from flywheel.cli import CLI, sanitize_string


class TestDueDateSanitization:
    """Test suite for due_date field sanitization."""

    def test_due_date_with_html_tags_is_sanitized(self):
        """Test that HTML tags in due_date are removed."""
        # Create a mock storage
        with patch('flywheel.cli.Storage') as mock_storage_class:
            mock_storage = Mock()
            mock_storage.add.return_value = Mock(id=1, title="Test Todo")
            mock_storage_class.return_value = mock_storage

            cli = CLI()
            args = Namespace(
                title="Test Todo",
                description=None,
                priority=None,
                due_date="<script>alert('xss')</script>",
                tags=None
            )

            cli.add(args)

            # Verify that the due_date was sanitized before being stored
            added_todo = mock_storage.add.call_args[0][0]
            assert "<script>" not in added_todo.due_date
            assert ">" not in added_todo.due_date
            assert "<" not in added_todo.due_date

    def test_due_date_with_shell_metacharacters_is_sanitized(self):
        """Test that shell metacharacters in due_date are removed."""
        with patch('flywheel.cli.Storage') as mock_storage_class:
            mock_storage = Mock()
            mock_storage.add.return_value = Mock(id=1, title="Test Todo")
            mock_storage_class.return_value = mock_storage

            cli = CLI()
            args = Namespace(
                title="Test Todo",
                description=None,
                priority=None,
                due_date="2024-01-01; rm -rf /",
                tags=None
            )

            cli.add(args)

            added_todo = mock_storage.add.call_args[0][0]
            assert ";" not in added_todo.due_date

    def test_due_date_with_control_characters_is_sanitized(self):
        """Test that control characters in due_date are removed."""
        with patch('flywheel.cli.Storage') as mock_storage_class:
            mock_storage = Mock()
            mock_storage.add.return_value = Mock(id=1, title="Test Todo")
            mock_storage_class.return_value = mock_storage

            cli = CLI()
            args = Namespace(
                title="Test Todo",
                description=None,
                priority=None,
                due_date="2024-01-01\n2024-01-02",
                tags=None
            )

            cli.add(args)

            added_todo = mock_storage.add.call_args[0][0]
            assert "\n" not in added_todo.due_date

    def test_due_date_with_quotes_is_sanitized(self):
        """Test that quotes in due_date are removed."""
        with patch('flywheel.cli.Storage') as mock_storage_class:
            mock_storage = Mock()
            mock_storage.add.return_value = Mock(id=1, title="Test Todo")
            mock_storage_class.return_value = mock_storage

            cli = CLI()
            args = Namespace(
                title="Test Todo",
                description=None,
                priority=None,
                due_date='2024-01-01" OR "1"="1',
                tags=None
            )

            cli.add(args)

            added_todo = mock_storage.add.call_args[0][0]
            assert '"' not in added_todo.due_date

    def test_valid_due_date_preserved(self):
        """Test that valid due dates are preserved (mostly)."""
        with patch('flywheel.cli.Storage') as mock_storage_class:
            mock_storage = Mock()
            mock_storage.add.return_value = Mock(id=1, title="Test Todo")
            mock_storage_class.return_value = mock_storage

            cli = CLI()
            args = Namespace(
                title="Test Todo",
                description=None,
                priority=None,
                due_date="2024-01-01",
                tags=None
            )

            cli.add(args)

            added_todo = mock_storage.add.call_args[0][0]
            # The date should still contain the alphanumeric characters and hyphens
            assert "2024" in added_todo.due_date
            assert "01" in added_todo.due_date
            assert "-" in added_todo.due_date

    def test_due_date_matches_sanitize_string_behavior(self):
        """Test that due_date is sanitized using the same function as title/description."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "2024-01-01; rm -rf /",
            "2024-01-01\n2024-01-02",
            '2024-01-01" OR "1"="1',
            "2024-01-01`whoami`",
            "2024-01-01 && evil",
        ]

        for malicious_input in malicious_inputs:
            # Verify that sanitize_string removes dangerous characters
            sanitized = sanitize_string(malicious_input)

            # Test that due_date gets the same treatment
            with patch('flywheel.cli.Storage') as mock_storage_class:
                mock_storage = Mock()
                mock_storage.add.return_value = Mock(id=1, title="Test Todo")
                mock_storage_class.return_value = mock_storage

                cli = CLI()
                args = Namespace(
                    title="Test Todo",
                    description=None,
                    priority=None,
                    due_date=malicious_input,
                    tags=None
                )

                cli.add(args)

                added_todo = mock_storage.add.call_args[0][0]
                # The due_date should be sanitized the same way as sanitize_string does
                assert added_todo.due_date == sanitized, \
                    f"Expected due_date '{added_todo.due_date}' to match sanitize_string output '{sanitized}'"
