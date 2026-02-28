"""Regression test for issue #6214: CLI missing 'rename' command."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists(tmp_path, capsys) -> None:
    """CLI should accept 'rename' command."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Now rename it - this should work, not raise an error
    args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
    assert run_command(args) == 0

    # Verify the rename worked
    out = capsys.readouterr().out
    assert "renamed task" in out


def test_cli_rename_command_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """Rename command should return error code 1 for non-existent id."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_app_rename_method_exists(tmp_path) -> None:
    """TodoApp should have a rename method."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    assert added.text == "original"

    # This should work - TodoApp.rename() must exist
    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"


def test_app_rename_nonexistent_raises_error(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent id."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")
