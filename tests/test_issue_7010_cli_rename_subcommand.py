"""Regression tests for Issue #7010: CLI missing 'rename' subcommand.

This test file ensures that the CLI exposes the Todo.rename() functionality
through a 'rename' subcommand with proper argument handling and error handling.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists() -> None:
    """The 'rename' subcommand should be available in the CLI parser."""
    parser = build_parser()
    # This will raise if 'rename' is not a valid subcommand
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """CLI 'rename' command should successfully rename a todo."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])

    result = run_command(args)
    assert result == 0, "rename command should return 0 on success"

    # Verify the todo was renamed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"

    # Verify success message is printed
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out


def test_cli_rename_command_not_found(tmp_path, capsys) -> None:
    """CLI 'rename' command should return 1 for non-existent todo."""
    db = str(tmp_path / "db.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])

    result = run_command(args)
    assert result == 1, "rename command should return 1 when todo not found"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """CLI 'rename' command should return 1 for empty text after strip."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])

    result = run_command(args)
    assert result == 1, "rename command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()

    # Verify the original text is unchanged
    todos = app.list()
    assert todos[0].text == "original text"


def test_cli_rename_command_whitespace_only(tmp_path, capsys) -> None:
    """CLI 'rename' command should return 1 for whitespace-only text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "   "])

    result = run_command(args)
    assert result == 1, "rename command should return 1 for whitespace-only text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()

    # Verify the original text is unchanged
    todos = app.list()
    assert todos[0].text == "original text"


def test_cli_rename_command_strips_whitespace(tmp_path, capsys) -> None:
    """CLI 'rename' command should strip whitespace from text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "  padded text  "])

    result = run_command(args)
    assert result == 0

    # Verify the text was stripped
    todos = app.list()
    assert todos[0].text == "padded text"


def test_cli_rename_command_sanitizes_output(tmp_path, capsys) -> None:
    """CLI 'rename' command should sanitize text in success message."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    # Text with newline and ANSI escape code
    args = parser.parse_args(["--db", db, "rename", "1", "text\nwith\x1b[31m"])

    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # The output should be sanitized - no raw escape codes or newlines
    assert "\x1b[" not in captured.out
    assert "\n" not in captured.out.split("Renamed")[1].split(":")[1].strip()
