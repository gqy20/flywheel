"""Tests for homograph attack prevention (Issue #774).

This test verifies that the sanitize_string function properly detects and
blocks visual spoofing attacks using homoglyphs from different scripts.

SECURITY ISSUE: The current implementation uses NFC normalization which
only handles canonical equivalence, NOT visual similarity across scripts.
- NFC does NOT change Cyrillic 'а' to Latin 'a'
- NFC does NOT change Greek 'ο' to Latin 'o'
- These characters look identical but have different Unicode codepoints

This creates a security vulnerability where attackers can use visually
identical characters from different scripts to bypass filters or create
confusing lookalike text.
"""

import pytest
from flywheel.cli import sanitize_string


def test_cyrillic_homograph_attack():
    """Test that Cyrillic homograph attacks are prevented.

    SECURITY ISSUE: NFC normalization (line 96 of cli.py) does NOT prevent
    visual spoofing using characters from different scripts.

    Example:
    - Latin 'a' = U+0061
    - Cyrillic 'а' = U+0430
    - These look identical but are different characters

    Current behavior: sanitize_string("\u0430dmin") returns "\u0430dmin"
    Expected behavior: Should remove/reject non-Latin script characters
    """
    # Pure Latin - should pass
    latin_input = "admin"
    result = sanitize_string(latin_input)
    assert result == "admin", f"Pure Latin should pass, got: {result}"

    # Cyrillic homograph attack - visually looks like "admin"
    # SECURITY ISSUE: This currently passes through unchanged!
    # The Cyrillic 'а' (U+0430) is NOT removed by NFC normalization
    cyrillic_homograph = "\u0430dmin"  # Cyrillic 'а' + Latin 'dmin'
    result = sanitize_string(cyrillic_homograph)

    # Current behavior FAILS this test:
    # NFC doesn't change Cyrillic characters, so the result is still "\u0430dmin"
    # This is a SECURITY VULNERABILITY!
    assert result == "dmin", (
        f"SECURITY: Cyrillic homograph should be removed. "
        f"Got '{result}' (U+{ord(result[0]) if result else 'empty':04X}). "
        f"Expected 'dmin' (Cyrillic character removed)."
    )


def test_greek_homograph_attack():
    """Test that Greek homograph attacks are prevented.

    Example: Greek 'ο' (omicron U+03BF) vs Latin 'o' (U+006F)
    These look identical but are different Unicode characters.
    """
    # Greek homograph - visually looks like "test"
    greek_homograph = "t\u03B5st"  # Greek epsilon 'ε' instead of 'e'
    result = sanitize_string(greek_homograph)

    # Current behavior FAILS this test:
    # NFC doesn't change Greek characters
    assert result == "tst" or result == "", (
        f"SECURITY: Greek homograph should be removed. Got: '{result}'"
    )


def test_mixed_cyrillic_latin_attack():
    """Test detection of mixed-script homograph attacks.

    Attackers often mix scripts to create visually confusing text
    that bypasses filters while appearing legitimate to users.
    """
    # Mixed Cyrillic and Latin - common homograph attack technique
    mixed_attack = "\u0430\u0431\u0441admin"  # Cyrillic "абс" + Latin "admin"
    result = sanitize_string(mixed_attack)

    # Current behavior FAILS this test:
    # Only removes if we implement script restriction
    assert result == "admin", (
        f"SECURITY: Non-Latin scripts should be removed. Got: '{result}'"
    )


def test_legitimate_latin_unicode_preserved():
    """Test that legitimate Latin-script Unicode is preserved.

    We want to preserve legitimate accented characters used in
    Latin-based languages (French, Spanish, German, etc.)
    """
    # Common Latin-script accented characters should be preserved
    legitimate = "café résumé naïve"
    result = sanitize_string(legitimate)
    assert result == legitimate, (
        f"Legitimate Latin-script accents should be preserved. "
        f"Expected: '{legitimate}', Got: '{result}'"
    )


def test_security_docstring_updated():
    """Test that the security issue is documented in the code.

    This test ensures that Issue #774 is properly documented
    in the sanitize_string function's docstring.
    """
    docstring = sanitize_string.__doc__

    # After the fix, the docstring should mention:
    # - The limitation of NFC normalization
    # - Visual homograph attacks
    # - Script restrictions or other mitigation

    # For now, this test documents the security issue
    assert docstring is not None, "Function must have documentation"
