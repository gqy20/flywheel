"""Tests for issue #2534 - Version consistency between __init__.py and pyproject.toml."""

from __future__ import annotations

import importlib.metadata
import re


def test_version_attribute_exists() -> None:
    """Verify that flywheel has a __version__ attribute."""
    import flywheel

    assert hasattr(flywheel, "__version__")
    assert isinstance(flywheel.__version__, str)


def test_version_format_is_valid() -> None:
    """Verify that __version__ follows semantic versioning format (X.Y.Z)."""
    import flywheel

    version_pattern = r"^\d+\.\d+\.\d+"
    assert re.match(version_pattern, flywheel.__version__), (
        f"Version '{flywheel.__version__}' does not follow semantic versioning format"
    )


def test_version_not_empty() -> None:
    """Verify that __version__ is not an empty string."""
    import flywheel

    assert flywheel.__version__, "Version should not be empty"


def test_version_matches_installed_package() -> None:
    """Verify that flywheel.__version__ matches the installed package version from importlib.metadata."""
    import flywheel

    try:
        installed_version = importlib.metadata.version("flywheel")
    except importlib.metadata.PackageNotFoundError:
        # Package not installed in development environment, skip this test
        return

    assert flywheel.__version__ == installed_version, (
        f"Version mismatch: flywheel.__version__='{flywheel.__version__}' "
        f"but installed version is '{installed_version}'"
    )
