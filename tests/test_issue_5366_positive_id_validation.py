"""Regression tests for Issue #5366: Negative or zero IDs accepted by argparse.

This test file ensures that CLI commands reject negative or zero IDs with
clear error messages before storage lookup, since Todo IDs are positive
integers (starting from 1 per storage.next_id).

Acceptance criteria:
- CLI rejects negative or zero IDs with clear error message before storage lookup
- Positive IDs still work as expected
"""

from __future__ import annotations

from flywheel.cli import main


def test_cli_done_rejects_negative_id(capsys) -> None:
    """'todo done -1' should show clear error message about positive ID."""
    result = main(["done", "-1"])
    assert result == 1, "main should return 1 for negative ID"

    captured = capsys.readouterr()
    # Should show error about ID being positive, not just "not found"
    assert "positive" in captured.err.lower() or "positive" in captured.out.lower()


def test_cli_done_rejects_zero_id(capsys) -> None:
    """'todo done 0' should show clear error message about positive ID."""
    result = main(["done", "0"])
    assert result == 1, "main should return 1 for zero ID"

    captured = capsys.readouterr()
    # Should show error about ID being positive, not just "not found"
    assert "positive" in captured.err.lower() or "positive" in captured.out.lower()


def test_cli_undone_rejects_negative_id(capsys) -> None:
    """'todo undone -1' should show clear error message about positive ID."""
    result = main(["undone", "-1"])
    assert result == 1, "main should return 1 for negative ID"

    captured = capsys.readouterr()
    assert "positive" in captured.err.lower() or "positive" in captured.out.lower()


def test_cli_undone_rejects_zero_id(capsys) -> None:
    """'todo undone 0' should show clear error message about positive ID."""
    result = main(["undone", "0"])
    assert result == 1, "main should return 1 for zero ID"

    captured = capsys.readouterr()
    assert "positive" in captured.err.lower() or "positive" in captured.out.lower()


def test_cli_rm_rejects_negative_id(capsys) -> None:
    """'todo rm -1' should show clear error message about positive ID."""
    result = main(["rm", "-1"])
    assert result == 1, "main should return 1 for negative ID"

    captured = capsys.readouterr()
    assert "positive" in captured.err.lower() or "positive" in captured.out.lower()


def test_cli_rm_rejects_zero_id(capsys) -> None:
    """'todo rm 0' should show clear error message about positive ID."""
    result = main(["rm", "0"])
    assert result == 1, "main should return 1 for zero ID"

    captured = capsys.readouterr()
    assert "positive" in captured.err.lower() or "positive" in captured.out.lower()


def test_cli_done_positive_id_works(tmp_path, capsys) -> None:
    """'todo done 1' should still work for valid positive IDs."""
    import os

    db = tmp_path / "test.json"
    os.chdir(tmp_path)

    # First add a todo
    result = main(["--db", str(db), "add", "test todo"])
    assert result == 0

    # Then mark it done - should work
    result = main(["--db", str(db), "done", "1"])
    assert result == 0, "main should return 0 for valid positive ID"

    captured = capsys.readouterr()
    assert "done" in captured.out.lower()
