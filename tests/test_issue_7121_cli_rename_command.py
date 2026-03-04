"""Regression tests for Issue #7121: Todo.rename() method exists but CLI lacks rename command.

This test file ensures that the rename command is exposed through the CLI, allowing users
to rename existing todos via: todo rename <id> <new_text>

Issue #7121 highlights that Todo.rename() method exists in todo.py but cli.py does not
expose a corresponding command.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists(tmp_path) -> None:
    """rename command should be available in the CLI parser.

    Issue #7121: The parser should include a 'rename' subcommand.
    """
    parser = build_parser()
    # This should not raise an error - if rename subcommand doesn't exist,
    # parse_args will fail
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "rename", "1", "New text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "New text"


def test_cli_rename_command_renames_todo(tmp_path, capsys) -> None:
    """rename command should rename an existing todo.

    Issue #7121: User can rename a todo via CLI and new text persists.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0
    capsys.readouterr()  # Clear output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Updated text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "Updated text" in captured.out

    # Verify the rename persisted by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Updated text" in captured.out
    assert "Original text" not in captured.out


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """rename command should return non-zero exit code for non-existent id.

    Issue #7121: Renaming a non-existent id should return error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    assert result != 0, "rename command should return non-zero for non-existent id"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_empty_text_returns_error(tmp_path, capsys) -> None:
    """rename command should reject empty text.

    Issue #7121: Renaming to empty string should be rejected.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear output

    # Try to rename to empty string
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    assert result != 0, "rename command should return non-zero for empty text"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize text in output message.

    The rename command should use _sanitize_text for output, consistent with
    other commands (add, done, undone).
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear output

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New\ntext"])
    result = run_command(rename_args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Output should NOT contain actual newline
    assert "\n" not in captured.out.strip()
