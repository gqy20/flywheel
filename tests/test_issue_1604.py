"""Test for Issue #1604 - Potential bypass of length check via Unicode normalization expansion.

This test verifies that the pre-normalization length check properly handles
Unicode characters that expand significantly during NFKC normalization.
"""

import pytest
from flywheel.cli import sanitize_for_security_context


def test_unicode_nfkc_expansion_bypass():
    """Test that extreme NFKC expansion cannot bypass length checks.

    Issue #1604: Some Unicode characters can expand significantly during
    NFKC normalization. The pre-normalization check uses 2x multiplier,
    but we need to ensure this doesn't allow bypassing memory limits.

    This test uses ligature characters that expand during NFKC normalization:
    - ﬁ (U+FB01) → fi (2 characters)
    - ﬂ (U+FB02) → fl (2 characters)
    - ﬃ (U+FB03) → ffi (3 characters)
    - ﬄ (U+FB04) → ffl (3 characters)
    """
    max_length = 100

    # Create a string that will expand during NFKC normalization
    # Using ligature characters that expand to multiple characters
    ligatures = 'ﬃ' * 50  # Each expands to 3 chars after NFKC
    # Before NFKC: len = 50
    # After NFKC: len = 150 (exceeds max_length=100)

    # The pre-normalization check (2x multiplier) allows up to 200 chars
    # So 50 chars should pass the pre-check
    assert len(ligatures) == 50  # Pre-normalization length

    # After NFKC normalization, this should be truncated to max_length
    result = sanitize_for_security_context(ligatures, context="filename", max_length=max_length)

    # The result should not exceed max_length after normalization
    # NFKC normalization converts each ligature, then truncation should happen
    assert len(result) <= max_length, (
        f"Result length {len(result)} exceeds max_length {max_length}. "
        f"This indicates the length check was bypassed via NFKC expansion."
    )


def test_unicode_nfkc_expansion_with_repeating_ligatures():
    """Test edge case with many repeating expanding characters.

    Uses characters that expand significantly to test the boundaries
    of the 2x pre-normalization multiplier.
    """
    max_length = 50

    # Use characters that expand significantly: ㎖ (U+3396) is "ml" (2 chars)
    # But can combine to create longer expansions
    # Let's use a more extreme case: combining characters
    # Each combining sequence can expand differently

    # Create string with combining marks that could expand
    # Using multiple compatibility ligatures
    test_input = 'ﬄ' * 30  # Each expands to 3 chars

    # Pre-check: 30 chars * 2 = 60 (passes pre-check with 2x multiplier for max_length=50)
    # Post-NFKC: 30 * 3 = 90 chars (should be truncated to 50)
    assert len(test_input) == 30

    result = sanitize_for_security_context(test_input, context="filename", max_length=max_length)

    # Must respect max_length even after expansion
    assert len(result) <= max_length, (
        f"NFKC expansion bypassed length check: {len(result)} > {max_length}"
    )


def test_normalization_happens_before_final_truncation():
    """Verify the order: normalize first, then truncate.

    This ensures that even if pre-normalization check allows some expansion,
    the final truncation after normalization enforces the limit.
    """
    max_length = 20

    # Create input that expands during normalization
    # Using multiple expanding characters
    input_str = 'ﬁﬂﬃﬄ' * 10  # Mix of ligatures

    result = sanitize_for_security_context(input_str, context="url", max_length=max_length)

    # Result must be within limits
    assert len(result) <= max_length

    # Verify normalization happened (ligatures should be expanded)
    # The result should contain ASCII equivalents, not original ligatures
    assert 'ﬁ' not in result
    assert 'ﬂ' not in result
    assert 'ﬃ' not in result
    assert 'ﬄ' not in result
