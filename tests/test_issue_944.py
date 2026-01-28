"""Tests for issue #944 - NFKC normalization may cause data loss.

Issue: Unicode normalization (NFKC) may cause data loss or semantic change.
Location: src/flywheel/cli.py, line 68

The problem is that NFKC normalization converts compatibility characters
to their canonical forms, which can lose user intent:
- Superscripts: ² → 2, ³ → 3
- Ligatures: ﬁ → fi, ﬂ → fl
- Trademark symbols: ™ → tm, © → c

For a general Todo application, users may intentionally use these special
characters for mathematical notation, branding, or stylistic reasons.

This test demonstrates the data loss issue with NFKC normalization.
"""

import pytest
from flywheel.cli import remove_control_chars


class TestIssue944NFKCDataLoss:
    """Test that NFKC normalization causes unacceptable data loss."""

    def test_superscript_numbers_are_converted(self):
        """Superscript numbers should be preserved, not converted to regular digits.

        Users may use superscripts for mathematical notation like x², y³.
        NFKC converts ² (U+00B2) → 2 and ³ (U+00B3) → 3, losing the semantic meaning.
        """
        # Mathematical notation: x squared
        input_text = "x²"
        result = remove_control_chars(input_text)

        # Current implementation (NFKC) converts ² → 2, giving "x2"
        # Expected behavior: preserve the superscript
        assert result == "x²", \
            f"Superscript ² should be preserved, but got '{result}' (data loss!)"

    def test_superscript_three(self):
        """Superscript three should be preserved.

        Users may use superscripts like y³ for mathematical notation.
        """
        input_text = "y³"
        result = remove_control_chars(input_text)

        # Current implementation (NFKC) converts ³ → 3, giving "y3"
        # Expected behavior: preserve the superscript
        assert result == "y³", \
            f"Superscript ³ should be preserved, but got '{result}' (data loss!)"

    def test_ligatures_are_converted(self):
        """Ligatures should be preserved, not converted to separate characters.

        Users may use ligatures for typographic reasons or in specific texts.
        NFKC converts ﬁ (U+FB01) → "fi" and ﬂ (U+FB02) → "fl", losing
        the single-character semantic.
        """
        # Ligature examples
        input_text = "ﬁ"  # U+FB01 LATIN SMALL LIGATURE FI
        result = remove_control_chars(input_text)

        # Current implementation (NFKC) converts ﬁ → "fi"
        # Expected behavior: preserve the ligature
        assert result == "ﬁ", \
            f"Ligature ﬁ should be preserved, but got '{result}' (data loss!)"

    def test_trademark_symbol_preserved(self):
        """Trademark symbol should be preserved.

        Users may use ™ for branding purposes. NFKC converts ™ → "tm",
        which loses the trademark symbol meaning.
        """
        input_text = "MyProduct™"
        result = remove_control_chars(input_text)

        # Current implementation (NFKC) converts ™ → "tm"
        # Expected behavior: preserve the trademark symbol
        assert result == "MyProduct™", \
            f"Trademark ™ should be preserved, but got '{result}' (data loss!)"

    def test_copyright_symbol_preserved(self):
        """Copyright symbol should be preserved.

        Users may use © for copyright notices. NFKC can affect this.
        """
        input_text = "© 2024 Company"
        result = remove_control_chars(input_text)

        # Copyright symbol should be preserved
        assert result == "© 2024 Company", \
            f"Copyright © should be preserved, but got '{result}' (data loss!)"

    def test_fraction_preserved(self):
        """Fraction characters should be preserved.

        Users may use ½, ¼, ¾ for fractional notation.
        NFKC converts ½ → "1/2", ¼ → "1/4", etc.
        """
        input_text = "½ cup flour"
        result = remove_control_chars(input_text)

        # Current implementation (NFKC) converts ½ → "1/2"
        # Expected behavior: preserve the fraction character
        assert result == "½ cup flour", \
            f"Fraction ½ should be preserved, but got '{result}' (data loss!)"
