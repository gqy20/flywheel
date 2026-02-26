"""Regression tests for Issue #5856: run_command() unreachable code path.

This test file ensures that the unreachable code path at line 123
(raise ValueError for unsupported command) is properly handled.

Since argparse is configured with required=True for subparsers,
this code path is unreachable - argparse will block invalid commands
before run_command() is ever called.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_argparse_blocks_invalid_command() -> None:
    """argparse should block invalid commands before run_command is called.

    The subparsers are configured with required=True, so argparse will
    raise SystemExit (exit with error message) if an invalid command is passed.
    """
    parser = build_parser()

    # Invalid command should cause argparse to raise SystemExit
    try:
        parser.parse_args(["invalid_command"])
        raise AssertionError("argparse should have raised SystemExit for invalid command")
    except SystemExit:
        # Expected behavior - argparse blocks invalid commands
        pass


def test_argparse_requires_command() -> None:
    """argparse should require a command when subparsers are required."""
    parser = build_parser()

    # No command should cause argparse to raise SystemExit
    try:
        parser.parse_args([])
        raise AssertionError("argparse should have raised SystemExit for missing command")
    except SystemExit:
        # Expected behavior - argparse requires a command
        pass


def test_valid_commands_work_correctly(tmp_path) -> None:
    """All defined commands should work correctly through run_command."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Test 'add' command
    args = parser.parse_args(["--db", str(db), "add", "test todo"])
    result = run_command(args)
    assert result == 0, "add command should succeed"

    # Test 'list' command
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0, "list command should succeed"

    # Test 'done' command
    args = parser.parse_args(["--db", str(db), "done", "1"])
    result = run_command(args)
    assert result == 0, "done command should succeed"

    # Test 'undone' command
    args = parser.parse_args(["--db", str(db), "undone", "1"])
    result = run_command(args)
    assert result == 0, "undone command should succeed"

    # Test 'rm' command
    args = parser.parse_args(["--db", str(db), "rm", "1"])
    result = run_command(args)
    assert result == 0, "rm command should succeed"


def test_unreachable_code_path_needs_assertion_error() -> None:
    """Verify the unreachable code path uses AssertionError, not ValueError.

    This is a code structure test to ensure the fix from Issue #5856
    is in place. The code path for unknown commands should use
    `raise AssertionError` to indicate it's unreachable, not `raise ValueError`
    which suggests a recoverable error condition.
    """
    import ast
    import inspect

    from flywheel.cli import run_command

    source = inspect.getsource(run_command)
    tree = ast.parse(source)

    # Find Raise nodes that raise AssertionError (for unreachable code marker)
    raise_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            raise_nodes.append(node)

    # Verify there's a `raise AssertionError(...)` pattern marking unreachable code
    has_unreachable_marker = False
    for raise_node in raise_nodes:
        if (
            isinstance(raise_node.exc, ast.Call)
            and isinstance(raise_node.exc.func, ast.Name)
            and raise_node.exc.func.id == "AssertionError"
        ):
            has_unreachable_marker = True
            break

    assert has_unreachable_marker, (
        "Expected `raise AssertionError` pattern to mark unreachable code path. "
        "This indicates to maintainers that the code is intentionally unreachable."
    )

    # Also verify there are no `raise ValueError` patterns for unsupported commands
    for raise_node in raise_nodes:
        if (
            isinstance(raise_node.exc, ast.Call)
            and isinstance(raise_node.exc.func, ast.Name)
            and raise_node.exc.func.id == "ValueError"
            and raise_node.exc.args
        ):
            arg = raise_node.exc.args[0]
            if isinstance(arg, ast.JoinedStr):
                for value in arg.values:
                    if isinstance(value, ast.Constant) and "Unsupported command" in str(
                        value.value
                    ):
                        raise AssertionError(
                            "Found `raise ValueError` for unsupported command. "
                            "This code path is unreachable and should use "
                            "`raise AssertionError` or be removed."
                        )
            elif isinstance(arg, ast.Constant):
                msg = arg.value
                if "Unsupported command" in str(msg):
                    raise AssertionError(
                        "Found `raise ValueError` for unsupported command. "
                        "This code path is unreachable and should use "
                        "`raise AssertionError` or be removed."
                    )
