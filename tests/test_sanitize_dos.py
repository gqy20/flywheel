"""Test for DoS vulnerability in sanitize_string (Issue #619)."""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_basic_removal():
    """Test that dangerous characters are removed."""
    # Test basic dangerous character removal
    assert sanitize_string('test<script>') == 'testscript'
    assert sanitize_string('test"quote') == 'testquote'
    assert sanitize_string("test'quote") == 'testquote'
    assert sanitize_string('test`backtick') == 'testbacktick'
    assert sanitize_string('test$dollar') == 'testdollar'
    assert sanitize_string('test&ampersand') == 'testampersand'
    assert sanitize_string('test|pipe') == 'testpipe'
    assert sanitize_string('test;semicolon') == 'testsemicolon'
    assert sanitize_string('test(parens)') == 'testparens'
    assert sanitize_string('test[brackets]') == 'testbrackets'
    assert sanitize_string('test{braces}') == 'testbraces'
    assert sanitize_string('test\\backslash') == 'testbackslash'


def test_sanitize_string_no_dos_on_long_input():
    """Test that sanitize_string doesn't cause DoS on long strings with many backslashes.

    This test verifies that the function handles long strings efficiently
    and completes within a reasonable time, preventing potential ReDoS attacks.

    Issue #619: The regex pattern contains backslashes that might cause
    catastrophic backtracking on very long strings.
    """
    import time

    # Create a long string with many backslashes and dangerous characters
    # This could potentially cause catastrophic backtracking in vulnerable regex
    long_dangerous = ('\\' * 10000) + ('<' * 100) + ('>' * 100)

    start = time.time()
    result = sanitize_string(long_dangerous)
    elapsed = time.time() - start

    # The function should complete quickly (within 1 second)
    # A vulnerable regex could take much longer
    assert elapsed < 1.0, f"sanitize_string took {elapsed:.2f}s, potential DoS vulnerability"

    # Result should have all dangerous characters removed
    assert '<' not in result
    assert '>' not in result
    # Backslashes should be removed
    assert '\\' not in result


def test_sanitize_string_handles_edge_cases():
    """Test edge cases for sanitize_string."""
    assert sanitize_string('') == ''
    assert sanitize_string(None) == ''
    assert sanitize_string('safe text 123') == 'safe text 123'
    assert sanitize_string('test\u200Bzero\u200Dwidth') == 'testzerowidth'
