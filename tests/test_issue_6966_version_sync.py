"""Test for issue #6966: Version mismatch between __init__.py and pyproject.toml."""

from __future__ import annotations

import re
from importlib.metadata import version

import flywheel


def test_version_matches_package_metadata() -> None:
    """Bug #6966: flywheel.__version__ must match pyproject.toml version.

    The version should be read from package metadata (pyproject.toml) at runtime
    rather than being hardcoded in __init__.py to avoid version drift.
    """
    # Get version from installed package metadata
    metadata_version = version("flywheel")

    # Get version from the module
    module_version = flywheel.__version__

    # They must match
    assert module_version == metadata_version, (
        f"Version mismatch: flywheel.__version__='{module_version}' "
        f"but package metadata version='{metadata_version}'"
    )


def test_version_format_is_valid() -> None:
    """Verify version follows semantic versioning format."""
    version_str = flywheel.__version__

    # Basic semver pattern: major.minor.patch with optional pre-release/build
    semver_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$"

    assert re.match(semver_pattern, version_str), (
        f"Version '{version_str}' does not follow semantic versioning format"
    )
