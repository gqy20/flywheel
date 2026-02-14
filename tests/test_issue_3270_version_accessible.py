"""Test for issue #3270: __version__ should be accessible from flywheel package."""

from __future__ import annotations

import flywheel


def test_version_is_accessible() -> None:
    """Verify that __version__ is accessible from the flywheel package."""
    # Should be able to access __version__ directly
    assert hasattr(flywheel, "__version__")
    assert isinstance(flywheel.__version__, str)
    assert flywheel.__version__ != ""


def test_version_format_is_valid() -> None:
    """Verify that __version__ follows semantic versioning format."""
    version = flywheel.__version__
    # Basic semver check: major.minor.patch
    parts = version.split(".")
    assert len(parts) >= 2, f"Version '{version}' should have at least major.minor"
    assert all(part.isdigit() for part in parts), f"Version '{version}' parts should be numeric"
