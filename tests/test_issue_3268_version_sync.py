"""Test for issue #3268: Version should be defined in one place only."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import flywheel


def test_version_matches_pyproject_toml() -> None:
    """Bug #3268: __version__ should match version in pyproject.toml."""
    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)

    expected_version = pyproject_data["project"]["version"]

    # The __version__ should match pyproject.toml version
    assert flywheel.__version__ == expected_version, (
        f"Version mismatch: __init__.py has {flywheel.__version__!r}, "
        f"pyproject.toml has {expected_version!r}"
    )


def test_version_not_hardcoded_in_init() -> None:
    """Bug #3268: Version should NOT be hardcoded in __init__.py.

    The version should be dynamically loaded from package metadata to ensure
    a single source of truth (pyproject.toml).
    """
    init_path = Path(flywheel.__file__)
    init_content = init_path.read_text(encoding="utf-8")

    # Check that the version is NOT hardcoded as a literal string assignment
    # This pattern matches lines like: __version__ = "0.1.0"
    hardcoded_pattern = r'^__version__\s*=\s*["\'][\d.]+["\']'
    match = re.search(hardcoded_pattern, init_content, re.MULTILINE)

    assert match is None, (
        f"Version appears to be hardcoded in __init__.py: {match.group()!r}. "
        "Use importlib.metadata or similar to read version from package metadata."
    )
