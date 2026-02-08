"""Regression tests for Issue #2277: The --pending flag logic is inverted.

The core issue is that TodoApp.list() defaults to show_all=True, which means:
1. `todo list` shows all todos including completed (unexpected UX)
2. `todo list --pending` shows only pending (correct, but idempotent)

Expected behavior:
- `todo list` should show only pending todos by default
- `todo list --pending` should also show only pending todos (idempotent)
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_cli_list_default_shows_only_pending(tmp_path, capsys) -> None:
    """`todo list` without flags should show only pending todos by default.

    This is the core issue #2277: users expect the default list command
    to show only pending items, not all items including completed ones.
    """
    db = tmp_path / "db.json"
    storage = TodoStorage(str(db))

    # Create todos: 2 pending, 2 done
    pending_1 = Todo(id=1, text="Pending task 1")
    pending_2 = Todo(id=2, text="Pending task 2")
    done_1 = Todo(id=3, text="Done task 1")
    done_1.mark_done()
    done_2 = Todo(id=4, text="Done task 2")
    done_2.mark_done()

    storage.save([pending_1, pending_2, done_1, done_2])

    # Run list without --pending flag
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)

    assert result == 0, "list command should succeed"

    captured = capsys.readouterr()
    output = captured.out

    # Should show pending todos
    assert "Pending task 1" in output
    assert "Pending task 2" in output

    # Should NOT show completed todos
    assert "Done task 1" not in output
    assert "Done task 2" not in output

    # Only 2 items should be shown (the pending ones)
    lines = [line for line in output.split("\n") if line.strip()]
    assert len(lines) == 2, f"Expected 2 pending todos, got {len(lines)} lines"


def test_cli_list_with_pending_flag_shows_only_pending(tmp_path, capsys) -> None:
    """`todo list --pending` should show only pending todos.

    This should be idempotent with the default behavior after the fix.
    """
    db = tmp_path / "db.json"
    storage = TodoStorage(str(db))

    # Create todos: 2 pending, 2 done
    pending_1 = Todo(id=1, text="Pending task 1")
    pending_2 = Todo(id=2, text="Pending task 2")
    done_1 = Todo(id=3, text="Done task 1")
    done_1.mark_done()
    done_2 = Todo(id=4, text="Done task 2")
    done_2.mark_done()

    storage.save([pending_1, pending_2, done_1, done_2])

    # Run list with --pending flag
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)

    assert result == 0, "list command should succeed"

    captured = capsys.readouterr()
    output = captured.out

    # Should show pending todos
    assert "Pending task 1" in output
    assert "Pending task 2" in output

    # Should NOT show completed todos
    assert "Done task 1" not in output
    assert "Done task 2" not in output

    # Only 2 items should be shown (the pending ones)
    lines = [line for line in output.split("\n") if line.strip()]
    assert len(lines) == 2, f"Expected 2 pending todos, got {len(lines)} lines"


def test_cli_list_empty_database(tmp_path, capsys) -> None:
    """`todo list` on empty database should show 'No todos yet.' message."""
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)

    assert result == 0, "list command should succeed"

    captured = capsys.readouterr()
    assert "No todos yet" in captured.out


def test_cli_list_all_completed_todos(tmp_path, capsys) -> None:
    """`todo list` when all todos are done should show empty message."""
    db = tmp_path / "db.json"
    storage = TodoStorage(str(db))

    # Create only completed todos
    done_1 = Todo(id=1, text="Done task 1")
    done_1.mark_done()
    done_2 = Todo(id=2, text="Done task 2")
    done_2.mark_done()

    storage.save([done_1, done_2])

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)

    assert result == 0, "list command should succeed"

    captured = capsys.readouterr()
    # Should show empty message since no pending todos exist
    assert "No todos yet" in captured.out
    assert "Done task" not in captured.out
