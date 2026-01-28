"""Test for Issue #1604 - Verify NFKC expansion memory pressure vulnerability.

This test demonstrates that while the final truncation protects against data overflow,
there's a potential memory pressure issue during normalization.
"""

import pytest
import unicodedata
from flywheel.cli import sanitize_for_security_context


def test_extreme_nfkc_expansion():
    """Test that demonstrates the 2x multiplier assumption may be insufficient.

    The issue is that while the final truncation (line 221-223) prevents actual
    overflow, there's a brief window where the normalized string exceeds max_length,
    causing potential memory pressure.

    This test uses characters that expand more than 2x during NFKC normalization.
    """
    max_length = 50

    # Construct input that's just under 2x but will expand significantly
    # Use characters that each expand to 3 characters
    expanding_chars = 'ﬃ' * 35  # 35 chars * 3 = 105 after NFKC
    # 35 <= 50 * 2 = 100 (passes pre-check)
    # 35 * 3 = 105 > 50 (violates max_length after normalization)

    print(f"\nTest input:")
    print(f"  Pre-NFKC length: {len(expanding_chars)}")
    print(f"  Pre-check threshold (2x): {max_length * 2}")
    print(f"  Passes pre-check: {len(expanding_chars) <= max_length * 2}")

    # Manually check what NFKC expansion looks like
    normalized = unicodedata.normalize('NFKC', expanding_chars)
    print(f"  Post-NFKC length (manual): {len(normalized)}")
    print(f"  Exceeds max_length: {len(normalized) > max_length}")

    # Call the function
    result = sanitize_for_security_context(expanding_chars, context="filename", max_length=max_length)

    print(f"\nFunction output:")
    print(f"  Result length: {len(result)}")
    print(f"  Result <= max_length: {len(result) <= max_length}")

    # The function should still enforce max_length via final truncation
    # But the issue is about the memory pressure during normalization
    assert len(result) <= max_length, (
        f"Result length {len(result)} exceeds max_length {max_length}"
    )


def test_verify_normalization_order():
    """Verify that normalization happens BEFORE final truncation.

    The issue is that the current code:
    1. Pre-check: limits to 2x (line 171-172)
    2. Normalize: can expand beyond 2x (line 197)
    3. Post-check: truncates to max_length (line 221-223)

    The problem is step 2 can cause memory issues if expansion > 2x.
    """
    max_length = 20

    # Create input that will expand significantly
    test_input = 'ﬃ' * 15  # 15 chars, expands to 45 after NFKC
    # 15 <= 40 (2x), passes pre-check
    # 45 > 20 (max_length), needs post-normalization truncation

    result = sanitize_for_security_context(test_input, context="url", max_length=max_length)

    # Verify normalization happened (ligatures expanded)
    assert 'ﬃ' not in result, "NFKC normalization should have expanded the ligature"
    assert 'f' in result or len(result) == 0, "Result should contain expanded characters"

    # Verify truncation happened
    assert len(result) <= max_length, f"Result {len(result)} exceeds max_length {max_length}"


def test_edge_case_exactly_2x():
    """Test edge case where input is exactly at 2x threshold."""
    max_length = 50
    threshold = max_length * 2  # 100

    # Input at exactly 2x threshold with characters that expand
    test_input = 'ﬃ' * 33  # 33 chars, could expand to 99
    # 33 <= 100 (passes pre-check)

    result = sanitize_for_security_context(test_input, context="filename", max_length=max_length)

    # Should still be within limits
    assert len(result) <= max_length
