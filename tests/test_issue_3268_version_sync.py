"""Test for issue #3268: Version should be defined in one place (pyproject.toml).

The __version__ in src/flywheel/__init__.py should be derived from
pyproject.toml to avoid synchronization risk.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import flywheel


def test_version_matches_pyproject_toml() -> None:
    """Bug #3268: __version__ should match the version in pyproject.toml."""
    # Find pyproject.toml relative to the package
    package_dir = Path(flywheel.__file__).resolve().parent
    project_root = package_dir.parent.parent  # src/flywheel -> src -> project root
    pyproject_path = project_root / "pyproject.toml"

    assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"

    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)

    pyproject_version = pyproject_data["project"]["version"]

    # The __version__ should match the pyproject.toml version
    assert flywheel.__version__ == pyproject_version, (
        f"Version mismatch: flywheel.__version__={flywheel.__version__!r} "
        f"but pyproject.toml has version={pyproject_version!r}. "
        f"__version__ should be derived from pyproject.toml to avoid sync issues."
    )


def test_version_is_derived_from_pyproject_toml_not_hardcoded() -> None:
    """Bug #3268: __version__ should be dynamically loaded, not hardcoded.

    This test ensures the version is derived from pyproject.toml at runtime
    rather than hardcoded as a string literal in __init__.py.
    """
    # Read the source file
    init_file = Path(flywheel.__file__).resolve()

    source_content = init_file.read_text(encoding="utf-8")

    # Check that there's no hardcoded version string like __version__ = "0.1.0"
    # The fix should use importlib.metadata or read from pyproject.toml
    hardcoded_pattern = r'__version__\s*=\s*["\'][^"\']+["\']'

    assert not re.search(hardcoded_pattern, source_content), (
        "Version appears to be hardcoded in __init__.py. "
        "__version__ should be derived from pyproject.toml to ensure "
        "single source of truth and avoid synchronization issues."
    )
