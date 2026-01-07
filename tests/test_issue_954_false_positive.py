"""Test to verify Issue #954 is a false positive.

Issue #954 claims that NFC normalization introduces security risks because
fullwidth characters are preserved. However, this is a false positive because:

1. remove_control_chars() is for data storage normalization of display text
   (titles, descriptions), NOT for filenames or shell parameters
2. The function's SECURITY WARNING (lines 21-27) explicitly states it does
   NOT provide security protection
3. The code comments (lines 94-95) already state that additional processing
   should be applied for filenames/shell parameters at those boundaries
4. Current usage (cli.py:370-371, 427-429) only applies this function to
   display text fields (title, description), never to filenames or shell args

This test verifies that the current behavior is CORRECT:
- Fullwidth characters are preserved for legitimate display text
- Control characters and dangerous metacharacters are removed
- The function is NOT used for security-sensitive contexts
"""

import pytest
from flywheel.cli import remove_control_chars


class TestIssue954FalsePositive:
    """Tests to verify Issue #954 is a false positive."""

    def test_fullwidth_characters_preserved_for_display_text(self):
        """Fullwidth characters should be preserved for display text.

        NFC normalization (Issue #944) preserves fullwidth characters because
        they are legitimate Unicode characters used in CJK languages. They are
        NOT security risks when used in display text (titles, descriptions).

        Security risks only exist if these characters are used in security-
        sensitive contexts (filenames, shell parameters), which this function
        is NOT designed for.
        """
        # Fullwidth alphanumeric characters (U+FF01-U+FF5E)
        # These are commonly used in Japanese, Chinese, etc.
        fullwidth_text = "Ｈｅｌｌｏ　Ｗｏｒｌｄ"
        assert remove_control_chars(fullwidth_text) == fullwidth_text

        # Fullwidth Latin letters are valid display text
        fullword_latin = "Ｔｅｓｔ"
        assert remove_control_chars(fullword_latin) == fullword_latin

    def test_dangerous_metacharacters_are_removed(self):
        """Even with NFC normalization, dangerous metacharacters are removed.

        The function DOES remove characters that could interfere with data
        formats, regardless of normalization form.
        """
        # Shell metacharacters are removed
        assert remove_control_chars("test;command") == "testcommand"
        assert remove_control_chars("test|pipe") == "testpipe"
        assert remove_control_chars("test`backtick") == "testbacktick"

        # Format string characters are removed
        assert remove_control_chars("test{value}") == "testvalue"
        assert remove_control_chars("test%format") == "testformat"

    def test_control_characters_removed_regardless_of_normalization(self):
        """Control characters are removed regardless of NFC normalization."""
        # Null bytes and control chars are removed
        assert remove_control_chars("test\x00null") == "testnull"
        assert remove_control_chars("test\nnewline") == "testnewline"
        assert remove_control_chars("test\ttab") == "testtab"

    def test_unicode_spoofing_characters_removed(self):
        """Unicode spoofing characters are removed even with NFC."""
        # Zero-width characters are removed
        assert remove_control_chars("test\u200Bzero") == "testzero"

        # Bidirectional override characters are removed
        assert remove_control_chars("test\u202Aoverride") == "testoverride"

    def test_international_characters_preserved(self):
        """International characters (non-fullwidth) are preserved.

        NFC normalization handles canonical equivalence without removing
        legitimate international characters.
        """
        # Cyrillic
        assert remove_control_chars("Привет") == "Привет"

        # CJK
        assert remove_control_chars("你好") == "你好"

        # Arabic
        assert remove_control_chars("مرحبا") == "مرحبا"

        # Combined characters (NFC handles canonical equivalence)
        # é (U+00E9) vs e + combining acute (U+0065 U+0301)
        combined = "e\u0301"  # e + combining acute
        assert remove_control_chars(combined) == "é"  # Should normalize to composed form

    def test_function_is_not_for_security_sensitive_contexts(self):
        """Verify this function is documented as NOT for security contexts.

        The function's docstring explicitly states it does NOT provide
        security protection. It is for data normalization only.
        """
        # The function should have a clear SECURITY WARNING in its docstring
        docstring = remove_control_chars.__doc__
        assert "SECURITY WARNING" in docstring
        assert "does NOT provide security protection" in docstring
        assert "ONLY for data normalization" in docstring

    def test_nfc_vs_nfkc_difference(self):
        """Demonstrate the difference between NFC and NFKC normalization.

        NFC (current): Preserves compatibility characters like fullwidth
        NFKC (previous): Would convert fullwidth to ASCII

        Issue #944 changed from NFKC to NFC to prevent data loss for
        legitimate use of special characters. This is correct for display
        text but would be wrong for filenames (which would need NFKC or
        additional filtering).
        """
        # Fullwidth characters are preserved with NFC (current behavior)
        fullwidth = "ＡＢＣ"
        result = remove_control_chars(fullwidth)
        assert result == fullwidth  # Preserved

        # But dangerous characters are still removed
        dangerous = "ＡＢＣ；danger"  # Fullwidth semicolon
        result = remove_control_chars(dangerous)
        assert result == "ＡＢＣdanger"  # Semicolon removed, fullwidth preserved
