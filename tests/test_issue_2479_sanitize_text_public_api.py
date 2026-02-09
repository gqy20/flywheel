"""Regression tests for Issue #2479: _sanitize_text private function is exported and used externally.

Issue #2479 highlights an encapsulation problem where:
1. formatter.py defines _sanitize_text as a private function (leading underscore)
2. cli.py imports this private function: `from .formatter import TodoFormatter, _sanitize_text`
3. This breaks Python convention that private functions (names starting with _) are
   implementation details not meant for external use

The fix should:
1. Make sanitize_text a public API (remove leading underscore)
2. Add it to __all__ in formatter.py to declare the public API explicitly
3. Update cli.py to use the public API
"""

from __future__ import annotations

import ast
import importlib


def test_cli_does_not_import_private_formatter_functions() -> None:
    """cli.py should NOT import private functions from formatter module.

    Issue #2479: cli.py currently imports _sanitize_text (a private function),
    breaking encapsulation. Private functions (prefixed with _) should remain
    implementation details of the formatter module.

    This test will FAIL until the fix is implemented (converting _sanitize_text
    to a public API).
    """
    # Parse cli.py to find imports from formatter module
    with open("src/flywheel/cli.py") as f:
        cli_source = f.read()

    cli_tree = ast.parse(cli_source)

    # Find all import statements that import from .formatter
    private_imports = []
    for node in ast.walk(cli_tree):
        if isinstance(node, ast.ImportFrom):
            # Check for relative import from .formatter (level=1 means ".")
            # or absolute import from flywheel.formatter
            is_formatter_import = (
                (node.level == 1 and node.module == "formatter") or
                (node.level == 0 and node.module == "flywheel.formatter")
            )
            if is_formatter_import:
                for alias in node.names:
                    if alias.name.startswith("_"):
                        private_imports.append(alias.name)

    # This assertion FAILS initially because cli.py imports _sanitize_text
    assert not private_imports, (
        f"cli.py imports private function(s) from formatter module: {private_imports}. "
        "Private functions (prefixed with _) should not be imported externally. "
        "The formatter module should provide a public API instead."
    )


def test_formatter_has_public_sanitize_text_function() -> None:
    """formatter.py should export sanitize_text as a public function.

    Issue #2479 fix: After renaming _sanitize_text to sanitize_text (public),
    verify it exists and is callable.
    """
    from flywheel import formatter

    # Verify the public function exists
    assert hasattr(formatter, "sanitize_text"), (
        "formatter module should export sanitize_text as a public function"
    )

    # Verify it's callable
    assert callable(formatter.sanitize_text), (
        "sanitize_text should be callable"
    )


def test_formatter_declares_public_api_via_all() -> None:
    """formatter.py should declare its public API via __all__.

    Issue #2479 fix: The module should explicitly declare what is public
    using __all__ to make the API contract clear.
    """
    from flywheel import formatter

    # Verify __all__ exists and includes expected public exports
    assert hasattr(formatter, "__all__"), (
        "formatter module should declare __all__ to specify public API"
    )

    expected_exports = {"sanitize_text", "TodoFormatter"}
    actual_exports = set(formatter.__all__)

    assert expected_exports.issubset(actual_exports), (
        f"formatter.__all__ should include {expected_exports}, "
        f"but got {actual_exports}"
    )


def test_sanitize_text_functionality_preserved() -> None:
    """sanitize_text (formerly _sanitize_text) should work correctly.

    Issue #2479: After making the function public, verify its core
    sanitization behavior is preserved.
    """
    from flywheel.formatter import sanitize_text

    # Test newline escaping
    assert sanitize_text("Hello\nWorld") == r"Hello\nWorld"

    # Test carriage return escaping
    assert sanitize_text("Hello\rWorld") == r"Hello\rWorld"

    # Test tab escaping
    assert sanitize_text("Hello\tWorld") == r"Hello\tWorld"

    # Test backslash escaping (done first to prevent ambiguity)
    assert sanitize_text("Hello\\nWorld") == r"Hello\\nWorld"

    # Test control character (0x00) escaping
    assert sanitize_text("Hello\x00World") == r"Hello\x00World"

    # Test C1 control character (0x80) escaping
    assert sanitize_text("Hello\x80World") == r"Hello\x80World"

    # Test DEL (0x7f) escaping
    assert sanitize_text("Hello\x7fWorld") == r"Hello\x7fWorld"

    # Test normal text is unchanged
    assert sanitize_text("Normal text") == "Normal text"
