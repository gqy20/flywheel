"""Test that pywin32 is declared as a Windows dependency (Issue #319)."""

import os
import sys
from pathlib import Path

import pytest

# Use tomllib (Python 3.11+) or fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("tomli required for pyproject.toml parsing")


class TestIssue319Pywin32Dependency:
    """Test that pywin32 is properly declared as a dependency.

    Issue #319: Windows security settings depend on external library pywin32.
    The fix should explicitly declare pywin32 in project dependencies so that
    users on Windows know to install it, rather than discovering this at runtime.

    This test verifies that pyproject.toml declares pywin32 appropriately.
    """

    def test_pywin32_declared_in_dependencies(self):
        """Test that pywin32 is declared in pyproject.toml.

        On Windows, pywin32 should be declared as a dependency so users know
        to install it. The test checks that pyproject.toml either:
        1. Declares pywin32 in the main dependencies list (for all platforms), or
        2. Declares pywin32 in a Windows-specific optional dependency group
        """
        # Read pyproject.toml
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml should exist"

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Check project dependencies
        project_deps = config.get("project", {}).get("dependencies", [])

        # Check if pywin32 is declared in main dependencies
        # (This is the ideal solution - always declare it for all platforms)
        pywin32_in_main = any(
            "pywin32" in dep.lower() for dep in project_deps
        )

        # Check optional dependencies for Windows-specific declaration
        optional_deps = config.get("project", {}).get("optional-dependencies", {})
        windows_deps = optional_deps.get("windows", [])
        pywin32_in_windows = any(
            "pywin32" in dep.lower() for dep in windows_deps
        )

        # At least one should be True
        has_pywin32 = pywin32_in_main or pywin32_in_windows

        # This is the assertion that should fail before the fix
        assert has_pywin32, (
            "pywin32 should be declared in pyproject.toml dependencies. "
            "Either add it to the main dependencies list, or create a "
            "'windows' optional-dependencies group. "
            "This ensures Windows users know they need pywin32 for secure "
            "directory permissions. "
            f"\nCurrent main dependencies: {project_deps}"
            f"\nCurrent optional dependencies: {optional_deps}"
        )

    def test_pywin32_installation_instructions_present(self):
        """Test that installation instructions mention pywin32 for Windows.

        Verify that README.md or similar documentation mentions pywin32
        installation for Windows users.
        """
        readme_path = Path(__file__).parent.parent / "README.md"

        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read().lower()

            # Check if README mentions Windows installation with pywin32
            # This is a nice-to-have, not strictly required
            mentions_windows = "windows" in content
            mentions_pywin32 = "pywin32" in content

            if mentions_windows and not mentions_pywin32:
                pytest.warn(
                    UserWarning(
                        "README.md mentions Windows but not pywin32. "
                        "Consider adding installation instructions for Windows users."
                    )
                )
        else:
            # If README doesn't exist, that's okay - just skip this test
            pytest.skip("README.md not found")
