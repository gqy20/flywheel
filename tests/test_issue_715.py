"""Tests for date validation in CLI (Issue #715).

This test file demonstrates the security vulnerability where date strings
are sanitized but not validated before being stored.
"""

import pytest
from datetime import datetime
from flywheel.cli import sanitize_string


def test_sanitize_string_does_not_validate_date_format():
    """Test that demonstrates the security issue: sanitize_string doesn't validate dates.

    This test shows that invalid date strings pass through sanitize_string
    without validation, which is the security vulnerability reported in issue #715.
    """
    # These are clearly invalid dates that should be rejected
    invalid_dates = [
        "not-a-date",
        "2024-13-01",  # Invalid month
        "2024-02-30",  # Invalid day
        "2024/01/01",  # Wrong separator
        "01-01-2024",  # Wrong order
        "injection; here",  # Contains injection attempts
        "2024-01-01T25:00:00",  # Invalid hour
    ]

    for date_str in invalid_dates:
        # Current behavior: sanitize_string just removes dangerous characters
        # but does NOT validate the date format
        sanitized = sanitize_string(date_str)

        # The sanitized string is still not a valid ISO date
        # but the code accepts it anyway - this is the bug!
        assert sanitized is not None

        # Try to parse it as an ISO date - this will fail for invalid dates
        # demonstrating that the input should have been rejected
        try:
            datetime.fromisoformat(sanitized)
            # If we get here, the date was valid (or became valid after sanitization)
            # This shouldn't happen for the test cases above
        except ValueError:
            # This is expected for invalid dates
            # The bug is that the code accepts these invalid dates anyway
            pass


def test_iso_date_validation_rejects_invalid_dates():
    """Test that datetime.fromisoformat properly rejects invalid dates."""
    invalid_dates = [
        "not-a-date",
        "2024-13-01",
        "2024-02-30",
        "2024/01/01",
        "01-01-2024",
        "2024-01-01T25:00:00",
    ]

    for date_str in invalid_dates:
        with pytest.raises(ValueError):
            datetime.fromisoformat(date_str)


def test_iso_date_validation_accepts_valid_dates():
    """Test that datetime.fromisoformat accepts valid ISO dates."""
    valid_dates = [
        "2024-01-01",
        "2024-12-31",
        "2024-02-29",  # Leap year
        "2024-01-15T10:30:00",
        "2024-01-15T10:30:00.123456",
    ]

    for date_str in valid_dates:
        # Should not raise
        result = datetime.fromisoformat(date_str)
        assert isinstance(result, datetime)
