"""Regression tests for Issue #2660: Exception handler leaks sensitive paths.

This test file ensures that error messages in run_command are sanitized
to prevent information disclosure through full filesystem paths.
"""

from __future__ import annotations

import re

from flywheel.cli import build_parser, run_command


def _contains_full_path(output: str) -> bool:
    """Check if output contains a path with multiple directory separators.

    This is a heuristic: full paths contain multiple '/' characters.
    Relative paths or sanitized messages like '<database_path>' are safe.
    """
    # Look for patterns like /home/user/..., C:\Users\..., etc.
    # But exclude generic placeholders
    output_without_placeholders = output.replace("<database_path>", "").replace("<file_path>", "")
    # Check for 2+ consecutive path separators (indicates full path)
    path_pattern = r"[/\\][^/\\]+[/\\]"
    return bool(re.search(path_pattern, output_without_placeholders))


def test_cli_error_messages_sanitize_full_paths(tmp_path, capsys) -> None:
    """Error messages should not expose full filesystem paths.

    When errors occur (e.g., invalid JSON), the error message should
    use generic placeholders instead of revealing the user's directory
    structure or sensitive folder names.

    Example insecure output: "Invalid JSON in '/home/user/.secrets/todo.json': ..."
    Expected secure output: "Invalid JSON in <database_path>: ..."
    """
    # Create a path that simulates a sensitive directory structure
    sensitive_dir = tmp_path / "private_data" / "secrets" / ".config"
    sensitive_dir.mkdir(parents=True)
    db = sensitive_dir / "todo.json"

    # Write invalid JSON to trigger error
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on error"

    captured = capsys.readouterr()
    error_output = captured.err or captured.out

    # The fix should sanitize the path - either use placeholder or no full path
    assert not _contains_full_path(error_output), (
        f"Error output should not contain full filesystem paths. "
        f"Got: {error_output}"
    )


def test_cli_error_message_preserves_actionable_context(tmp_path, capsys) -> None:
    """Error messages should remain useful for debugging.

    While sanitizing paths, we should preserve the actual error type
    and what went wrong (e.g., "Invalid JSON", "Permission denied").
    """
    db = tmp_path / "db.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    error_output = captured.err or captured.out

    # Should mention the error type (JSON decode error)
    assert "json" in error_output.lower() or "error" in error_output.lower()


def test_cli_error_generic_message_for_permission_errors(tmp_path, capsys) -> None:
    """Permission errors should show generic messages, not full paths.

    Test with a path simulating restricted system directories.
    """
    # Create a file (not directory) to trigger path-as-directory error
    blocker = tmp_path / "blocker"
    blocker.write_text("I'm a file, not a dir")

    # Try to use a path that would go through the file
    bad_path = blocker / "subdir" / "todo.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(bad_path), "add", "test"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    error_output = captured.err or captured.out

    # Should not reveal full path structure
    assert not _contains_full_path(error_output), (
        f"Permission error should not expose full path. Got: {error_output}"
    )


def test_cli_error_sanitizes_file_too_large_message(tmp_path, capsys) -> None:
    """File size errors should not expose paths."""
    db = tmp_path / "sensitive" / "large_db.json"
    db.parent.mkdir(parents=True)

    # Write a file larger than _MAX_JSON_SIZE_BYTES (10MB)
    # Actually write ~11MB of data
    db.write_bytes(b"x" * (11 * 1024 * 1024))

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    error_output = captured.err or captured.out

    # Should mention the size limit but not the full path
    assert not _contains_full_path(error_output), (
        f"File size error should not expose full path. Got: {error_output}"
    )
