"""Regression tests for issue #1858: Path traversal vulnerability in TodoStorage.

Issue: Path parameter can escape intended directory via '..' components.
The TodoStorage class accepts arbitrary user-controlled paths without validation,
allowing access to files outside the intended directory.

These tests verify that paths escaping the current working directory are rejected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_path_with_double_dot_escape_is_rejected(tmp_path) -> None:
    """Issue #1858: Paths escaping CWD via '..' should be rejected.

    Attack scenario: User provides --db '../../../etc/passwd' or similar
    to access files outside the intended working directory.

    Expected behavior after fix:
    - Path is resolved and checked
    - ValueError raised if path escapes current working directory
    """
    # Create a working directory
    cwd = tmp_path / "workspace"
    cwd.mkdir()

    # Create a file outside the workspace (simulating sensitive data)
    outside_file = tmp_path / "sensitive.json"
    outside_file.write_text('["sensitive data"]')

    # Change to workspace directory
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)

        # Try to use a path with '..' to escape the workspace
        # This path would resolve to the parent's sensitive.json
        escaped_path = Path("..") / "sensitive.json"

        # After fix: Should reject paths escaping CWD
        with pytest.raises(ValueError, match=r"outside.*current working directory"):
            TodoStorage(str(escaped_path))

    finally:
        os.chdir(original_cwd)


def test_path_with_double_dot_normalized_inside_workspace(tmp_path) -> None:
    """Issue #1858: Paths with '..' that stay within CWD should work.

    Example: './subdir/../todo.json' should be normalized to './todo.json'
    and work correctly.
    """
    cwd = tmp_path / "workspace"
    cwd.mkdir()

    subdir = cwd / "subdir"
    subdir.mkdir()

    # Change to workspace as CWD
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)

        # Use a path with '..' that stays within workspace/CWD
        # subdir/../todo.json should normalize to workspace/todo.json
        path_with_double_dot = Path("subdir") / ".." / "todo.json"

        storage = TodoStorage(str(path_with_double_dot))

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Should be able to load back
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_absolute_path_outside_cwd_is_allowed(tmp_path) -> None:
    """Issue #1858: Absolute paths outside cwd are allowed (not a traversal attack).

    The path traversal vulnerability specifically concerns paths using '..' components
    to escape the intended directory. Absolute paths are explicitly specified by the
    user and don't use '..' for traversal, so they are allowed.
    """
    cwd = tmp_path / "workspace"
    cwd.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_db = outside_dir / "todo.json"

    # Change to workspace as CWD
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)

        # Absolute paths should be allowed (user explicitly specified them)
        storage = TodoStorage(str(outside_db))

        # Should be able to save/load to this absolute path
        todos = [Todo(id=1, text="absolute path test")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "absolute path test"
    finally:
        os.chdir(original_cwd)


def test_normal_relative_path_works(tmp_path) -> None:
    """Issue #1858: Normal relative paths within CWD should work fine."""
    cwd = tmp_path / "workspace"
    cwd.mkdir()

    subdir = cwd / "data"
    subdir.mkdir()

    # Change to workspace as CWD
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)

        # Normal relative path within CWD - should work
        normal_path = Path("data") / "todo.json"
        storage = TodoStorage(str(normal_path))

        todos = [Todo(id=1, text="normal path")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "normal path"
    finally:
        os.chdir(original_cwd)


def test_path_traversal_via_multiple_dots(tmp_path) -> None:
    """Issue #1858: Multiple '..' components should still be caught."""
    cwd = tmp_path / "deep" / "nested" / "workspace"
    cwd.mkdir(parents=True)

    # Create sensitive file at root
    sensitive = tmp_path / "sensitive.json"
    sensitive.write_text('["secret"]')

    # Try to escape multiple levels up
    escaped_path = cwd / ".." / ".." / ".." / "sensitive.json"

    # Should raise ValueError about path traversal
    with pytest.raises(ValueError, match=r"outside.*current working directory"):
        TodoStorage(str(escaped_path))


def test_current_directory_default_is_safe(tmp_path) -> None:
    """Issue #1858: Default path (current directory) should be safe."""
    cwd = tmp_path
    original_cwd = Path.cwd()

    try:
        # Change to temp directory
        import os
        os.chdir(cwd)

        # Default storage should use .todo.json in current directory
        storage = TodoStorage()  # No path - should default to ".todo.json"

        todos = [Todo(id=1, text="default test")]
        storage.save(todos)

        # File should be in current directory
        assert (Path.cwd() / ".todo.json").exists()

        loaded = storage.load()
        assert len(loaded) == 1
    finally:
        os.chdir(original_cwd)
