"""Regression tests for Issue #2111: cli.py imports private _sanitize_text from formatter.

This test file ensures that cli.py only imports public APIs from the formatter module
and does not depend on private implementation details like _sanitize_text.

Issue #2111 acceptance criteria:
- cli.py imports only public APIs from formatter module (no underscore-prefixed functions)
- All existing tests pass after refactoring
- formatter module exposes a public sanitize_text function or TodoFormatter.sanitize_text method
"""

from __future__ import annotations

import re

from flywheel.cli import build_parser, run_command


def test_cli_module_does_not_import_private_underscore_functions_from_formatter() -> None:
    """cli.py should not import private _ functions from formatter module.

    Issue #2111: cli.py:8 imports _sanitize_text directly from formatter,
    violating encapsulation by depending on a private function.
    """
    # Read the source file directly to check imports
    with open('src/flywheel/cli.py') as f:
        cli_source = f.read()

    # Check if there's a direct import of private functions from formatter
    # Pattern: from .formatter import ..., _private_function
    private_import_pattern = r'from\s+\.formatter\s+import.*_[a-zA-Z_]+'
    matches = re.findall(private_import_pattern, cli_source)

    assert not matches, (
        f"cli.py contains imports of private functions from formatter: {matches}. "
        "This violates encapsulation - use public APIs instead."
    )


def test_cli_formatter_has_public_sanitize_text_api() -> None:
    """formatter module should expose a public sanitize_text API.

    Issue #2111 acceptance criteria: formatter module should expose
    a public sanitize_text function or TodoFormatter.sanitize_text method.
    """
    import flywheel.formatter as formatter_module

    # Check for public function
    if hasattr(formatter_module, 'sanitize_text'):
        assert callable(formatter_module.sanitize_text), "sanitize_text should be callable"
        return

    # Check for class method on TodoFormatter
    if hasattr(formatter_module, 'TodoFormatter'):
        formatter_class = formatter_module.TodoFormatter
        if hasattr(formatter_class, 'sanitize_text'):
            assert callable(formatter_class.sanitize_text), "TodoFormatter.sanitize_text should be callable"
            return

    # If we get here, no public API exists
    raise AssertionError(
        "formatter module must expose a public sanitize_text API, "
        "either as module.function or TodoFormatter.sanitize_text method"
    )


def test_cli_sanitization_still_works_after_refactor(tmp_path, capsys) -> None:
    """CLI sanitization should still work after refactoring to public API.

    Issue #2111: After refactoring to use public APIs, all existing
    sanitization functionality should still work.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Test that sanitization still works with control characters
    args = parser.parse_args(["--db", str(db), "add", "Task\nwith\rcontrol\tchars"])
    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Verify output is sanitized
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\t" in captured.out
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
