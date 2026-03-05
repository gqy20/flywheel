"""Tests for issue #7330: Missing 'rename' command in CLI."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subparser() -> None:
    """Verify that 'rename' subparser is defined in CLI."""
    parser = build_parser()
    # This should not raise an error if rename subparser exists
    args = parser.parse_args(["--db", ".test.json", "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """Test that 'todo rename 1 new text' successfully updates todo text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    added = app.add("original text")
    assert added.id == 1
    assert added.text == "original text"

    # Now test via CLI
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "renamed text"])
    exit_code = run_command(args)
    assert exit_code == 0

    # Verify output
    captured = capsys.readouterr()
    assert "Renamed #1:" in captured.out
    assert "renamed text" in captured.out

    # Verify the todo was actually updated
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """Error handling for non-existent ID returns exit code 1."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    exit_code = run_command(args)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_app_rename_method_exists() -> None:
    """Verify TodoApp.rename() method exists and works."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db = f"{tmp}/test.json"
        app = TodoApp(db)

        added = app.add("original")
        assert added.text == "original"

        renamed = app.rename(1, "renamed")
        assert renamed.text == "renamed"
        assert renamed.id == 1


def test_app_rename_nonexistent_raises_error() -> None:
    """TodoApp.rename() raises ValueError for non-existent ID."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db = f"{tmp}/test.json"
        app = TodoApp(db)

        with pytest.raises(ValueError, match="not found"):
            app.rename(99, "new text")
