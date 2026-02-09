"""Tests for issue #2432: Storage path configuration default value hierarchy.

This test suite verifies that TodoStorage respects the following priority
for resolving the default database path:
1. TODO_DB_PATH environment variable (highest priority)
2. XDG_DATA_HOME environment variable (typically ~/.local/share)
3. Current directory .todo.json (fallback, lowest priority)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage


def test_default_path_fallback_to_current_directory(tmp_path, monkeypatch) -> None:
    """Test that when home is not accessible, path defaults to .todo.json in current directory."""
    # Ensure both env vars are unset
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    # Change to tmp_path to isolate test
    monkeypatch.chdir(tmp_path)

    # Mock Path.home() to raise exception so we fall back to current directory
    with patch("flywheel.storage.Path.home", side_effect=RuntimeError("No home")):
        storage = TodoStorage()
        # Should resolve to absolute path in current directory
        expected = (Path.cwd() / ".todo.json").resolve()
        assert storage.path == expected


def test_xdg_data_home_respects_todo_subdirectory(tmp_path, monkeypatch) -> None:
    """Test that XDG_DATA_HOME uses todo/todo.json subdirectory."""
    # Set XDG_DATA_HOME to tmp_path
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()
    expected = tmp_path / "todo" / "todo.json"
    assert storage.path == expected


def test_todo_db_path_has_highest_priority(tmp_path, monkeypatch) -> None:
    """Test that TODO_DB_PATH overrides XDG_DATA_HOME."""
    # Set both env vars
    custom_path = tmp_path / "custom" / "db.json"

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("TODO_DB_PATH", str(custom_path))

    storage = TodoStorage()
    assert storage.path == custom_path


def test_todo_db_path_absolute_path_respected(tmp_path, monkeypatch) -> None:
    """Test that TODO_DB_PATH absolute path is used directly."""
    custom_db = tmp_path / "absolute" / "path" / "todo.json"

    monkeypatch.setenv("TODO_DB_PATH", str(custom_db))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    storage = TodoStorage()
    assert storage.path == custom_db


def test_explicit_path_overrides_env_vars(tmp_path, monkeypatch) -> None:
    """Test that explicit path argument overrides all env vars."""
    explicit_path = tmp_path / "explicit" / "db.json"

    monkeypatch.setenv("TODO_DB_PATH", "/tmp/env.json")
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg")

    storage = TodoStorage(str(explicit_path))
    assert storage.path == explicit_path


def test_path_resolution_creates_parent_directory_on_save(tmp_path, monkeypatch) -> None:
    """Test that parent directory is created when saving with XDG path."""
    xdg_dir = tmp_path / "xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))
    monkeypatch.delenv("TODO_DB_PATH", raising=False)

    storage = TodoStorage()
    # Parent directory shouldn't exist yet
    assert not storage.path.parent.exists()

    from flywheel.todo import Todo

    # Saving should create parent directory
    storage.save([Todo(id=1, text="test")])

    # Verify directory was created and file exists
    assert storage.path.parent.exists()
    assert storage.path.exists()


def test_xdg_default_fallback_to_home(monkeypatch) -> None:
    """Test that XDG falls back to ~/.local/share when not set."""
    # Unset both env vars
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    # Mock Path.home() to return a predictable path
    fake_home = Path("/fake/home")
    with patch("flywheel.storage.Path.home", return_value=fake_home):
        storage = TodoStorage()
        # Should use XDG default ~/.local/share/todo/todo.json
        expected = fake_home / ".local" / "share" / "todo" / "todo.json"
        assert storage.path == expected


def test_fallback_to_current_directory_when_home_not_available(monkeypatch, tmp_path) -> None:
    """Test that current directory is used when XDG path cannot be determined."""
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    # Mock Path.home() to raise exception
    with patch("flywheel.storage.Path.home", side_effect=RuntimeError("No home")):
        storage = TodoStorage()
        # Should fall back to current directory .todo.json (resolved to absolute)
        expected = (Path.cwd() / ".todo.json").resolve()
        assert storage.path == expected
