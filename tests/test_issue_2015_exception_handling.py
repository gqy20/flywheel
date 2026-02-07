"""Regression tests for Issue #2015: run_command exception handling.

This test file ensures that run_command catches all exceptions (not just ValueError)
to prevent unhandled crashes from storage operations.

Issue: https://github.com/gqy20/flywheel/issues/2015
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_run_command_handles_json_decode_error(tmp_path, capsys) -> None:
    """run_command should handle JSONDecodeError from corrupted JSON files.

    Scenario: User manually edits the DB file and introduces invalid JSON.
    Expected: Return code 1 with error message (not crash).
    """
    db = tmp_path / "corrupt.json"
    # Write invalid JSON that will trigger json.JSONDecodeError
    db.write_text('{"invalid": json missing close bracket}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1 (error), not raise unhandled exception
    result = run_command(args)
    assert result == 1

    # Should show error message
    captured = capsys.readouterr()
    assert "Error:" in captured.out or "Error:" in captured.err


def test_run_command_handles_oserror_from_save(tmp_path, capsys) -> None:
    """run_command should handle OSError from storage operations.

    Scenario: Permission denied when trying to save to protected directory.
    Expected: Return code 1 with error message (not crash).
    """
    db = tmp_path / "protected.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Mock os.replace to raise PermissionError (subclass of OSError)
    with patch("flywheel.storage.os.replace", side_effect=PermissionError("Permission denied")):
        # Should return 1 (error), not raise unhandled exception
        result = run_command(args)
        assert result == 1

    # Should show error message
    captured = capsys.readouterr()
    assert "Error:" in captured.out or "Error:" in captured.err


def test_run_command_handles_oserror_from_load_stat(tmp_path, capsys) -> None:
    """run_command should handle OSError from file stat operations.

    Scenario: Permission denied when trying to read file metadata.
    Expected: Return code 1 with error message (not crash).
    """
    db = tmp_path / "no_access.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock Path.stat to raise PermissionError
    with patch.object(Path, "stat", side_effect=PermissionError("Permission denied")):
        # Should return 1 (error), not raise unhandled exception
        result = run_command(args)
        assert result == 1

    # Should show error message
    captured = capsys.readouterr()
    assert "Error:" in captured.out or "Error:" in captured.err
