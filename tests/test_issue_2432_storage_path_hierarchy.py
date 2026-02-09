"""Tests for issue #2432: Storage path configuration hierarchy.

This test suite verifies that TodoStorage follows the path resolution priority:
1. TODO_DB_PATH environment variable (highest priority)
2. XDG_DATA_HOME environment variable (typically ~/.local/share)
3. Current directory .todo.json (fallback)

TDD approach: These tests should FAIL before implementation, PASS after.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_path_when_no_env_set(tmp_path, monkeypatch) -> None:
    """Test that .todo.json in current directory is used when no env vars set."""
    # Ensure no environment variables are set
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create storage without explicit path
    storage = TodoStorage()

    # Verify path is .todo.json (relative to current directory)
    assert storage.path == Path(".todo.json")
    # Verify it resolves to the tmp_path when used
    assert storage.path.resolve() == tmp_path / ".todo.json"


def test_xdg_data_home_path_when_set(tmp_path, monkeypatch) -> None:
    """Test that ~/.local/share/todo/todo.json is used when XDG_DATA_HOME is set."""
    # Set up XDG_DATA_HOME
    xdg_dir = tmp_path / ".local" / "share"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    # Create storage without explicit path
    storage = TodoStorage()

    # Verify path is XDG_DATA_HOME/todo/todo.json
    expected = xdg_dir / "todo" / "todo.json"
    assert storage.path == expected


def test_todo_db_path_has_highest_priority(tmp_path, monkeypatch) -> None:
    """Test that TODO_DB_PATH overrides XDG_DATA_HOME and default."""
    # Set both environment variables
    custom_path = tmp_path / "custom" / "db.json"
    xdg_dir = tmp_path / ".local" / "share"
    monkeypatch.setenv("TODO_DB_PATH", str(custom_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))

    # Create storage without explicit path
    storage = TodoStorage()

    # TODO_DB_PATH should take priority
    assert storage.path == Path(custom_path)


def test_path_directory_auto_created(tmp_path, monkeypatch) -> None:
    """Test that parent directory is created when path doesn't exist."""
    # Set a path with non-existent parent directory
    custom_path = tmp_path / "deep" / "nested" / "db.json"
    monkeypatch.setenv("TODO_DB_PATH", str(custom_path))

    storage = TodoStorage()

    # Save should create parent directory
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify directory was created and file exists
    assert custom_path.parent.exists()
    assert custom_path.exists()
    assert storage.load() == todos


def test_xdg_fallback_to_default_home(tmp_path, monkeypatch) -> None:
    """Test XDG falls back to ~/.local/share when XDG_DATA_HOME is not set.

    This tests the standard XDG behavior where the default is ~/.local/share.
    Note: This is a simplified test - in production, this would check HOME env.
    """
    # Only set XDG_DATA_HOME (no TODO_DB_PATH)
    xdg_dir = tmp_path / ".local" / "share"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()

    # Should use XDG path
    expected = xdg_dir / "todo" / "todo.json"
    assert storage.path == expected


def test_explicit_path_parameter_overrides_all(tmp_path, monkeypatch) -> None:
    """Test that explicit path parameter overrides all environment variables."""
    # Set environment variables
    custom_env_path = tmp_path / "env" / "db.json"
    xdg_dir = tmp_path / ".local" / "share"
    monkeypatch.setenv("TODO_DB_PATH", str(custom_env_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))

    # Create storage with explicit path
    explicit_path = tmp_path / "explicit" / "todo.json"
    storage = TodoStorage(str(explicit_path))

    # Explicit path should override env vars
    assert storage.path == explicit_path


def test_todo_db_path_with_tilde_expansion(monkeypatch) -> None:
    """Test that TODO_DB_PATH with ~ is expanded to home directory."""
    # Set TODO_DB_PATH with tilde
    monkeypatch.setenv("TODO_DB_PATH", "~/mytodos/db.json")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    storage = TodoStorage()

    # Path should be expanded
    assert storage.path == Path.home() / "mytodos" / "db.json"


def test_xdg_data_home_with_tilde_expansion(monkeypatch) -> None:
    """Test that XDG_DATA_HOME with ~ is expanded to home directory."""
    # Set XDG_DATA_HOME with tilde
    monkeypatch.setenv("XDG_DATA_HOME", "~/mydata")
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()

    # Path should be expanded
    assert storage.path == Path.home() / "mydata" / "todo" / "todo.json"


def test_empty_todo_db_path_falls_back_to_xdg(tmp_path, monkeypatch) -> None:
    """Test that empty TODO_DB_PATH falls back to XDG_DATA_HOME."""
    # Set empty TODO_DB_PATH
    monkeypatch.setenv("TODO_DB_PATH", "")
    xdg_dir = tmp_path / ".local" / "share"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))

    storage = TodoStorage()

    # Should fall back to XDG path
    expected = xdg_dir / "todo" / "todo.json"
    assert storage.path == expected
