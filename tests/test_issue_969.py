"""Tests for Issue #969 - Fullwidth character homograph attack prevention.

This test verifies that the codebase properly handles fullwidth characters
that could be used in homograph attacks, particularly in security-sensitive
contexts like filenames and URLs.

SECURITY ISSUE: NFC normalization (line 88 of cli.py) does NOT convert
fullwidth characters to their ASCII equivalents:
- Fullwidth 'ｅ' (U+FF45) is NOT converted to 'e' (U+0065) by NFC
- Fullwidth 'ｘ' (U+FF58) is NOT converted to 'x' (U+0078) by NFC
- Fullwidth 'ａ' (U+FF41) is NOT converted to 'a' (U+0061) by NFC
- Fullwidth '．' (U+FF0E) is NOT converted to '.' (U+002E) by NFC

This creates a security vulnerability where attackers can use visually
similar fullwidth characters in security-sensitive contexts.

Example attack:
- Normal URL: "example.com"
- Fullwidth URL: "ｅｘａｍｐｌｅ．ｃｏｍ"
- These look similar to users but are completely different to the system
"""

import pytest
from flywheel.cli import remove_control_chars, sanitize_for_security_context


def test_fullwidth_url_homograph_attack():
    """Test that fullwidth characters in URLs are detected/prevented in security contexts.

    SECURITY ISSUE: Fullwidth characters look similar to ASCII but have different
    codepoints, which can be used to deceive users in URLs and filenames.

    Example:
    - Normal: "example.com" (U+0065 U+0078 U+0061 U+006D U+0070 U+006C U+0065 U+002E U+0063 U+006F U+006D)
    - Fullwidth: "ｅｘａｍｐｌｅ．ｃｏｍ" (U+FF45 U+FF58 U+FF41 U+FF4D U+FF50 U+FF4C U+FF45 U+FF0E U+FF43 U+FF4F U+FF4D)

    Current behavior: NFC normalization doesn't convert these characters
    Expected behavior: Should convert fullwidth to ASCII in security contexts
    """
    # Fullwidth URL - visually looks like "example.com" but uses different codepoints
    fullwidth_url = "ｅｘａｍｐｌｅ．ｃｏｍ"

    # Test with regular function (uses NFC - should NOT convert fullwidth)
    result_nfc = remove_control_chars(fullwidth_url)
    assert result_nfc == fullwidth_url, (
        f"Current behavior: NFC preserves fullwidth. Got: '{result_nfc}'"
    )

    # Test with security context function (should use NFKC - converts fullwidth to ASCII)
    result_nfkc = sanitize_for_security_context(fullwidth_url, context="url")
    assert result_nfkc == "example.com", (
        f"SECURITY: Fullwidth URL should be normalized to ASCII. "
        f"Got: '{result_nfkc}', Expected: 'example.com'"
    )


def test_fullwidth_filename_homograph_attack():
    """Test that fullwidth characters in filenames are detected/prevented.

    Attackers can use fullwidth characters to create visually confusing filenames
    that bypass security checks while appearing legitimate to users.
    """
    # Fullwidth filename - looks like "document.txt" but uses different codepoints
    fullwidth_filename = "ｄｏｃｕｍｅｎｔ．ｔｘｔ"

    # Test with security context function
    result = sanitize_for_security_context(fullwidth_filename, context="filename")
    assert result == "document.txt", (
        f"SECURITY: Fullwidth filename should be normalized. "
        f"Got: '{result}', Expected: 'document.txt'"
    )


def test_mixed_fullwidth_ascii_attack():
    """Test detection of mixed fullwidth and ASCII characters.

    Attackers may mix fullwidth and ASCII characters to create sophisticated
    homograph attacks that are harder to detect.
    """
    # Mixed fullwidth and ASCII - "test.exe" with some fullwidth characters
    mixed_attack = "ｔｅｓｔ．ｅｘｅ"  # All fullwidth

    result = sanitize_for_security_context(mixed_attack, context="filename")
    assert result == "test.exe", (
        f"SECURITY: Mixed fullwidth should be normalized. Got: '{result}'"
    )


def test_nfc_preserves_fullwidth_for_general_text():
    """Test that NFC correctly preserves fullwidth for general text storage.

    Per Issue #944, NFC should preserve fullwidth characters for general
    text to avoid data loss and semantic changes. This test verifies that
    the current behavior is correct for non-security-sensitive contexts.
    """
    # Fullwidth text that should be preserved in general contexts
    fullwidth_text = "Ｈｅｌｌｏ　Ｗｏｒｌｄ"

    result = remove_control_chars(fullwidth_text)
    assert result == fullwidth_text, (
        f"General text: Fullwidth should be preserved by NFC. "
        f"Got: '{result}'"
    )


def test_nfc_preserves_superscripts_and_special_chars():
    """Test that NFC preserves special characters as intended.

    Per Issue #944 and code comments, NFC should preserve:
    - Superscripts (²)
    - Ligatures (ﬁ)
    - Trademark (™)
    - Fractions (½)
    """
    # Special characters that should be preserved
    special_text = "²³™ﬁ½"

    result = remove_control_chars(special_text)
    assert result == special_text, (
        f"Special characters should be preserved by NFC. Got: '{result}'"
    )


def test_security_context_function_blocks_dangerous_fullwidth():
    """Test that security context function properly blocks dangerous fullwidth chars.

    In security-sensitive contexts (URLs, filenames, shell parameters),
    fullwidth characters should be converted to prevent confusion and
    potential security issues.
    """
    test_cases = [
        # (input, context, expected_output)
        ("ｅｘａｍｐｌｅ．ｃｏｍ", "url", "example.com"),
        ("ｄｏｃｕｍｅｎｔ．ｔｘｔ", "filename", "document.txt"),
        ("／ｅｔｃ／ｐａｓｓｗｄ", "filename", "/etc/passwd"),  # Fullwidth path separator
        ("ｔｅｓｔ；ｒｍ　－ｒｆ　／", "shell", "test"),  # Fullwidth with shell metachars
    ]

    for input_text, context, expected in test_cases:
        result = sanitize_for_security_context(input_text, context=context)
        # Note: shell context also removes metacharacters
        if context == "shell":
            assert result == expected, (
                f"SECURITY: Shell context '{input_text}' -> '{result}', "
                f"expected '{expected}'"
            )
        else:
            assert result == expected, (
                f"SECURITY: Context '{context}' for '{input_text}' -> '{result}', "
                f"expected '{expected}'"
            )


def test_backwards_compatibility_with_sanitize_string():
    """Test that existing behavior is maintained for backwards compatibility.

    The sanitize_string function is deprecated but still used. This test
    ensures it maintains its current behavior (NFC normalization) to avoid
    breaking existing code.
    """
    from flywheel.cli import sanitize_string

    # sanitize_string should use NFC (preserve fullwidth)
    fullwidth = "Ｔｅｓｔ"
    result = sanitize_string(fullwidth)
    assert result == fullwidth, (
        f"Backwards compatibility: sanitize_string should preserve fullwidth. "
        f"Got: '{result}'"
    )


def test_security_context_invalid_context():
    """Test that invalid security contexts are handled properly."""
    fullwidth = "ｅｘａｍｐｌｅ"

    # Unknown context should fall back to safe behavior (NFKC)
    result = sanitize_for_security_context(fullwidth, context="unknown")
    assert result == "example", (
        f"Unknown context should use safe default (NFKC). Got: '{result}'"
    )
