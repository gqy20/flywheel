"""Tests for __version__ accessibility (Issue #3270).

These tests verify that:
1. __version__ can be imported from the flywheel module
2. __version__ is a string in valid semantic version format
3. __version__ is included in the module's __all__ export list
"""

from __future__ import annotations

import re

import flywheel


def test_version_is_accessible() -> None:
    """__version__ should be accessible from the flywheel module."""
    assert hasattr(flywheel, "__version__")
    assert flywheel.__version__ is not None


def test_version_is_string() -> None:
    """__version__ should be a string."""
    assert isinstance(flywheel.__version__, str)


def test_version_format() -> None:
    """__version__ should follow semantic versioning format (X.Y.Z)."""
    version_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    assert re.match(version_pattern, flywheel.__version__), (
        f"Version '{flywheel.__version__}' does not match semver pattern"
    )


def test_version_in_all() -> None:
    """__version__ should be included in __all__ export list."""
    assert "__version__" in flywheel.__all__


def test_version_value() -> None:
    """__version__ should match the expected version."""
    assert flywheel.__version__ == "0.1.0"
