"""Test for issue #3268: Version should have single source of truth.

This test verifies that __version__ is dynamically loaded from package metadata
(pyproject.toml) rather than hardcoded, ensuring version synchronization.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def test_version_exists_and_non_empty() -> None:
    """Verify __version__ is accessible and non-empty."""
    from flywheel import __version__

    assert __version__, "__version__ should not be empty"
    assert isinstance(__version__, str), "__version__ should be a string"


def test_version_matches_package_metadata() -> None:
    """Verify __version__ matches the version in pyproject.toml via metadata."""
    import importlib.metadata

    from flywheel import __version__

    try:
        # When package is installed, version should match metadata
        metadata_version = importlib.metadata.version("flywheel")
        assert __version__ == metadata_version, (
            f"__version__ ({__version__}) should match package metadata ({metadata_version})"
        )
    except importlib.metadata.PackageNotFoundError:
        # When package not installed (dev environment), version should be dev fallback
        assert __version__ == "0.0.0.dev", (
            f"__version__ should be '0.0.0.dev' when package not installed, got {__version__}"
        )


def test_init_py_no_hardcoded_version_string() -> None:
    """Verify __init__.py does NOT contain hardcoded version string literal.

    This is the key test for issue #3268: ensures the fix is properly applied
    by verifying that __version__ is NOT assigned a hardcoded string literal
    like __version__ = "0.1.0" at the top level (outside exception handlers).

    A fallback dev version string inside an except clause is acceptable.
    """
    init_path = Path(__file__).parent.parent / "src" / "flywheel" / "__init__.py"
    source = init_path.read_text()

    # Parse the AST to check for hardcoded string assignments to __version__
    tree = ast.parse(source)

    # Check if __version__ is assigned inside a try block (dynamic loading pattern)
    # vs. a simple top-level assignment (hardcoded pattern)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            # Check if any assignment in the try or except body assigns to __version__
            for stmt in node.body + node.orelse:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "__version__":
                            # Found dynamic pattern - this is the fix!
                            return  # Test passes

            # Check except handlers for fallback assignment
            for handler in node.handlers:
                for stmt in handler.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "__version__"
                            ):
                                # Fallback in except is okay
                                return  # Test passes

    # If we didn't find the dynamic pattern, check for top-level hardcoded assignment
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                is_version_assign = (
                    isinstance(target, ast.Name) and target.id == "__version__"
                )
                is_string_literal = isinstance(node.value, ast.Constant) and isinstance(
                    node.value.value, str
                )
                if is_version_assign and is_string_literal:
                    version_val = node.value.value
                    # Only reject if it looks like a real version, not a dev fallback
                    if version_val != "0.0.0.dev":
                        pytest.fail(
                            f"__version__ is hardcoded as string literal '{version_val}' "
                            f"in {init_path}. Use importlib.metadata.version() instead."
                        )


def test_version_uses_importlib_metadata() -> None:
    """Verify __init__.py imports from importlib.metadata for dynamic version."""
    init_path = Path(__file__).parent.parent / "src" / "flywheel" / "__init__.py"
    source = init_path.read_text()

    # The fix should import from importlib.metadata
    assert "importlib.metadata" in source or "importlib_metadata" in source, (
        "__init__.py should import from importlib.metadata to dynamically load version"
    )
