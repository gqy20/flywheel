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
        self._next_id: int = 1  # Track next available ID for O(1) generation
        self._lock = threading.Lock()  # Thread safety lock
        self._load()

    def _load(self) -> None:
        """Load todos from file."""
        with self._lock:
            if not self.path.exists():
                self._todos = []
                self._next_id = 1
                return

            try:
                raw_data = json.loads(self.path.read_text())

                # Handle both new format (dict with metadata) and old format (list)
                if isinstance(raw_data, dict):
                    # New format with metadata
                    todos_data = raw_data.get("todos", [])
                    self._next_id = raw_data.get("next_id", 1)
                elif isinstance(raw_data, list):
                    # Old format - backward compatibility
                    todos_data = raw_data
                    # Calculate next_id from existing todos
                    self._next_id = max((t.id for t in [Todo.from_dict(item) for item in raw_data if isinstance(item, dict)]), default=0) + 1
                else:
                    logger.warning(f"Invalid data format in {self.path}: expected dict or list, got {type(raw_data).__name__}")
                    self._todos = []
                    self._next_id = 1
                    return

                todos = []
                for i, item in enumerate(todos_data):
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

        # Save with metadata for efficient ID generation
        data = json.dumps({
            "todos": [t.to_dict() for t in self._todos],
            "next_id": self._next_id
        }, indent=2)

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

        # Save with metadata for efficient ID generation
        data = json.dumps({
            "todos": [t.to_dict() for t in todos],
            "next_id": self._next_id
        }, indent=2)

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
                # Use _next_id for O(1) ID generation instead of max() which is O(N)
                todo_id = self._next_id
                self._next_id += 1  # Increment counter for next use
                # Create a new todo with the generated ID
                todo = Todo(id=todo_id, title=todo.title, status=todo.status)
            else:
                # Todo already has an ID, check if it exists in storage
                existing = self.get(todo_id)
                if existing is not None:
                    # Todo with this ID already exists, this might be an error
                    # Return the existing todo to indicate it's already been added
                    return existing
                # Update _next_id if the provided ID is >= current _next_id
                if todo_id >= self._next_id:
                    self._next_id = todo_id + 1

            # Create a copy of todos list with the new todo
            new_todos = self._todos + [todo]
            # Try to save first, only update memory if save succeeds
            self._save_with_todos(new_todos)
            self._todos = new_todos
            return todo

    def list(self, status: str | None = None) -> list[Todo]:
        """List all todos."""
        with self._lock:
            if status:
                return [t for t in self._todos if t.status == status]
            return list(self._todos)  # Return a copy to prevent external modification

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
        with self._lock:
            return self._next_id
