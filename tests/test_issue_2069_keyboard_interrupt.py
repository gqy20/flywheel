"""Regression tests for Issue #2069: Overly broad exception catching.

This test file ensures that run_command does NOT catch critical exceptions
that should propagate for proper error handling and debugging.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_memory_error_propagates(tmp_path) -> None:
    """MemoryError should propagate and NOT be caught by run_command.

    MemoryError indicates a serious system condition that should not be
    silently converted to return code 1. It should propagate to allow
    proper handling or crash reporting.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock load() to raise MemoryError
    with patch("flywheel.cli.TodoApp._load", side_effect=MemoryError("Out of memory")):
        # run_command should re-raise MemoryError, not return 1
        with pytest.raises(MemoryError):
            run_command(args)


def test_cli_recursion_error_propagates(tmp_path) -> None:
    """RecursionError should propagate and NOT be caught by run_command.

    RecursionError indicates a programming error (infinite recursion) that
    should not be silently converted to return code 1. It should propagate
    to allow proper debugging.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock load() to raise RecursionError
    with patch("flywheel.cli.TodoApp._load", side_effect=RecursionError("Maximum recursion depth exceeded")):
        # run_command should re-raise RecursionError, not return 1
        with pytest.raises(RecursionError):
            run_command(args)


def test_cli_value_error_still_caught(tmp_path) -> None:
    """ValueError should still be caught and return 1.

    This ensures existing functionality for catching expected errors
    (like invalid todo data) continues to work after the fix.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # Should return 1 (ValueError for "not found" should be caught)
    result = run_command(args)
    assert result == 1


def test_cli_os_error_still_caught(tmp_path) -> None:
    """OSError should still be caught and return 1.

    This ensures existing functionality for catching file system errors
    (like permission denied) continues to work after the fix.
    """
    # Create a directory at the db path to trigger OSError
    db = tmp_path / "db.json"
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Should return 1 (OSError should be caught)
    result = run_command(args)
    assert result == 1


def test_cli_json_decode_error_still_caught(tmp_path) -> None:
    """json.JSONDecodeError should still be caught and return 1.

    This ensures existing functionality for catching JSON parsing errors
    continues to work after the fix.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1 (ValueError from JSON decode should be caught)
    result = run_command(args)
    assert result == 1
