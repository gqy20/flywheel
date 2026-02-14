"""Regression tests for Issue #3282: CLI rename command is missing.

This test file ensures that the Todo.rename() method is exposed to users
through a CLI subcommand, similar to how mark_done/mark_undone are implemented.

Issue #3282: The rename() method exists in Todo model but no CLI command exposes it.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists(tmp_path, capsys) -> None:
    """CLI should have a 'rename' subcommand to update todo text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear add output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "new text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out


def test_cli_rename_updates_todo_text_and_persists(tmp_path, capsys) -> None:
    """Running 'todo rename 1 new text' should update todo text and persist change."""
    db = tmp_path / "db.json"
    app = TodoApp(str(db))

    # Add a todo via app
    app.add("original task")

    # Verify initial state
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "original task"

    # Now use CLI to rename
    parser = build_parser()
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "renamed task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    # Verify change persisted via app
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed task"


def test_cli_rename_updates_updated_at_timestamp(tmp_path) -> None:
    """Rename should update the updated_at timestamp."""
    db = tmp_path / "db.json"
    app = TodoApp(str(db))

    added = app.add("original")
    original_updated_at = added.updated_at

    # Small delay to ensure timestamp changes
    import time
    time.sleep(0.01)

    # Rename via CLI
    parser = build_parser()
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "renamed"])
    run_command(rename_args)

    # Verify timestamp updated
    todos = app.list()
    assert todos[0].updated_at > original_updated_at


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """Error handling for non-existent id should match other commands."""
    db = tmp_path / "db.json"
    parser = build_parser()

    rename_args = parser.parse_args(["--db", str(db), "rename", "99", "new text"])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_whitespace_only_text_raises_error(tmp_path, capsys) -> None:
    """Rename with whitespace-only text should raise error via CLI."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for whitespace-only text"

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method_exists(tmp_path) -> None:
    """TodoApp should have a rename method similar to mark_done/mark_undone."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    assert added.text == "original"

    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"
    assert renamed.id == 1
