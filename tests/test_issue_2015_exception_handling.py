"""Regression test for issue #2015: run_command should catch all exceptions, not just ValueError.

Issue: https://github.com/gqy20/flywheel/issues/2015

The bug is that run_command only catches ValueError, but other exception types
like json.JSONDecodeError and OSError can be raised from storage.py and will
cause unhandled crashes.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_run_command_handles_json_decode_error(tmp_path, capsys) -> None:
    """Test that run_command handles JSONDecodeError from corrupted JSON files.

    When a JSON file is corrupted (invalid JSON), json.loads raises JSONDecodeError
    which is NOT caught by ValueError-only exception handling.

    Regression test for issue #2015.
    """
    db = tmp_path / "corrupt.json"
    parser = build_parser()

    # Write invalid JSON to simulate a corrupted database
    db.write_text("not valid json {[}", encoding="utf-8")

    # Try to list todos - should return 1 (error), not crash
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)

    # Should return error code 1, not raise an uncaught exception
    assert result == 1, "run_command should return 1 for JSONDecodeError"

    # Error message should be printed (check output)
    out = capsys.readouterr().out
    assert "Error:" in out or "error" in out.lower() or out != "", "Should show error message"


def test_run_command_handles_os_error_for_unreadable_file(tmp_path, capsys) -> None:
    """Test that run_command handles OSError from file permission/IO errors.

    When there's a file I/O error (permissions, disk issues, etc.), os.replace
    and Path.stat can raise OSError which is NOT caught by ValueError-only handling.

    Regression test for issue #2015.
    """
    parser = build_parser()

    # Create a file (not a directory) and try to use it as a directory path
    # This will trigger OSError when trying to create a subdirectory
    fake_file = tmp_path / "not_a_directory"
    fake_file.write_text("I am a file, not a directory")

    # Try to add a todo with an invalid path (file where directory expected)
    # This will cause OSError during save when trying to create the directory
    fake_db = fake_file / "subdir" / "db.json"

    args = parser.parse_args(["--db", str(fake_db), "add", "test"])
    result = run_command(args)

    # Should return error code 1, not crash with OSError
    assert result == 1, "run_command should return 1 for OSError"

    # Error message should be shown
    out = capsys.readouterr().out
    assert out != "", "Should have error output"


def test_run_command_handles_os_error_for_permission_denied(tmp_path, capsys) -> None:
    """Test that run_command handles OSError from permission errors.

    Simulate a permission error by using /root/db.json path which typically
    requires root access.

    Regression test for issue #2015.
    """
    parser = build_parser()

    # Use a path that will likely fail with permission error
    # Note: In container environments, this might fail differently
    args = parser.parse_args(["--db", "/root/flywheel_test_db.json", "list"])
    result = run_command(args)

    # Should return error code 1, not crash with OSError
    assert result == 1, "run_command should return 1 for OSError/permission errors"
