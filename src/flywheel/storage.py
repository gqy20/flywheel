"""Todo storage backend."""

import atexit
import errno
import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path

from flywheel.todo import Todo

logger = logging.getLogger(__name__)

# Platform-specific file locking (Issue #268, #411, #451)
# IMPORTANT: Windows file locking implementation
# - Windows uses win32file.LockFileEx which provides MANDATORY LOCKING
# - Mandatory locks enforce mutual exclusion and prevent concurrent access
# - All processes are blocked from writing while the lock is held
# - Unix systems use fcntl.flock which provides strong synchronization
#
# Security fix for Issue #429: Windows modules are now imported at module level
# to prevent race conditions in multi-threaded environments. Module-level imports
# ensure thread-safe initialization and eliminate TOCTOU vulnerabilities between
# __init__ checks and actual module usage.
#
# On Windows, all pywin32 modules are imported at module level. If pywin32 is not
# installed, the import will fail immediately with a clear ImportError, preventing
# runtime crashes later. This is preferred over lazy imports for thread safety.
if os.name == 'nt':  # Windows
    # Thread-safe module-level imports for Windows security (Issue #429)
    # These imports happen once when the module is loaded, ensuring all threads
    # see consistent module availability and preventing race conditions.
    #
    # Security fix for Issue #535: Declare module variables at global scope
    # before try/except to ensure they are accessible everywhere in the module.
    # This prevents NameError when _is_degraded_mode() tries to access win32file.
    win32security = None
    win32con = None
    win32api = None
    win32file = None
    pywintypes = None

    try:
        import win32security
        import win32con
        import win32api
        import win32file
        import pywintypes
    except ImportError as e:
        # Security fix for Issue #539: Remove environment variable bypass
        # pywin32 is now strictly required on Windows - no degraded mode allowed
        # This prevents security bypass through environment variable manipulation
        logger.error(
            f"pywin32 import failed: {e}",
            exc_info=True
        )
        raise ImportError(
            "pywin32 is required on Windows for secure directory permissions "
            "and mandatory file locking (Issue #451, #429, #539). "
            "Install it with: pip install pywin32"
        ) from e
else:  # Unix-like systems
    import fcntl


def _is_degraded_mode() -> bool:
    """Check if running in degraded mode without pywin32 (Issue #514)."""
    return os.name == 'nt' and win32file is None


