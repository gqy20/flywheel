"""Tests for Issue #675 - Potential log injection vulnerability.

This test ensures that all user-generated content (like todo.title) is properly
sanitized to remove control characters (especially newlines) when being output,
to prevent log forging or terminal character injection.
"""

import pytest
from io import StringIO
import sys
from unittest.mock import patch

from flywheel.cli import CLI, sanitize_string
from flywheel.storage import Storage
from flywheel.todo import Todo, Status


class TestLogInjectionVulnerability:
    """Test suite for Issue #675 - Log injection vulnerability."""

    def test_sanitize_string_removes_newlines(self):
        """Test that sanitize_string removes newline characters."""
        # Test with various newline injections
        test_cases = [
            ("Normal task\nInjected log line", "Normal taskInjected log line"),
            ("Task\r\nCarriage return", "TaskCarriage return"),
            ("Task\rWith carriage", "TaskWith carriage"),
            ("Multi\nLine\n\rInjection", "MultiLineInjection"),
            ("Task\tWith\tTabs", "TaskWithTabs"),
            ("Task\x00Null\x01Byte", "TaskNullByte"),
        ]

        for input_str, expected_part in test_cases:
            result = sanitize_string(input_str)
            # Verify no control characters remain
            assert '\n' not in result, f"Newline found in: {repr(result)}"
            assert '\r' not in result, f"Carriage return found in: {repr(result)}"
            assert '\t' not in result, f"Tab found in: {repr(result)}"
            assert '\x00' not in result, f"Null byte found in: {repr(result)}"
            # Verify the expected content is preserved
            assert expected_part in result or result.replace(" ", "") == expected_part.replace(" ", "")

    def test_complete_command_output_sanitized(self):
        """Test that complete command output is sanitized."""
        # Create a CLI instance with mock storage
        cli = CLI()
        storage = Storage()

        # Create a todo with potentially malicious title
        malicious_title = "Buy milk\n[ERROR] System compromised!\r\n[INFO] Fake log entry"
        todo = Todo(
            id=1,
            title=sanitize_string(malicious_title),
            description="Test description",
            status=Status.TODO
        )

        # Add the todo
        added_todo = storage.add(todo)

        # Mock args for complete command
        class Args:
            id = 1

        args = Args()

        # Capture output
        output = StringIO()
        with patch('sys.stdout', output):
            cli.complete(args)

        result = output.getvalue()

        # Verify no control characters in output
        assert '\n' not in result, f"Newline found in output: {repr(result)}"
        assert '\r' not in result, f"Carriage return found in output: {repr(result)}"
        # Verify the sanitized title is in output
        assert "Buy milk" in result
        assert "[ERROR]" not in result or result.count("[ERROR]") == 0

    def test_add_command_output_sanitized(self):
        """Test that add command output is sanitized."""
        cli = CLI()

        # Mock args with malicious title
        class Args:
            title = "Initial task\nInjected log line"
            description = None
            priority = None
            due_date = None
            tags = None

        args = Args()

        # Capture output
        output = StringIO()
        with patch('sys.stdout', output):
            cli.add(args)

        result = output.getvalue()

        # Verify no control characters in output
        assert '\n' not in result.rstrip('\n'), f"Newline found in output: {repr(result)}"
        assert '\r' not in result, f"Carriage return found in output: {repr(result)}"
        # Should only have one newline (the one print adds)
        assert result.count('\n') == 1, f"Expected 1 newline, found {result.count('\n')}"

    def test_sanitize_preserves_legitimate_content(self):
        """Test that sanitization preserves legitimate content."""
        test_cases = [
            "Normal task with quotes 'single' and \"double\"",
            "Task with 100% effort",
            "Task with [brackets] and {braces}",  # braces should be removed
            "UUID: 550e8400-e29b-41d4-a716-446655440000",
            "Date: 2024-01-15",
            "Phone: 1-800-555-0123",
            "Windows path: C:\\Users\\test",  # internal backslash preserved
            "Code: def foo(): return bar",
        ]

        for test_str in test_cases:
            result = sanitize_string(test_str)
            # Verify no control characters
            assert '\n' not in result
            assert '\r' not in result
            assert '\t' not in result
            # Verify content is preserved (except braces which are removed)
            assert len(result) > 0, f"Result is empty for: {test_str}"
