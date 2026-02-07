"""Tests for path traversal vulnerability (Issue #1883)."""

from __future__ import annotations

import tempfile

import pytest

from flywheel.storage import TodoStorage


def test_storage_rejects_path_traversal_with_parent_dotdot() -> None:
    """Path traversal with '../' should be rejected when escaping cwd."""
    with pytest.raises(ValueError, match="outside allowed directory"):
        TodoStorage("../../../etc/passwd")


def test_storage_rejects_absolute_path_outside_cwd() -> None:
    """Absolute paths outside current working directory should be rejected."""
    with pytest.raises(ValueError, match="outside allowed directory"):
        TodoStorage("/tmp/test.json")


def test_storage_rejects_symlink_pointing_outside_cwd(tmp_path) -> None:
    """Symlinks pointing outside cwd should be detected."""
    import contextlib

    # Create a temp file outside the cwd
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, dir="/tmp") as f:
        f.write('[]')
        outside_file = f.name

    try:
        # Create symlink within tmp_path pointing outside
        symlink_path = tmp_path / "escape.json"
        symlink_path.symlink_to(outside_file)

        # The symlink resolves to /tmp, which is outside cwd, so it should be rejected
        with pytest.raises(ValueError, match="outside allowed directory"):
            TodoStorage(str(symlink_path))
    finally:
        import os
        with contextlib.suppress(OSError):
            os.unlink(outside_file)


def test_storage_allows_relative_path_within_cwd() -> None:
    """Relative paths within current working directory should be allowed."""
    storage = TodoStorage(".todo.json")
    assert storage.path.name == ".todo.json"


def test_storage_rejects_absolute_path_in_subdir_of_cwd(tmp_path) -> None:
    """Absolute paths within tmp directories outside cwd should be rejected."""
    # tmp_path is /tmp/..., which is outside /home/runner/work/flywheel/flywheel (cwd)
    db_path = tmp_path / "todo.json"
    with pytest.raises(ValueError, match="outside allowed directory"):
        TodoStorage(str(db_path))


def test_storage_allows_path_within_cwd_subdir(tmp_path) -> None:
    """Paths within a subdirectory of cwd should be allowed when using relative path."""
    from pathlib import Path

    # Create a subdirectory within cwd
    subdir = Path.cwd() / "test_todo_subdir"
    subdir.mkdir(exist_ok=True)

    try:
        # Use relative path to subdirectory
        db_path = "test_todo_subdir/todo.json"
        storage = TodoStorage(db_path)
        assert storage.path == Path(db_path)
    finally:
        import shutil
        shutil.rmtree(subdir, ignore_errors=True)
