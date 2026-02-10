"""Regression tests for issue #1908: Path traversal vulnerability in TodoStorage.

Issue: TodoStorage accepts any path string including '../' sequences, allowing
writes outside the intended working directory.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_rejects_path_traversal_with_parent_dot_dot() -> None:
    """Issue #1908: TodoStorage should reject paths containing '../' sequences.

    Before fix: TodoStorage('../../../tmp/evil.json') allows writes outside working dir
    After fix: TodoStorage should raise ValueError for paths with '..'
    """
    # Try to create storage with path traversal
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("../../../tmp/evil.json")


def test_storage_rejects_parent_directory_reference() -> None:
    """Issue #1908: Direct '..' reference should be rejected."""
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("..")


def test_storage_rejects_mixed_path_traversal() -> None:
    """Issue #1908: Mixed paths with '..' should be rejected."""
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("subdir/../../etc/passwd")


def test_storage_allows_safe_relative_paths() -> None:
    """Issue #1908: Safe relative paths without '..' should still work."""
    # These paths should be allowed - they don't contain '..'
    storage1 = TodoStorage(".todo.json")
    assert storage1.path == Path(".todo.json")

    storage2 = TodoStorage("data/todos.json")
    assert storage2.path == Path("data/todos.json")

    storage3 = TodoStorage("./subdir/.todo.json")
    assert storage3.path == Path("./subdir/.todo.json")


def test_storage_allows_absolute_paths(tmp_path) -> None:
    """Issue #1908: Absolute paths should be allowed (legitimate use case).

    The security concern is specifically about path traversal via '..',
    not about absolute paths which users may legitimately need.
    """
    # Absolute paths to tmp directories are commonly used in tests
    # and potentially by users who want to specify an exact location
    abs_path = tmp_path / "todo.json"

    storage = TodoStorage(str(abs_path))
    assert storage.path == abs_path

    # Basic save should work
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify it worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_storage_save_and_load_with_valid_path(tmp_path) -> None:
    """Issue #1908: Normal operations should work with valid paths."""
    storage = TodoStorage(str(tmp_path / "todos.json"))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]

    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True
