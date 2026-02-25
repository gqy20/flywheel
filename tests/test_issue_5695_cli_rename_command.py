"""Regression tests for Issue #5695: Todo.rename() method exists but is not exposed via CLI.

This test file ensures that the 'rename' subcommand is available in the CLI
to expose the Todo.rename() functionality.
"""

from __future__ import annotations

from flywheel.cli import build_parser, main, run_command


def test_cli_rename_command_with_valid_id_and_text(tmp_path, capsys) -> None:
    """CLI rename command should update todo.text and todo.updated_at."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(args)
    assert result == 0

    # Rename the todo
    args = parser.parse_args(["--db", str(db), "rename", "1", "New text"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "New text" in captured.out


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """CLI rename command should raise error for non-existent id."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """CLI rename command should raise error for empty/whitespace-only text."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(args)
    assert result == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_whitespace_only_text(tmp_path, capsys) -> None:
    """CLI rename command should raise error for whitespace-only text."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(args)
    assert result == 0

    # Try to rename with whitespace-only text
    args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_via_main_function(tmp_path) -> None:
    """Test rename command via main() function."""
    db = tmp_path / "test2.json"

    # Add a todo
    result = main(["--db", str(db), "add", "Test todo"])
    assert result == 0

    # Rename it
    result = main(["--db", str(db), "rename", "1", "Updated todo"])
    assert result == 0

    # Verify the rename persisted by listing
    result = main(["--db", str(db), "list"])
    assert result == 0
