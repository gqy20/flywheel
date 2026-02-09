"""Regression tests for Issue #2479: _sanitize_text private function is exported and used externally by CLI.

This test file ensures that:
1. The formatter module provides a public sanitize_text API
2. The CLI module uses only public APIs from the formatter module
3. The public sanitize_text function works correctly for sanitization

Issue #2479 acceptance criteria:
- CLI should not import private functions (leading underscore) from other modules
- All todo text output should use public API methods only
- Tests should pass without requiring direct access to private _sanitize_text function
"""

from __future__ import annotations

import ast
from pathlib import Path

from flywheel.formatter import sanitize_text


def test_formatter_module_exports_public_sanitize_text() -> None:
    """formatter.py should export a public sanitize_text function.

    Issue #2479: The _sanitize_text private function should have a public wrapper
    that can be used by external modules like cli.py.
    """
    # sanitize_text should be importable from formatter module
    assert callable(sanitize_text), "sanitize_text should be a callable function"


def test_sanitize_text_escapes_control_characters() -> None:
    """public sanitize_text should escape control characters correctly.

    This ensures the public API maintains the same sanitization behavior
    as the original private _sanitize_text function.
    """
    # Test newline escape
    assert sanitize_text("Hello\nWorld") == r"Hello\nWorld"

    # Test carriage return escape
    assert sanitize_text("Hello\rWorld") == r"Hello\rWorld"

    # Test tab escape
    assert sanitize_text("Hello\tWorld") == r"Hello\tWorld"

    # Test backslash escape (must come first to prevent double-escaping)
    assert sanitize_text("C:\\path") == r"C:\\path"

    # Test NULL byte escape
    assert sanitize_text("Hello\x00World") == r"Hello\x00World"

    # Test DEL character escape
    assert sanitize_text("Hello\x7fWorld") == r"Hello\x7fWorld"

    # Test ANSI escape sequence (C1 control character)
    assert sanitize_text("\x1b[31mRed") == r"\x1b[31mRed"

    # Test normal text (no escaping needed)
    assert sanitize_text("Normal Text") == "Normal Text"


def test_sanitize_text_complex_control_characters() -> None:
    """public sanitize_text should handle complex combinations of control characters.

    This tests edge cases and combinations that might appear in real-world input.
    """
    # Multiple control characters in sequence
    assert sanitize_text("\n\r\t") == r"\n\r\t"

    # Control characters mixed with normal text
    assert sanitize_text("Line1\nLine2\rLine3\tLine4") == r"Line1\nLine2\rLine3\tLine4"

    # Test backslash followed by control characters
    # Backslash should be escaped first, then control characters
    result = sanitize_text("\\\n")
    assert result == r"\\\n", f"Expected '\\\\\\n', got '{result}'"

    # Test the exact issue from #2083 - carriage return injection
    input_text = "Valid task\r[INJECTED]"
    result = sanitize_text(input_text)
    assert result == r"Valid task\r[INJECTED]"
    # The raw \r should NOT be in the result
    assert "\r" not in result


def test_cli_module_imports_only_public_symbols() -> None:
    """cli.py should not import private functions (leading underscore) from formatter.

    Issue #2479: The CLI module breaks encapsulation by importing _sanitize_text
    directly from formatter module. This test verifies that only public symbols
    are imported.
    """
    cli_path = Path(__file__).parent.parent / "src/flywheel/cli.py"
    cli_content = cli_path.read_text()

    # Parse the CLI module to check its imports
    tree = ast.parse(cli_content)

    # Find all imports from the formatter module
    formatter_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "formatter" in node.module:
                for alias in node.names:
                    formatter_imports.append(alias.name)

    # Check that no private functions (starting with underscore) are imported
    private_imports = [name for name in formatter_imports if name.startswith("_")]
    assert (
        not private_imports
    ), f"CLI imports private functions from formatter: {private_imports}. Use public APIs instead."

    # Verify sanitize_text is imported (public API)
    assert "sanitize_text" in formatter_imports, "CLI should import public sanitize_text from formatter"


def test_cli_uses_public_sanitize_text_in_success_messages(tmp_path, capsys) -> None:
    """CLI should use public sanitize_text for all user-facing output.

    This integration test verifies that CLI commands (add, done, undone)
    properly sanitize todo text using the public API.
    """
    from flywheel.cli import build_parser, run_command

    db = tmp_path / "db.json"
    parser = build_parser()

    # Test add command with control characters
    add_args = parser.parse_args(["--db", str(db), "add", "Task\nWith\nNewlines"])
    run_command(add_args)
    captured = capsys.readouterr()

    # Output should contain escaped newlines
    assert r"\n" in captured.out, "Newlines should be escaped in output"
    # Output should NOT contain actual newlines in the todo text portion
    # (Note: print() adds a trailing newline, so we strip for checking)
    assert "Task\nWith\nNewlines" not in captured.out, "Actual newline characters should be escaped"

    # Test done command
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(done_args)
    captured = capsys.readouterr()
    assert r"\n" in captured.out, "Newlines should be escaped in done command output"

    # Test undone command
    undone_args = parser.parse_args(["--db", str(db), "undone", "1"])
    run_command(undone_args)
    captured = capsys.readouterr()
    assert r"\n" in captured.out, "Newlines should be escaped in undone command output"


def test_backward_compatibility_private_sanitize_text_still_works() -> None:
    """Private _sanitize_text should still work for backward compatibility.

    While new code should use the public sanitize_text API, the private
    _sanitize_text function should remain functional for any code that
    may have used it (even though it was discouraged).
    """
    from flywheel.formatter import _sanitize_text

    # The private function should still work the same way
    assert _sanitize_text("Test\nText") == r"Test\nText"
    assert _sanitize_text("Test\rText") == r"Test\rText"
    assert _sanitize_text("Test\tText") == r"Test\tText"