class Storage:
    """File-based todo storage."""

    def __init__(self, path: str = "~/.flywheel/todos.json"):
        self.path = Path(path).expanduser()

        # Security fix for Issue #429: Module-level imports ensure thread safety.
        # Windows modules (win32security, win32con, win32api, win32file, pywintypes)
        # are now imported at module level, preventing race conditions in multi-threaded
        # environments. The ImportError is raised immediately if pywin32 is missing,
        # so no need to check again here.

        # Security fix for Issue #486: Create and secure parent directories atomically.
        # This eliminates the race condition window between the previous separate calls
        # to _create_and_secure_directories and _secure_all_parent_directories.
        #
        # The _secure_all_parent_directories method now handles both creation and securing
        # in a single atomic operation, ensuring there's no window where directories
        # can be created with insecure permissions.
        #
        # This approach:
        # 1. Creates directories that don't exist with secure permissions from the start
        # 2. Secures all parent directories (even those created by other processes)
        # 3. Handles race conditions where multiple processes create directories concurrently
        # 4. Uses retry logic with exponential backoff to handle TOCTOU issues
        #
        # On Unix: Creates directories with mode=0o700 using restricted umask (Issue #474, #479)
        # On Windows: Creates directories with atomic ACLs using win32file.CreateDirectory (Issue #400)
        self._secure_all_parent_directories(self.path.parent)
        self._todos: list[Todo] = []
        self._next_id: int = 1  # Track next available ID for O(1) generation
        self._lock = threading.RLock()  # Thread safety lock (reentrant for internal lock usage)
        self._lock_range: int = 0  # File lock range cache (Issue #361)
        self._dirty: bool = False  # Track if data has been modified (Issue #203)
        # File lock timeout to prevent indefinite hangs (Issue #396)
        # 30 seconds is a reasonable timeout for file operations
        self._lock_timeout: float = 30.0
        # Retry interval for non-blocking lock attempts (Issue #396)
        # 100ms allows for responsive retries without excessive CPU usage
        self._lock_retry_interval: float = 0.1
        # Gracefully handle load failures to allow object instantiation (Issue #456)
        # If the file is corrupted or malformed, log the error and start with empty state
        init_success = False
        try:
            self._load()
            init_success = True
        except RuntimeError as e:
            # _load() already created a backup and wrapped the error
            # Log the error and continue with empty state
            logger.warning(
                f"Failed to load todos from {self.path}: {e}. "
                f"Starting with empty state. Backup file created."
            )
            # Reset to empty state (already initialized above)
            self._todos = []
            self._next_id = 1
            self._dirty = False
            # Still mark as success since we handled the error gracefully
            init_success = True
        finally:
            # Register cleanup handler to save dirty data on exit (Issue #203)
            # IMPORTANT: Only register if initialization succeeded (Issue #525)
            # This prevents calling cleanup on partially initialized objects
            if init_success:
                atexit.register(self._cleanup)

    def _get_file_lock_range_from_handle(self, file_handle) -> tuple:
        """Get the Windows file lock range for mandatory locking.

        This method returns lock range parameters for Windows mandatory file
        locking using win32file.LockFileEx. On Windows, a fixed very large
        lock range is used to prevent deadlocks when the file size changes
        between lock acquisition and release (Issue #375, #426, #451).

        Args:
            file_handle: The open file handle (unused, kept for API compatibility).

        Returns:
            On Windows: A tuple of (low, high) representing the LENGTH to lock in bytes.
                The actual lock region starts from offset 0 (file beginning) and extends
                for (low + high << 32) bytes. Returns (0, 1) for exactly 4GB.
            On Unix: A placeholder value (ignored by fcntl.flock).

        Note:
            PYWIN32 API SEMANTICS (Issue #496):
            The pywin32 LockFileEx wrapper uses these parameters:
                LockFileEx(hFile, dwFlags, dwReserved,
                          NumberOfBytesToLockLow, NumberOfBytesToLockHigh,
                          overlapped)

            - The 4th and 5th parameters (returned by this method) specify the LENGTH
              to lock, NOT the offset. The offset is specified via the overlapped
              structure, which defaults to 0 (file start).
            - Therefore, (0, 1) means: lock 4GB bytes starting from file beginning
              (offset 0) to offset 4GB.

            - On Windows, uses win32file.LockFileEx for MANDATORY locking (Issue #451)
            - Mandatory locks enforce mutual exclusion on all systems
            - Returns (0, 1) representing exactly 4GB (0x100000000 bytes) of lock LENGTH
            - This approach prevents the issue where file grows between lock
              acquisition and release
            - On Unix, fcntl.flock doesn't use lock ranges, so value is ignored
        """
        if os.name == 'nt':  # Windows
            # Security fix for Issue #375, #426, and #451: Use a fixed very large
            # lock range with win32file.LockFileEx for mandatory locking
            #
            # Mandatory locking (Issue #451):
            # - Uses win32file.LockFileEx instead of msvcrt.locking
            # - Enforces mutual exclusion on ALL processes, not just cooperative ones
            # - Prevents malicious or unaware processes from writing concurrently
            # - Provides data integrity guarantees that advisory locks cannot
            #
            # PYWIN32 API SEMANTICS (Issue #496):
            # The pywin32 LockFileEx wrapper has signature:
            #   LockFileEx(hFile, dwFlags, dwReserved, NumberOfBytesToLockLow,
            #              NumberOfBytesToLockHigh, overlapped)
            #
            # - The 4th and 5th parameters specify the LENGTH to lock (not offset)
            # - The offset is specified via the overlapped structure (defaults to 0)
            # - We use a default OVERLAPPED() which locks from offset 0 (file start)
            #
            # Therefore, (0, 1) means: lock 4GB bytes starting from file beginning
            # - Length = 0 + (1 << 32) = 0x100000000 = 4294967296 bytes = exactly 4GB
            # - Offset = 0 (from default OVERLAPPED structure)
            #
            # Security fix for Issue #465: Starting from offset 0 instead of 0xFFFFFFFF
            # prevents lock failures on files smaller than 4GB. The previous approach
            # attempted to lock from beyond EOF, causing ERROR_LOCK_VIOLATION (error 33).
            # Security fix for Issue #469: Corrected from (0, 0xFFFFFFFF) to (0xFFFFFFFF, 0)
            # to accurately represent 4GB. The old value (0, 0xFFFFFFFF) would lock
            # ~16 Exabytes, which did not match the documented behavior.
            # Security fix for Issue #480: Corrected from (0xFFFFFFFF, 0) to (0, 1) to
            # represent exactly 4GB (0x100000000 bytes). The old value (0xFFFFFFFF, 0)
            # represented 4GB-1 (0xFFFFFFFF bytes), which is not exactly 4GB as documented.
            # Security fix for Issue #496: Clarified that (0, 1) specifies LENGTH, not offset.
            # The offset is 0 (file start) from the default OVERLAPPED structure.
            return (0, 1)
        else:
            # On Unix, fcntl.flock doesn't use lock ranges
            # Return a placeholder value (will be ignored)
            return 0

    def _acquire_file_lock(self, file_handle) -> None:
        """Acquire an exclusive file lock for multi-process safety (Issue #268, #451).

        Args:
            file_handle: The file handle to lock.

        Raises:
            IOError: If the lock cannot be acquired.
            RuntimeError: If lock acquisition times out (Issue #396).

        Note:
            PLATFORM DIFFERENCES (Issue #411, #451):

            Windows (win32file.LockFileEx):
            - Uses MANDATORY LOCKING - enforces mutual exclusion on ALL processes
            - Blocks ALL processes from writing, including malicious or unaware ones
            - Provides strong data integrity guarantees
            - Uses LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK flags
            - Non-blocking mode with retry to prevent hangs (Issue #396)

            Unix-like systems (fcntl.flock):
            - Provides strong synchronization guarantees
            - Uses non-blocking mode (LOCK_EX | LOCK_NB) with retry

            For Windows, a fixed 4GB lock LENGTH (0, 1) is used to prevent
            deadlocks when the file size changes between lock acquisition and
            release (Issue #375, #426, #451, #465, #469, #480, #496).

            IMPORTANT (Issue #496): The values (0, 1) represent LENGTH, not offset.
            The pywin32 LockFileEx wrapper specifies lock length via parameters and
            offset via the overlapped structure (which defaults to 0). Therefore,
            (0, 1) locks 4GB bytes starting from file offset 0 (file beginning).

            All file operations are serialized by self._lock (RLock), ensuring
            that acquire and release are always properly paired (Issue #366).

            Timeout mechanism (Issue #396):
            - Windows: Uses LOCKFILE_FAIL_IMMEDIATELY with retry loop and timeout
            - Unix: Uses LOCK_EX | LOCK_NB with retry loop and timeout
        """
        if os.name == 'nt':  # Windows
            # Security fix for Issue #514: Check for degraded mode
            if _is_degraded_mode():
                # Running without pywin32 - skip file locking
                # Log a warning that file locking is disabled
                logger.warning(
                    f"File locking DISABLED (degraded mode, Issue #514). "
                    f"Multi-process safety is NOT guaranteed. "
                    f"Install pywin32 for secure file locking."
                )
                # Mark as "locked" to maintain API consistency
                self._lock_range = None
                return

            # Windows locking: win32file.LockFileEx for MANDATORY locking (Issue #451)
            # SECURITY: Mandatory locks enforce mutual exclusion on ALL processes
            # - Prevents malicious or unaware processes from writing concurrently
            # - Provides data integrity guarantees that advisory locks cannot
            # - Uses win32file.LockFileEx instead of msvcrt.locking
            #
            # Security fix for Issue #429: Windows modules are imported at module level,
            # ensuring thread-safe initialization. No need to import here.

            try:
                # Get the Windows file handle from Python file object
                win_handle = win32file._get_osfhandle(file_handle.fileno())

                # Get the lock range (fixed large value for mandatory locking)
                lock_range_low, lock_range_high = self._get_file_lock_range_from_handle(file_handle)

                # Cache the lock range for use in _release_file_lock (Issue #351)
                # This ensures we use the same range for unlock
                self._lock_range = (lock_range_low, lock_range_high)

                # CRITICAL: Flush buffers before locking (Issue #390)
                # Python file objects have buffers that must be flushed before
                # locking to ensure data is synchronized to disk
                file_handle.flush()

                # Create overlapped structure for async operation
                overlapped = pywintypes.OVERLAPPED()

                # Timeout mechanism for lock acquisition (Issue #396)
                # Use LOCKFILE_FAIL_IMMEDIATELY with retry loop
                start_time = time.time()
                last_error = None

                # Lock flags: LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK
                lock_flags = win32con.LOCKFILE_FAIL_IMMEDIATELY | win32con.LOCKFILE_EXCLUSIVE_LOCK

                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= self._lock_timeout:
                        # Timeout exceeded - raise error with details
                        raise RuntimeError(
                            f"File lock acquisition timed out after {elapsed:.1f}s "
                            f"(timeout: {self._lock_timeout}s). "
                            f"This may indicate a competing process died while holding "
                            f"the lock or a deadlock condition. File: {file_handle.name}"
                        )

                    try:
                        # Try non-blocking mandatory lock (Issue #451)
                        # win32file.LockFileEx provides MANDATORY locking on Windows
                        # This blocks ALL processes from writing, not just cooperative ones
                        #
                        # PYWIN32 API (Issue #496):
                        # LockFileEx(hFile, dwFlags, dwReserved,
                        #            NumberOfBytesToLockLow, NumberOfBytesToLockHigh,
                        #            overlapped)
                        # - lock_range_low/high: LENGTH to lock (not offset)
                        # - overlapped: specifies offset (defaults to 0 = file start)
                        # - Therefore: locks from file start for 4GB bytes
                        win32file.LockFileEx(
                            win_handle,
                            lock_flags,
                            0,  # Reserved
                            lock_range_low,  # NumberOfBytesToLockLow (LENGTH, not offset)
                            lock_range_high,  # NumberOfBytesToLockHigh (LENGTH, not offset)
                            overlapped  # Specifies offset (defaults to 0)
                        )
                        # Lock acquired successfully
                        break
                    except pywintypes.error as e:
                        # Lock is held by another process
                        # Error code 33: ERROR_LOCK_VIOLATION
                        # Error code 167: ERROR_LOCK_FAILED
                        if e.winerror in (33, 167):
                            # Save error for potential reporting
                            last_error = e
                            # Wait before retrying
                            time.sleep(self._lock_retry_interval)
                            # Continue retry loop
                        else:
                            # Unexpected error - raise immediately
                            logger.error(f"Failed to acquire Windows mandatory lock: {e}")
                            raise

            except (pywintypes.error, RuntimeError) as e:
                if isinstance(e, RuntimeError):
                    # Re-raise timeout errors as-is
                    logger.error(f"Failed to acquire Windows mandatory lock: {e}")
                    raise
                else:
                    logger.error(f"Failed to acquire Windows mandatory lock: {e}")
                    raise
        else:  # Unix-like systems
            # Unix locking: fcntl.flock (Issue #411)
            # Provides strong synchronization guarantees
            # LOCK_EX = exclusive lock
            # LOCK_NB = non-blocking mode
            # Use retry loop with timeout for consistency with Windows (Issue #396)
            try:
                # Cache a placeholder lock range for consistency (Issue #351)
                # On Unix, this isn't used by fcntl.flock but we cache it
                # to maintain consistent API behavior across platforms
                self._lock_range = 0

                # Timeout mechanism for lock acquisition (Issue #396)
                # Use non-blocking mode with retry loop for consistency with Windows
                start_time = time.time()
                last_error = None

                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= self._lock_timeout:
                        # Timeout exceeded - raise error with details
                        raise RuntimeError(
                            f"File lock acquisition timed out after {elapsed:.1f}s "
                            f"(timeout: {self._lock_timeout}s). "
                            f"This may indicate a competing process died while holding "
                            f"the lock or a deadlock condition. File: {file_handle.name}"
                        )

                    try:
                        # Try non-blocking lock (LOCK_EX | LOCK_NB)
                        # This returns immediately with IOError if lock is held
                        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        # Lock acquired successfully
                        break
                    except IOError as e:
                        # Lock is held by another process
                        # Save error for potential reporting
                        last_error = e
                        # Wait before retrying
                        time.sleep(self._lock_retry_interval)
                        # Continue retry loop

            except (IOError, RuntimeError) as e:
                if isinstance(e, RuntimeError):
                    # Re-raise timeout errors as-is
                    logger.error(f"Failed to acquire Unix file lock: {e}")
                    raise
                else:
                    logger.error(f"Failed to acquire Unix file lock: {e}")
                    raise

    def _release_file_lock(self, file_handle) -> None:
        """Release a file lock for multi-process safety (Issue #268, #451).

        Args:
            file_handle: The file handle to unlock.

        Raises:
            IOError: If the lock cannot be released.

        Note:
            PLATFORM DIFFERENCES (Issue #411, #451):

            Windows (win32file.UnlockFile):
            - Mandatory lock release - enforces mutual exclusion
            - Must match exact lock length used during acquisition
            - Uses cached length to prevent deadlocks

            Unix-like systems (fcntl.flock):
            - Provides strong release guarantees
            - Simple unlock without range matching

            For Windows, the lock length matches the fixed 4GB LENGTH
            (0, 1) used during acquisition to avoid errors.
            Uses the cached lock length from _acquire_file_lock (Issue #351, #465, #469, #480, #496).

            IMPORTANT (Issue #496): The cached values (0, 1) represent LENGTH, not offset.
            The pywin32 UnlockFile wrapper takes the length to unlock as parameters.
            The offset is implied from the overlapped structure used during LockFileEx.
            Therefore, (0, 1) unlocks 4GB bytes starting from file offset 0 (file beginning).

            With the fixed length approach (Issue #375, #426, #451), file size
            changes between lock and unlock no longer cause deadlocks or unlock
            failures, as the locked region is always large enough.

            The lock length cache is thread-safe because all file operations are
            serialized by self._lock (RLock), ensuring proper acquire/release
            pairing (Issue #366).

            Error handling is consistent with _acquire_file_lock - exceptions
            are re-raised to ensure lock release failures are not silently
            ignored (Issue #376).
        """
        if os.name == 'nt':  # Windows
            # Security fix for Issue #514: Check for degraded mode
            if _is_degraded_mode():
                # Running without pywin32 - skip file unlocking
                # (nothing was locked in acquire)
                return

            # Windows unlocking: win32file.UnlockFile (Issue #451)
            # Mandatory lock release for strong synchronization
            # Unlock range must match lock range exactly (Issue #271)
            # Use the cached lock range from _acquire_file_lock (Issue #351)
            #
            # Security fix for Issue #429: Windows modules are imported at module level,
            # ensuring thread-safe initialization. No need to import here.

            try:
                # Get the Windows file handle from Python file object
                win_handle = win32file._get_osfhandle(file_handle.fileno())

                # Use the cached lock range from acquire to ensure consistency (Issue #351)
                # Validate lock range before using it (Issue #366)
                # Security fix (Issue #374): Raise exception instead of insecure fallback
                lock_range = self._lock_range
                if not isinstance(lock_range, tuple) or len(lock_range) != 2:
                    # Invalid lock range - this should never happen if acquire was called
                    # Security fix (Issue #374): Raise instead of falling back
                    raise RuntimeError(
                        f"Invalid lock range {lock_range} in _release_file_lock. "
                        f"This indicates acquire/release are not properly paired (Issue #366). "
                        f"Refusing to use insecure partial lock fallback."
                    )

                lock_range_low, lock_range_high = lock_range

                # Unlock the file using win32file.UnlockFile (Issue #451)
                # This releases the mandatory lock acquired by LockFileEx
                #
                # PYWIN32 API (Issue #496):
                # UnlockFile(hFile, NumberOfBytesToUnlockLow, NumberOfBytesToUnlockHigh)
                # - The parameters specify the LENGTH to unlock (must match lock length)
                # - The offset is specified via the overlapped structure used during LockFileEx
                # - Therefore: unlocks 4GB bytes starting from file start (offset 0)
                win32file.UnlockFile(
                    win_handle,
                    lock_range_low,  # NumberOfBytesToUnlockLow (LENGTH, must match lock)
                    lock_range_high  # NumberOfBytesToUnlockHigh (LENGTH, must match lock)
                )
            except (pywintypes.error, RuntimeError) as e:
                if isinstance(e, RuntimeError):
                    logger.error(f"Failed to release Windows mandatory lock: {e}")
                    raise
                else:
                    logger.error(f"Failed to release Windows mandatory lock: {e}")
                    raise
        else:  # Unix-like systems
            # Unix unlocking
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            except IOError as e:
                logger.error(f"Failed to release Unix file lock: {e}")
                raise

    def _secure_directory(self, directory: Path) -> None:
        """Set restrictive permissions on the storage directory.

        This method attempts to set restrictive permissions on the storage
        directory to protect sensitive data. The approach varies by platform:

        - Unix-like systems: Uses chmod(0o700) to set owner-only access.
          Raises RuntimeError if chmod fails.
        - Windows: Uses win32security to set restrictive ACLs.
          Raises RuntimeError if ACL setup fails.

        Args:
            directory: The directory path to secure.

        Raises:
            RuntimeError: If directory permissions cannot be set securely.

        Note:
            This method will raise an exception and prevent execution if
            secure directory permissions cannot be established. This ensures
            the application does not run with unprotected sensitive data (Issue #304).

            On Windows, pywin32 availability is verified in __init__ (Issue #414).
            This ensures early, clear error messages instead of runtime crashes.

            Security fix for Issue #514: In degraded mode without pywin32, directory
            security is skipped with a warning. This is UNSAFE for production use.
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
            # Security fix for Issue #514: Check for degraded mode
            if _is_degraded_mode():
                # Running without pywin32 - skip directory security
                # Log a warning that directory security is disabled
                logger.warning(
                    f"Directory security DISABLED (degraded mode, Issue #514). "
                    f"Directory {directory} may have insecure permissions. "
                    f"This is UNSAFE for production use. "
                    f"Install pywin32 for secure directory permissions."
                )
                return

            # Security fix for Issue #429: Windows modules are imported at module level,
            # ensuring thread-safe initialization. Modules are available immediately
            # when this code runs, preventing race conditions.

            # Attempt to use Windows ACLs for security (Issue #226)
            win32_success = False
            try:
                # Get the current user's SID using Windows API (Issue #229)
                # Use GetUserNameEx to get the primary domain instead of relying
                # on environment variables which can be manipulated or missing
                # Initialize domain to ensure it's always defined (Issue #234)
                domain = None

                # Security fix (Issue #329): Do NOT fall back to environment variables
                # when GetUserName fails. Environment variables can be manipulated by
                # the process or parent process, which is a security risk when setting ACLs.
                try:
                    user = win32api.GetUserName()
                except Exception as e:
                    # GetUserName failed - raise error immediately without fallback
                    raise RuntimeError(
                        "Cannot set Windows security: win32api.GetUserName() failed. "
                        "Unable to securely determine username. "
                        f"Install pywin32: pip install pywin32. Error: {e}"
                    ) from e

                # Validate user - do NOT use environment variable fallback (Issue #329)
                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                    # GetUserName returned invalid value - raise error
                    raise RuntimeError(
                        "Cannot set Windows security: win32api.GetUserName() returned invalid value. "
                        "Unable to securely determine username. "
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
                    # Validate that name is a string before parsing (Issue #349)
                    if not isinstance(name, str):
                        raise TypeError(
                            f"GetUserNameEx returned non-string value: {type(name).__name__}"
                        )
                    # Extract domain from the qualified DN
                    # Format: CN=user,OU=users,DC=domain,DC=com
                    parts = name.split(',')
                    # Build domain from all DC= parts (execute once, not in loop)
                    # Validate that split results have expected format (Issue #349)
                    dc_parts = []
                    for p in parts:
                        p = p.strip()
                        if p.startswith('DC='):
                            split_parts = p.split('=', 1)
                            if len(split_parts) >= 2:
                                dc_parts.append(split_parts[1])
                            else:
                                # Malformed DN - raise error instead of silently continuing (Issue #349)
                                raise ValueError(
                                    f"Malformed domain component in DN: '{p}'. "
                                    f"Expected format 'DC=value', got '{p}'"
                                )
                    if dc_parts:
                        domain = '.'.join(dc_parts)
                    else:
                        # Fallback to local computer if no domain found
                        domain = win32api.GetComputerName()
                except (TypeError, ValueError) as e:
                    # Parsing failed due to invalid format - raise error (Issue #349)
                    # These exceptions indicate GetUserNameEx returned invalid data
                    # We should NOT silently fall back to GetComputerName in this case
                    # as it could lead to insecure configuration
                    raise RuntimeError(
                        f"Cannot set Windows security: GetUserNameEx returned invalid data. "
                        f"Unable to parse domain information. Error: {e}. "
                        f"Install pywin32: pip install pywin32"
                    ) from e
                except Exception:
                    # GetUserNameEx failed (not a parsing error) - fallback to GetComputerName
                    # This is expected in non-domain environments
                    # Security fix (Issue #329): Do NOT fall back to environment variables
                    try:
                        domain = win32api.GetComputerName()
                    except Exception as e:
                        # GetComputerName also failed - raise error
                        raise RuntimeError(
                            "Cannot set Windows security: Unable to determine domain. "
                            f"win32api.GetComputerName() failed. "
                            f"Install pywin32: pip install pywin32. Error: {e}"
                        ) from e

                # Validate domain - ensure it's defined before LookupAccountName (Issue #234)
                # Security fix (Issue #329): Do NOT fall back to environment variables
                if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                    raise RuntimeError(
                        "Cannot set Windows security: Unable to determine domain. "
                        "Domain is None or empty after Windows API calls. "
                        "Install pywin32: pip install pywin32"
                    )

                # Validate user before calling LookupAccountName (Issue #240)
                # Ensure user is initialized and non-empty to prevent passing invalid values
                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                    raise ValueError(
                        f"Invalid user name '{user}': Cannot set Windows security. "
                        f"GetUserName() returned invalid value."
                    )

                # Security fix (Issue #329): Do NOT fall back to environment variables
                # when LookupAccountName fails. Environment variables can be manipulated.
                try:
                    sid, _, _ = win32security.LookupAccountName(domain, user)
                except Exception as e:
                    # LookupAccountName failed - raise error without fallback
                    raise RuntimeError(
                        f"Failed to set Windows ACLs: Unable to lookup account '{user}' in domain '{domain}'. "
                        f"Install pywin32: pip install pywin32. Error: {e}"
                    ) from e

                # Create a security descriptor with owner-only access
                security_descriptor = win32security.SECURITY_DESCRIPTOR()
                security_descriptor.SetSecurityDescriptorOwner(sid, False)

                # Create a DACL (Discretionary Access Control List)
                # Use minimal permissions instead of FILE_ALL_ACCESS (Issue #239)
                # Following the principle of least privilege (Issue #249)
                # Do NOT use FILE_GENERIC_READ | FILE_GENERIC_WRITE as they include DELETE
                # Use explicit minimal permissions
                # Remove FILE_READ_EA and FILE_WRITE_EA (Issue #254)
                # Add DELETE permission to allow file management (Issue #274)
                # This prevents disk space leaks from old/temporary files
                dacl = win32security.ACL()
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    win32con.FILE_LIST_DIRECTORY |
                    win32con.FILE_ADD_FILE |
                    win32con.FILE_READ_ATTRIBUTES |
                    win32con.FILE_WRITE_ATTRIBUTES |
                    win32con.DELETE |
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

            except Exception as e:
                # Failed to set ACLs - raise error for security (Issue #304)
                # Note: ImportError for missing pywin32 is now caught at module import time (Issue #324)
                raise RuntimeError(
                    f"Failed to set Windows ACLs on {directory}: {e}. "
                    f"Cannot continue without secure directory permissions. "
                    f"Install pywin32: pip install pywin32"
                ) from e

    def _create_and_secure_directories(self, target_directory: Path) -> None:
        """Create and secure directories atomically to prevent race condition (Issue #395).

        This method creates directories one by one from the root towards the target,
        securing each directory immediately after creation. This eliminates the
        security window that exists when using mkdir(parents=True) followed by
        _secure_directory, where a crash could leave directories with insecure
        inherited ACLs on Windows.

        Args:
            target_directory: The target directory to create and secure.

        Raises:
            RuntimeError: If any directory cannot be created or secured.

        Note:
            This is a security fix for Issue #395 and Issue #400. On Windows, we use
            win32file.CreateDirectory() with a security descriptor to create directories
            atomically with the correct ACLs, eliminating the time window entirely.

            On Unix, we use mkdir() followed by chmod() which is still atomic enough
            for practical purposes (the time window is microseconds).

            Race condition fix (Issue #409): Implements retry mechanism with exponential
            backoff to handle TOCTOU (Time-of-Check-Time-of-Use) race conditions where
            multiple threads/processes attempt to create the same directory simultaneously.

            Security fix for Issue #481: When FileExistsError is caught (indicating
            another process created the directory), ALWAYS verify and fix permissions
            by calling _secure_directory, rather than checking permissions first and
            conditionally fixing them. This ensures we never assume the other process
            created the directory securely. The verification is critical because we
            cannot trust that another process created the directory with correct permissions.

            The algorithm:
            1. Build list of directories from root to target
            2. For each directory that doesn't exist:
               a. On Windows: Create with win32file.CreateDirectory() + security descriptor
               b. On Unix: Create with mkdir() and immediately chmod()
            3. If creation fails with FileExistsError, ALWAYS verify and secure directory
            4. Use exponential backoff for retries (max 5 attempts, ~500ms total)
        """
        # Build list of directories from outermost to innermost
        # Start from the target and walk up to find what needs to be created
        directories_to_create = []
        current = target_directory

        # Walk up from target to root, collecting non-existent directories
        while current != current.parent:  # Stop at filesystem root
            if not current.exists():
                directories_to_create.append(current)
            current = current.parent

        # Reverse to create from outermost to innermost
        directories_to_create.reverse()

        # Create and secure each directory with retry mechanism (Issue #409)
        import time
        max_retries = 5
        base_delay = 0.01  # 10ms starting delay

        for directory in directories_to_create:
            # Retry loop with exponential backoff for race condition handling
            success = False
            last_error = None

            for attempt in range(max_retries):
                try:
                    if os.name == 'nt':  # Windows - use atomic directory creation (Issue #400)
                        # Security fix for Issue #514: Check for degraded mode
                        if _is_degraded_mode():
                            # Running without pywin32 - fall back to Unix-style directory creation
                            # Security fix for Issue #474 and #479: Temporarily restrict umask
                            old_umask = os.umask(0o077)
                            try:
                                directory.mkdir(mode=0o700)
                            finally:
                                os.umask(old_umask)
                            logger.warning(
                                f"Using degraded directory creation (Issue #514). "
                                f"Directory {directory} may have insecure permissions. "
                                f"Install pywin32 for secure directory creation."
                            )
                            success = True
                            break

                        # Security fix for Issue #429: Windows modules are imported at module level,
                        # ensuring thread-safe initialization. Modules are available immediately.

                        # Security fix for Issue #400: Use CreateDirectory with security descriptor
                        # to eliminate the time window between directory creation and ACL application.
                        # This is truly atomic - the directory is created with the correct ACLs
                        # from the very moment it exists.
                        #
                        # First, prepare the security descriptor
                        # Get the current user's SID
                        user = win32api.GetUserName()

                        # Fix Issue #251: Extract pure username if GetUserName returns
                        # 'COMPUTERNAME\\username' or 'DOMAIN\\username' format
                        if '\\' in user:
                            parts = user.rsplit('\\', 1)
                            if len(parts) == 2:
                                user = parts[1]

                        # Get domain
                        try:
                            name = win32api.GetUserNameEx(win32con.NameFullyQualifiedDN)
                            if not isinstance(name, str):
                                raise TypeError(
                                    f"GetUserNameEx returned non-string value: {type(name).__name__}"
                                )
                            # Extract domain from the qualified DN
                            parts = name.split(',')
                            dc_parts = []
                            for p in parts:
                                p = p.strip()
                                if p.startswith('DC='):
                                    split_parts = p.split('=', 1)
                                    if len(split_parts) >= 2:
                                        dc_parts.append(split_parts[1])
                            if dc_parts:
                                domain = '.'.join(dc_parts)
                            else:
                                domain = win32api.GetComputerName()
                        except (TypeError, ValueError):
                            raise RuntimeError(
                                f"Cannot set Windows security: GetUserNameEx returned invalid data. "
                                f"Install pywin32: pip install pywin32"
                            )
                        except Exception:
                            domain = win32api.GetComputerName()

                        # Validate domain
                        if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                            raise RuntimeError(
                                "Cannot set Windows security: Unable to determine domain. "
                                "Install pywin32: pip install pywin32"
                            )

                        # Validate user
                        if not user or not isinstance(user, str) or len(user.strip()) == 0:
                            raise ValueError(
                                f"Invalid user name '{user}': Cannot set Windows security."
                            )

                        # Lookup account SID
                        try:
                            sid, _, _ = win32security.LookupAccountName(domain, user)
                        except Exception as e:
                            raise RuntimeError(
                                f"Failed to set Windows ACLs: Unable to lookup account '{user}'. "
                                f"Install pywin32: pip install pywin32. Error: {e}"
                            ) from e

                        # Create security descriptor with owner-only access
                        security_descriptor = win32security.SECURITY_DESCRIPTOR()
                        security_descriptor.SetSecurityDescriptorOwner(sid, False)

                        # Create DACL with minimal permissions (Issue #239, #249, #254, #274)
                        dacl = win32security.ACL()
                        dacl.AddAccessAllowedAce(
                            win32security.ACL_REVISION,
                            win32con.FILE_LIST_DIRECTORY |
                            win32con.FILE_ADD_FILE |
                            win32con.FILE_READ_ATTRIBUTES |
                            win32con.FILE_WRITE_ATTRIBUTES |
                            win32con.DELETE |
                            win32con.SYNCHRONIZE,
                            sid
                        )

                        security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)

                        # Create SACL for auditing (Issue #244)
                        sacl = win32security.ACL()
                        security_descriptor.SetSecurityDescriptorSacl(0, sacl, 0)

                        # Set DACL protection to prevent inheritance (Issue #256)
                        security_descriptor.SetSecurityDescriptorControl(
                            win32security.SE_DACL_PROTECTED, 1
                        )

                        # Create directory atomically with security descriptor (Issue #400)
                        # win32file.CreateDirectory creates the directory with the specified
                        # security attributes atomically - there's no time window where
                        # the directory exists with insecure permissions.
                        win32file.CreateDirectory(
                            str(directory),
                            security_descriptor
                        )

                    else:  # Unix-like systems
                        # On Unix, create the directory and immediately secure it
                        # The time window is extremely small (microseconds) and acceptable
                        # for practical purposes
                        #
                        # Security fix for Issue #419: Do NOT use exist_ok=True
                        # If we use exist_ok=True, the FileExistsError handling below
                        # won't be triggered, and we won't properly handle the race
                        # condition where the directory is created by another process.
                        # Instead, let FileExistsError be raised and handle it in the
                        # exception handler below.
                        #
                        # Security fix for Issue #439: Use mode=0o700 to create directory
                        # with restrictive permissions from the start. This ensures that
                        # even if _secure_directory fails (e.g., due to race condition
                        # or error), the directory has secure permissions and is not left
                        # with umask-dependent insecure permissions.
                        #
                        # Security fix for Issue #474 and #479: Temporarily restrict umask
                        # to 0o077 during directory creation to prevent umask from making the
                        # directory more permissive than intended. This eliminates the
                        # TOCTOU security window where mkdir(mode=0o700) could create a
                        # directory with 0o755 permissions if umask is 0o022. The umask
                        # restriction ensures atomic creation with secure permissions.
                        old_umask = os.umask(0o077)  # Restrictive umask for mkdir
                        try:
                            directory.mkdir(mode=0o700)  # Create with secure permissions
                        finally:
                            os.umask(old_umask)  # Restore original umask
                        self._secure_directory(directory)  # Ensure consistency

                    # If we get here, creation succeeded
                    success = True
                    break

                except FileExistsError:
                    # Race condition fix (Issue #409): Directory was created by another thread/process
                    # between our check and creation attempt.
                    #
                    # Security fix for Issue #424: Always verify and secure the directory,
                    # regardless of platform. This prevents TOCTOU vulnerabilities where
                    # another process could create the directory with insecure permissions.
                    #
                    # Security fix for Issue #481: ALWAYS call _secure_directory to verify
                    # and fix permissions, rather than checking first. This ensures we don't
                    # assume the other process created the directory securely. The verification
                    # is critical because we cannot trust that another process (especially a
                    # malicious or compromised one) created the directory with correct permissions.
                    # By always securing, we guarantee the directory meets our security requirements.
                    if directory.exists():
                        try:
                            # Security fix for Issue #481: Always verify permissions after catching
                            # FileExistsError, regardless of platform. Do NOT check permissions first
                            # and conditionally call _secure_directory - this could leave a window
                            # where we proceed with insecure permissions. Instead, ALWAYS secure to
                            # ensure correctness, even if it's slightly less efficient.
                            #
                            # This is safe because _secure_directory is idempotent and efficient.
                            # On Unix: chmod(0o700) is a fast syscall even if permissions are correct.
                            # On Windows: ACL reapplication is necessary because verification is complex.
                            #
                            # The tradeoff: A few extra microseconds of syscall time for guaranteed
                            # security. This is acceptable because directory creation is a rare operation
                            # (only happens during initialization), not a hot path.
                            self._secure_directory(directory)

                            # Directory exists and is now secure
                            # Consider this a success (another process created it for us)
                            success = True
                            logger.debug(
                                f"Directory {directory} already exists (created by competing process). "
                                f"Verified and secured directory to ensure correct permissions (Issue #481)."
                            )
                            break
                        except Exception as verify_error:
                            # Failed to verify security - save error and retry
                            last_error = verify_error
                            logger.debug(
                                f"Attempt {attempt + 1}/{max_retries}: Directory {directory} "
                                f"exists but verification failed: {verify_error}. Retrying..."
                            )
                    else:
                        # Directory doesn't exist but we got FileExistsError
                        # This is unusual - save error and retry
                        last_error = e
                        logger.debug(
                            f"Attempt {attempt + 1}/{max_retries}: Got FileExistsError but "
                            f"{directory} doesn't exist. Retrying..."
                        )

                    # Exponential backoff before retry
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)

                except Exception as e:
                    # Non-retryable error - save and break out of retry loop
                    last_error = e
                    break

            # After all retries, check if we succeeded
            if not success:
                # If we fail to create or secure a directory after all retries,
                # raise an error to prevent running with insecure directories
                raise RuntimeError(
                    f"Failed to create and secure directory {directory} after {max_retries} attempts. "
                    f"Last error: {last_error}. "
                    f"Cannot continue without secure directory permissions."
                ) from last_error

    def _acquire_directory_lock(self, directory: Path) -> None:
        """Acquire a lock file for directory creation to prevent TOCTOU race conditions.

        This method creates a lock file in the parent directory to ensure atomic
        directory creation. The lock prevents multiple processes from creating the
        same directory concurrently, which could lead to permission issues.

        This is a security fix for Issue #521 to address TOCTOU race conditions
        in directory creation.

        Args:
            directory: The directory for which to acquire a lock.

        Raises:
            RuntimeError: If the lock cannot be acquired after multiple attempts.
            OSError: If the lock file cannot be created.
        """
        # Use the parent directory for the lock file location
        # If parent doesn't exist, we need to handle that
        parent_dir = directory.parent

        # Create a lock file path
        # Use a hash of the directory path to avoid filesystem issues
        dir_hash = hashlib.sha256(str(directory).encode()).hexdigest()[:16]
        lock_path = parent_dir / f".flywheel_lock_{dir_hash}.lock"

        # Try to acquire the lock with retries
        max_retries = 10
        base_delay = 0.005  # 5ms starting delay

        for attempt in range(max_retries):
            try:
                # Try to create the lock file exclusively (atomic operation)
                # This uses O_CREAT | O_EXCL flags which are atomic
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)

                # Lock acquired successfully
                try:
                    # Write our PID to the lock file for debugging
                    os.write(fd, str(os.getpid()).encode())
                finally:
                    os.close(fd)

                # Lock acquired - store the lock path for cleanup
                if not hasattr(self, '_directory_locks'):
                    self._directory_locks = []
                self._directory_locks.append(lock_path)

                return

            except FileExistsError:
                # Lock file exists - check if it's stale (from a crashed process)
                try:
                    # Try to read the lock file
                    with open(lock_path, 'r') as f:
                        pid_str = f.read().strip()

                    # Check if the process is still running
                    try:
                        pid = int(pid_str)
                        # Try to send signal 0 to check if process exists
                        os.kill(pid, 0)
                        # Process is still running - lock is valid
                        # Wait and retry
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            time.sleep(delay)
                            continue
                        else:
                            raise RuntimeError(
                                f"Could not acquire directory lock for {directory} "
                                f"after {max_retries} attempts. Lock file: {lock_path}"
                            )
                    except (OSError, ValueError, ProcessLookupError):
                        # Process is not running - stale lock file
                        # Remove it and retry
                        try:
                            os.remove(lock_path)
                            # Continue to next iteration to try acquiring again
                            continue
                        except OSError:
                            # Someone else removed it or we can't remove it
                            # Just retry
                            if attempt < max_retries - 1:
                                delay = base_delay * (2 ** attempt)
                                time.sleep(delay)
                                continue
                            else:
                                raise RuntimeError(
                                    f"Could not acquire directory lock for {directory} "
                                    f"after {max_retries} attempts"
                                )

                except (OSError, IOError) as e:
                    # Can't read lock file - treat as locked and retry
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        raise RuntimeError(
                            f"Could not acquire directory lock for {directory}: {e}"
                        ) from e

            except OSError as e:
                # Other error creating lock file
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(
                        f"Failed to create lock file for {directory}: {e}"
                    ) from e

        # Should not reach here
        raise RuntimeError(
            f"Failed to acquire directory lock for {directory} after {max_retries} attempts"
        )

    def _release_directory_lock(self, directory: Path) -> None:
        """Release a directory lock file.

        This method removes the lock file created by _acquire_directory_lock.

        Args:
            directory: The directory for which to release the lock.
        """
        # Calculate the lock path the same way as in _acquire_directory_lock
        parent_dir = directory.parent
        dir_hash = hashlib.sha256(str(directory).encode()).hexdigest()[:16]
        lock_path = parent_dir / f".flywheel_lock_{dir_hash}.lock"

        # Remove the lock file if it exists
        try:
            if lock_path.exists():
                os.remove(lock_path)

            # Remove from our tracking list
            if hasattr(self, '_directory_locks') and lock_path in self._directory_locks:
                self._directory_locks.remove(lock_path)

        except OSError:
            # Lock file might have been removed by another process
            # This is not a critical error
            pass

    def _secure_all_parent_directories(self, directory: Path) -> None:
        """Secure all parent directories with restrictive permissions.

        This method secures not just the final directory, but all parent
        directories that may have been created by mkdir(parents=True).
        This is critical on Windows where mkdir's mode parameter is ignored
        and parent directories may inherit insecure default permissions.

        The method walks up the directory tree from the target directory
        to the root (or until it finds a directory that's already secured),
        applying _secure_directory to each one.

        Args:
            directory: The target directory whose parents should be secured.

        Raises:
            RuntimeError: If any directory cannot be created or secured.

        Note:
            This is a security fix for Issue #369, #441, and #476. This method is now
            called on ALL platforms (Windows and Unix) to ensure parent directories
            are secured even if they were created by other processes.

            Security fix for Issue #476: This method now handles TOCTOU (Time-of-Check-
            Time-of-Use) race conditions where directories might be created by other
            processes with insecure permissions. The implementation tries to secure
            each directory and handles the case where it doesn't exist gracefully,
            rather than checking existence first. This ensures that if a directory
            is created by another process at any point, it will be secured.

            Security fix for Issue #486: This method now CREATES directories if they
            don't exist, eliminating the race condition window between
            _create_and_secure_directories and _secure_all_parent_directories. By
            combining creation and securing in a single method, we ensure atomicity
            and eliminate the security window where directories could be created with
            insecure permissions.

            Security fix for Issue #521: This method now uses dedicated lock files
            to prevent TOCTOU race conditions in directory creation. The lock files
            ensure that the check-exist-create sequence is atomic, eliminating the
            window where multiple processes could race to create the same directory.

            On Windows: When mkdir creates parent directories, they inherit
            default permissions which may be too permissive. By explicitly
            securing each parent directory, we ensure the entire directory chain
            is protected with proper ACLs.

            On Unix: This is less critical since mkdir's mode parameter works,
            but we still apply it for defense in depth. Parent directories might
            have been created by other processes with insecure umask settings.
        """
        # Get all parent directories from root to target
        # We want to secure them in order: from outermost to innermost
        # This ensures that if we need to create any intermediate structure,
        # we do it from the outside in
        parents_to_secure = []

        # Start from the target directory and walk up
        current = directory
        while current != current.parent:  # Stop at filesystem root
            parents_to_secure.append(current)
            current = current.parent

        # Reverse to secure from outermost to innermost
        parents_to_secure.reverse()

        # Security fix for Issue #486: Create and secure each parent directory atomically
        # This eliminates the race condition window between the separate
        # _create_and_secure_directories call and _secure_all_parent_directories call.
        # By combining creation and securing in a single loop, we ensure that directories
        # are created and secured in one atomic operation.
        for parent_dir in parents_to_secure:
            # Security fix for Issue #521: Acquire lock before checking/creating directory
            # This prevents TOCTOU race conditions where multiple processes could
            # race between the exists() check and mkdir() call.
            lock_acquired = False
            try:
                self._acquire_directory_lock(parent_dir)
                lock_acquired = True
            except RuntimeError as lock_error:
                # If we can't acquire the lock, it means another process is creating
                # this directory. Wait a bit and check if it gets created.
                logger.debug(f"Could not acquire lock for {parent_dir}: {lock_error}")
                if parent_dir.exists():
                    # Directory was created by another process, just secure it
                    try:
                        self._secure_directory(parent_dir)
                        continue
                    except Exception as secure_error:
                        logger.warning(f"Failed to secure directory {parent_dir}: {secure_error}")
                        continue
                else:
                    # Directory doesn't exist and we can't create it
                    logger.warning(f"Cannot create {parent_dir}: lock acquisition failed")
                    continue

            # Retry loop for handling race conditions (Issue #409, #486)
            import time
            max_retries = 5
            base_delay = 0.01  # 10ms starting delay
            success = False
            last_error = None

            try:
                for attempt in range(max_retries):
                    try:
                        # Security fix for Issue #521: With lock held, check and create directory
                        # The lock ensures this sequence is atomic - no other process can
                        # create the directory between the check and creation.
                        if not parent_dir.exists():
                            if os.name == 'nt':  # Windows - use atomic directory creation (Issue #400)
                                # Security fix for Issue #514: Check for degraded mode
                                if _is_degraded_mode():
                                    # Running without pywin32 - fall back to Unix-style directory creation
                                    # Security fix for Issue #474 and #479: Temporarily restrict umask
                                    old_umask = os.umask(0o077)
                                    try:
                                        parent_dir.mkdir(mode=0o700)
                                    finally:
                                        os.umask(old_umask)
                                    logger.warning(
                                        f"Using degraded directory creation (Issue #514). "
                                        f"Directory {parent_dir} may have insecure permissions. "
                                        f"Install pywin32 for secure directory creation."
                                    )
                            else:
                                # Security fix for Issue #429: Windows modules are imported at module level,
                                # ensuring thread-safe initialization. Modules are available immediately.

                                # Use CreateDirectory with security descriptor (Issue #400)
                                user = win32api.GetUserName()

                                # Fix Issue #251: Extract pure username
                                if '\\' in user:
                                    parts = user.rsplit('\\', 1)
                                    if len(parts) == 2:
                                        user = parts[1]

                                # Get domain
                                try:
                                    name = win32api.GetUserNameEx(win32con.NameFullyQualifiedDN)
                                    if not isinstance(name, str):
                                        raise TypeError(
                                            f"GetUserNameEx returned non-string value: {type(name).__name__}"
                                        )
                                    parts = name.split(',')
                                    dc_parts = []
                                    for p in parts:
                                        p = p.strip()
                                        if p.startswith('DC='):
                                            split_parts = p.split('=', 1)
                                            if len(split_parts) >= 2:
                                                dc_parts.append(split_parts[1])
                                    if dc_parts:
                                        domain = '.'.join(dc_parts)
                                    else:
                                        domain = win32api.GetComputerName()
                                except (TypeError, ValueError):
                                    raise RuntimeError(
                                        f"Cannot set Windows security: GetUserNameEx returned invalid data. "
                                        f"Install pywin32: pip install pywin32"
                                    )
                                except Exception:
                                    domain = win32api.GetComputerName()

                                # Validate domain
                                if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                                    raise RuntimeError(
                                        "Cannot set Windows security: Unable to determine domain. "
                                        "Install pywin32: pip install pywin32"
                                    )

                                # Validate user
                                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                                    raise ValueError(
                                        f"Invalid user name '{user}': Cannot set Windows security."
                                    )

                                # Lookup account SID
                                try:
                                    sid, _, _ = win32security.LookupAccountName(domain, user)
                                except Exception as e:
                                    raise RuntimeError(
                                        f"Failed to set Windows ACLs: Unable to lookup account '{user}'. "
                                        f"Install pywin32: pip install pywin32. Error: {e}"
                                    ) from e

                                # Create security descriptor
                                security_descriptor = win32security.SECURITY_DESCRIPTOR()
                                security_descriptor.SetSecurityDescriptorOwner(sid, False)

                                # Create DACL with minimal permissions
                                dacl = win32security.ACL()
                                dacl.AddAccessAllowedAce(
                                    win32security.ACL_REVISION,
                                    win32con.FILE_LIST_DIRECTORY |
                                    win32con.FILE_ADD_FILE |
                                    win32con.FILE_READ_ATTRIBUTES |
                                    win32con.FILE_WRITE_ATTRIBUTES |
                                    win32con.DELETE |
                                    win32con.SYNCHRONIZE,
                                    sid
                                )

                                security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)

                                # Create SACL for auditing
                                sacl = win32security.ACL()
                                security_descriptor.SetSecurityDescriptorSacl(0, sacl, 0)

                                # Set DACL protection
                                security_descriptor.SetSecurityDescriptorControl(
                                    win32security.SE_DACL_PROTECTED, 1
                                )

                                # Create directory atomically with security descriptor
                                win32file.CreateDirectory(
                                    str(parent_dir),
                                    security_descriptor
                                )

                        else:  # Unix-like systems
                            # Security fix for Issue #474 and #479: Temporarily restrict umask
                            # to 0o077 during directory creation
                            old_umask = os.umask(0o077)
                            try:
                                parent_dir.mkdir(mode=0o700)
                            finally:
                                os.umask(old_umask)

                    # Always secure the directory (Issue #481, #486)
                    # Even if we just created it, call _secure_directory to ensure consistency
                    # This is safe because _secure_directory is idempotent
                    self._secure_directory(parent_dir)

                    # Success - break out of retry loop
                    success = True
                    break

                except FileExistsError:
                    # Security fix for Issue #481: Directory was created by another process
                    # Always verify and secure it, don't just assume it's secure
                    if parent_dir.exists():
                        try:
                            self._secure_directory(parent_dir)
                            success = True
                            break
                        except Exception as verify_error:
                            last_error = verify_error
                            if attempt < max_retries - 1:
                                delay = base_delay * (2 ** attempt)
                                time.sleep(delay)
                    else:
                        # Directory doesn't exist but we got FileExistsError
                        last_error = Exception("Got FileExistsError but directory doesn't exist")
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            time.sleep(delay)

                except PermissionError as e:
                    # Security fix for Issue #434: Handle PermissionError gracefully
                    # when parent directories are owned by another user or have restrictive
                    # permissions preventing ACL/chmod modification. Log a warning and
                    # continue rather than crashing the application.
                    logger.warning(
                        f"Cannot set secure permissions on {parent_dir}: {e}. "
                        f"This directory may be owned by another user or have restrictive "
                        f"permissions. The application will continue, but this directory "
                        f"may have less restrictive permissions than desired."
                    )
                    # Mark as success to continue with other directories
                    # The immediate application directory will still be secured separately
                    success = True
                    break

                except Exception as e:
                    # Non-retryable error
                    last_error = e
                    break

            # After all retries, check if we succeeded
            if not success:
                # Security fix for Issue #434: Check if the error is permission-related
                # If so, log a warning and continue instead of crashing
                error_is_permission_related = (
                    isinstance(last_error, PermissionError) or
                    (isinstance(last_error, RuntimeError) and
                     ("Permission denied" in str(last_error) or
                      "Cannot continue without secure directory permissions" in str(last_error)))
                )

                if error_is_permission_related:
                    # Log a warning and continue
                    logger.warning(
                        f"Cannot secure directory {parent_dir}: {last_error}. "
                        f"This may be due to insufficient permissions. The application will "
                        f"continue, but this directory may have less restrictive permissions."
                    )
                    # Continue to next directory instead of raising
                    continue
                else:
                    # For other errors, still raise to prevent running with insecure state
                    raise RuntimeError(
                        f"Failed to create and secure directory {parent_dir} after {max_retries} attempts. "
                        f"Last error: {last_error}. "
                        f"Cannot continue without secure directory permissions."
                    ) from last_error
            finally:
                # Security fix for Issue #521: Always release the lock, even if an error occurred
                if lock_acquired:
                    self._release_directory_lock(parent_dir)

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

        Note on file truncation (Issue #370):
        This implementation uses tempfile.mkstemp() + os.replace() which
        naturally prevents data corruption from size reduction:
        - mkstemp creates a new empty file (no old data remnants possible)
        - os.replace atomically replaces the target file
        This is superior to manual truncation as it's atomic and safer.
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

            File truncation (Issue #370): Uses tempfile.mkstemp() + os.replace()
            which naturally prevents data corruption from size reduction by creating
            a new empty file and atomically replacing the target.
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

    def health_check(self) -> bool:
        """Check if storage backend is healthy and functional.

        This method performs a quick diagnostic check to verify that:
        1. The storage directory exists and is writable
        2. File locks can be acquired and released
        3. Temporary files can be created and cleaned up

        This is useful for startup diagnostics and configuration validation.

        Returns:
            True if the storage backend is healthy, False otherwise.

        Example:
            >>> storage = Storage()
            >>> if storage.health_check():
            ...     print("Storage is healthy")
            ... else:
            ...     print("Storage has issues")
        """
        import tempfile

        try:
            # Create a test temporary file in the storage directory
            fd, temp_path = tempfile.mkstemp(
                dir=self.path.parent,
                prefix=".health_check_",
                suffix=".tmp"
            )

            try:
                # Try to acquire a file lock on the temp file
                # This tests both write permissions and locking mechanism
                self._acquire_file_lock(os.fdopen(fd, 'r'))

                # If we got here, we can write and lock successfully
                # Release the lock
                self._release_file_lock(os.fdopen(fd, 'r'))

                # Clean up the temp file
                try:
                    os.close(fd)
                except:
                    pass  # Already closed or invalid
                os.remove(temp_path)

                return True

            except Exception:
                # Lock acquisition failed - clean up and return False
                try:
                    os.close(fd)
                except:
                    pass
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
                return False

        except (OSError, IOError, PermissionError):
            # Cannot create temp file - directory doesn't exist or isn't writable
            return False
        except Exception:
            # Any other error indicates unhealthy storage
            return False

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
