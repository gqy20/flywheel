"""Tests for issue #2757: Version synchronization between __init__.py and pyproject.toml.

The issue is that __version__ in __init__.py is exported via __all__, but pyproject.toml
has a hardcoded version. This creates a risk of version drift where the two sources
get out of sync.

The fix uses dynamic versioning from __init__.py as the single source of truth.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_flywheel_version_exists() -> None:
    """Verify flywheel package has __version__ attribute exported via __all__."""
    import flywheel

    # __version__ should be exported via __all__
    assert "__version__" in flywheel.__all__, "__version__ must be in __all__ for proper API"

    # __version__ should be accessible
    assert hasattr(flywheel, "__version__"), "__version__ attribute must exist"

    # __version__ should not be empty
    assert flywheel.__version__, "__version__ must not be empty"


def test_flywheel_version_format() -> None:
    """Verify __version__ follows semantic versioning format."""
    import flywheel

    version = flywheel.__version__

    # Check for semver-like format: major.minor.patch (e.g., 0.1.0, 1.2.3)
    # Allow optional pre-release identifiers like -dev, -alpha, etc.
    semver_pattern = r"^\d+\.\d+\.\d+([a-zA-Z0-9.\-+]*)?$"
    assert re.match(semver_pattern, version), (
        f"Version '{version}' does not follow semantic versioning format. "
        f"Expected format: X.Y.Z where X, Y, Z are integers."
    )


def test_version_single_source_of_truth() -> None:
    """Verify that pyproject.toml uses dynamic version from __init__.py.

    This test reads pyproject.toml and ensures it uses dynamic versioning
    rather than a hardcoded version value.
    """
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    pyproject_content = pyproject_path.read_text()

    # Check that version is dynamic, not hardcoded
    # The pyproject.toml should have 'dynamic = ["version"]' in [project] section
    # and should NOT have 'version = "X.Y.Z"' in [project] section

    # Look for [project] section and check if version is listed in dynamic
    project_section_match = re.search(
        r"\[project\](.*?)(?=\n\[|\Z)", pyproject_content, re.DOTALL
    )
    assert project_section_match, "Could not find [project] section in pyproject.toml"

    project_section = project_section_match.group(1)

    # Check for dynamic version
    has_dynamic_version = 'dynamic = ["version"]' in project_section or "dynamic = ['version']" in project_section

    # Check for hardcoded version (should not exist in [project] section if using dynamic)
    has_hardcoded_version = bool(
        re.search(r'^version\s*=\s*["\'].*?["\']', project_section, re.MULTILINE)
    )

    assert has_dynamic_version, (
        "pyproject.toml should use dynamic versioning. "
        "Add 'dynamic = [\"version\"]' to [project] section."
    )

    assert not has_hardcoded_version, (
        "pyproject.toml should not have a hardcoded 'version' in [project] section. "
        "Use 'dynamic = [\"version\"]' instead to read from flywheel.__version__"
    )


def test_version_match_with_import() -> None:
    """Verify that importing flywheel.__version__ returns the expected value."""
    import flywheel

    # When dynamic versioning is set up, flywheel.__version__ should be accessible
    # This is a basic smoke test to ensure the import works
    version = flywheel.__version__

    # Version should be a non-empty string
    assert isinstance(version, str)
    assert len(version) > 0
