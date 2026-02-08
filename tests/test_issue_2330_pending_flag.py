"""Regression test for Issue #2330: --pending flag semantic clarity.

The --pending flag should show only pending (not done) todos when specified,
and show all todos when not specified.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_list_without_pending_flag_shows_all_todos(tmp_path) -> None:
    """Issue #2330: 'list' without --pending should show all todos (done and not done)."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add multiple todos
    app.add("pending task 1")
    app.add("pending task 2")
    todo3 = app.add("task to be completed")

    # Mark one as done
    app.mark_done(todo3.id)

    # list() without args (default pending_only=False) should return all todos
    all_todos = app.list(pending_only=False)
    assert len(all_todos) == 3
    assert all_todos[0].done is False
    assert all_todos[1].done is False
    assert all_todos[2].done is True


def test_list_with_show_all_false_shows_only_pending_todos(tmp_path) -> None:
    """Issue #2330: list(pending_only=True) should return only pending todos."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add multiple todos
    app.add("pending task 1")
    app.add("pending task 2")
    todo3 = app.add("task to be completed")

    # Mark one as done
    app.mark_done(todo3.id)

    # list(pending_only=True) should return only pending todos
    pending_todos = app.list(pending_only=True)
    assert len(pending_todos) == 2
    assert all(not todo.done for todo in pending_todos)


def test_cli_list_without_pending_flag_shows_all_todos(tmp_path, capsys) -> None:
    """Issue #2330: 'todo list' (without --pending) should show all todos."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    # Add todos - some pending, some done
    args = parser.parse_args(["--db", db, "add", "pending task"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "add", "another pending"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "done", "1"])
    assert run_command(args) == 0

    # List without --pending flag should show all todos
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out

    # Both pending and done todos should be visible
    assert "pending task" in out
    assert "another pending" in out
    # The done todo should also appear
    assert "[x]" in out or "✓" in out or "1" in out


def test_cli_list_with_pending_flag_shows_only_pending_todos(tmp_path, capsys) -> None:
    """Issue #2330: 'todo list --pending' should show only pending (not done) todos."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    # Add todos - some pending, some done
    args = parser.parse_args(["--db", db, "add", "pending task"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "add", "another pending"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "add", "done task"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "done", "1"])
    assert run_command(args) == 0

    # List with --pending flag should show only pending todos
    args = parser.parse_args(["--db", db, "list", "--pending"])
    assert run_command(args) == 0
    out = capsys.readouterr().out

    # Only pending todos should be visible
    assert "another pending" in out
    assert "done task" in out

    # Check that the done todo (id 1) is NOT in the output
    # The todo list output should contain "[ ]" for pending items and "[x]" for done
    # Count how many "[ ]" (pending) vs "[x]" (done) markers appear
    pending_markers = out.count("[ ]")
    done_markers = out.count("[x]")

    # Should have 2 pending todos and 0 done todos shown
    assert pending_markers == 2, f"Expected 2 pending todos, found {pending_markers}"
    assert done_markers == 0, f"Expected 0 done todos in --pending view, found {done_markers}"
