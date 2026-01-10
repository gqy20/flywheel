"""Test for Issue #1309 - NFKC normalization expansion DoS protection.

This test verifies that the sanitize_for_security_context function properly
handles the case where NFKC normalization expands the string length, which
could potentially bypass length-based DoS protection.

Issue: https://github.com/anthropics/flywheel/issues/1309
"""

import pytest
import unicodedata
from flywheel.cli import sanitize_for_security_context


def test_nfkc_normalization_does_not_bypass_length_limit():
    """Test that NFKC normalization cannot bypass max_length limit.

    This test uses compatibility characters that expand during NFKC normalization:
    - The ligature 'ﬁ' (U+FB01) expands to 'fi' (2 characters)
    - The superscript '²' (U+00B2) expands to '2' (1 character)
    - Fullwidth characters like 'ｅ' (U+FF45) expand to 'e' (1 character)

    If max_length check happens BEFORE normalization, an attacker could craft
    a string with many compatibility characters that appears short but becomes
    very long after normalization, potentially bypassing the length limit.
    """
    # Create a string with compatibility characters that expand during NFKC
    # Each ligature 'ﬁ' (1 char) expands to 'fi' (2 chars)
    # We'll use 200 ligatures, which is 200 chars before NFKC
    # After NFKC, it becomes 400 chars
    compatibility_chars = 'ﬁ' * 200  # 200 characters

    # Verify that NFKC normalization does expand the string
    normalized = unicodedata.normalize('NFKC', compatibility_chars)
    assert len(normalized) == 400  # Each ﬁ becomes fi (2 chars)

    # With max_length=255, the function should reject this input
    # even though the pre-normalization length is 200 (< 255)
    # because post-normalization it would be 400 (> 255)
    result = sanitize_for_security_context(compatibility_chars, context="url", max_length=255)

    # The result should be truncated to max_length (255)
    # If the check happens before normalization, it would NOT be truncated
    # and would return all 400 characters (or close to it)
    assert len(result) <= 255, (
        f"NFKC normalization bypassed length limit: "
        f"input length={len(compatibility_chars)}, "
        f"normalized length={len(normalized)}, "
        f"result length={len(result)}, "
        f"max_length=255"
    )


def test_pre_normalization_length_check():
    """Test that there's a pre-normalization length check to prevent obvious DoS.

    While NFKC normalization is needed to prevent homograph attacks (Issue #1049),
    we should still have a coarse pre-check to prevent extremely long inputs from
    causing memory pressure during normalization.

    This test verifies that a very long string (even if mostly ASCII) is rejected
    early, before normalization, when it's obviously too long.
    """
    # Create a very long ASCII string (10,000 characters)
    # ASCII characters don't change during NFKC normalization
    very_long_string = 'a' * 10000

    # With max_length=255, this should be truncated
    result = sanitize_for_security_context(very_long_string, context="url", max_length=255)

    # The result should be truncated to 255
    assert len(result) <= 255, (
        f"Very long string was not properly truncated: "
        f"input length={len(very_long_string)}, "
        f"result length={len(result)}, "
        f"max_length=255"
    )


def test_mixed_expansion_characters():
    """Test with a mix of characters that expand during NFKC normalization.

    This tests a more realistic scenario where an attacker might mix various
    compatibility characters to maximize the expansion factor.
    """
    # Mix of different compatibility characters
    # ﬁ (1->2), ² (1->1), ™ (1->2), ½ (1->3)
    mixed = 'ﬁ²™½' * 100  # 400 characters before normalization

    # Verify expansion
    normalized = unicodedata.normalize('NFKC', mixed)
    # Each ﬁ²™½ becomes fi2tm1/2 (8 chars)
    # So 400 * 4 = 1600 input chars -> 400 * 8 = 3200 output chars
    assert len(normalized) > len(mixed), "NFKC should expand the string"

    # With max_length=255, this should be properly limited
    result = sanitize_for_security_context(mixed, context="filename", max_length=255)

    assert len(result) <= 255, (
        f"Mixed expansion characters bypassed length limit: "
        f"input length={len(mixed)}, "
        f"normalized length={len(normalized)}, "
        f"result length={len(result)}"
    )
