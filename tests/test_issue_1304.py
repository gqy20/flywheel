"""Test for Issue #1304 - Fix FORMAT_STRING_PATTERN ReDoS vulnerability.

This test ensures that FORMAT_STRING_PATTERN:
1. Correctly matches format string characters {, }, %, and \
2. Does not have ReDoS vulnerabilities with malicious inputs
3. Uses a safe character class pattern

The issue: The pattern r'[{}\\%]' contains a backslash in a character class,
which could lead to unexpected behavior. The fix uses a clearer pattern.
"""

import re
import time
import pytest


def test_format_string_pattern_matches_curly_braces():
    """Test that FORMAT_STRING_PATTERN matches curly braces."""
    # Import the pattern from the module
    from flywheel.cli import FORMAT_STRING_PATTERN

    # Test opening curly brace
    assert FORMAT_STRING_PATTERN.search('{') is not None, "Should match '{'"

    # Test closing curly brace
    assert FORMAT_STRING_PATTERN.search('}') is not None, "Should match '}'"

    # Test string with curly braces
    assert FORMAT_STRING_PATTERN.search('Use {var} for values') is not None
    assert FORMAT_STRING_PATTERN.search('{key}: value') is not None


def test_format_string_pattern_matches_percent():
    """Test that FORMAT_STRING_PATTERN matches percent sign."""
    from flywheel.cli import FORMAT_STRING_PATTERN

    assert FORMAT_STRING_PATTERN.search('%') is not None, "Should match '%'"
    assert FORMAT_STRING_PATTERN.search('50% complete') is not None
    assert FORMAT_STRING_PATTERN.search('%s placeholder') is not None


def test_format_string_pattern_matches_backslash():
    """Test that FORMAT_STRING_PATTERN matches backslash."""
    from flywheel.cli import FORMAT_STRING_PATTERN

    assert FORMAT_STRING_PATTERN.search('\\') is not None, "Should match backslash"
    assert FORMAT_STRING_PATTERN.search('C:\\Users\\path') is not None
    assert FORMAT_STRING_PATTERN.search('escape\\nsequence') is not None


def test_format_string_pattern_no_match_for_safe_chars():
    """Test that FORMAT_STRING_PATTERN doesn't match safe characters."""
    from flywheel.cli import FORMAT_STRING_PATTERN

    # These should NOT match
    assert FORMAT_STRING_PATTERN.search('abc') is None
    assert FORMAT_STRING_PATTERN.search('123') is None
    assert FORMAT_STRING_PATTERN.search('normal text') is None
    assert FORMAT_STRING_PATTERN.search('hello-world') is None


def test_format_string_pattern_no_redos_with_long_strings():
    """Test that FORMAT_STRING_PATTERN is not vulnerable to ReDoS attacks.

    ReDoS (Regular Expression Denial of Service) occurs when a regex
    takes exponential time to match certain inputs. This test ensures
    that the pattern completes quickly even with malicious input.

    A safe pattern should complete in O(n) time where n is string length.
    An unsafe pattern could take O(2^n) time with carefully crafted input.
    """
    from flywheel.cli import FORMAT_STRING_PATTERN

    # Create potentially malicious input: alternating pattern that could
    # cause catastrophic backtracking in vulnerable regexes
    # For this pattern, we use a long string without format chars
    # to test the negative case (no match should be fast)
    malicious_input = 'a' * 10000

    # Time the search operation
    start_time = time.time()
    result = FORMAT_STRING_PATTERN.search(malicious_input)
    elapsed_time = time.time() - start_time

    # Should return None (no match) quickly
    assert result is None
    # Should complete in under 1 second (even 0.1s is generous)
    assert elapsed_time < 1.0, f"Pattern took {elapsed_time:.3f}s, potential ReDoS vulnerability"


def test_format_string_pattern_no_redos_with_repeated_chars():
    """Test ReDoS resistance with repeated format string characters."""
    from flywheel.cli import FORMAT_STRING_PATTERN

    # Test with many format string characters
    malicious_input = '%' * 10000

    start_time = time.time()
    result = FORMAT_STRING_PATTERN.search(malicious_input)
    elapsed_time = time.time() - start_time

    # Should find a match quickly
    assert result is not None
    assert elapsed_time < 1.0, f"Pattern took {elapsed_time:.3f}s, potential ReDoS vulnerability"


def test_format_string_pattern_character_class_is_safe():
    """Test that the pattern uses a safe character class.

    The issue mentions that [{}\\%] contains a backslash which could
    cause unexpected behavior. This test verifies the pattern is correct.
    """
    from flywheel.cli import FORMAT_STRING_PATTERN

    # Get the pattern string
    pattern_str = FORMAT_STRING_PATTERN.pattern

    # The pattern should match exactly these 4 characters: {, }, \, %
    # Verify by checking each character individually
    test_chars = ['{', '}', '%', '\\']

    for char in test_chars:
        match = FORMAT_STRING_PATTERN.search(char)
        assert match is not None, f"Pattern should match '{char}'"
        assert match.group() == char, f"Pattern should match exactly '{char}', got '{match.group()}'"

    # Verify pattern doesn't have unintended ranges
    # In regex character classes, [a-z] is a range, [abc] is individual chars
    # Our pattern should only match specific chars, not ranges
    assert FORMAT_STRING_PATTERN.search('z') is None, "Should not match 'z'"
    assert FORMAT_STRING_PATTERN.search('A') is None, "Should not match 'A'"
    assert FORMAT_STRING_PATTERN.search('0') is None, "Should not match '0'"


def test_format_string_pattern_findall_behavior():
    """Test that findall correctly identifies all format string chars."""
    from flywheel.cli import FORMAT_STRING_PATTERN

    # Test string with multiple format chars
    test_string = "Use {format} with %s and \\ escape"
    matches = FORMAT_STRING_PATTERN.findall(test_string)

    # Should find: {, }, %, %, \
    assert len(matches) == 5, f"Expected 5 matches, got {len(matches)}: {matches}"
    assert '{' in matches
    assert '}' in matches
    assert '%' in matches
    assert '\\' in matches
