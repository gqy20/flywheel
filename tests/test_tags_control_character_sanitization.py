"""Tests for tags field control character sanitization (Issue #1591)."""

import pytest
from flywheel.todo import Todo, _sanitize_text


class TestTagsControlCharacterSanitization:
    """Test that tags field sanitizes control characters like title and description."""

    def test_tags_with_control_characters_are_sanitized(self):
        """Test that control characters in tags are sanitized."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["tag\x00with\x00null", "normal\x1btag", "another\x0tag"]
        }
        todo = Todo.from_dict(data)

        # Each tag should have control characters removed
        assert "\x00" not in todo.tags[0]
        assert todo.tags[0] == "tag with null"
        assert "\x1b" not in todo.tags[1]
        assert todo.tags[1] == "normaltag"
        assert "\x0c" not in todo.tags[2]

    def test_tags_with_zero_width_spaces_are_sanitized(self):
        """Test that zero-width spaces in tags are sanitized."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["tag\u200Bwith\u200Bzws", "normal"]
        }
        todo = Todo.from_dict(data)

        # Zero-width spaces should be removed
        assert "\u200B" not in todo.tags[0]
        assert todo.tags[0] == "tagwithzws"
        assert todo.tags[1] == "normal"

    def test_tags_with_newlines_and_tabs_are_normalized(self):
        """Test that newlines and tabs in tags are normalized to spaces."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["tag\nwith\nnewlines", "tag\twith\ttabs", "normal"]
        }
        todo = Todo.from_dict(data)

        # Newlines and tabs should be normalized to single spaces
        assert "\n" not in todo.tags[0]
        assert "\r" not in todo.tags[0]
        assert todo.tags[0] == "tag with newlines"
        assert "\t" not in todo.tags[1]
        assert todo.tags[1] == "tag with tabs"
        assert todo.tags[2] == "normal"

    def test_tags_with_multiple_control_characters(self):
        """Test tags with multiple types of control characters."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["tag\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"]
        }
        todo = Todo.from_dict(data)

        # All control characters should be removed
        for control_char in ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x0b', '\x0c', '\x0e', '\x0f']:
            assert control_char not in todo.tags[0], f"Control character {repr(control_char)} should be removed"

    def test_tags_with_del_character_are_sanitized(self):
        """Test that DEL character (0x7f) in tags is sanitized."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["tag\x7fwith\x7fdel"]
        }
        todo = Todo.from_dict(data)

        # DEL character should be removed
        assert "\x7f" not in todo.tags[0]
        assert todo.tags[0] == "tagwithdel"

    def test_tags_consistency_with_title_and_description(self):
        """Test that tags use the same sanitization as title and description."""
        malicious = "bad\x00\x1b\u200Bstuff"

        # Manually sanitize using _sanitize_text
        expected = _sanitize_text(malicious)

        data = {
            "id": 1,
            "title": malicious,
            "description": malicious,
            "tags": [malicious]
        }
        todo = Todo.from_dict(data)

        # All fields should have the same sanitization applied
        assert todo.title == expected
        assert todo.description == expected
        assert todo.tags[0] == expected

    def test_tags_sanitization_prevents_log_injection(self):
        """Test that tags sanitization prevents potential log injection attacks."""
        # Log injection often uses newlines to add fake log entries
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["legit", "2025-01-13\x0aERROR: Fake error message", "another"]
        }
        todo = Todo.from_dict(data)

        # Newline should be normalized to space, preventing log injection
        assert "\n" not in todo.tags[1]
        assert "\r" not in todo.tags[1]
        # The tag should be sanitized to a single line
        assert todo.tags[1] == "2025-01-13 ERROR: Fake error message"

    def test_empty_tags_after_sanitization(self):
        """Test that tags that become empty after sanitization are handled."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "tags": ["\x00\x01\x02", "normal", "   "]
        }
        todo = Todo.from_dict(data)

        # Tags that become empty after sanitization should be handled
        # Based on current implementation, they might be kept as empty strings
        # or filtered out - this test verifies current behavior
        assert todo.tags[0] == "" or todo.tags[0] not in todo.tags
        assert todo.tags[1] == "normal"
        assert todo.tags[2] == ""
