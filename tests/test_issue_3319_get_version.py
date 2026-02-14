"""Tests for get_version() function - Issue #3319."""

from __future__ import annotations


def test_get_version_importable() -> None:
    """Test that get_version can be imported from flywheel."""
    from flywheel import get_version


def test_get_version_returns_string() -> None:
    """Test that get_version returns a string."""
    from flywheel import get_version

    result = get_version()
    assert isinstance(result, str)


def test_get_version_equals_version_variable() -> None:
    """Test that get_version() returns the same value as __version__."""
    from flywheel import __version__, get_version

    assert get_version() == __version__


def test_get_version_value() -> None:
    """Test that get_version() returns expected version string."""
    from flywheel import get_version

    assert get_version() == "0.1.0"


def test_get_version_in_all() -> None:
    """Test that get_version is in __all__."""
    from flywheel import __all__

    assert "get_version" in __all__
