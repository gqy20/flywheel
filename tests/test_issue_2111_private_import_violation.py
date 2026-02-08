"""Regression tests for Issue #2111: cli.py imports private _sanitize_text from formatter.

This test file ensures that cli.py only imports public APIs from the formatter module
and does not directly import underscore-prefixed (private) functions.

Issue #2111: cli.py line 8 imports _sanitize_text directly, violating encapsulation
by coupling CLI to internal implementation details.
"""

from __future__ import annotations

import ast


def test_cli_imports_only_public_formatter_apis() -> None:
    """cli.py should only import public APIs from formatter module.

    Issue #2111: cli.py imports private _sanitize_text function directly from
    formatter module, violating encapsulation. This test checks that no underscore-
    prefixed functions are imported from formatter in cli.py.
    """
    # Read cli.py source code
    with open("src/flywheel/cli.py") as f:
        cli_source = f.read()

    # Parse the AST
    cli_tree = ast.parse(cli_source)

    # Track imports from formatter module
    private_imports: list[str] = []

    for node in ast.walk(cli_tree):
        if isinstance(node, ast.ImportFrom) and node.module in (
            ".formatter",
            "flywheel.formatter",
            "formatter",
        ):
                for alias in node.names:
                    imported_name = alias.name
                    # Check if it's a private import (starts with underscore)
                    if imported_name.startswith("_"):
                        private_imports.append(imported_name)

    # Assert that no private imports were found
    assert not private_imports, (
        f"cli.py imports private functions from formatter module: {private_imports}. "
        "This violates encapsulation. Please use public APIs only."
    )


def test_formatter_exposes_public_sanitize_text() -> None:
    """formatter module should expose a public sanitize_text function.

    Issue #2111 acceptance criteria: formatter module exposes a public
    sanitize_text function that cli.py can use instead of private _sanitize_text.
    """
    # Import the formatter module
    from flywheel import formatter

    # Check that public sanitize_text function exists
    assert hasattr(formatter, "sanitize_text"), (
        "formatter module should expose a public sanitize_text function"
    )

    # Verify it's callable
    assert callable(formatter.sanitize_text), (
        "formatter.sanitize_text should be callable"
    )

    # Verify it works correctly
    test_input = "Test\nString\x1b[31m"
    expected_output = r"Test\nString\x1b[31m"
    actual_output = formatter.sanitize_text(test_input)
    assert actual_output == expected_output, (
        f"sanitize_text should work correctly: expected {expected_output}, got {actual_output}"
    )


def test_formatter_public_api_works() -> None:
    """Public formatter.sanitize_text should work the same as the old private function.

    This ensures backward compatibility after refactoring from _sanitize_text
    to sanitize_text.
    """
    from flywheel.formatter import sanitize_text

    # Test basic control character escaping
    assert sanitize_text("hello\nworld") == r"hello\nworld"
    assert sanitize_text("hello\rworld") == r"hello\rworld"
    assert sanitize_text("hello\tworld") == r"hello\tworld"
    assert sanitize_text("hello\x00world") == r"hello\x00world"
    assert sanitize_text("hello\x1bworld") == r"hello\x1bworld"
    assert sanitize_text("hello\x7fworld") == r"hello\x7fworld"

    # Test that normal text passes through
    assert sanitize_text("normal text") == "normal text"

    # Test backslash escaping (done before control char escaping)
    assert sanitize_text(r"C:\Users\test") == r"C:\\Users\\test"
