"""Regression tests for Issue #3580: CLI lacks edit command for renaming todos.

This test file ensures that the CLI exposes an 'edit' subcommand that calls
Todo.rename() to update todo text. The Todo class already has the rename()
method implemented, but it was not exposed through the CLI.

Issue #3580 specifically requests:
- CLI support: todo edit <id> <new_text>
- Edit should update updated_at timestamp
- Empty text should raise clear error
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_exists(tmp_path) -> None:
    """CLI should have an 'edit' subcommand available."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # The parser should be able to parse the edit command
    args = parser.parse_args(["--db", str(db), "edit", "1", "new text"])
    assert args.command == "edit"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update the todo text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(add_args)
    assert result == 0
    capsys.readouterr()  # Clear output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "new text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Edited #1" in captured.out or "edit" in captured.out.lower()

    # Verify the text was updated by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_edit_command_updates_timestamp(tmp_path, capsys) -> None:
    """edit command should update the updated_at timestamp."""
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "task to edit"])
    run_command(add_args)
    capsys.readouterr()

    # Get original timestamp
    data = json.loads(db.read_text())
    original_updated_at = data[0]["updated_at"]

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "edited task"])
    result = run_command(edit_args)
    assert result == 0

    # Verify timestamp was updated
    data = json.loads(db.read_text())
    new_updated_at = data[0]["updated_at"]
    assert new_updated_at != original_updated_at, "updated_at should be updated after edit"


def test_cli_edit_command_empty_text_raises_error(tmp_path, capsys) -> None:
    """edit command with empty text should raise a clear error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "some task"])
    run_command(add_args)
    capsys.readouterr()

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)
    assert result == 1, "edit with empty text should fail"

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "empty" in captured.err.lower()


def test_cli_edit_command_whitespace_text_raises_error(tmp_path, capsys) -> None:
    """edit command with whitespace-only text should raise a clear error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "some task"])
    run_command(add_args)
    capsys.readouterr()

    # Try to edit with whitespace-only text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(edit_args)
    assert result == 1, "edit with whitespace-only text should fail"

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "empty" in captured.err.lower()


def test_cli_edit_command_nonexistent_id_raises_error(tmp_path, capsys) -> None:
    """edit command with non-existent ID should raise a clear error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "new text"])
    result = run_command(edit_args)
    assert result == 1, "edit with non-existent ID should fail"

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "not found" in captured.err.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    This ensures consistency with other commands that use _sanitize_text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "task"])
    run_command(add_args)
    capsys.readouterr()

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "task\n\rinjected"])
    result = run_command(edit_args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
