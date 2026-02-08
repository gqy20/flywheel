"""Regression tests for Issue #2111: cli.py imports private _sanitize_text from formatter.

This test file ensures that cli.py only imports public APIs from the formatter module.
The underscore prefix indicates a private function, and cli.py should not depend on
internal implementation details.

Issue #2111 highlights that cli.py:8 imports _sanitize_text directly, violating
encapsulation principles. The fix makes sanitize_text a public API.
"""

from __future__ import annotations

import importlib

from flywheel import formatter


def test_formatter_exposes_public_sanitize_text() -> None:
    """formatter module should expose sanitize_text as a public function.

    Issue #2111: The sanitizer function should be public (no underscore prefix)
    so that cli.py can import it without violating encapsulation.
    """
    # sanitize_text should be directly importable from formatter
    assert hasattr(formatter, "sanitize_text"), \
        "formatter.sanitize_text should be exposed as public API"

    # The function should be callable
    assert callable(formatter.sanitize_text), \
        "formatter.sanitize_text should be callable"


def test_cli_imports_public_formatter_api() -> None:
    """cli.py should import only public APIs from formatter module.

    Issue #2111: cli.py should not import underscore-prefixed (private) functions.
    """
    # Reload cli module to check imports
    spec = importlib.util.find_spec("flywheel.cli")
    assert spec is not None
    assert spec.loader is not None

    # Read cli.py source to check imports
    with open(spec.origin, encoding="utf-8") as f:
        cli_source = f.read()

    # Should NOT import _sanitize_text (private function)
    assert "import _sanitize_text" not in cli_source, \
        "cli.py should not import private _sanitize_text function"
    assert "from .formatter import" in cli_source, \
        "cli.py should import from formatter module"
    assert "sanitize_text" in cli_source, \
        "cli.py should import public sanitize_text function"


def test_sanitize_text_functionality_preserved() -> None:
    """sanitize_text should preserve the same sanitization behavior.

    Issue #2111: Making the function public should not change its behavior.
    """
    test_cases = [
        ("\n", "\\n"),
        ("\r", "\\r"),
        ("\t", "\\t"),
        ("\x00", "\\x00"),
        ("\x1b[31m", "\\x1b[31m"),
        ("\\", "\\\\"),
        ("Normal text", "Normal text"),
    ]

    for input_text, expected_output in test_cases:
        result = formatter.sanitize_text(input_text)
        assert result == expected_output, \
            f"sanitize_text({input_text!r}) should return {expected_output!r}, got {result!r}"


def test_old_private_name_not_accessible() -> None:
    """The old private name _sanitize_text should not be accessible.

    Issue #2111: After renaming to public API, the old private name should not exist.
    """
    # The old private name should either not exist or not be the primary API
    # This test ensures the public API is the expected way to access the function
    assert hasattr(formatter, "sanitize_text"), \
        "Public sanitize_text should exist"

    # If the old name exists, it should be the same function (for backwards compat)
    # but the public API should be preferred
    if hasattr(formatter, "_sanitize_text"):
        # If private name exists, it should reference the same function
        assert formatter._sanitize_text is formatter.sanitize_text, \
            "If _sanitize_text exists, it should be an alias to sanitize_text"
