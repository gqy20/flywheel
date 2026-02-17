"""Regression tests for Issue #3979: run_command hides exception type.

This test file ensures that run_command includes the exception type name
in error output for better debugging (e.g., "ValueError: Todo #999 not found"
instead of just "Error: Todo #999 not found").
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_error_output_includes_valueerror_type_name(tmp_path, capsys) -> None:
    """Error output should include ValueError type name for debugging.

    When a ValueError is raised (e.g., non-existent todo), the error
    output should include 'ValueError' for better debugging.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger a ValueError by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1, "run_command should return 1 on ValueError"

    captured = capsys.readouterr()
    # The error message should include the exception type name
    assert "ValueError" in captured.err, (
        f"Error output should include exception type 'ValueError', "
        f"got: {captured.err!r}"
    )


def test_cli_error_output_includes_oserror_type_name(tmp_path, capsys) -> None:
    """Error output should include OSError type name for debugging.

    When an OSError is raised (e.g., permission denied), the error
    output should include 'OSError' for better debugging.
    """
    # Create a directory at the db path to trigger OSError when trying to write
    db = tmp_path / "db.json"
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on OSError"

    captured = capsys.readouterr()
    # The error message should include the exception type name
    # Note: This could be OSError or a subclass like PermissionError/IsADirectoryError
    assert "Error" in captured.err and (
        "OSError" in captured.err
        or "PermissionError" in captured.err
        or "IsADirectoryError" in captured.err
    ), (
        f"Error output should include exception type (OSError or subclass), "
        f"got: {captured.err!r}"
    )


def test_cli_error_output_includes_jsondecodeerror_type_name(tmp_path, capsys) -> None:
    """Error output should include exception type name for debugging.

    When invalid JSON is encountered, the storage layer catches JSONDecodeError
    and re-raises as ValueError with context. The error output should include
    the exception type name for better debugging.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause json.JSONDecodeError
    # The storage layer wraps this in a ValueError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on JSON decode error"

    captured = capsys.readouterr()
    # The error message should include the exception type name
    # Since the storage layer wraps JSONDecodeError in ValueError, we see ValueError
    assert "ValueError" in captured.err, (
        f"Error output should include exception type 'ValueError', "
        f"got: {captured.err!r}"
    )
