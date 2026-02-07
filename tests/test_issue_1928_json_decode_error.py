"""Regression test for issue #1928: json.loads should catch JSONDecodeError.

Issue: Invalid JSON files cause uncaught JSONDecodeError instead of friendly ValueError.
This test verifies that TodoStorage.load() properly converts JSONDecodeError to ValueError.
"""

from __future__ import annotations

import json

import pytest

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage


def test_storage_load_invalid_json_raises_valueerror(tmp_path) -> None:
    """Invalid JSON file should raise ValueError, not JSONDecodeError.

    JSONDecodeError is technically a subclass of ValueError, but we want
    to catch it explicitly and raise a proper ValueError with file context.
    """
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create invalid JSON files with different types of malformation
    invalid_json_contents = [
        "{",  # Incomplete object
        "not json",  # Plain text
        "[",  # Incomplete array
        '{"incomplete": ',  # Trailing comma-like syntax
    ]

    for invalid_content in invalid_json_contents:
        db.write_text(invalid_content, encoding="utf-8")

        # Should raise ValueError (not json.JSONDecodeError directly)
        # The error should NOT be a json.JSONDecodeError instance
        try:
            storage.load()
            raise AssertionError(f"Expected ValueError for invalid JSON: {invalid_content!r}")
        except json.JSONDecodeError as err:
            raise AssertionError(
                f"json.JSONDecodeError should be caught and converted to ValueError. "
                f"Got raw JSONDecodeError for: {invalid_content!r}"
            ) from err
        except ValueError as e:
            # Should be ValueError with file context
            assert "invalid.json" in str(e) or str(db) in str(e)


def test_storage_load_invalid_json_includes_file_context(tmp_path) -> None:
    """Error message should include the file path for debugging."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    db.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Error message should reference the file path
    error_msg = str(exc_info.value)
    assert "invalid.json" in error_msg or str(db) in error_msg


def test_cli_handles_invalid_json_gracefully(tmp_path, capsys) -> None:
    """CLI should catch ValueError from invalid JSON and return exit code 1."""
    db = tmp_path / "invalid.json"
    db_path = str(db)

    # Write invalid JSON
    db.write_text("not valid json", encoding="utf-8")

    # Try to list todos with invalid JSON file
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "list"])

    exit_code = run_command(args)
    assert exit_code == 1

    # Verify error message is printed
    out = capsys.readouterr().out
    assert "Error:" in out
