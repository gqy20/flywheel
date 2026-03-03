"""Test for issue #6966: Version consistency between __init__.py and pyproject.toml."""

from __future__ import annotations

import ast
import importlib.metadata

import flywheel


def test_version_matches_package_metadata() -> None:
    """Bug #6966: flywheel.__version__ should match package metadata.

    The __version__ in src/flywheel/__init__.py should be dynamically read
    from importlib.metadata.version('flywheel') to ensure consistency
    with pyproject.toml during releases.
    """
    # Get the version from package metadata (pyproject.toml)
    metadata_version = importlib.metadata.version("flywheel")

    # The package __version__ should match
    assert flywheel.__version__ == metadata_version, (
        f"Version mismatch: flywheel.__version__='{flywheel.__version__}' "
        f"does not match metadata version='{metadata_version}'"
    )


def test_version_is_dynamically_obtained() -> None:
    """Bug #6966: Ensure __version__ is dynamically obtained from importlib.metadata.

    This test verifies that __init__.py uses importlib.metadata.version()
    rather than hardcoding the version string, ensuring single source of truth.
    """
    # Read the __init__.py source
    import pathlib

    init_path = pathlib.Path(flywheel.__file__)
    source = init_path.read_text()

    # Parse the AST
    tree = ast.parse(source)

    # Check that the code uses importlib.metadata.version()
    uses_importlib_metadata = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for importlib.metadata.version() or version() call
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "version":
                    uses_importlib_metadata = True
                    break
            elif isinstance(node.func, ast.Name) and node.func.id == "version":
                uses_importlib_metadata = True
                break

    assert uses_importlib_metadata, (
        "__version__ should be obtained from importlib.metadata.version() "
        "rather than being hardcoded"
    )
