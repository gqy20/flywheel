"""Tests for get_version() function - Issue #3319."""

from __future__ import annotations


def test_get_version_exists_and_returns_string() -> None:
    """get_version() function should exist and return a string."""
    from flywheel import get_version

    result = get_version()
    assert isinstance(result, str)


def test_get_version_equals_version() -> None:
    """get_version() should return the same value as __version__."""
    from flywheel import __version__, get_version

    assert get_version() == __version__


def test_get_version_returns_expected_format() -> None:
    """get_version() should return a valid version string."""
    from flywheel import get_version

    version = get_version()
    # Check it returns a non-empty string matching semver-like pattern
    assert version == "0.1.0"


def test_get_version_has_type_annotation() -> None:
    """get_version() should have -> str type annotation."""
    from flywheel import get_version

    # Verify the return type annotation is str
    assert get_version.__annotations__.get("return") is str
