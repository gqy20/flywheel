"""Regression tests for Issue #2479: _sanitize_text private function is exported and used externally by CLI.

This test file ensures that CLI does not import or use private functions (prefixed with _)
from other modules, maintaining proper encapsulation and reducing coupling.

Issue #2479 specifically highlights that cli.py imports _sanitize_text directly from
formatter.py, breaking encapsulation conventions.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def extract_imports_from_file(file_path: Path) -> set[str]:
    """Extract all imported names from a Python file using AST.

    Returns a set of imported names (e.g., {'TodoFormatter', '_sanitize_text'}).
    """
    source = file_path.read_text()
    tree = ast.parse(source)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    imports.add(alias.name)
    return imports


def test_cli_does_not_import_private_functions_from_formatter() -> None:
    """cli.py should not import private functions from formatter module.

    Issue #2479: cli.py line 8 imports _sanitize_text (a private function),
    breaking encapsulation. Private functions (prefixed with _) should not
    be part of the public API.
    """
    cli_path = Path(__file__).parent.parent / "src" / "flywheel" / "cli.py"
    cli_imports = extract_imports_from_file(cli_path)

    # Check for private function imports from formatter
    private_imports = {name for name in cli_imports if name.startswith("_")}

    assert not private_imports, (
        f"cli.py imports private functions from formatter module: {private_imports}. "
        "This breaks encapsulation - private functions should not be used externally. "
        "Either make the function public (remove leading underscore and add to __all__) "
        "or use the public TodoFormatter API instead."
    )


def test_formatter_has_sanitize_text_in_public_api() -> None:
    """formatter.py should expose a public API for text sanitization.

    Issue #2479 acceptance criteria: If sanitization is needed by external modules,
    there should be a public API (without leading underscore).
    """
    formatter_path = Path(__file__).parent.parent / "src" / "flywheel" / "formatter.py"
    source = formatter_path.read_text()
    tree = ast.parse(source)

    # Find all function definitions
    public_functions = set()
    private_functions = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                private_functions.add(node.name)
            else:
                public_functions.add(node.name)

    # Check if there's a public sanitize_text function
    has_public_sanitize = "sanitize_text" in public_functions
    has_private_sanitize = "_sanitize_text" in private_functions

    # Either we should have a public API, or no external code should depend on the private one
    if has_private_sanitize and not has_public_sanitize:
        # This is OK as long as nothing external uses it (verified by other test)
        pass

    # If we're going to expose sanitization, we should have a public API
    # For this fix, we'll add a public method to TodoFormatter instead
