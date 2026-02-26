"""Tests for issue #5915: Handle simple filename without directory component.

Regression tests for TodoStorage when path is a simple filename like 'todo.json'
in the current directory (no parent directory component).
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


class TestSimpleFilenameHandling:
    """Test that TodoStorage works correctly with simple filenames."""

    def test_save_with_simple_filename_in_current_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Test that save() works when path is a simple filename like 'todo.json'.

        This tests the case where file_path.parent returns '.' (current directory).
        """
        # Change to tmp_path directory for this test
        monkeypatch.chdir(tmp_path)

        # Use a simple filename without any directory component
        storage = TodoStorage("todo.json")

        # This should NOT raise any errors
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Verify file was created in current directory
        assert (tmp_path / "todo.json").exists()

        # Verify we can load it back
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    def test_save_with_explicit_current_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Test that save() works when path explicitly uses './todo.json'."""
        monkeypatch.chdir(tmp_path)

        storage = TodoStorage("./todo.json")

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        assert (tmp_path / "todo.json").exists()
        loaded = storage.load()
        assert len(loaded) == 1

    def test_ensure_parent_directory_with_current_dir_parent(self, tmp_path: Path, monkeypatch) -> None:
        """Test _ensure_parent_directory handles Path('.') parent correctly.

        When file_path is 'todo.json', parent is Path('.').
        This should not raise an error since current directory always exists.
        """
        monkeypatch.chdir(tmp_path)

        # This should not raise any exception
        _ensure_parent_directory(Path("todo.json"))

        # Current directory should still exist (no side effects)
        assert tmp_path.exists()

    def test_multiple_saves_with_simple_filename(self, tmp_path: Path, monkeypatch) -> None:
        """Test multiple saves work correctly with simple filename."""
        monkeypatch.chdir(tmp_path)

        storage = TodoStorage("todo.json")

        # First save
        storage.save([Todo(id=1, text="first")])
        assert len(storage.load()) == 1

        # Second save (update)
        storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])
        loaded = storage.load()
        assert len(loaded) == 2

        # Third save (replace)
        storage.save([Todo(id=3, text="third")])
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "third"

    def test_path_parent_is_current_directory(self) -> None:
        """Verify that Path('todo.json').parent returns Path('.')."""
        parent = Path("todo.json").parent
        # Path('.') equals Path('') in Python 3.9+
        # Both represent the current directory
        assert str(parent) in (".", "")
        assert parent == Path(".")
