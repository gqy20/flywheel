"""Todo storage backend."""

import atexit
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
        # Set restrictive directory permissions (0o700) to protect temporary files
        # from the race condition between mkstemp and fchmod (Issue #194)
        # This ensures that even if temp files have loose permissions momentarily,
        # they cannot be accessed by other users
        if os.name != 'nt':  # Skip on Windows
            self.path.parent.chmod(0o700)
        self._todos: list[Todo] = []
        self._next_id: int = 1  # Track next available ID for O(1) generation
        self._lock = threading.RLock()  # Thread safety lock (reentrant for internal lock usage)
        self._dirty: bool = False  # Track if data has been modified (Issue #203)
        self._load()
        # Register cleanup handler to save dirty data on exit (Issue #203)
        atexit.register(self._cleanup)

    def _create_backup(self, error_message: str) -> str:
        """Create a backup of the todo file.

        Args:
            error_message: Description of the error that triggered the backup.

        Returns:
            Path to the backup file.

        Raises:
            RuntimeError: If backup creation fails.
        """
        import shutil

        backup_path = str(self.path) + ".backup"
        try:
            shutil.copy2(self.path, backup_path)
            logger.error(f"{error_message}. Backup created at {backup_path}")
        except Exception as backup_error:
            logger.error(f"Failed to create backup: {backup_error}")
            raise RuntimeError(f"{error_message}. Failed to create backup") from backup_error
        return backup_path

    def _cleanup(self) -> None:
        """Cleanup handler called on program exit.

        Ensures any pending changes are saved before the program exits.
        This prevents data loss when the program terminates unexpectedly.
        """
        if self._dirty:
            try:
                self._save()
                logger.info("Saved pending changes on exit")
            except Exception as e:
                logger.error(f"Failed to save pending changes on exit: {e}")

    def _validate_storage_schema(self, data: dict | list) -> None:
        """Validate the storage data schema for security (Issue #7).

        This method performs strict schema validation to prevent:
        - Injection attacks via malformed data structures
        - Type confusion vulnerabilities
        - Unexpected nested structures

        Args:
            data: The raw parsed JSON data (dict or list)

        Raises:
            RuntimeError: If the data structure is invalid or potentially malicious.
        """
        # Validate top-level structure
        if isinstance(data, dict):
            # New format with metadata
            # Check for unexpected keys that could indicate tampering
            expected_keys = {"todos", "next_id", "metadata"}
            actual_keys = set(data.keys())
            # Warn about unexpected keys but don't fail (forward compatibility)
            unexpected = actual_keys - expected_keys
            if unexpected:
                logger.warning(f"Unexpected keys in storage file: {unexpected}")

            # Validate 'todos' field
            if "todos" in data:
                if not isinstance(data["todos"], list):
                    raise RuntimeError(
                        f"Invalid schema: 'todos' must be a list, got {type(data['todos']).__name__}"
                    )

            # Validate 'next_id' field
            if "next_id" in data:
                if not isinstance(data["next_id"], int):
                    raise RuntimeError(
                        f"Invalid schema: 'next_id' must be an int, got {type(data['next_id']).__name__}"
                    )
                if data["next_id"] < 1:
                    raise RuntimeError(f"Invalid schema: 'next_id' must be >= 1, got {data['next_id']}")

        elif isinstance(data, list):
            # Old format - list of todos
            # No additional validation needed, individual todos will be validated
            pass
        else:
            # Invalid top-level type
            raise RuntimeError(
                f"Invalid schema: expected dict or list at top level, got {type(data).__name__}"
            )

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
                self._dirty = False  # Reset dirty flag (Issue #203)
                return

            try:
                # Read file and parse JSON atomically using json.load()
                # This prevents TOCTOU issues by keeping the file handle open
                # during parsing, instead of separating read_text() and json.loads()
                with self.path.open('r') as f:
                    raw_data = json.load(f)

                # Validate schema before deserializing (Issue #7)
                # This prevents injection attacks and malformed data from causing crashes
                self._validate_storage_schema(raw_data)

                # Handle both new format (dict with metadata) and old format (list)
                # Schema validation already performed above (Issue #7)
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
                    next_id = max(set(valid_ids), default=0) + 1

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
                # Reset dirty flag after successful load (Issue #203)
                self._dirty = False
            except json.JSONDecodeError as e:
                # Create backup before raising exception to prevent data loss
                backup_path = self._create_backup(f"Invalid JSON in {self.path}")
                raise RuntimeError(f"Invalid JSON in {self.path}. Backup saved to {backup_path}") from e
            except RuntimeError as e:
                # Re-raise RuntimeError without creating backup
                # This handles format validation errors that should not trigger backup
                raise
            except Exception as e:
                # Create backup before raising exception to prevent data loss
                backup_path = self._create_backup(f"Failed to load todos from {self.path}")
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
            # Set strict file permissions (0o600) to prevent unauthorized access
            # This ensures security regardless of umask settings (Issue #179)
            # Moved inside try block to ensure fd is closed in finally block on failure (Issue #196)
            try:
                os.fchmod(fd, 0o600)
            except AttributeError:
                # os.fchmod is not available on Windows
                # Apply chmod IMMEDIATELY to prevent race condition (Issue #205)
                # The file must have restrictive permissions BEFORE any data is written
                os.chmod(temp_path, 0o600)

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

            # Close file descriptor AFTER chmod to avoid race condition (Issue #200)
            # Close BEFORE replace to avoid "file being used" errors on Windows (Issue #190)
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
            except OSError:
                # Catch OSError specifically to prevent masking original exception
                # os.close() can only raise OSError, so we don't need the broader Exception
                pass

    def _save_with_todos(self, todos: list[Todo]) -> None:
        """Save specified todos to file using atomic write.

        Uses Copy-on-Write pattern: captures data under lock, releases lock,
        then performs I/O. This minimizes lock contention and prevents blocking
        other threads during file operations.

        Args:
            todos: The todos list to save. This will become the new internal state.

        Note:
            This method updates self._todos ONLY after successful file write
            to maintain consistency and prevent race conditions (fixes Issue #95, #105, #121).
        """
        import tempfile
        import copy

        # Phase 1: Capture data under lock (minimal critical section)
        # DO NOT update internal state yet - wait until write succeeds
        with self._lock:
            # Deep copy the new todos to ensure we have a consistent snapshot
            todos_copy = copy.deepcopy(todos)
            # Calculate next_id from the todos being saved (fixes Issue #166, #170)
            # This ensures the saved next_id matches the actual max ID in the file
            if todos:
                max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
                next_id_copy = max(max_id + 1, self._next_id)
            else:
                # Preserve current next_id when todos list is empty (fixes Issue #175)
                # This prevents ID conflicts by not resetting to 1
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
            # Set strict file permissions (0o600) to prevent unauthorized access
            # This ensures security regardless of umask settings (Issue #179)
            # Moved inside try block to ensure fd is closed in finally block on failure (Issue #196)
            try:
                os.fchmod(fd, 0o600)
            except AttributeError:
                # os.fchmod is not available on Windows
                # Apply chmod IMMEDIATELY to prevent race condition (Issue #205)
                # The file must have restrictive permissions BEFORE any data is written
                os.chmod(temp_path, 0o600)

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

            # Close file descriptor AFTER chmod to avoid race condition (Issue #200)
            # Close BEFORE replace to avoid "file being used" errors on Windows (Issue #190)
            os.close(fd)
            fd = -1  # Mark as closed to prevent double-close in finally block

            # Atomically replace the original file
            Path(temp_path).replace(self.path)

            # Phase 3: Update internal state ONLY after successful write
            # This ensures consistency between memory and disk (fixes Issue #121, #150)
            with self._lock:
                # Use the original todos parameter to update internal state (fixes Issue #150)
                # Deep copy to prevent external modifications from affecting internal state
                import copy
                self._todos = copy.deepcopy(todos)
                # Recalculate _next_id to maintain consistency (fixes Issue #101)
                # If the new todos contain higher IDs than current _next_id, update it
                if todos:
                    max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
                    if max_id >= self._next_id:
                        self._next_id = max_id + 1
                # Mark as clean after successful save (Issue #203)
                self._dirty = False
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
            except OSError:
                # Catch OSError specifically to prevent masking original exception
                # os.close() can only raise OSError, so we don't need the broader Exception
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
                # Capture the ID but DON'T increment self._next_id yet
                # The increment will happen in _save_with_todos after successful write
                # This prevents state inconsistency if save fails (fixes Issue #9)
                todo_id = self._next_id
                # Create a new todo with the generated ID
                todo = Todo(id=todo_id, title=todo.title, status=todo.status)
            # Note: For external IDs, _next_id will be updated in _save_with_todos
            # to maintain consistency (fixes Issue #9)

            # Create a copy of todos list with the new todo
            new_todos = self._todos + [todo]
            # Mark as dirty since we're modifying the data (Issue #203)
            self._dirty = True
            # Save and update internal state atomically
            # _save_with_todos will update self._todos and self._next_id
            # only after successful write (fixes Issue #9)
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
                    # Mark as dirty since we're modifying the data (Issue #203)
                    self._dirty = True
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
                    # Mark as dirty since we're modifying the data (Issue #203)
                    self._dirty = True
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
