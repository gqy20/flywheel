"""Tests for ReDoS vulnerability in sanitize_string (Issue #729).

This test ensures that the regex character class in sanitize_string is properly
constructed to prevent ReDoS attacks when characters like hyphen or closing bracket
are in the character list.

The vulnerability occurs because:
1. A hyphen (-) in the middle of a character class creates a range (e.g., [a-z])
2. A closing bracket (]) in the middle prematurely closes the character class
3. This can lead to catastrophic backtracking or unexpected behavior

The fix ensures that special regex characters in character classes are properly
escaped or positioned to prevent misinterpretation.
"""

import pytest
import re
from flywheel.cli import sanitize_string


class TestReDoSVulnerability:
    """Test that sanitize_string is safe from ReDoS attacks."""

    def test_sanitize_removes_dangerous_chars(self):
        """Test that dangerous characters are properly removed."""
        # Test basic dangerous characters
        assert sanitize_string("test;semi") == "testsemi"
        assert sanitize_string("test|pipe") == "testpipe"
        assert sanitize_string("test&amp") == "testamp"
        assert sanitize_string("test`backtick") == "testbacktick"
        assert sanitize_string("test$dollar") == "testdollar"
        assert sanitize_string("test(paren)") == "testparen"
        assert sanitize_string("test<angle>") == "testangle"
        assert sanitize_string("test{brace}") == "testbrace"

    def test_sanitize_preserves_safe_chars(self):
        """Test that safe characters are preserved."""
        # Hyphens should be preserved (Issue #725)
        assert sanitize_string("test-hyphen") == "test-hyphen"
        assert sanitize_string("550e8400-e29b-41d4-a716") == "550e8400-e29b-41d4-a716"
        assert sanitize_string("2024-01-15") == "2024-01-15"

        # Brackets should be preserved
        assert sanitize_string("test[bracket]") == "test[bracket]"
        assert sanitize_string("array[0]") == "array[0]"

        # Quotes should be preserved
        assert sanitize_string('test"quote"') == 'test"quote"'
        assert sanitize_string("test'apostrophe'") == "test'apostrophe'"

        # Backslash should be preserved (Issue #705)
        assert sanitize_string("C:\\Users\\test") == "C:\\Users\\test"

        # Percentage should be preserved
        assert sanitize_string("50% complete") == "50% complete"

    def test_no_redos_with_long_input(self):
        """Test that long inputs don't cause ReDoS (catastrophic backtracking).

        This test ensures the regex is efficient and doesn't exhibit
        exponential time complexity with certain input patterns.
        """
        import time

        # Create a long string that could trigger ReDoS if the regex is vulnerable
        # A vulnerable regex like [a-] would behave unexpectedly
        long_input = "a" * 10000 + "test" + ";" * 100

        # This should complete quickly (less than 1 second)
        # If vulnerable to ReDoS, this could take much longer
        start = time.time()
        result = sanitize_string(long_input)
        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0, f"sanitize_string took {elapsed:.2f}s, possible ReDoS"
        assert ";" not in result
        assert "test" in result

    def test_regex_char_class_safety(self):
        """Test that the character class regex pattern is safe.

        This verifies that special regex characters in the character class
        don't create ranges or close the class prematurely.
        """
        # Test that brackets in input are preserved (not part of the regex)
        assert sanitize_string("test[bracket]") == "test[bracket]"

        # Test that hyphens are preserved and not interpreted as ranges
        assert sanitize_string("a-z") == "a-z"
        assert sanitize_string("test-range") == "test-range"

        # Test mixed characters
        assert sanitize_string("test[a-z]{danger}") == "test[a-z]danger"

    def test_character_class_pattern_is_safe(self):
        """Test that the actual regex pattern used is safe from ReDoS.

        This test verifies that the character class pattern in sanitize_string
        doesn't have hyphens in the middle (which create ranges) or unescaped
        closing brackets (which close the class early).
        """
        # Read the source code to extract the dangerous_chars pattern
        import inspect
        source = inspect.getsource(sanitize_string)

        # Find the dangerous_chars assignment
        for line in source.split('\n'):
            if 'dangerous_chars' in line and '=' in line:
                # Extract the character class pattern
                # It should be something like: dangerous_chars = r';|&`$()<>{}'
                chars = line.split("r'")[1].split("'")[0]

                # Verify that the character class construction is safe
                # When used in f'[{dangerous_chars}]', we need to ensure:
                # 1. If - is present, it's at the end
                # 2. If ] is present, it's escaped

                # The current implementation should not have - or ] in dangerous_chars
                # since those are preserved for legitimate use
                assert '-' not in chars, "Hyphen should not be in dangerous_chars (preserved for UUIDs, dates, etc.)"
                assert ']' not in chars, "Closing bracket should not be in dangerous_chars (preserved for arrays, etc.)"

                # Verify the pattern is properly escaped for use in a character class
                # When building [chars], we need to ensure special chars don't break it
                pattern = f'[{chars}]'

                # This should compile without errors
                # If it has unescaped ] or misplaced -, it will either fail
                # or create an incorrect pattern
                try:
                    compiled = re.compile(pattern)
                    # Test with a simple string to ensure it works correctly
                    test_result = compiled.sub('', 'test;danger')
                    assert 'danger' in test_result
                    assert ';' not in test_result
                except re.error as e:
                    pytest.fail(f"Character class pattern is invalid: {e}")

                return  # Found and tested the pattern

        pytest.fail("Could not find dangerous_chars definition in sanitize_string")
