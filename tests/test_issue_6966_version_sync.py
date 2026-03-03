"""Regression test for issue #6966: Version mismatch between __init__.py and pyproject.toml."""

from __future__ import annotations

from importlib.metadata import version


def test_version_matches_pyproject_toml() -> None:
    """Bug #6966: flywheel.__version__ must match version in pyproject.toml.

    The version should be read dynamically from package metadata at runtime,
    eliminating the need for a hardcoded version string in __init__.py.
    """
    import flywheel

    # The version should match what's declared in pyproject.toml
    # via importlib.metadata.version()
    expected_version = version("flywheel")
    assert flywheel.__version__ == expected_version, (
        f"Version mismatch: __init__.__version__={flywheel.__version__!r} "
        f"but pyproject.toml version={expected_version!r}"
    )


def test_version_not_hardcoded() -> None:
    """Bug #6966: Ensure version is dynamically loaded, not hardcoded.

    This test verifies that __version__ is not a hardcoded string literal
    but is read from package metadata using importlib.metadata.version().
    """
    import ast
    import pathlib

    init_path = pathlib.Path(__file__).parent.parent / "src" / "flywheel" / "__init__.py"
    source = init_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Check that the source imports version from importlib.metadata
    has_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "importlib.metadata" in node.module:
            for alias in node.names:
                if alias.name == "version":
                    has_import = True
                    break

    assert has_import, "Missing 'from importlib.metadata import version'"

    # Check that __version__ is assigned from version("flywheel") in the try block
    # We look for a Try node that has __version__ assigned from a Call to version
    found_dynamic_assignment = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == "__version__"
                            and isinstance(stmt.value, ast.Call)
                        ):
                            found_dynamic_assignment = True

    assert found_dynamic_assignment, (
        "__version__ should be dynamically assigned from version('flywheel') "
        "in a try block, with a fallback in except clause"
    )
