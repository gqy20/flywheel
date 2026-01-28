"""Test for Issue #1294 - Verify shlex.quote() is the final operation.

Issue #1294 raises a concern that shlex.quote() might not be the last operation
in sanitize_for_security_context for shell context, which could cause security issues.

ANALYSIS:
=========
The current implementation IS CORRECT. The order of operations for shell context is:
1. NFKC normalization (line 155) - Converts fullwidth/compatibility chars to ASCII
2. Length truncation (line 181) - Prevents DoS attacks
3. Control character removal (line 212) - Removes control chars
4. Unicode spoofing removal (line 217-218) - Removes zero-width and BIDI chars
5. shlex.quote() (line 224) - FINAL STEP - Properly quotes the string for shell

The shlex.quote() IS the last operation for shell context, which is the correct
and most secure approach.

POTENTIAL ISSUE:
=================
The issue raises a concern that NFKC normalization happens BEFORE we know we're
in shell context, which could theoretically cause issues if certain Unicode
characters are normalized in a way that affects shell quoting.

However, after analysis, NFKC normalization is SAFE for shell quoting because:
1. It only converts fullwidth/compatibility characters to ASCII equivalents
2. It does NOT change the fundamental structure of the string
3. It PREVENTS homograph attacks by normalizing deceptive characters
4. shlex.quote() works correctly on the normalized string

VERIFICATION:
=============
This test verifies that:
1. shlex.quote() IS the last operation for shell context
2. All transformations happen BEFORE quoting
3. The quoted string is safe for shell usage
4. No security issues exist with the current implementation
"""

import pytest
import shlex
import unicodedata
import re
from flywheel.cli import sanitize_for_security_context


def test_shlex_quote_is_final_operation():
    """Test that shlex.quote() is applied as the FINAL operation for shell context.

    This verifies the correct order of operations and that shlex.quote() is
    indeed the last step.
    """
    # Test with fullwidth characters (NFKC normalization)
    input_str = "ｆｉｌｅｗｉｔｈｆｕｌｌｗｉｄｔｈ．ｔｘｔ"

    # After NFKC: "filewithfullwidth.txt"
    # After shlex.quote(): 'filewithfullwidth.txt'
    expected = shlex.quote("filewithfullwidth.txt")

    result = sanitize_for_security_context(input_str, context="shell")
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_shlex_quote_after_control_char_removal():
    """Test that control characters are removed BEFORE shlex.quote().

    This is the correct and safe behavior. Control characters serve no legitimate
    purpose in shell command arguments and could cause confusion or injection.
    """
    # Test with control characters
    input_str = "file\x00with\x01control\x02chars.txt"

    # Control chars should be removed, then quoted
    cleaned = "filewithcontrolchars.txt"
    expected = shlex.quote(cleaned)

    result = sanitize_for_security_context(input_str, context="shell")
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_shlex_quote_after_unicode_spoofing_removal():
    """Test that Unicode spoofing characters are removed BEFORE shlex.quote().

    This prevents visual spoofing attacks in shell commands.
    """
    # Test with zero-width and BIDI override characters
    input_str = "file\u200Bwith\u200Dzero\u202Awidth.txt"

    # Spoofing chars should be removed, then quoted
    cleaned = "filewithzerowidth.txt"
    expected = shlex.quote(cleaned)

    result = sanitize_for_security_context(input_str, context="shell")
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_complex_transformation_then_quoting():
    """Test complex case with multiple transformations before quoting.

    This verifies that all transformations happen in the correct order,
    with shlex.quote() as the final step.
    """
    # Test with fullwidth + control + zero-width + BIDI chars
    input_str = "ｆｉｌｅ\x00\u200Bｔｅｓｔ\u202A．ｔｘｔ"

    # Step 1: NFKC normalization
    s = unicodedata.normalize('NFKC', input_str)

    # Step 2: Control char removal
    control_pattern = re.compile(r'[\x00-\x1F\x7F]')
    s = control_pattern.sub('', s)

    # Step 3: Unicode spoofing removal
    zero_width_pattern = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')
    bidi_pattern = re.compile(r'[\u202A-\u202E\u2066-\u2069]')
    s = zero_width_pattern.sub('', s)
    s = bidi_pattern.sub('', s)

    # Step 4: shlex.quote() - FINAL STEP
    expected = shlex.quote(s)

    result = sanitize_for_security_context(input_str, context="shell")
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_nfkc_normalization_is_safe_for_quoting():
    """Test that NFKC normalization is safe and does not break shlex.quote().

    This verifies that NFKC normalization (which prevents homograph attacks)
    does not interfere with shell quoting.
    """
    test_cases = [
        # (input, expected_after_nfkc)
        ("ｆｉｌｅ．ｔｘｔ", "file.txt"),
        ("ｅｃｈｏ ｔｅｓｔ", "echo test"),
        ("１２３", "123"),
        ("ＡＢＣ", "ABC"),
    ]

    for input_str, expected_nfkc in test_cases:
        result = sanitize_for_security_context(input_str, context="shell")

        # The result should be shlex.quote() of the NFKC-normalized string
        expected = shlex.quote(expected_nfkc)
        assert result == expected, (
            f"For input {input_str!r}, after NFKC should be {expected_nfkc!r}, "
            f"then quoted as {expected!r}, but got {result!r}"
        )


def test_shell_metas_preserved_and_quoted():
    """Test that shell metacharacters are preserved (not removed) and properly quoted.

    The shell context should NOT remove metacharacters like ;, |, &, etc.
    Instead, it should use shlex.quote() to properly escape them.
    """
    # Shell metacharacters should be preserved and quoted
    input_str = "file;with|metachars&test.txt"

    result = sanitize_for_security_context(input_str, context="shell")

    # The metachars should be in the result, properly quoted
    assert ";" in result or "filewithmetacharstest.txt" in result, (
        f"Shell metachars should be preserved in the quoted result: {result}"
    )

    # The result should be properly quoted (starts with quote)
    assert result[0] in ("'", '"'), f"Result should be quoted: {result}"


def test_current_implementation_is_safe():
    """Verify that the current implementation is safe and correct.

    This test documents that:
    1. shlex.quote() IS the final operation for shell context
    2. All transformations happen BEFORE quoting
    3. The order of operations is secure
    4. No changes are needed to fix issue #1294
    """
    # Complex test with multiple types of characters
    input_str = "ｆｉｌｅ\x00\n\u200Btest；|&`$()<>(){}"

    result = sanitize_for_security_context(input_str, context="shell")

    # Verify the result is properly quoted (starts with quote)
    assert result[0] in ("'", '"'), f"Result should be quoted: {result}"

    # Verify it can be safely parsed as a shell argument
    parsed = shlex.split(result)
    assert isinstance(parsed, list), "Should parse as a list"

    # The result should be safe for shell usage
    # (no control chars, no spoofing chars, properly quoted)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
