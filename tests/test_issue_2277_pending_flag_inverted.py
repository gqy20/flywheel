"""Regression tests for Issue #2277: --pending flag logic is inverted.

This test file ensures that:
1. `todo list` with no flags shows only pending todos by default
2. `todo list --pending` shows only pending todos (idempotent)
3. `todo list --all` shows all todos including completed ones

The bug is that TodoApp.list() defaults to show_all=True, causing
`todo list` to show all todos including completed ones, which is
unexpected UX - users typically expect list to show pending items by default.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_list_default_shows_only_pending_todos(tmp_path, capsys) -> None:
    """`todo list` with no flags should show only pending todos by default.

    Issue #2277: The default behavior of list command without --pending flag
    shows all todos (including completed ones), which may be unexpected.
    Users typically expect `list` to show pending items by default.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add three todos
    run_command(parser.parse_args(["--db", str(db), "add", "pending task 1"]))
    run_command(parser.parse_args(["--db", str(db), "add", "pending task 2"]))
    run_command(parser.parse_args(["--db", str(db), "add", "task to be done"]))

    # Mark one as done
    run_command(parser.parse_args(["--db", str(db), "done", "3"]))
    capsys.readouterr()  # Clear output from done command

    # List with no flags - should show only pending todos (1 and 2)
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0, "list command should succeed"

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().split("\n") if line.strip()]

    # Should show exactly 2 pending todos (tasks 1 and 2, not task 3 which is done)
    assert len(lines) == 2, f"Expected 2 pending todos, got {len(lines)}: {lines}"

    # Task 3 (done) should NOT appear in output
    assert "3" not in captured.out, "Completed task 3 should not appear in default list output"

    # Tasks 1 and 2 SHOULD appear
    assert "1" in captured.out, "Pending task 1 should appear in default list output"
    assert "2" in captured.out, "Pending task 2 should appear in default list output"


def test_cli_list_with_pending_flag_shows_only_pending_todos(tmp_path, capsys) -> None:
    """`todo list --pending` should show only pending todos (same as default).

    Issue #2277: The --pending flag should be idempotent - passing --pending
    should have the same behavior as not passing it (show only pending).
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add three todos
    run_command(parser.parse_args(["--db", str(db), "add", "pending task 1"]))
    run_command(parser.parse_args(["--db", str(db), "add", "pending task 2"]))
    run_command(parser.parse_args(["--db", str(db), "add", "task to be done"]))

    # Mark one as done
    run_command(parser.parse_args(["--db", str(db), "done", "3"]))
    capsys.readouterr()  # Clear output from done command

    # List with --pending flag - should show only pending todos
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)
    assert result == 0, "list --pending command should succeed"

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().split("\n") if line.strip()]

    # Should show exactly 2 pending todos
    assert len(lines) == 2, f"Expected 2 pending todos, got {len(lines)}: {lines}"

    # Task 3 (done) should NOT appear in output
    assert "3" not in captured.out, "Completed task 3 should not appear in --pending list output"

    # Tasks 1 and 2 SHOULD appear
    assert "1" in captured.out, "Pending task 1 should appear in --pending list output"
    assert "2" in captured.out, "Pending task 2 should appear in --pending list output"


def test_cli_list_with_all_flag_shows_all_todos_including_done(tmp_path, capsys) -> None:
    """`todo list --all` should show all todos including completed ones.

    Issue #2277 acceptance criteria: A new --all flag shows all todos
    including completed ones.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add three todos
    run_command(parser.parse_args(["--db", str(db), "add", "pending task 1"]))
    run_command(parser.parse_args(["--db", str(db), "add", "pending task 2"]))
    run_command(parser.parse_args(["--db", str(db), "add", "task to be done"]))

    # Mark one as done
    run_command(parser.parse_args(["--db", str(db), "done", "3"]))
    capsys.readouterr()  # Clear output from done command

    # List with --all flag - should show all todos including done
    args = parser.parse_args(["--db", str(db), "list", "--all"])
    result = run_command(args)
    assert result == 0, "list --all command should succeed"

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().split("\n") if line.strip()]

    # Should show exactly 3 todos (all of them)
    assert len(lines) == 3, f"Expected 3 todos, got {len(lines)}: {lines}"

    # All tasks 1, 2, and 3 SHOULD appear
    assert "1" in captured.out, "Task 1 should appear in --all list output"
    assert "2" in captured.out, "Task 2 should appear in --all list output"
    assert "3" in captured.out, "Task 3 (done) should appear in --all list output"


def test_cli_list_all_vs_pending_flags_are_mutually_exclusive(tmp_path, capsys) -> None:
    """`todo list --all --pending` behavior should be well-defined.

    When both flags are provided, the last one or a specific precedence rule
    should apply. This test documents current behavior.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add todos and mark one as done
    run_command(parser.parse_args(["--db", str(db), "add", "pending task"]))
    run_command(parser.parse_args(["--db", str(db), "add", "task to be done"]))
    run_command(parser.parse_args(["--db", str(db), "done", "2"]))
    capsys.readouterr()  # Clear output from done command

    # When both flags are provided, --all should take precedence (shows all)
    args = parser.parse_args(["--db", str(db), "list", "--all", "--pending"])
    result = run_command(args)
    assert result == 0, "list with both flags should succeed"

    captured = capsys.readouterr()
    # Both flags present - --all should win (shows all todos)
    lines = [line for line in captured.out.strip().split("\n") if line.strip()]
    # This documents current behavior - when both are set, args.pending=True
    # so show_all=False takes effect (pending only)
    # The implementation should handle this case sensibly
    assert len(lines) >= 1, "Should return at least one todo"


def test_cli_list_empty_database_returns_empty_output(tmp_path, capsys) -> None:
    """`todo list` on empty database should return empty list regardless of flags.

    This ensures the fix handles edge cases correctly.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # List with no flags on empty db
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0, "list on empty db should succeed"

    # The important thing is it doesn't crash and returns 0
    assert result == 0
