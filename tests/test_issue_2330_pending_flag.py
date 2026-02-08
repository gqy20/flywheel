"""Regression test for issue #2330: --pending flag semantics.

Issue: list command's --pending flag uses confusing double negative logic.
Expected behavior:
- Without --pending: show all todos (completed and pending)
- With --pending: show only pending (not done) todos
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command


def test_list_default_shows_all_todos(tmp_path, capsys) -> None:
    """Without --pending flag, list should show both completed and pending todos."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    # Add two todos
    args = parser.parse_args(["--db", db, "add", "task1"])
    run_command(args)

    args = parser.parse_args(["--db", db, "add", "task2"])
    run_command(args)

    # Mark first todo as done
    args = parser.parse_args(["--db", db, "done", "1"])
    run_command(args)

    # Clear captured output before the list command
    capsys.readouterr()

    # List without --pending should show both todos
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out

    # Both completed and pending todos should be shown
    assert "[x]" in out  # Completed todo
    assert "[ ]" in out  # Pending todo
    assert "task1" in out
    assert "task2" in out


def test_list_with_pending_shows_only_pending_todos(tmp_path, capsys) -> None:
    """With --pending flag, list should show only pending (not done) todos."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    # Add two todos
    args = parser.parse_args(["--db", db, "add", "task1"])
    run_command(args)

    args = parser.parse_args(["--db", db, "add", "task2"])
    run_command(args)

    # Mark first todo as done
    args = parser.parse_args(["--db", db, "done", "1"])
    run_command(args)

    # Clear captured output before the list command
    capsys.readouterr()

    # List with --pending should show only pending todos
    args = parser.parse_args(["--db", db, "list", "--pending"])
    assert run_command(args) == 0
    out = capsys.readouterr().out

    # Only pending todo should be shown
    assert "[x]" not in out  # Completed todo should NOT be shown
    assert "[ ]" in out  # Pending todo should be shown
    assert "task1" not in out  # Completed task
    assert "task2" in out  # Pending task
