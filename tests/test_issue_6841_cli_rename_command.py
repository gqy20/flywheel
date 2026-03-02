"""Tests for issue #6841: CLI should expose 'rename' command."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists() -> None:
    """CLI should have a 'rename' subparser."""
    parser = build_parser()
    # Parse with rename command - should not raise
    args = parser.parse_args(["--db", ".todo.json", "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_returns_success(tmp_path, capsys) -> None:
    """Rename command should return exit code 0 on success."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
    assert run_command(args) == 0

    # Verify output contains the renamed text
    captured = capsys.readouterr()
    assert "Renamed" in captured.out or "renamed" in captured.out.lower()
    assert "#1" in captured.out


def test_cli_rename_command_persists(tmp_path) -> None:
    """Renamed text should persist after reload."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "persisted text"])
    run_command(args)

    # Verify rename persisted
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "persisted text"


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """Rename command should return exit code 1 when todo not found."""
    db = str(tmp_path / "cli.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """Rename command should return exit code 1 for empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_cli_rename_command_rejects_whitespace_only_text(tmp_path, capsys) -> None:
    """Rename command should return exit code 1 for whitespace-only text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "   "])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()
