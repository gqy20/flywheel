"""Regression tests for Issue #7121: Todo.rename() method exists but CLI lacks rename command.

This test file ensures that:
1. Users can rename a todo via CLI: todo rename <id> <new_text>
2. Non-existent id returns non-zero exit code with error message
3. Empty text is rejected with error

Issue #7121: The rename method exists on Todo class (todo.py:50) but there's no
corresponding CLI subcommand for users to invoke it.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists_and_works(tmp_path, capsys) -> None:
    """rename command should exist and allow renaming a todo's text.

    Issue #7121 acceptance criteria: Users can rename todo via CLI.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Should confirm the rename
    assert "Renamed" in captured.out or "rename" in captured.out.lower()
    assert "#1" in captured.out


def test_cli_rename_command_persists_new_text(tmp_path, capsys) -> None:
    """Rename should persist the new text to storage.

    Issue #7121 acceptance criteria: Verify new text persists.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add and rename
    add_args = parser.parse_args(["--db", str(db), "add", "Old text"])
    run_command(add_args)

    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New text"])
    run_command(rename_args)
    capsys.readouterr()  # Clear rename output

    # Verify via list command
    list_args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(list_args)
    assert result == 0

    captured = capsys.readouterr()
    assert "New text" in captured.out
    assert "Old text" not in captured.out


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """Renaming non-existent id should return non-zero exit code with error.

    Issue #7121 acceptance criteria: Non-existent id returns non-zero exit code.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    assert result == 1, "rename should return 1 for non-existent id"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_empty_text_rejected(tmp_path, capsys) -> None:
    """Renaming to empty text should be rejected with error.

    Issue #7121 acceptance criteria: Empty text is rejected with error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Some task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    assert result == 1, "rename should return 1 for empty text"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_sanitizes_output(tmp_path, capsys) -> None:
    """Rename command should sanitize todo text in success message.

    Following pattern from Issue #2083: success messages should use _sanitize_text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo with control characters
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename to text with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Task\nWith\x1b[31mANSI"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Control characters should be escaped
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Raw control chars should NOT appear
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
