"""Test for NFKC normalization expansion DoS protection (Issue #1614)."""

import pytest
from flywheel.cli import sanitize_for_security_context


def test_nfkc_expansion_dos_protection():
    """Test that extreme NFKC expansion is prevented to avoid DoS attacks.

    This test ensures that even when NFKC normalization causes significant
    string expansion (e.g., compatibility ligatures like 'ﬁ' → 'fi'), the
    function should still enforce strict max_length limits and not cause
    memory exhaustion or excessive processing time.

    The current implementation has a pre-check mechanism (lines 179-189)
    but it may not be sufficient for all edge cases. This test will FAIL
    until the issue is fixed.
    """
    # Use a string that will expand significantly under NFKC normalization
    # The ligature 'ﬁ' (U+FB01) expands to 'fi' (2 characters)
    # Using many ligatures to create extreme expansion
    ligature = 'ﬁ'  # Single character that expands to 2
    input_string = ligature * 500  # 500 characters

    # Set a small max_length to test the protection
    max_length = 100

    result = sanitize_for_security_context(
        input_string,
        context="url",
        max_length=max_length
    )

    # The result should be strictly limited to max_length
    # Even if NFKC expansion would make it much longer
    assert len(result) <= max_length, (
        f"Result length {len(result)} exceeds max_length {max_length}. "
        "This indicates that NFKC expansion bypassed the length check, "
        "which could lead to DoS attacks."
    )


def test_nfkc_expansion_with_extreme_multiplier():
    """Test protection against strings with extreme NFKC expansion ratios.

    This test uses characters that expand even more dramatically under NFKC
    to ensure the pre-check mechanism handles worst-case scenarios.
    """
    # Use various compatibility characters that expand under NFKC
    # ² (superscript 2) → '2' (1 char, no expansion)
    # ﬁ (ligature) → 'fi' (1 → 2 chars)
    # ﬀ (ligature) → 'ff' (1 → 2 chars)
    # ㈱ (circled number) → '（株）' (1 → 3+ chars)

    # Create a string with characters that have high expansion ratios
    # Using '㈱' which expands significantly
    problematic_char = '㈱'  # Can expand to multiple characters
    input_string = problematic_char * 100  # 100 characters

    max_length = 50
    result = sanitize_for_security_context(
        input_string,
        context="filename",
        max_length=max_length
    )

    # Strict enforcement regardless of expansion ratio
    assert len(result) <= max_length, (
        f"Result length {len(result)} exceeds max_length {max_length}. "
        "NFKC expansion with high multiplier ratio bypassed protection."
    )


def test_nfkc_expansion_does_not_cause_memory_exhaustion():
    """Test that NFKC expansion cannot cause memory exhaustion.

    This test ensures that even with a large input that would expand
    massively under NFKC, the function should process it efficiently
    and enforce strict limits.
    """
    # Construct input that would be very large after NFKC normalization
    # but starts with a reasonable length
    ligature = 'ﬁﬂﬃﬄ'  # Multiple ligatures, each expanding

    # Create a string that's within limits before normalization
    # but would exceed limits after normalization
    input_string = ligature * 1000  # 4000 characters
    max_length = 255  # Standard filename limit

    result = sanitize_for_security_context(
        input_string,
        context="filename",
        max_length=max_length
    )

    # Should be strictly limited
    assert len(result) <= max_length, (
        f"Memory exhaustion vulnerability: result length {len(result)} "
        f"exceeds max_length {max_length}"
    )


def test_precheck_copy_limit_effectiveness():
    """Test that the pre-check copy limit prevents DoS.

    The current implementation creates a copy up to 2*max_length for checking.
    This test verifies that this mechanism is effective and cannot be bypassed.
    """
    # Create a string that's just under 2*max_length but would expand
    # massively after NFKC normalization
    max_length = 100
    copy_limit = max_length * 2  # Current implementation uses this

    # Use ligature that doubles in size
    ligature = 'ﬁ'

    # Create string exactly at copy limit
    input_string = ligature * copy_limit  # 200 characters

    result = sanitize_for_security_context(
        input_string,
        context="url",
        max_length=max_length
    )

    # Should still enforce max_length strictly
    assert len(result) <= max_length, (
        f"Pre-check copy limit bypassed: result length {len(result)} "
        f"exceeds max_length {max_length}"
    )
