"""Regression tests for issue #1883: Path traversal vulnerability via user-controlled db_path.

Issue: The --db CLI argument accepts arbitrary paths including '../' sequences and
absolute paths, allowing attackers to read/write files outside the intended directory.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.cli import _validate_cli_db_path
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_path_traversal_with_dot_dot_slash_rejected(tmp_path) -> None:
    """Issue #1883: Path with '../' sequences should be rejected.

    Before fix: Accepts '../../../etc/passwd' and reads arbitrary system files
    After fix: Should raise ValueError with security message
    """
    # Try to use path traversal to escape the working directory
    malicious_path = "../../../etc/passwd"

    # Should raise ValueError when trying to create storage with malicious path
    with pytest.raises(ValueError, match=r"(security|unsafe|outside|allowed|path)"):
        storage = TodoStorage(malicious_path)
        # Try to trigger the validation by calling load/save
        storage.load()


def test_multiple_dot_dot_slash_components_rejected(tmp_path) -> None:
    """Issue #1883: Multiple '../' components should be rejected."""
    malicious_path = "../../../../../../tmp/test"

    with pytest.raises(ValueError, match=r"(security|unsafe|outside|allowed|path)"):
        storage = TodoStorage(malicious_path)
        storage.load()


def test_absolute_path_outside_cwd_rejected(tmp_path, monkeypatch) -> None:
    """Issue #1883: Absolute paths outside current working directory should be rejected via CLI.

    Before fix: Accepts '/tmp/test.json' which could be used to write arbitrary files
    After fix: Should raise ValueError for absolute paths outside allowed directory

    Note: This tests the CLI validation (_validate_cli_db_path) which is the security
    boundary for user input. TodoStorage itself allows absolute paths for programmatic use.
    """
    # Use /tmp path as it's almost always outside project directory
    malicious_path = "/tmp/flywheel_test_1883.json"

    # The CLI validation should reject absolute paths outside cwd
    with pytest.raises(ValueError, match=r"(security|unsafe|outside|allowed|path|unauthorized)"):
        _validate_cli_db_path(malicious_path)


def test_relative_path_within_cwd_accepted(tmp_path, monkeypatch) -> None:
    """Issue #1883: Safe relative paths within current directory should still work."""
    # Change to tmp_path for this test
    monkeypatch.chdir(tmp_path)

    # Safe relative path - should work
    safe_path = "subdir/todo.json"
    storage = TodoStorage(safe_path)

    # Should be able to save and load without errors
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_nested_subdirectory_within_cwd_accepted(tmp_path, monkeypatch) -> None:
    """Issue #1883: Nested subdirectories within cwd should work."""
    monkeypatch.chdir(tmp_path)

    # Safe nested path
    safe_path = "a/b/c/d/todo.json"
    storage = TodoStorage(safe_path)

    todos = [Todo(id=1, text="nested todo")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "nested todo"


def test_current_directory_file_accepted(tmp_path, monkeypatch) -> None:
    """Issue #1883: Simple filename in current directory should work."""
    monkeypatch.chdir(tmp_path)

    storage = TodoStorage("simple.json")
    todos = [Todo(id=1, text="simple")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "simple"


def test_dot_slash_prefix_accepted(tmp_path, monkeypatch) -> None:
    """Issue #1883: Path with './' prefix within cwd should work."""
    monkeypatch.chdir(tmp_path)

    storage = TodoStorage("./local.json")
    todos = [Todo(id=1, text="local")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1


def test_symlink_outside_cwd_rejected(tmp_path, monkeypatch) -> None:
    """Issue #1883: Symlinks pointing outside allowed directory should be detected and rejected.

    Before fix: Resolves symlink and allows access to files outside cwd
    After fix: Should detect that resolved path escapes cwd and raise ValueError
    """
    # Create a file outside the "allowed" directory
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "target.json"

    # Create a directory that will be our "cwd"
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()

    # Create symlink inside cwd pointing outside
    symlink_path = cwd_dir / "escape.json"
    symlink_path.symlink_to(outside_file)

    # Change to the cwd directory
    monkeypatch.chdir(cwd_dir)

    # The symlink should be rejected because it points outside cwd
    with pytest.raises(ValueError, match=r"(security|unsafe|outside|allowed|path|symlink)"):
        storage = TodoStorage("escape.json")
        storage.load()


def test_complex_path_traversal_rejected(tmp_path) -> None:
    """Issue #1883: Complex path traversal patterns should be rejected."""
    # Various traversal patterns that should all be rejected
    malicious_patterns = [
        "./../../etc/passwd",
        "....//....//etc/passwd",
        "/etc/passwd/../shadow",
        "..\\..\\..\\windows\\system32",  # Windows-style traversal
    ]

    for pattern in malicious_patterns:
        with pytest.raises(ValueError, match=r"(security|unsafe|outside|allowed|path)"):
            storage = TodoStorage(pattern)
            storage.load()


def test_empty_path_uses_safe_default(tmp_path, monkeypatch) -> None:
    """Issue #1883: Empty/None path should use default '.todo.json' in cwd."""
    monkeypatch.chdir(tmp_path)

    # No path provided - should use safe default
    storage = TodoStorage()
    todos = [Todo(id=1, text="default")]
    storage.save(todos)

    # Should create .todo.json in current directory
    assert (Path.cwd() / ".todo.json").exists()

    loaded = storage.load()
    assert len(loaded) == 1


def test_save_with_validated_path_succeeds(tmp_path, monkeypatch) -> None:
    """Issue #1883: Save operation should work normally with validated paths."""
    monkeypatch.chdir(tmp_path)

    storage = TodoStorage("safe_db.json")

    # Multiple save/load cycles should work
    for i in range(3):
        todos = [Todo(id=j, text=f"todo {i}-{j}") for j in range(5)]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 5
