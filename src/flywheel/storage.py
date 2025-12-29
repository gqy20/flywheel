"""Todo storage backend."""

import json
import logging
import os
import threading
from pathlib import Path

from flywheel.todo import Todo

logger = logging.getLogger(__name__)


class Storage:
    """File-based todo storage."""

    def __init__(self, path: str = "~/.flywheel/todos.json"):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._todos: list[Todo] = []
        self._lock = threading.Lock()  # Thread safety lock
        self._load()

    def _load(self) -> None:
        """Load todos from file."""
        with self._lock:
            if not self.path.exists():
                self._todos = []
                return

            try:
                data = json.loads(self.path.read_text())
                if not isinstance(data, list):
                    logger.warning(f"Invalid data format in {self.path}: expected list, got {type(data).__name__}")
                    self._todos = []
                    return

                todos = []
                for i, item in enumerate(data):
                    try:
                        todo = Todo.from_dict(item)
                        todos.append(todo)
                    except (ValueError, TypeError, KeyError) as e:
                        # Skip invalid todo items but continue loading valid ones
                        logger.warning(f"Skipping invalid todo at index {i}: {e}")
                self._todos = todos
            except json.JSONDecodeError as e:
                # Create backup before raising exception to prevent data loss
                backup_path = str(self.path) + ".backup"
                try:
                    import shutil
                    shutil.copy2(self.path, backup_path)
                    logger.error(f"Invalid JSON in {self.path}. Backup created at {backup_path}: {e}")
                except Exception as backup_error:
                    logger.error(f"Failed to create backup: {backup_error}")
                raise RuntimeError(f"Invalid JSON in {self.path}. Backup saved to {backup_path}") from e
            except Exception as e:
                # Create backup before raising exception to prevent data loss
                backup_path = str(self.path) + ".backup"
                try:
                    import shutil
                    shutil.copy2(self.path, backup_path)
                    logger.error(f"Failed to load todos. Backup created at {backup_path}: {e}")
                except Exception as backup_error:
                    logger.error(f"Failed to create backup: {backup_error}")
                raise RuntimeError(f"Failed to load todos. Backup saved to {backup_path}") from e

    def _save(self) -> None:
        """Save todos to file using atomic write."""
        import tempfile

        data = json.dumps([t.to_dict() for t in self._todos], indent=2)

        # Write to temporary file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=self.path.name + ".",
            suffix=".tmp"
        )

        try:
            # Write data directly to file descriptor to avoid duplication
            # Use a loop to handle partial writes
            data_bytes = data.encode('utf-8')
            total_written = 0
            while total_written < len(data_bytes):
                written = os.write(fd, data_bytes[total_written:])
                if written == 0:
                    raise OSError("Write returned 0 bytes - disk full?")
                total_written += written
            os.fsync(fd)  # Ensure data is written to disk

            # Close fd before replacing file to avoid issues on Windows
            os.close(fd)
            fd = -1  # Mark as closed

            # Atomically replace the original file
            Path(temp_path).replace(self.path)
        except Exception:
            # Clean up temp file on error
            # fd must be closed before unlinking on some systems
            try:
                if fd >= 0:
                    os.close(fd)
                    fd = -1
            except Exception:
                pass
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise
        finally:
            # Ensure fd is always closed exactly once
            try:
                if fd >= 0:
                    os.close(fd)
            except Exception:
                pass

    def _save_with_todos(self, todos: list[Todo]) -> None:
        """Save specified todos to file using atomic write."""
        import tempfile

        data = json.dumps([t.to_dict() for t in todos], indent=2)

        # Write to temporary file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=self.path.name + ".",
            suffix=".tmp"
        )

        try:
            # Write data directly to file descriptor to avoid duplication
            # Use a loop to handle partial writes
            data_bytes = data.encode('utf-8')
            total_written = 0
            while total_written < len(data_bytes):
                written = os.write(fd, data_bytes[total_written:])
                if written == 0:
                    raise OSError("Write returned 0 bytes - disk full?")
                total_written += written
            os.fsync(fd)  # Ensure data is written to disk

            # Close fd before replacing file to avoid issues on Windows
            os.close(fd)
            fd = -1  # Mark as closed

            # Atomically replace the original file
            Path(temp_path).replace(self.path)
        except Exception:
            # Clean up temp file on error
            # fd must be closed before unlinking on some systems
            try:
                if fd >= 0:
                    os.close(fd)
                    fd = -1
            except Exception:
                pass
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise
        finally:
            # Ensure fd is always closed exactly once
            try:
                if fd >= 0:
                    os.close(fd)
            except Exception:
                pass

    def add(self, todo: Todo) -> Todo:
        """Add a new todo with atomic ID generation."""
        with self._lock:
            # Capture the ID from the todo atomically to prevent race conditions
            # Even if another thread modifies todo.id after this check, we use the captured value
            todo_id = todo.id

            # If todo doesn't have an ID, generate one atomically
            # Inline the ID generation logic to ensure atomicity with insertion
            if todo_id is None:
                # Calculate next ID directly within the lock to prevent race conditions
                if not self._todos:
                    todo_id = 1
                else:
                    todo_id = max(t.id for t in self._todos) + 1
                # Create a new todo with the generated ID
                todo = Todo(id=todo_id, title=todo.title, status=todo.status)
            else:
                # Todo already has an ID, check if it exists in storage
                existing = self.get(todo_id)
                if existing is not None:
                    # Todo with this ID already exists, this might be an error
                    # Return the existing todo to indicate it's already been added
                    return existing

            # Create a copy of todos list with the new todo
            new_todos = self._todos + [todo]
            # Try to save first, only update memory if save succeeds
            self._save_with_todos(new_todos)
            self._todos = new_todos
            return todo

    def list(self, status: str | None = None) -> list[Todo]:
        """List all todos."""
        if status:
            return [t for t in self._todos if t.status == status]
        return self._todos

    def get(self, todo_id: int) -> Todo | None:
        """Get a todo by ID."""
        with self._lock:
            for todo in self._todos:
                if todo.id == todo_id:
                    return todo
            return None

    def update(self, todo: Todo) -> Todo | None:
        """Update a todo."""
        with self._lock:
            for i, t in enumerate(self._todos):
                if t.id == todo.id:
                    # Create a copy of todos list with the updated todo
                    new_todos = self._todos.copy()
                    new_todos[i] = todo
                    # Try to save first, only update memory if save succeeds
                    self._save_with_todos(new_todos)
                    self._todos = new_todos
                    return todo
            return None

    def delete(self, todo_id: int) -> bool:
        """Delete a todo."""
        with self._lock:
            for i, t in enumerate(self._todos):
                if t.id == todo_id:
                    # Create a copy of todos list without the deleted todo
                    new_todos = self._todos[:i] + self._todos[i+1:]
                    # Try to save first, only update memory if save succeeds
                    self._save_with_todos(new_todos)
                    self._todos = new_todos
                    return True
            return False

    def get_next_id(self) -> int:
        """Get next available ID."""
        if not self._todos:
            return 1
        return max(t.id for t in self._todos) + 1
