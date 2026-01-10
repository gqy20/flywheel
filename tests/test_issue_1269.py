"""Tests for Issue #1269 - Unicode bidirectional override characters in shell context."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestUnicodeBidirectionalOverrideInShell:
    """Test that Unicode bidirectional override characters are removed in shell context.

    Issue #1269: In 'shell' context, although shlex.quote() is used, Unicode
    bidirectional override characters (like RLO/LRO) should be removed BEFORE
    calling shlex.quote() to prevent terminal spoofing attacks.

    The bidirectional override characters include:
    - U+202A: LEFT-TO-RIGHT EMBEDDING (LRE)
    - U+202B: RIGHT-TO-LEFT EMBEDDING (RLE)
    - U+202C: POP DIRECTIONAL FORMATTING (PDF)
    - U+202D: LEFT-TO-RIGHT OVERRIDE (LRO)
    - U+202E: RIGHT-TO-LEFT OVERRIDE (RLO)
    - U+2066: LEFT-TO-RIGHT ISOLATE (LRI)
    - U+2067: RIGHT-TO-LEFT ISOLATE (RLI)
    - U+2068: FIRST STRONG ISOLATE (FSI)
    - U+2069: POP DIRECTIONAL ISOLATE (PDI)

    These characters can be used for terminal output spoofing attacks and must
    be removed before shell quoting.
    """

    def test_lro_removed_in_shell_context(self):
        """Test that LEFT-TO-RIGHT OVERRIDE (U+202D) is removed in shell context."""
        # LRO character: \u202D
        test_string = "file\u202Dname.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # LRO should be removed before quoting
        assert "\u202D" not in result
        # Result should be properly quoted
        assert result == shlex.quote("filename.txt")

    def test_rlo_removed_in_shell_context(self):
        """Test that RIGHT-TO-LEFT OVERRIDE (U+202E) is removed in shell context."""
        # RLO character: \u202E
        test_string = "file\u202Ename.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # RLO should be removed before quoting
        assert "\u202E" not in result
        # Result should be properly quoted
        assert result == shlex.quote("filename.txt")

    def test_lre_removed_in_shell_context(self):
        """Test that LEFT-TO-RIGHT EMBEDDING (U+202A) is removed in shell context."""
        # LRE character: \u202A
        test_string = "file\u202Aname.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # LRE should be removed before quoting
        assert "\u202A" not in result

    def test_rle_removed_in_shell_context(self):
        """Test that RIGHT-TO-LEFT EMBEDDING (U+202B) is removed in shell context."""
        # RLE character: \u202B
        test_string = "file\u202Bname.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # RLE should be removed before quoting
        assert "\u202B" not in result

    def test_pdf_removed_in_shell_context(self):
        """Test that POP DIRECTIONAL FORMATTING (U+202C) is removed in shell context."""
        # PDF character: \u202C
        test_string = "file\u202Cname.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # PDF should be removed before quoting
        assert "\u202C" not in result

    def test_lri_removed_in_shell_context(self):
        """Test that LEFT-TO-RIGHT ISOLATE (U+2066) is removed in shell context."""
        # LRI character: \u2066
        test_string = "file\u2066name.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # LRI should be removed before quoting
        assert "\u2066" not in result

    def test_rli_removed_in_shell_context(self):
        """Test that RIGHT-TO-LEFT ISOLATE (U+2067) is removed in shell context."""
        # RLI character: \u2067
        test_string = "file\u2067name.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # RLI should be removed before quoting
        assert "\u2067" not in result

    def test_fsi_removed_in_shell_context(self):
        """Test that FIRST STRONG ISOLATE (U+2068) is removed in shell context."""
        # FSI character: \u2068
        test_string = "file\u2068name.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # FSI should be removed before quoting
        assert "\u2068" not in result

    def test_pdi_removed_in_shell_context(self):
        """Test that POP DIRECTIONAL ISOLATE (U+2069) is removed in shell context."""
        # PDI character: \u2069
        test_string = "file\u2069name.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # PDI should be removed before quoting
        assert "\u2069" not in result

    def test_multiple_bidi_chars_removed_in_shell_context(self):
        """Test that multiple bidirectional override characters are removed in shell context."""
        # Multiple BIDI characters
        test_string = "file\u202D\u202E\u202A\u202B\u202Cname.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # All BIDI characters should be removed
        assert "\u202D" not in result
        assert "\u202E" not in result
        assert "\u202A" not in result
        assert "\u202B" not in result
        assert "\u202C" not in result
        # Result should be clean filename
        assert result == shlex.quote("filename.txt")

    def test_bidi_chars_with_spaces_and_special_chars(self):
        """Test BIDI character removal with spaces and special characters in shell context."""
        # BIDI characters with spaces and special chars that need quoting
        test_string = "file \u202Ewith spaces & special.txt"
        result = sanitize_for_security_context(test_string, context="shell")
        # BIDI character should be removed
        assert "\u202E" not in result
        # Result should be properly quoted
        assert "file with spaces" in result
        # Should be shell-quoted
        assert result.startswith("'")

    def test_bidi_removed_before_quoting(self):
        """Test that BIDI characters are removed BEFORE shlex.quote() is applied.

        This is the critical security requirement from Issue #1269:
        BIDI override characters must be removed BEFORE calling shlex.quote(),
        not after. This prevents terminal spoofing attacks.
        """
        # Create a string that would be dangerous if BIDI chars weren't removed before quoting
        # The attack attempts to hide malicious commands using bidirectional overrides
        dangerous = "safe\u202Ecommand.sh"  # RLO attempts to reverse the display

        result = sanitize_for_security_context(dangerous, context="shell")

        # The BIDI character must be removed before quoting happens
        # This means the result should not contain any BIDI characters
        assert "\u202E" not in result

        # The result should be a properly quoted version of the cleaned string
        # not a quoted version containing BIDI characters
        expected = shlex.quote("safecommand.sh")
        assert result == expected


# Import shlex for comparison
import shlex
