"""Todo storage backend."""

import errno
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
        self._lock = threading.RLock()  # Thread safety lock (reentrant for internal lock usage)
        self._load()

    def _load(self) -> None:
        """Load todos from file.

        File read and state update are performed atomically within the lock
        to prevent race conditions where the file could change between
        reading and updating internal state.
        """
        # Acquire lock first to ensure atomicity of read + state update
        with self._lock:
            if not self.path.exists():
                self._todos = []
                self._next_id = 1
                return

            try:
                # Read file and parse JSON inside the lock to ensure atomicity
                # This prevents 'check-then-act' race conditions
                raw_data = json.loads(self.path.read_text())

                # Handle both new format (dict with metadata) and old format (list)
                if isinstance(raw_data, dict):
                    # New format with metadata
                    todos_data = raw_data.get("todos", [])
                    next_id = raw_data.get("next_id", 1)
                elif isinstance(raw_data, list):
                    # Old format - backward compatibility
                    todos_data = raw_data
                    # Calculate next_id from existing todos, safely handling invalid items
                    valid_ids = []
                    for item in raw_data:
                        if isinstance(item, dict):
                            try:
                                todo = Todo.from_dict(item)
                                valid_ids.append(todo.id)
                            except (ValueError, TypeError, KeyError):
                                # Skip invalid items when calculating next_id
                                pass
                    next_id = max(valid_ids, default=0) + 1
                else:
                    # Invalid format - raise exception and trigger backup mechanism
                    error_msg = f"Invalid data format in {self.path}: expected dict or list, got {type(raw_data).__name__}"
                    raise RuntimeError(error_msg)

                # Deserialize todo items inside the lock
                todos = []
                for i, item in enumerate(todos_data):
                    try:
                        todo = Todo.from_dict(item)
                        todos.append(todo)
                    except (ValueError, TypeError, KeyError) as e:
                        # Skip invalid todo items but continue loading valid ones
                        logger.warning(f"Skipping invalid todo at index {i}: {e}")

                # Update internal state
                self._todos = todos
                self._next_id = next_id
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
        """Save todos to file using atomic write.

        Uses Copy-on-Write pattern: captures data under lock, releases lock,
        then performs I/O. This minimizes lock contention and prevents blocking
        other threads during file operations.
        """
        import tempfile
        import copy

        # Phase 1: Capture data under lock (minimal critical section)
        with self._lock:
            # Deep copy todos to ensure we have a consistent snapshot
            todos_copy = copy.deepcopy(self._todos)
            next_id_copy = self._next_id

        # Phase 2: Serialize and perform I/O OUTSIDE the lock
        # Save with metadata for efficient ID generation
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy
        }, indent=2)

        # Write to temporary file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=self.path.name + ".",
            suffix=".tmp"
        )

        try:
            # Write data directly to file descriptor to avoid duplication
            # Use a loop to handle partial writes and EINTR errors
            data_bytes = data.encode('utf-8')
            total_written = 0
            while total_written < len(data_bytes):
                try:
                    written = os.write(fd, data_bytes[total_written:])
                    if written == 0:
                        raise OSError("Write returned 0 bytes - disk full?")
                    total_written += written
                except OSError as e:
                    # Handle EINTR (interrupted system call) by retrying
                    if e.errno == errno.EINTR:
                        continue
                    # Re-raise other OSErrors (like ENOSPC - disk full)
                    raise
            os.fsync(fd)  # Ensure data is written to disk

            # Close file descriptor BEFORE replace to avoid "file being used" errors on Windows
            os.close(fd)
            fd = -1  # Mark as closed to prevent double-close in finally block

            # Atomically replace the original file
            Path(temp_path).replace(self.path)
        except Exception:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise
        finally:
            # Ensure fd is always closed exactly once
            # This runs both on success and exception
            # (on success, fd is already closed and set to -1)
            try:
                if fd != -1:
                    os.close(fd)
            except Exception:
                pass

    def _save_with_todos(self, todos: list[Todo]) -> None:
        """Save specified todos to file using atomic write.

        Uses Copy-on-Write pattern: captures data under lock, releases lock,
        then performs I/O. This minimizes lock contention and prevents blocking
        other threads during file operations.

        Args:
            todos: The todos list to save. This will become the new internal state.

        Note:
            This method updates self._todos to maintain consistency between
            memory and file storage (fixes Issue #95, #105).
        """
        import tempfile
        import copy

        # Phase 1: Capture data under lock (minimal critical section)
        with self._lock:
            # Update internal state first to maintain consistency (Issue #95, #105)
            self._todos = todos
            # Deep copy todos to ensure we have a consistent snapshot
            todos_copy = copy.deepcopy(self._todos)
            next_id_copy = self._next_id

        # Phase 2: Serialize and perform I/O OUTSIDE the lock
        # Save with metadata for efficient ID generation
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy
        }, indent=2)

        # Write to temporary file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=self.path.name + ".",
            suffix=".tmp"
        )

        try:
            # Write data directly to file descriptor to avoid duplication
            # Use a loop to handle partial writes and EINTR errors
            data_bytes = data.encode('utf-8')
            total_written = 0
            while total_written < len(data_bytes):
                try:
                    written = os.write(fd, data_bytes[total_written:])
                    if written == 0:
                        raise OSError("Write returned 0 bytes - disk full?")
                    total_written += written
                except OSError as e:
                    # Handle EINTR (interrupted system call) by retrying
                    if e.errno == errno.EINTR:
                        continue
                    # Re-raise other OSErrors (like ENOSPC - disk full)
                    raise
            os.fsync(fd)  # Ensure data is written to disk

            # Close file descriptor BEFORE replace to avoid "file being used" errors on Windows
            os.close(fd)
            fd = -1  # Mark as closed to prevent double-close in finally block

            # Atomically replace the original file
            Path(temp_path).replace(self.path)
        except Exception:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise
        finally:
            # Ensure fd is always closed exactly once
            # This runs both on success and exception
            # (on success, fd is already closed and set to -1)
            try:
                if fd != -1:
                    os.close(fd)
            except Exception:
                pass

    def add(self, todo: Todo) -> Todo:
        """Add a new todo with atomic ID generation.

        Raises:
            ValueError: If a todo with the same ID already exists.
        """
        with self._lock:
            # Capture the ID from the todo atomically to prevent race conditions
            # Even if another thread modifies todo.id after this check, we use the captured value
            todo_id = todo.id

            # Check for duplicate ID FIRST, before any other logic
            # This prevents race conditions when todo.id is set externally
            if todo_id is not None:
                # Direct iteration to avoid reentrant lock acquisition
                # (self.get() would acquire the lock again while we already hold it)
                for existing_todo in self._todos:
                    if existing_todo.id == todo_id:
                        # Todo with this ID already exists - raise an error
                        # The caller should use update() instead for existing todos
                        raise ValueError(f"Todo with ID {todo_id} already exists. Use update() instead.")

            # If todo doesn't have an ID, generate one atomically
            # Inline the ID generation logic to ensure atomicity with insertion
            if todo_id is None:
                # Use _next_id for O(1) ID generation instead of max() which is O(N)
                todo_id = self._next_id
                self._next_id += 1  # Increment counter for next use
                # Create a new todo with the generated ID
                todo = Todo(id=todo_id, title=todo.title, status=todo.status)
            else:
                # Todo has an external ID, update _next_id if needed
                # Update _next_id if the provided ID is >= current _next_id
                if todo_id >= self._next_id:
                    self._next_id = todo_id + 1

            # Create a copy of todos list with the new todo
            new_todos = self._todos + [todo]
            # Save and update internal state atomically
            self._save_with_todos(new_todos)
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
                    # Save and update internal state atomically
                    self._save_with_todos(new_todos)
                    return todo
            return None

    def delete(self, todo_id: int) -> bool:
        """Delete a todo."""
        with self._lock:
            for i, t in enumerate(self._todos):
                if t.id == todo_id:
                    # Create a copy of todos list without the deleted todo
                    new_todos = self._todos[:i] + self._todos[i+1:]
                    # Save and update internal state atomically
                    self._save_with_todos(new_todos)
                    return True
            return False

    def get_next_id(self) -> int:
        """Get next available ID."""
        with self._lock:
            return self._next_id

    def close(self) -> None:
        """Close storage and release resources.

        This method is provided for API completeness and resource management.
        Currently, RLock does not require explicit cleanup, but this method
        allows for future expansion (e.g., closing file handles, connections).
        The method is idempotent and can be called multiple times safely.

        Example:
            >>> storage = Storage()
            >>> storage.add(Todo(title="Task"))
            >>> storage.close()
        """
        # RLock in Python does not need explicit cleanup
        # This method exists for API completeness and future extensibility
        # It is intentionally idempotent (safe to call multiple times)
        pass
