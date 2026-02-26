"""Regression tests for Issue #5856: run_command() unreachable ValueError branch.

The ValueError at cli.py:123 is theoretically unreachable because argparse
is configured with required=True on subparsers, guaranteeing that args.command
is always one of the valid subcommands when run_command() is called.

This test documents the expected behavior that this branch should be
marked as unreachable (assert False) or removed.
"""

from __future__ import annotations

import argparse

import pytest

from flywheel.cli import build_parser, run_command


class TestUnreachableCommandBranch:
    """Tests documenting the unreachable ValueError branch in run_command()."""

    def test_argparse_rejects_unknown_command(self) -> None:
        """argparse with required=True should reject unknown commands before run_command."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            # This will raise SystemExit (argparse error), not reach run_command
            parser.parse_args(["unknown_command"])

    def test_argparse_requires_subcommand(self) -> None:
        """argparse with required=True should require a subcommand."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            # No subcommand provided - argparse should error
            parser.parse_args([])

    def test_valid_commands_are_accepted(self, tmp_path) -> None:
        """All defined subcommands should be accepted by argparse."""
        parser = build_parser()
        db_path = str(tmp_path / "test.json")

        # All valid commands should parse without error
        valid_commands = [
            ["--db", db_path, "add", "test todo"],
            ["--db", db_path, "list"],
            ["--db", db_path, "list", "--pending"],
            ["--db", db_path, "done", "1"],
            ["--db", db_path, "undone", "1"],
            ["--db", db_path, "rm", "1"],
        ]

        for cmd in valid_commands:
            args = parser.parse_args(cmd)
            assert args.command in {"add", "list", "done", "undone", "rm"}

    def test_run_command_needs_no_else_branch(self, tmp_path, capsys) -> None:
        """run_command should handle all valid commands without reaching ValueError.

        This test verifies that the final else/ValueError branch in run_command
        is unreachable when called via the normal argparse flow.
        """
        parser = build_parser()
        db_path = str(tmp_path / "test.json")

        # First add a todo
        args = parser.parse_args(["--db", db_path, "add", "test"])
        result = run_command(args)
        assert result == 0

        # Verify all commands work without hitting the ValueError branch
        commands = [
            ["--db", db_path, "list"],
            ["--db", db_path, "done", "1"],
            ["--db", db_path, "undone", "1"],
            ["--db", db_path, "rm", "1"],
        ]

        for cmd in commands:
            args = parser.parse_args(cmd)
            result = run_command(args)
            assert result == 0

    def test_unreachable_branch_is_assertion_not_valueerror(
        self, tmp_path
    ) -> None:
        """The unreachable branch should raise AssertionError, not ValueError.

        Since argparse guarantees a valid command, the final else branch
        represents a programming error (invariant violation), which should
        be signaled via assert False rather than ValueError.

        This test simulates reaching the unreachable branch to verify
        the expected behavior after the fix.
        """
        db_path = str(tmp_path / "test.json")

        # Create a namespace with an invalid command
        # This simulates what would happen if someone bypassed argparse
        args = argparse.Namespace(db=db_path, command="invalid_command")

        # After the fix, this should raise AssertionError, not ValueError
        with pytest.raises(AssertionError):
            run_command(args)
