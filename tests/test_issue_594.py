"""Test for Issue #594 - Potential injection via tags if not properly sanitized.

This test ensures that tags are properly sanitized to prevent injection attacks,
especially if tags are used in system commands or queries.
"""

import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.cli import CLI


class TestTagSanitization(unittest.TestCase):
    """Test tag input sanitization (Issue #594)."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_tags_with_shell_metacharacters_are_sanitized(self):
        """Test that tags with shell metacharacters are sanitized (Issue #594).

        Tags containing shell metacharacters like ;, &, |, $, `, $( ), etc.
        should be sanitized to prevent command injection attacks.
        """
        # Create CLI with temporary directory
        cli = CLI()
        cli.storage._path = os.path.join(self.temp_dir, "todos.json")

        # Test case 1: Tags with semicolon (command separator)
        args = argparse.Namespace(
            title="Test todo",
            description="",
            priority=None,
            due_date=None,
            tags="work;rm -rf /",  # Malicious: command separator
        )

        # This should either sanitize the tags or raise an error
        todo = cli.storage.add(
            type('Todo', (), {
                'id': None,
                'title': args.title,
                'description': args.description,
                'priority': args.priority or 'medium',
                'due_date': args.due_date,
                'tags': args.tags.split(",") if args.tags else [],
            })()
        )

        # Tags should not contain raw shell metacharacters
        for tag in todo.tags:
            self.assertNotIn(';', tag, "Tag should not contain semicolon")
            self.assertNotIn('&', tag, "Tag should not contain ampersand")
            self.assertNotIn('|', tag, "Tag should not contain pipe")
            self.assertNotIn('$', tag, "Tag should not contain dollar sign")
            self.assertNotIn('`', tag, "Tag should not contain backtick")

    def test_tags_with_command_substitution_are_sanitized(self):
        """Test that tags with command substitution are sanitized (Issue #594).

        Tags containing $(command) or `command` patterns should be sanitized
        to prevent command injection attacks.
        """
        cli = CLI()
        cli.storage._path = os.path.join(self.temp_dir, "todos.json")

        args = argparse.Namespace(
            title="Test todo",
            description="",
            priority=None,
            due_date=None,
            tags="$(cat /etc/passwd)",  # Malicious: command substitution
        )

        todo = cli.storage.add(
            type('Todo', (), {
                'id': None,
                'title': args.title,
                'description': args.description,
                'priority': args.priority or 'medium',
                'due_date': args.due_date,
                'tags': args.tags.split(",") if args.tags else [],
            })()
        )

        # Tags should not contain command substitution patterns
        for tag in todo.tags:
            self.assertNotIn('$(', tag, "Tag should not contain $()")
            self.assertNotIn('`', tag, "Tag should not contain backtick")

    def test_tags_with_newline_injection_are_sanitized(self):
        """Test that tags with newline injection are sanitized (Issue #594).

        Tags containing newline characters could be used to inject commands
        in multi-line contexts.
        """
        cli = CLI()
        cli.storage._path = os.path.join(self.temp_dir, "todos.json")

        args = argparse.Namespace(
            title="Test todo",
            description="",
            priority=None,
            due_date=None,
            tags="work\nmalicious_command",  # Malicious: newline injection
        )

        todo = cli.storage.add(
            type('Todo', (), {
                'id': None,
                'title': args.title,
                'description': args.description,
                'priority': args.priority or 'medium',
                'due_date': args.due_date,
                'tags': args.tags.split(",") if args.tags else [],
            })()
        )

        # Tags should not contain newlines or carriage returns
        for tag in todo.tags:
            self.assertNotIn('\n', tag, "Tag should not contain newline")
            self.assertNotIn('\r', tag, "Tag should not contain carriage return")

    def test_tags_with_null_bytes_are_sanitized(self):
        """Test that tags with null bytes are sanitized (Issue #594).

        Null bytes can be used to bypass string validation in some systems.
        """
        cli = CLI()
        cli.storage._path = os.path.join(self.temp_dir, "todos.json")

        args = argparse.Namespace(
            title="Test todo",
            description="",
            priority=None,
            due_date=None,
            tags="work\x00malicious",  # Malicious: null byte injection
        )

        todo = cli.storage.add(
            type('Todo', (), {
                'id': None,
                'title': args.title,
                'description': args.description,
                'priority': args.priority or 'medium',
                'due_date': args.due_date,
                'tags': args.tags.split(",") if args.tags else [],
            })()
        )

        # Tags should not contain null bytes
        for tag in todo.tags:
            self.assertNotIn('\x00', tag, "Tag should not contain null bytes")

    def test_tags_with_pipe_injection_are_sanitized(self):
        """Test that tags with pipe injection are sanitized (Issue #594).

        Pipes can be used to chain commands in shell contexts.
        """
        cli = CLI()
        cli.storage._path = os.path.join(self.temp_dir, "todos.json")

        args = argparse.Namespace(
            title="Test todo",
            description="",
            priority=None,
            due_date=None,
            tags="work|malicious",  # Malicious: pipe injection
        )

        todo = cli.storage.add(
            type('Todo', (), {
                'id': None,
                'title': args.title,
                'description': args.description,
                'priority': args.priority or 'medium',
                'due_date': args.due_date,
                'tags': args.tags.split(",") if args.tags else [],
            })()
        )

        # Tags should not contain pipe characters
        for tag in todo.tags:
            self.assertNotIn('|', tag, "Tag should not contain pipe character")


if __name__ == "__main__":
    unittest.main()
