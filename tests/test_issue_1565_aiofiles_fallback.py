"""Tests for aiofiles fallback safety (Issue #1565)

This test ensures that when aiofiles is not available,
the fallback mechanism works correctly without causing AttributeError.

The issue was that aiofiles was set to None with # type: ignore,
which could cause AttributeError if code tried to use it before
the fallback was assigned.
"""

import pytest
from flywheel.storage import HAS_AIOFILES, aiofiles


def test_aiofiles_is_never_none():
    """Test that aiofiles is never None, even when fallback is used.

    This is the core issue #1565 - aiofiles should always be a valid
    object with an 'open' method, never None.
    """
    # After module import, aiofiles should always be a valid object
    assert aiofiles is not None, (
        "aiofiles should never be None after module import. "
        "When aiofiles package is not available, it should be replaced "
        "with _AiofilesFallback implementation."
    )


def test_aiofiles_has_open_method():
    """Test that aiofiles always has an 'open' method."""
    assert hasattr(aiofiles, 'open'), (
        "aiofiles must have 'open' method. "
        "This should work whether using real aiofiles or fallback."
    )

    assert callable(aiofiles.open), (
        "aiofiles.open must be callable"
    )


def test_aiofiles_open_returns_context_manager():
    """Test that aiofiles.open returns a valid async context manager."""
    ctx = aiofiles.open('/tmp/test_fallback', 'r')

    assert ctx is not None, (
        "aiofiles.open should return a context manager object, not None"
    )

    # The context manager should have __aenter__ and __aexit__ methods
    assert hasattr(ctx, '__aenter__'), (
        "aiofiles.open should return an async context manager with __aenter__"
    )
    assert hasattr(ctx, '__aexit__'), (
        "aiofiles.open should return an async context manager with __aexit__"
    )


def test_has_aiofiles_flag():
    """Test that HAS_AIOFILES flag is correctly set."""
    # HAS_AIOFILES should be a boolean
    assert isinstance(HAS_AIOFILES, bool), (
        "HAS_AIOFILES should be a boolean flag"
    )

    # When HAS_AIOFILES is False, aiofiles should still be usable
    if not HAS_AIOFILES:
        assert aiofiles is not None, (
            "When HAS_AIOFILES is False, aiofiles should use fallback, not None"
        )
        assert hasattr(aiofiles, 'open'), (
            "Fallback aiofiles should have 'open' method"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
