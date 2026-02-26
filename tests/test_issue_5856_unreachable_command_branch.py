"""Regression tests for Issue #5856: Unreachable command branch should raise AssertionError.

The run_command() function has a dead code branch that raises ValueError
for "unsupported command", but argparse with required=True guarantees
the command is always valid. This branch is unreachable and should be
marked with raise AssertionError() to avoid confusing maintainers.
"""

from __future__ import annotations

import ast
import inspect

from flywheel.cli import run_command


def test_unreachable_command_branch_uses_assertion_error() -> None:
    """The final else branch in run_command should raise AssertionError.

    Since argparse guarantees valid commands via required=True, the
    "unsupported command" branch is unreachable. It should use
    raise AssertionError() to clearly indicate unreachable code, rather than
    raise ValueError which suggests a recoverable error.
    """
    source = inspect.getsource(run_command)

    # Parse the source to find raise statements
    tree = ast.parse(source)

    # Look for any raise ValueError with "Unsupported command" message
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            func = node.exc.func
            if isinstance(func, ast.Name) and func.id == "ValueError":
                for arg in node.exc.args:
                    if isinstance(arg, ast.JoinedStr):
                        for value in arg.values:
                            if isinstance(value, ast.Constant) and "Unsupported command" in str(
                                value.value
                            ):
                                raise AssertionError(
                                    "run_command() should use 'raise AssertionError' "
                                    "instead of 'raise ValueError' for unreachable "
                                    "command branch. This code path is unreachable "
                                    "because argparse guarantees valid commands."
                                )


def test_all_registered_commands_are_handled() -> None:
    """Verify all registered subcommands are handled in run_command.

    This ensures the if/elif chain covers all possible commands,
    making the final branch truly unreachable.
    """
    from flywheel.cli import build_parser

    parser = build_parser()

    # Get registered subcommands from argparse
    registered_commands = set()
    for action in parser._subparsers._actions:
        if hasattr(action, "choices") and action.choices is not None:
            registered_commands.update(action.choices.keys())

    # Commands handled in run_command
    handled_commands = {"add", "list", "done", "undone", "rm"}

    # All registered commands must be handled
    unhandled = registered_commands - handled_commands
    assert not unhandled, f"Commands {unhandled} are registered but not handled in run_command"

    # All handled commands must be registered
    extra = handled_commands - registered_commands
    assert not extra, f"Commands {extra} are handled but not registered in argparse"
