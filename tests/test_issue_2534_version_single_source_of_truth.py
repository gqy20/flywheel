"""Test for Issue #2534 - Version single source of truth.

This test ensures that the version is not duplicated between __init__.py and pyproject.toml.
The version should be read dynamically from pyproject.toml at runtime.
"""

from pathlib import Path

import pytest

try:
    import tomli
except ImportError:
    tomli = None


def test_version_matches_pyproject_toml():
    """Test that flywheel.__version__ matches the version in pyproject.toml."""
    import flywheel

    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    if tomli is None:
        # Fallback: simple regex extraction if tomli not available
        import re

        with open(pyproject_path) as f:
            content = f.read()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                expected_version = match.group(1)
            else:
                raise pytest.skip("tomli not available and cannot parse pyproject.toml")
    else:
        with open(pyproject_path, "rb") as f:
            pyproject = tomli.load(f)
        expected_version = pyproject["project"]["version"]

    # Verify that flywheel.__version__ matches pyproject.toml
    assert flywheel.__version__ == expected_version, (
        f"Version mismatch: flywheel.__version__='{flywheel.__version__}' "
        f"does not match pyproject.toml version='{expected_version}'"
    )


def test_version_is_accessible():
    """Test that __version__ attribute exists and is a string."""
    import flywheel

    assert hasattr(flywheel, "__version__"), "flywheel module should have __version__ attribute"
    assert isinstance(flywheel.__version__, str), "__version__ should be a string"
    assert len(flywheel.__version__) > 0, "__version__ should not be empty"


def test_version_format():
    """Test that version follows semantic versioning format."""
    import re

    import flywheel

    # Basic semantic versioning pattern: major.minor.patch
    # Allows for optional pre-release identifiers (e.g., 1.0.0-alpha, 2.1.3-beta.1)
    version_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"

    assert re.match(version_pattern, flywheel.__version__), (
        f"Version '{flywheel.__version__}' does not follow semantic versioning format"
    )


def test_version_is_read_from_pyproject_toml():
    """Test that __version__ is read dynamically from pyproject.toml.

    This is the key test for issue #2534. The version should not be hardcoded
    in __init__.py but instead read from pyproject.toml at runtime.

    We verify this by checking that there's no hardcoded version string in __init__.py.
    """
    import re
    from pathlib import Path

    init_path = Path(__file__).parent.parent / "src" / "flywheel" / "__init__.py"
    with open(init_path) as f:
        init_content = f.read()

    # Check that __version__ is NOT hardcoded with a version string like "0.1.0"
    # This regex looks for __version__ = "X.Y.Z" pattern
    hardcoded_version_pattern = r'__version__\s*=\s*"\d+\.\d+\.\d+'

    has_hardcoded_version = re.search(hardcoded_version_pattern, init_content)

    assert not has_hardcoded_version, (
        "Version should not be hardcoded in __init__.py. "
        "It should be read dynamically from pyproject.toml."
    )
