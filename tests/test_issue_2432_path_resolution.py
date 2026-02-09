"""Tests for issue #2432: Path resolution priority (env var > XDG > current dir).

This test suite verifies the hierarchical path resolution for TodoStorage:
1. TODO_DB_PATH environment variable (highest priority)
2. XDG_DATA_HOME environment variable (falls back to ~/.local/share)
3. Current directory .todo.json (fallback default)
"""
from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_path_when_no_env_vars_set(tmp_path, monkeypatch) -> None:
    """Test that current directory .todo.json is used when no env vars are set."""
    # Ensure no env vars are set (including HOME to force cwd fallback)
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    storage = TodoStorage()
    expected_path = tmp_path / ".todo.json"

    assert storage.path == expected_path

    # Verify file can be created in current directory
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert expected_path.exists()


def test_xdg_data_home_path_when_set(tmp_path, monkeypatch) -> None:
    """Test that XDG_DATA_HOME is used when TODO_DB_PATH is not set."""
    # Set XDG_DATA_HOME but not TODO_DB_PATH
    xdg_dir = tmp_path / "xdg_share"
    xdg_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    # Change to a different directory to ensure we're not using cwd
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    storage = TodoStorage()
    expected_path = xdg_dir / "todo" / "todo.json"

    assert storage.path == expected_path

    # Verify directory is created when saving
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert expected_path.exists()
    assert expected_path.parent.is_dir()


def test_xdg_fallback_to_home_local_share(tmp_path, monkeypatch) -> None:
    """Test that XDG falls back to ~/.local/share when XDG_DATA_HOME is not set."""
    # Set HOME but not XDG_DATA_HOME
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()
    expected_path = home_dir / ".local" / "share" / "todo" / "todo.json"

    assert storage.path == expected_path


def test_todo_db_path_takes_priority_over_xdg(tmp_path, monkeypatch) -> None:
    """Test that TODO_DB_PATH has highest priority, overriding XDG_DATA_HOME."""
    # Set both env vars
    custom_path = tmp_path / "custom" / "db.json"
    xdg_dir = tmp_path / "xdg_share"
    xdg_dir.mkdir()

    monkeypatch.setenv("TODO_DB_PATH", str(custom_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))

    storage = TodoStorage()

    assert storage.path == custom_path

    # Verify file is created at TODO_DB_PATH location
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert custom_path.exists()
    assert not (xdg_dir / "todo" / "todo.json").exists()


def test_explicit_path_overrides_all_defaults(tmp_path, monkeypatch) -> None:
    """Test that explicit path parameter overrides all environment variables."""
    explicit_path = tmp_path / "explicit" / "todo.json"
    env_path = tmp_path / "env" / "db.json"

    monkeypatch.setenv("TODO_DB_PATH", str(env_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    storage = TodoStorage(str(explicit_path))

    assert storage.path == explicit_path

    # Verify file is created at explicit path
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert explicit_path.exists()
    assert not env_path.exists()


def test_xdg_path_directory_auto_created(tmp_path, monkeypatch) -> None:
    """Test that XDG path directories are automatically created."""
    xdg_dir = tmp_path / "xdg_share"
    xdg_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()
    expected_dir = xdg_dir / "todo"

    # Directory should not exist initially
    assert not expected_dir.exists()

    # After save, directory should be created
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert expected_dir.is_dir()
    assert (expected_dir / "todo.json").exists()


def test_path_resolution_priority_order(tmp_path, monkeypatch) -> None:
    """Test the complete priority order: TODO_DB_PATH > XDG > cwd."""
    # Test with only TODO_DB_PATH set
    todo_db_path = tmp_path / "todo_db" / "db.json"
    monkeypatch.setenv("TODO_DB_PATH", str(todo_db_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    storage = TodoStorage()
    assert storage.path == todo_db_path

    # Test with only XDG_DATA_HOME set
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    xdg_dir = tmp_path / "xdg" / "share"
    xdg_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))

    storage = TodoStorage()
    assert storage.path == xdg_dir / "todo" / "todo.json"

    # Test with neither set (should use cwd)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    storage = TodoStorage()
    assert storage.path == cwd / ".todo.json"


def test_home_local_share_directory_auto_created(tmp_path, monkeypatch) -> None:
    """Test that ~/.local/share/todo directory is created when using default XDG path."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()
    expected_dir = home_dir / ".local" / "share" / "todo"

    # Directory should not exist initially
    assert not expected_dir.exists()

    # After save, directory should be created
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert expected_dir.is_dir()
    assert (expected_dir / "todo.json").exists()
