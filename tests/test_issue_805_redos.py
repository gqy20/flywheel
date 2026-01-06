"""Test for Issue #805 - ReDoS vulnerability in sanitize_string.

This test verifies that the sanitize_string function handles long strings
with complex Unicode characters efficiently, without causing performance
degradation due to ReDoS (Regular Expression Denial of Service).

ISSUE STATUS: ALREADY FIXED
===========================
This issue was addressed by the fix for Issue #830, which enforced max_length
BEFORE all regex processing to prevent ReDoS attacks.

The fix is implemented at lines 144-151 of src/flywheel/cli.py:
    # SECURITY FIX (Issue #830): This length check must happen BEFORE all
    # regex patterns below to prevent potential ReDoS attacks.
    if len(s) > max_length:
        s = s[:max_length]

This ensures that even with complex Unicode characters and multiple regex
patterns, the function completes in linear time rather than exhibiting
catastrophic backtracking behavior.

The original issue #805 mentioned concern about unicodedata.name() being
slow on long strings, but the current implementation uses unicodedata.normalize()
which is efficient and does not have ReDoS issues.
"""

import time
import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_performance_with_long_unicode_string():
    """Test that sanitize_string handles long Unicode strings efficiently.

    This test creates a very long string (exceeding max_length) with complex
    Unicode characters and verifies that:
    1. The function completes within a reasonable time (< 1 second)
    2. The output is properly truncated to max_length
    3. The function does not exhibit ReDoS-like behavior (exponential time)

    The test uses:
    - A string 10x longer than max_length (1,000,000 characters)
    - Complex Unicode characters that could trigger slow normalization
    - Timing assertions to ensure linear-time performance

    Addresses Issue #805 - ReDoS vulnerability through Unicode processing.
    FIX: Already implemented via Issue #830
    """
    # Create a very long string with complex Unicode characters
    # Using fullwidth characters which require Unicode normalization
    complex_unicode_chunk = "ＡＢＣＤＥＦＧＨＩＪ" * 100  # 1000 complex chars
    very_long_string = complex_unicode_chunk * 1000  # 1,000,000 chars

    # Verify the string is actually very long
    assert len(very_long_string) > 100000  # 10x max_length

    # Measure execution time
    start_time = time.time()

    # This should complete quickly despite the huge input
    # FIXED: max_length is enforced BEFORE regex processing (Issue #830)
    result = sanitize_string(very_long_string, max_length=100000)

    elapsed_time = time.time() - start_time

    # Assertions:
    # 1. Should complete in less than 1 second (linear time, not exponential)
    # 2. Result should be truncated to max_length or less
    # 3. Function should not hang or timeout

    # Allow 1 second for processing - this is generous for linear-time code
    # but would fail for ReDoS-vulnerable code (which could take minutes)
    assert elapsed_time < 1.0, (
        f"sanitize_string took {elapsed_time:.2f}s, expected < 1.0s. "
        "This suggests ReDoS vulnerability with long Unicode strings."
    )

    # Verify the result is properly truncated
    assert len(result) <= 100000, (
        f"Result length {len(result)} exceeds max_length of 100000"
    )

    # Verify that fullwidth characters were removed (they're in U+FF01-FF60 range)
    # The result should not contain any fullwidth characters
    fullwidth_found = any('\uFF01' <= c <= '\uFF60' for c in result)
    assert not fullwidth_found, "Fullwidth characters should be removed"


def test_sanitize_string_max_length_enforcement_before_regex():
    """Test that max_length is enforced BEFORE regex processing.

    This is a critical security check to prevent ReDoS attacks. The function
    should truncate the input to max_length BEFORE applying any regex patterns,
    especially the fullwidth character pattern which could be expensive.

    Addresses Issue #805 - Ensure max_length truncation happens early.
    FIX: Already implemented via Issue #830 at lines 150-151 of cli.py
    """
    # Create a string with many fullwidth characters
    # These trigger the expensive regex at line 216: r'[\uFF01-\uFF60]'
    test_string = "Ａ" * 200000  # 200k fullwidth characters

    # This should:
    # 1. Truncate to 100000 characters BEFORE regex processing
    # 2. Complete quickly (< 0.1 seconds)
    # 3. Return empty string (all chars are fullwidth and should be removed)

    start_time = time.time()
    result = sanitize_string(test_string, max_length=100000)
    elapsed_time = time.time() - start_time

    # Quick completion indicates truncation happened before regex
    assert elapsed_time < 0.1, (
        f"sanitize_string took {elapsed_time:.3f}s, expected < 0.1s. "
        "max_length should be enforced BEFORE regex processing."
    )

    # All fullwidth characters should be removed
    assert result == "", "All fullwidth characters should be removed"


def test_sanitize_string_empty_and_short_strings():
    """Test edge cases: empty strings and strings shorter than max_length.

    These should always complete instantly regardless of content.
    """
    # Empty string
    result = sanitize_string("")
    assert result == ""

    # Short string with complex Unicode
    result = sanitize_string("Hello Ｗｏｒｌｄ")
    assert result == "Hello "

    # String exactly at max_length (should be fast)
    test_string = "a" * 100000
    start_time = time.time()
    result = sanitize_string(test_string, max_length=100000)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 0.1, "String at max_length should process quickly"
    assert len(result) == 100000


def test_unicode_normalize_efficiency():
    """Test that unicodedata.normalize (not unicodedata.name) is efficient.

    The original issue #805 mentioned concern about unicodedata.name() being
    slow, but the current implementation uses unicodedata.normalize() which
    is much more efficient and does not have ReDoS issues.
    """
    # The current code uses unicodedata.normalize('NFC', s) at line 131
    # This is efficient even for long strings
    long_string = "a" * 100000
    start_time = time.time()
    result = sanitize_string(long_string)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 0.1, "Unicode normalization should be efficient"
    assert result == "a" * 100000
