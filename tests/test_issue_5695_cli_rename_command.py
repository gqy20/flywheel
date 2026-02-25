"""Regression tests for Issue #5695: Todo.rename() method exists but is not exposed via CLI.

This test file ensures that the CLI exposes a 'rename' subcommand to allow users
to rename existing todos. The Todo.rename() method exists in todo.py but was not
exposed via the CLI.

Issue #5695 acceptance criteria:
- CLI accepts 'todo rename <id> <text>' command
- rename command updates todo.text and todo.updated_at
- rename command raises error for non-existent id
- rename command raises error for empty/whitespace-only text
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_with_valid_id_and_text(tmp_path, capsys) -> None:
    """rename command should update todo text for valid id and text.

    Issue #5695: The CLI should accept 'rename <id> <text>' command
    to rename an existing todo.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New text"])
    result = run_command(rename_args)

    assert result == 0, "rename command should succeed"
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out


def test_cli_rename_command_updates_updated_at(tmp_path, capsys) -> None:
    """rename command should update todo.updated_at timestamp."""
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Get the original updated_at
    original_data = json.loads(db.read_text())
    original_updated_at = original_data[0]["updated_at"]

    # Small delay to ensure timestamp changes
    time.sleep(0.01)

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New text"])
    run_command(rename_args)
    capsys.readouterr()  # Clear rename output

    # Verify updated_at changed
    updated_data = json.loads(db.read_text())
    assert updated_data[0]["updated_at"] != original_updated_at
    assert updated_data[0]["text"] == "New text"


def test_cli_rename_command_non_existent_id(tmp_path, capsys) -> None:
    """rename command should raise error for non-existent id."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail for non-existent id"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """rename command should raise error for empty/whitespace-only text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail for empty text"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_whitespace_only_text(tmp_path, capsys) -> None:
    """rename command should raise error for whitespace-only text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail for whitespace-only text"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()
