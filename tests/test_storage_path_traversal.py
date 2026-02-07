"""Tests for path traversal vulnerability in TodoStorage."""

import pytest

from flywheel.storage import TodoStorage


def test_todostorage_rejects_parent_directory_traversal():
    """Test that TodoStorage rejects paths containing '../' for directory traversal."""
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("../../../etc/passwd")


def test_todostorage_rejects_single_parent_directory():
    """Test that TodoStorage rejects paths with single '..' component."""
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("../etc/passwd")


def test_todostorage_rejects_mixed_traversal():
    """Test that TodoStorage rejects paths with mixed traversal patterns."""
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("subdir/../../etc/passwd")
    with pytest.raises(ValueError, match="Path traversal"):
        TodoStorage("./../etc/passwd")


def test_todostorage_allows_safe_relative_paths():
    """Test that TodoStorage allows safe relative paths."""
    # These should all work without raising exceptions
    TodoStorage("safe.json")
    TodoStorage("data/todos.json")
    TodoStorage(".todo.json")
    TodoStorage("")  # Uses default ".todo.json"
    TodoStorage("./safe.json")  # Explicit current directory


def test_todostorage_allows_absolute_paths():
    """Test that TodoStorage allows absolute paths (user's responsibility)."""
    # Absolute paths are allowed - users have full control over their system
    TodoStorage("/tmp/test.json")
    TodoStorage("/home/user/data/todos.json")
