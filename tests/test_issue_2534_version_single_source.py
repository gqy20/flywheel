"""Regression test for issue #2534 - Version should have single source of truth.

This test verifies that the version is dynamically read from pyproject.toml
and is not duplicated in __init__.py.

Acceptance criteria:
- Version exists in single source of truth (pyproject.toml)
- Both `import flywheel; flywheel.__version__` and version in pyproject.toml return same value
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest


def test_version_matches_pyproject_toml() -> None:
    """Test that flywheel.__version__ matches the version in pyproject.toml.

    This ensures we have a single source of truth for version information.
    """
    import flywheel

    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    pyproject_data = tomllib.loads(pyproject_content)
    pyproject_version = pyproject_data["project"]["version"]

    # Verify that __version__ matches pyproject.toml
    assert flywheel.__version__ == pyproject_version, (
        f"Version mismatch: flywheel.__version__='{flywheel.__version__}' "
        f"!= pyproject.toml version='{pyproject_version}'"
    )


def test_version_not_hardcoded_in_init() -> None:
    """Test that __init__.py does not contain a hardcoded version string.

    This ensures version is read dynamically rather than duplicated.
    """
    init_path = Path(__file__).parent.parent / "src" / "flywheel" / "__init__.py"
    init_content = init_path.read_text(encoding="utf-8")

    # Check for hardcoded version pattern like __version__ = "0.1.0"
    # We want to ensure this pattern doesn't exist
    hardcoded_pattern = r'__version__\s*=\s*"[^"]+"'
    matches = re.findall(hardcoded_pattern, init_content)

    # If we find a hardcoded version assignment, the test fails
    # (unless it's dynamically computed from a function call)
    for match in matches:
        if "=" in match and not ("(" in match or "import" in init_content.split(match)[0][:200]):
            pytest.fail(
                f"Version appears to be hardcoded in __init__.py: {match}. "
                "Version should be read dynamically from pyproject.toml or importlib.metadata."
            )


def test_version_exists() -> None:
    """Test that flywheel.__version__ can be imported and is a string."""
    import flywheel

    assert hasattr(flywheel, "__version__"), "flywheel module should have __version__ attribute"
    assert isinstance(flywheel.__version__, str), "__version__ should be a string"
    assert len(flywheel.__version__) > 0, "__version__ should not be empty"
    # Basic semantic versioning format check (e.g., 0.1.0 or 1.2.3)
    assert re.match(r"^\d+\.\d+\.\d+", flywheel.__version__), (
        f"__version__ should follow semantic versioning (e.g., 0.1.0), got: {flywheel.__version__}"
    )
