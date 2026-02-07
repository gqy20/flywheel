"""Regression tests for Issue #2084: CLI output sanitization for add/done/undone commands.

This test file ensures that CLI commands (add, done, undone) properly sanitize
todo.text output to prevent terminal control character injection.
"""

from __future__ import annotations

import io
import sys

from flywheel.cli import TodoApp, run_command


def test_run_command_add_escapes_newline(tmp_path) -> None:
    """run_command for 'add' should escape \\n in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    args = argparse.Namespace(
        command="add",
        text="Buy milk\n[ ] FAKE",
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\n" in output, f"Expected '\\n' in output, got: {output!r}"
    # Should not contain actual newline in output (single line)
    assert output.count("\n") <= 1, f"Expected at most 1 newline, got {output.count(chr(10))}"


def test_run_command_add_escapes_carriage_return(tmp_path) -> None:
    """run_command for 'add' should escape \\r in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    args = argparse.Namespace(
        command="add",
        text="Task\r[ ] FAKE",
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\r" in output, f"Expected '\\r' in output, got: {output!r}"
    # Should not contain actual carriage return
    assert "\r" not in output, f"Output contains actual \\r character: {output!r}"


def test_run_command_add_escapes_tab(tmp_path) -> None:
    """run_command for 'add' should escape \\t in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    args = argparse.Namespace(
        command="add",
        text="Task\twith\ttabs",
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\t" in output, f"Expected '\\t' in output, got: {output!r}"
    # Should not contain actual tab character
    assert "\t" not in output, f"Output contains actual \\t character: {output!r}"


def test_run_command_add_escapes_ansi_codes(tmp_path) -> None:
    """run_command for 'add' should escape ANSI escape sequences."""
    import argparse

    db_path = tmp_path / "test.json"

    args = argparse.Namespace(
        command="add",
        text="\x1b[31mRed Text\x1b[0m Normal",
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\x1b" in output, f"Expected '\\x1b' in output, got: {output!r}"
    # Should not contain actual ESC character
    assert "\x1b" not in output, f"Output contains actual ESC character: {output!r}"


def test_run_command_done_escapes_newline(tmp_path) -> None:
    """run_command for 'done' should escape \\n in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    # First add a todo
    app = TodoApp(db_path=str(db_path))
    todo = app.add("Buy milk\n[ ] FAKE")

    args = argparse.Namespace(
        command="done",
        id=todo.id,
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\n" in output, f"Expected '\\n' in output, got: {output!r}"
    # Should not contain actual newline in output (single line)
    assert output.count("\n") <= 1, f"Expected at most 1 newline, got {output.count(chr(10))}"


def test_run_command_done_escapes_carriage_return(tmp_path) -> None:
    """run_command for 'done' should escape \\r in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    app = TodoApp(db_path=str(db_path))
    todo = app.add("Task\r[ ] FAKE")

    args = argparse.Namespace(
        command="done",
        id=todo.id,
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\r" in output, f"Expected '\\r' in output, got: {output!r}"
    # Should not contain actual carriage return
    assert "\r" not in output, f"Output contains actual \\r character: {output!r}"


def test_run_command_done_escapes_tab(tmp_path) -> None:
    """run_command for 'done' should escape \\t in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    app = TodoApp(db_path=str(db_path))
    todo = app.add("Task\twith\ttabs")

    args = argparse.Namespace(
        command="done",
        id=todo.id,
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\t" in output, f"Expected '\\t' in output, got: {output!r}"
    # Should not contain actual tab character
    assert "\t" not in output, f"Output contains actual \\t character: {output!r}"


def test_run_command_undone_escapes_newline(tmp_path) -> None:
    """run_command for 'undone' should escape \\n in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    # First add and mark done a todo
    app = TodoApp(db_path=str(db_path))
    todo = app.add("Buy milk\n[ ] FAKE")
    app.mark_done(todo.id)

    args = argparse.Namespace(
        command="undone",
        id=todo.id,
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\n" in output, f"Expected '\\n' in output, got: {output!r}"
    # Should not contain actual newline in output (single line)
    assert output.count("\n") <= 1, f"Expected at most 1 newline, got {output.count(chr(10))}"


def test_run_command_undone_escapes_carriage_return(tmp_path) -> None:
    """run_command for 'undone' should escape \\r in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    app = TodoApp(db_path=str(db_path))
    todo = app.add("Task\r[ ] FAKE")
    app.mark_done(todo.id)

    args = argparse.Namespace(
        command="undone",
        id=todo.id,
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\r" in output, f"Expected '\\r' in output, got: {output!r}"
    # Should not contain actual carriage return
    assert "\r" not in output, f"Output contains actual \\r character: {output!r}"


def test_run_command_undone_escapes_tab(tmp_path) -> None:
    """run_command for 'undone' should escape \\t in todo text."""
    import argparse

    db_path = tmp_path / "test.json"

    app = TodoApp(db_path=str(db_path))
    todo = app.add("Task\twith\ttabs")
    app.mark_done(todo.id)

    args = argparse.Namespace(
        command="undone",
        id=todo.id,
        db=str(db_path)
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        run_command(args)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Should contain escaped representation
    assert "\\t" in output, f"Expected '\\t' in output, got: {output!r}"
    # Should not contain actual tab character
    assert "\t" not in output, f"Output contains actual \\t character: {output!r}"
