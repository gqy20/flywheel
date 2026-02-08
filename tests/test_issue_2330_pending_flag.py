"""Regression tests for Issue #2330: list command --pending flag semantics.

This test file ensures that the --pending flag works correctly:
- Without --pending: show all todos (done and not done)
- With --pending: show only pending/not-done todos
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_list_without_pending_shows_all_todos(tmp_path, capsys) -> None:
    """list command without --pending should show all todos.

    Acceptance criteria:
    - 不带 --pending 参数时，list 命令显示全部 todos（已完成和未完成）
    """
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add 3 todos
    args = parser.parse_args(["--db", str(db), "add", "todo1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "todo2"])
    run_command(args)
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "todo3"])
    run_command(args)

    # Mark todo2 as done
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # Clear buffer from previous commands
    capsys.readouterr()

    # List without --pending (default behavior)
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)

    assert result == 0, "list command should return 0"
    captured = capsys.readouterr()

    # Should show all 3 todos
    output = captured.out
    assert "todo1" in output
    assert "todo2" in output
    assert "todo3" in output

    # Verify todo2 is marked as done
    assert "[x]" in output or "[X]" in output or "[✓]" in output


def test_list_with_pending_shows_only_pending_todos(tmp_path, capsys) -> None:
    """list command with --pending should show only pending todos.

    Acceptance criteria:
    - 带 --pending 参数时，list 命令只显示未完成的 todos（done=False）
    """
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add 3 todos
    args = parser.parse_args(["--db", str(db), "add", "todo1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "todo2"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "todo3"])
    run_command(args)

    # Mark todo2 as done
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # Clear buffer from previous commands
    capsys.readouterr()

    # List with --pending flag
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)

    assert result == 0, "list --pending command should return 0"
    captured = capsys.readouterr()

    # Should show only pending todos (1 and 3)
    output = captured.out
    assert "todo1" in output
    assert "todo3" in output

    # Should NOT show completed todo (todo2)
    assert "todo2" not in output


def test_list_all_done_with_pending_shows_none(tmp_path, capsys) -> None:
    """list --pending with all todos done should show empty list."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add 2 todos and mark both as done
    args = parser.parse_args(["--db", str(db), "add", "done1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "done2"])
    run_command(args)

    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # Clear buffer from previous commands
    capsys.readouterr()

    # List with --pending flag
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)

    assert result == 0, "list --pending command should return 0"
    captured = capsys.readouterr()

    # Should show empty list
    output = captured.out.strip()
    assert output == "" or "no todos" in output.lower()


def test_list_all_pending_with_pending_shows_all(tmp_path, capsys) -> None:
    """list --pending with all todos pending should show all."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add 2 todos (none done)
    args = parser.parse_args(["--db", str(db), "add", "pending1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "pending2"])
    run_command(args)

    # Clear buffer from previous commands
    capsys.readouterr()

    # List with --pending flag
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)

    assert result == 0, "list --pending command should return 0"
    captured = capsys.readouterr()

    # Should show both todos
    output = captured.out
    assert "pending1" in output
    assert "pending2" in output
