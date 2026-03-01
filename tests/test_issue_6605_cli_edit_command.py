"""Regression tests for Issue #6605: CLI missing rename/edit command.

This test file ensures that the CLI exposes an 'edit' command that allows
users to modify todo text via the command line, leveraging the existing
Todo.rename() method.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_modifies_todo_text(tmp_path, capsys) -> None:
    """The 'edit' command should modify the text of an existing todo."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args_add = parser.parse_args(["--db", str(db), "add", "original text"])
    result_add = run_command(args_add)
    assert result_add == 0, "add command should succeed"

    # Now edit the todo
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", "new text"])
    result_edit = run_command(args_edit)
    assert result_edit == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "new text" in captured.out, "Output should show new text"
    assert "Edited #1" in captured.out or "edited" in captured.out.lower(), (
        "Output should confirm edit"
    )


def test_cli_edit_command_updates_updated_at(tmp_path) -> None:
    """Editing a todo should update its updated_at timestamp."""
    import json

    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    args_add = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(args_add)

    # Get original updated_at
    data = json.loads(db.read_text())
    original_updated_at = data[0]["updated_at"]

    # Wait a tiny bit and edit
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", "modified"])
    run_command(args_edit)

    # Check updated_at changed
    data = json.loads(db.read_text())
    new_updated_at = data[0]["updated_at"]
    assert new_updated_at != original_updated_at, "updated_at should change after edit"


def test_cli_edit_command_empty_text_errors(tmp_path, capsys) -> None:
    """Empty text should trigger 'Todo text cannot be empty' error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo first
    args_add = parser.parse_args(["--db", str(db), "add", "some text"])
    run_command(args_add)

    # Try to edit with empty text
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(args_edit)

    assert result == 1, "edit with empty text should fail"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower(), (
        "Error should mention empty"
    )


def test_cli_edit_command_nonexistent_id_errors(tmp_path, capsys) -> None:
    """Editing a non-existent todo should return an error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a todo that doesn't exist
    args_edit = parser.parse_args(["--db", str(db), "edit", "999", "new text"])
    result = run_command(args_edit)

    assert result == 1, "edit with non-existent id should fail"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower(), (
        "Error should mention not found"
    )


def test_cli_edit_command_preserves_done_status(tmp_path) -> None:
    """Editing a todo should preserve its done status."""
    import json

    db = tmp_path / "db.json"
    parser = build_parser()

    # Add and mark done
    args_add = parser.parse_args(["--db", str(db), "add", "task"])
    run_command(args_add)
    args_done = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args_done)

    # Edit the todo
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", "modified task"])
    run_command(args_edit)

    # Check done status is preserved
    data = json.loads(db.read_text())
    assert data[0]["done"] is True, "done status should be preserved after edit"
