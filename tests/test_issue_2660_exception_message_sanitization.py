"""Regression tests for Issue #2660: Exception handler exposes sensitive paths.

This test file ensures that exception messages in run_command are sanitized
to prevent information disclosure through filesystem paths.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_exception_no_path_leakage_invalid_json(tmp_path, capsys) -> None:
    """Exception messages should not expose full filesystem paths.

    When JSON decode errors occur with paths in their messages,
    those paths should be sanitized to prevent information disclosure.

    This test uses a sensitive directory name that should NOT appear in
    the error output.
    """
    # Use a path with a "sensitive" directory name to test path sanitization
    sensitive_dir = tmp_path / "secret_api_keys" / "database.json"
    sensitive_dir.parent.mkdir(parents=True)

    # Write invalid JSON that will trigger ValueError with full path in message
    sensitive_dir.write_text('{invalid json here}', encoding='utf-8')

    parser = build_parser()
    args = parser.parse_args(['--db', str(sensitive_dir), 'list'])

    result = run_command(args)
    assert result == 1, 'run_command should return 1 on JSON decode error'

    captured = capsys.readouterr()

    # The error output should NOT contain the sensitive directory name
    # Currently this FAILS because the error message includes the full path
    assert 'secret_api_keys' not in captured.err, (
        f'Error message should not expose sensitive path component '
        f"'secret_api_keys'. Got stderr: {captured.err}"
    )

    # Error message should still be present (sanitized)
    assert captured.err, 'Error message should be present in stderr'
    # Should still indicate it was a JSON error
    assert 'json' in captured.err.lower(), 'Error should indicate JSON problem'


def test_cli_exception_no_path_leakage_file_too_large(tmp_path, capsys) -> None:
    """File size errors should not expose full filesystem paths."""
    # Create a path with sensitive naming
    sensitive_dir = tmp_path / 'production_configs' / 'db.json'
    sensitive_dir.parent.mkdir(parents=True)

    # Write a JSON file that exceeds the size limit
    # Max size is 10MB, let's create something larger (~27MB)
    large_content = '[' + ','.join(['{"text": "x"}' for _ in range(2000000)]) + ']'
    sensitive_dir.write_text(large_content, encoding='utf-8')

    parser = build_parser()
    args = parser.parse_args(['--db', str(sensitive_dir), 'list'])

    result = run_command(args)
    assert result == 1, 'run_command should return 1 on file size error'

    captured = capsys.readouterr()

    # Should not expose the sensitive directory name
    assert 'production_configs' not in captured.err, (
        f'Error message should not expose sensitive path component '
        f"'production_configs'. Got stderr: {captured.err}"
    )


def test_cli_exception_preserves_useful_error_info(tmp_path, capsys) -> None:
    """Error messages should remain useful for debugging while protecting sensitive info."""
    # Use a normal path without sensitive names
    db = tmp_path / 'db.json'
    db.write_text('{bad json}', encoding='utf-8')

    parser = build_parser()
    args = parser.parse_args(['--db', str(db), 'list'])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()

    # Should indicate what kind of error occurred
    assert 'error' in captured.err.lower(), 'Should contain "error"'
    # Should indicate it's related to JSON
    assert 'json' in captured.err.lower(), 'Should indicate JSON problem'
