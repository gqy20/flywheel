"""Todo storage backend."""

import atexit
import errno
import hashlib
import json
import logging
import os
import threading
from pathlib import Path

from flywheel.todo import Todo

logger = logging.getLogger(__name__)

# Platform-specific file locking (Issue #268)
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix-like systems
    import fcntl


class Storage:
    """File-based todo storage."""

    def __init__(self, path: str = "~/.flywheel/todos.json"):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Set restrictive directory permissions to protect temporary files
        # from the race condition between mkstemp and fchmod (Issue #194)
        # This ensures that even if temp files have loose permissions momentarily,
        # they cannot be accessed by other users
        self._secure_directory(self.path.parent)
        self._todos: list[Todo] = []
        self._next_id: int = 1  # Track next available ID for O(1) generation
        self._lock = threading.RLock()  # Thread safety lock (reentrant for internal lock usage)
        self._dirty: bool = False  # Track if data has been modified (Issue #203)
        self._load()
        # Register cleanup handler to save dirty data on exit (Issue #203)
        atexit.register(self._cleanup)

    def _get_file_lock_range_from_handle(self, file_handle) -> int:
        """Get the Windows file lock range based on open file handle size.

        This method returns a lock range for Windows file locking that is based
        on the actual file size from an open file handle. This prevents race
        conditions (Issue #311) by using the file handle that's already open,
        rather than making a separate file system check.

        Args:
            file_handle: The open file handle to get size from.

        Returns:
            A fixed lock range that is safe for all file sizes, preventing
            overflow issues (Issue #316).

        Note:
            - Uses file handle to avoid TOCTOU race conditions (Issue #311)
            - Uses fixed lock range to prevent integer overflow (Issue #316)
            - Windows msvcrt.locking works best with fixed regions
            - A 1MB fixed region is sufficient for mutual exclusion
            - The lock range must be a positive integer for msvcrt.locking()
        """
        # Use a fixed lock range to prevent integer overflow (Issue #316)
        # Windows msvcrt.locking doesn't require locking the entire file
        # A fixed region is sufficient for mutual exclusion and avoids:
        # 1. Integer overflow for large files
        # 2. Excessive lock ranges for small files
        # 3. Issues with file size changes between check and lock
        return 1024 * 1024  # 1MB fixed region

    def _acquire_file_lock(self, file_handle) -> None:
        """Acquire an exclusive file lock for multi-process safety (Issue #268).

        Args:
            file_handle: The file handle to lock.

        Raises:
            IOError: If the lock cannot be acquired.

        Note:
            For Windows (Issue #311, #316), a fixed 1MB lock region is used
            to prevent integer overflow and avoid excessive lock ranges.
        """
        if os.name == 'nt':  # Windows
            # Windows locking: msvcrt.locking
            # Lock a fixed 1MB region (LK_LOCK) with blocking mode
            # Using fixed region prevents integer overflow (Issue #316)
            # and avoids excessive lock ranges for small files
            try:
                # Get the fixed lock range (1MB)
                lock_range = self._get_file_lock_range_from_handle(file_handle)
                # Move to beginning of file before locking
                file_handle.seek(0)
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, lock_range)
            except IOError as e:
                logger.error(f"Failed to acquire Windows file lock: {e}")
                raise
        else:  # Unix-like systems
            # Unix locking: fcntl.flock
            # LOCK_EX = exclusive lock
            # LOCK_NB = non-blocking mode (not set - we want to block)
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
            except IOError as e:
                logger.error(f"Failed to acquire Unix file lock: {e}")
                raise

    def _release_file_lock(self, file_handle) -> None:
        """Release a file lock for multi-process safety (Issue #268).

        Args:
            file_handle: The file handle to unlock.

        Raises:
            IOError: If the lock cannot be released.

        Note:
            For Windows (Issue #311, #316), a fixed 1MB lock region is used
            to match the range used during lock acquisition.
        """
        if os.name == 'nt':  # Windows
            # Windows unlocking
            # Unlock range must match lock range exactly (Issue #271)
            # Use the same fixed 1MB region as acquire (Issue #316)
            try:
                # Get the fixed lock range (1MB) - must match the range
                # used in _acquire_file_lock to avoid "permission denied" errors
                lock_range = self._get_file_lock_range_from_handle(file_handle)
                file_handle.seek(0)
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, lock_range)
            except IOError as e:
                logger.warning(f"Failed to release Windows file lock: {e}")
                # Don't raise - we want to continue even if unlock fails
        else:  # Unix-like systems
            # Unix unlocking
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            except IOError as e:
                logger.warning(f"Failed to release Unix file lock: {e}")
                # Don't raise - we want to continue even if unlock fails

    def _secure_directory(self, directory: Path) -> None:
        """Set restrictive permissions on the storage directory.

        This method attempts to set restrictive permissions on the storage
        directory to protect sensitive data. The approach varies by platform:

        - Unix-like systems: Uses chmod(0o700) to set owner-only access.
          Raises RuntimeError if chmod fails.
        - Windows: Uses win32security to set restrictive ACLs.
          Raises RuntimeError if pywin32 is not installed or ACL setup fails.

        Args:
            directory: The directory path to secure.

        Raises:
            RuntimeError: If directory permissions cannot be set securely.

        Note:
            This method will raise an exception and prevent execution if
            secure directory permissions cannot be established. This ensures
            the application does not run with unprotected sensitive data (Issue #304).

            On Windows, pywin32 is required. Install it with: pip install pywin32
        """
        if os.name != 'nt':  # Unix-like systems
            try:
                directory.chmod(0o700)
            except OSError as e:
                # Raise error instead of warning for security (Issue #304)
                raise RuntimeError(
                    f"Failed to set directory permissions on {directory}: {e}. "
                    f"Cannot continue without secure directory permissions."
                ) from e
        else:  # Windows
            # Attempt to use Windows ACLs for security (Issue #226)
            win32_success = False
            try:
                import win32security
                import win32con
                import win32api

                # Get the current user's SID using Windows API (Issue #229)
                # Use GetUserNameEx to get the primary domain instead of relying
                # on environment variables which can be manipulated or missing
                # Initialize domain to ensure it's always defined (Issue #234)
                domain = None

                # Fix Issue #314: Fallback to environment variables when GetUserName fails
                # or returns edge case values (None, empty string, whitespace only)
                try:
                    user = win32api.GetUserName()
                except Exception:
                    # GetUserName failed - try environment variable fallback
                    user = os.environ.get('USERNAME', '').strip()

                # Validate user and use environment variable fallback if needed
                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                    # GetUserName returned invalid value - try environment variable
                    user = os.environ.get('USERNAME', '').strip()
                    if not user:
                        # No valid username available - raise error
                        raise RuntimeError(
                            "Cannot set Windows security: Unable to determine username. "
                            "Both win32api.GetUserName() and USERNAME environment variable are unavailable. "
                            "Install pywin32: pip install pywin32"
                        )

                # Fix Issue #251: Extract pure username if GetUserName returns
                # 'COMPUTERNAME\\username' or 'DOMAIN\\username' format
                # This can happen in non-domain environments and causes
                # LookupAccountName to fail
                if '\\' in user:
                    # Extract the part after the last backslash
                    parts = user.rsplit('\\', 1)
                    if len(parts) == 2:
                        user = parts[1]

                try:
                    # Try to get the fully qualified domain name
                    name = win32api.GetUserNameEx(win32con.NameFullyQualifiedDN)
                    # Extract domain from the qualified DN
                    # Format: CN=user,OU=users,DC=domain,DC=com
                    parts = name.split(',')
                    # Build domain from all DC= parts (execute once, not in loop)
                    dc_parts = [p.split('=')[1] for p in parts if p.strip().startswith('DC=')]
                    if dc_parts:
                        domain = '.'.join(dc_parts)
                    else:
                        # Fallback to local computer if no domain found
                        domain = win32api.GetComputerName()
                except Exception:
                    # Fallback: Use local computer for non-domain environments
                    try:
                        domain = win32api.GetComputerName()
                    except Exception:
                        # Fix Issue #314: Use USERDOMAIN environment variable as fallback
                        domain = os.environ.get('USERDOMAIN', '.')

                # Final fallback for domain (Issue #234, #314)
                # Ensures domain is always defined before LookupAccountName
                if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                    domain = os.environ.get('USERDOMAIN', '.')

                # Validate user before calling LookupAccountName (Issue #240)
                # Ensure user is initialized and non-empty to prevent passing invalid values
                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                    raise ValueError(
                        f"Invalid user name '{user}': Cannot set Windows security. "
                        f"GetUserName() returned invalid value."
                    )

                # Fix Issue #314: Try LookupAccountName with fallback to environment variables
                try:
                    sid, _, _ = win32security.LookupAccountName(domain, user)
                except Exception:
                    # LookupAccountName failed - try with environment variable username
                    env_username = os.environ.get('USERNAME', '').strip()
                    if env_username and env_username != user:
                        logger.warning(
                            f"LookupAccountName failed for user '{user}', "
                            f"retrying with environment variable USERNAME '{env_username}'"
                        )
                        user = env_username
                        # Update domain as well if available
                        env_domain = os.environ.get('USERDOMAIN', '').strip()
                        if env_domain:
                            domain = env_domain
                        try:
                            sid, _, _ = win32security.LookupAccountName(domain, user)
                        except Exception as e:
                            # Still failed - raise RuntimeError
                            raise RuntimeError(
                                f"Failed to set Windows ACLs: Unable to lookup account '{user}' in domain '{domain}'. "
                                f"Both win32api.GetUserName() and environment variables (USERNAME={os.environ.get('USERNAME')}, "
                                f"USERDOMAIN={os.environ.get('USERDOMAIN')}) failed to provide valid security context. "
                                f"Original error: {e}"
                            ) from e
                    else:
                        # No environment variable fallback available
                        raise RuntimeError(
                            f"Failed to set Windows ACLs: Unable to lookup account '{user}' in domain '{domain}'. "
                            f"Install pywin32: pip install pywin32"
                        )

                # Create a security descriptor with owner-only access
                security_descriptor = win32security.SECURITY_DESCRIPTOR()
                security_descriptor.SetSecurityDescriptorOwner(sid, False)

                # Create a DACL (Discretionary Access Control List)
                # Use minimal permissions instead of FILE_ALL_ACCESS (Issue #239)
                # Following the principle of least privilege (Issue #249)
                # Do NOT use FILE_GENERIC_READ | FILE_GENERIC_WRITE as they include DELETE
                # Use explicit minimal permissions without DELETE
                # Remove FILE_READ_EA and FILE_WRITE_EA (Issue #254)
                dacl = win32security.ACL()
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    win32con.FILE_LIST_DIRECTORY |
                    win32con.FILE_ADD_FILE |
                    win32con.FILE_READ_ATTRIBUTES |
                    win32con.FILE_WRITE_ATTRIBUTES |
                    win32con.SYNCHRONIZE,
                    sid
                )

                security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)

                # Fix Issue #244: Set SACL (System Access Control List) for auditing
                # SACL enables security auditing for access attempts on the directory
                # Create an empty SACL (no audit policies by default)
                # Administrators can configure audit policies using Windows Security Audit
                sacl = win32security.ACL()
                security_descriptor.SetSecurityDescriptorSacl(0, sacl, 0)

                # Fix Issue #256: Explicitly set DACL protection to prevent inheritance
                # This ensures PROTECTED_DACL_SECURITY_INFORMATION flag takes effect
                security_descriptor.SetSecurityDescriptorControl(
                    win32security.SE_DACL_PROTECTED, 1
                )

                # Apply the security descriptor to the directory
                # Include OWNER_SECURITY_INFORMATION to ensure owner info is applied (Issue #264)
                # Include SACL_SECURITY_INFORMATION to ensure SACL is applied (Issue #277)
                security_info = (
                    win32security.DACL_SECURITY_INFORMATION |
                    win32security.PROTECTED_DACL_SECURITY_INFORMATION |
                    win32security.OWNER_SECURITY_INFORMATION |
                    win32security.SACL_SECURITY_INFORMATION
                )
                win32security.SetFileSecurity(
                    str(directory),
                    security_info,
                    security_descriptor
                )
                logger.debug(f"Applied restrictive ACLs to {directory}")
                win32_success = True

            except ImportError as e:
                # pywin32 is not installed - raise error for security (Issue #304)
                raise RuntimeError(
                    f"pywin32 is required on Windows for secure directory permissions. "
                    f"Directory {directory} cannot be secured without pywin32. "
                    f"Install pywin32: pip install pywin32"
                ) from e
            except Exception as e:
                # Failed to set ACLs - raise error for security (Issue #304)
                raise RuntimeError(
                    f"Failed to set Windows ACLs on {directory}: {e}. "
                    f"Cannot continue without secure directory permissions. "
                    f"Install pywin32: pip install pywin32"
                ) from e

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

    def _calculate_checksum(self, todos: list) -> str:
        """Calculate SHA256 checksum of todos data (Issue #223).

        Args:
            todos: List of todo objects to calculate checksum for.

        Returns:
            Hexadecimal string representation of SHA256 hash.
        """
        # Serialize todos to JSON for hashing
        todos_json = json.dumps([t.to_dict() for t in todos], sort_keys=True)
        return hashlib.sha256(todos_json.encode('utf-8')).hexdigest()

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

            # Validate 'metadata' field if present (Issue #223)
            if "metadata" in data:
                if not isinstance(data["metadata"], dict):
                    raise RuntimeError(
                        f"Invalid schema: 'metadata' must be a dict, got {type(data['metadata']).__name__}"
                    )
                # Checksum is optional but must be a string if present
                if "checksum" in data["metadata"] and not isinstance(data["metadata"]["checksum"], str):
                    raise RuntimeError(
                        f"Invalid schema: 'metadata.checksum' must be a string"
                    )

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
                # Acquire file lock for multi-process safety (Issue #268)
                with self.path.open('r') as f:
                    self._acquire_file_lock(f)
                    try:
                        raw_data = json.load(f)
                    finally:
                        self._release_file_lock(f)

                # Validate schema before deserializing (Issue #7)
                # This prevents injection attacks and malformed data from causing crashes
                self._validate_storage_schema(raw_data)

                # Handle both new format (dict with metadata) and old format (list)
                # Schema validation already performed above (Issue #7)
                if isinstance(raw_data, dict):
                    # New format with metadata
                    todos_data = raw_data.get("todos", [])

                    # Verify data integrity using checksum (Issue #223)
                    metadata = raw_data.get("metadata", {})
                    stored_checksum = metadata.get("checksum")

                    if stored_checksum:
                        # Calculate checksum of loaded todos
                        calculated_checksum = None
                        try:
                            # Temporarily deserialize todos for checksum calculation
                            temp_todos = []
                            for item in todos_data:
                                try:
                                    temp_todos.append(Todo.from_dict(item))
                                except (ValueError, TypeError, KeyError):
                                    pass
                            calculated_checksum = self._calculate_checksum(temp_todos)

                            if calculated_checksum != stored_checksum:
                                # Checksum mismatch - data corruption detected
                                backup_path = self._create_backup(
                                    f"Checksum mismatch in {self.path}: "
                                    f"expected {stored_checksum}, got {calculated_checksum}"
                                )
                                raise RuntimeError(
                                    f"Data integrity check failed. Checksum mismatch. "
                                    f"Backup saved to {backup_path}"
                                )
                        except Exception as e:
                            if isinstance(e, RuntimeError):
                                raise
                            # If checksum calculation fails, log warning but continue
                            logger.warning(f"Failed to verify checksum: {e}")

                    # Use direct access after validation to ensure type safety (Issue #219)
                    # _validate_storage_schema already confirmed next_id is an int if it exists
                    next_id = raw_data["next_id"] if "next_id" in raw_data else 1
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
        # Save with metadata for efficient ID generation and data integrity (Issue #223)
        # Calculate checksum of todos data
        checksum = self._calculate_checksum(todos_copy)
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy,
            "metadata": {
                "checksum": checksum
            }
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
            # Check return value and handle errors (Issue #224)
            try:
                ret = os.fchmod(fd, 0o600)
                if ret != 0:
                    # fchmod returned non-zero indicating failure
                    # Raise OSError to ensure consistent error handling
                    raise OSError(f"os.fchmod failed with return code {ret}")
            except AttributeError:
                # os.fchmod is not available on Windows
                # Apply chmod IMMEDIATELY to prevent race condition (Issue #205)
                # The file must have restrictive permissions BEFORE any data is written
                os.chmod(temp_path, 0o600)
            except OSError:
                # fchmod failed (permission denied, invalid fd, etc.)
                # Re-raise to prevent writing data with incorrect permissions (Issue #224)
                raise

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

            # Atomically replace the original file using os.replace (Issue #227)
            # os.replace is atomic on POSIX systems and handles target file existence on Windows
            # Acquire file lock on target file before replacement for multi-process safety (Issue #268)
            if self.path.exists():
                with self.path.open('r') as target_file:
                    self._acquire_file_lock(target_file)
                    try:
                        os.replace(temp_path, self.path)
                    finally:
                        self._release_file_lock(target_file)
            else:
                # If target doesn't exist, no need to lock
                os.replace(temp_path, self.path)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
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
        # Save with metadata for efficient ID generation and data integrity (Issue #223)
        # Calculate checksum of todos data
        checksum = self._calculate_checksum(todos_copy)
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy,
            "metadata": {
                "checksum": checksum
            }
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
            # Check return value and handle errors (Issue #224)
            try:
                ret = os.fchmod(fd, 0o600)
                if ret != 0:
                    # fchmod returned non-zero indicating failure
                    # Raise OSError to ensure consistent error handling
                    raise OSError(f"os.fchmod failed with return code {ret}")
            except AttributeError:
                # os.fchmod is not available on Windows
                # Apply chmod IMMEDIATELY to prevent race condition (Issue #205)
                # The file must have restrictive permissions BEFORE any data is written
                os.chmod(temp_path, 0o600)
            except OSError:
                # fchmod failed (permission denied, invalid fd, etc.)
                # Re-raise to prevent writing data with incorrect permissions (Issue #224)
                raise

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

            # Atomically replace the original file using os.replace (Issue #227)
            # os.replace is atomic on POSIX systems and handles target file existence on Windows
            # Acquire file lock on target file before replacement for multi-process safety (Issue #268)
            if self.path.exists():
                with self.path.open('r') as target_file:
                    self._acquire_file_lock(target_file)
                    try:
                        os.replace(temp_path, self.path)
                    finally:
                        self._release_file_lock(target_file)
            else:
                # If target doesn't exist, no need to lock
                os.replace(temp_path, self.path)

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
                os.unlink(temp_path)
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
