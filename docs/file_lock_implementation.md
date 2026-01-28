# File Lock Implementation Documentation

## Overview

This document clarifies the file lock implementation in `src/flywheel/storage.py`, specifically addressing concerns raised in Issue #856.

## Issue #856 Analysis

**Claim:** "代码中并未展示基于文件的锁（.lock file）的具体实现逻辑"

**Reality:** The file-based lock implementation is **fully implemented** in the codebase.

## Implementation Details

### 1. Windows Degraded Mode (without pywin32)

**Location:** `src/flywheel/storage.py:950-1028`

When pywin32 is not available on Windows, the system uses a `.lock` file-based mechanism:

```python
# Line 950-1028
if _is_degraded_mode():
    # Use file-based lock mechanism with automatic stale lock cleanup
    lock_file_path = file_handle.name + ".lock"

    # Try to create lock file exclusively (atomic operation)
    with open(lock_file_path, 'x') as lock_file:
        # Write lock metadata for debugging and stale lock detection
        lock_file.write(f"pid={os.getpid()}\n")
        lock_file.write(f"locked_at={time.time()}\n")

    # Stale lock detection (line 996-1007)
    stale_threshold = 300  # 5 minutes
    if locked_at and (time.time() - locked_at) > stale_threshold:
        # Remove stale lock and retry
        os.unlink(lock_file_path)
```

**Features:**
- ✅ Atomic lock file creation using `open(..., 'x')`
- ✅ PID tracking for debugging
- ✅ Timestamp tracking for stale lock detection
- ✅ Automatic stale lock cleanup (5-minute threshold)
- ✅ Timeout and retry mechanism

### 2. Unix Degraded Mode (without fcntl)

**Location:** `src/flywheel/storage.py:1126-1201`

When fcntl is not available on Unix systems, the system uses a `.lock` directory-based mechanism:

```python
# Line 1126-1201
if _is_degraded_mode():
    # Implement file-based lock using atomic mkdir operation
    lock_dir = Path(str(file_handle.name) + ".lock")
    lock_pid_file = lock_dir / "pid"

    # Try to create lock directory (atomic operation)
    lock_dir.mkdir(exist_ok=False)

    # Write our PID to the lock file for debugging
    lock_pid_file.write_text(str(os.getpid()))

    # Stale lock detection using PID checking
    os.kill(pid, 0)  # Check if process is still running
```

**Features:**
- ✅ Atomic lock directory creation using `mkdir(exist_ok=False)`
- ✅ PID tracking for process verification
- ✅ Stale lock detection via `os.kill(pid, 0)`
- ✅ Automatic cleanup of stale locks

### 3. Lock Release Mechanism

**Windows (line 1298-1320):**
```python
if _is_degraded_mode():
    if hasattr(self, '_lock_range') and self._lock_range == "filelock":
        lock_file_path = file_handle.name + ".lock"
        os.unlink(lock_file_path)  # Remove lock file
```

**Unix (line 1370-1410):**
```python
if _is_degraded_mode():
    if isinstance(self._lock_range, str) and self._lock_range.endswith('.lock'):
        lock_dir = Path(self._lock_range)
        lock_dir.rmdir()  # Remove lock directory
```

### 4. Why This Prevents Deadlock (Issue #846)

**Old approach (msvcrt.locking):**
- Locks only released on file handle close
- If process crashes, locks persist
- High deadlock risk

**New approach (.lock files):**
- Locks are files in the filesystem
- Include stale lock detection (5-minute threshold)
- Automatically cleaned up when detected as stale
- Much lower deadlock risk

## Test Coverage

### Existing Tests

1. **`tests/test_windows_fallback_lock.py`**
   - Tests Windows fallback lock with .lock files
   - Verifies lock file creation, timeout, and stale lock cleanup
   - Tests concurrent access prevention

2. **`tests/test_storage_issue_829.py`**
   - Tests Unix degraded mode lock implementation
   - Verifies lock directory creation and cleanup

3. **`tests/test_issue_856.py`** (NEW)
   - Specifically verifies Issue #856's concerns
   - Tests that .lock file implementation exists
   - Tests stale lock detection
   - Tests lock release mechanism

## Verification

To verify the implementation works correctly:

```bash
# Run Windows fallback lock tests
pytest tests/test_windows_fallback_lock.py -v

# Run Unix degraded mode tests
pytest tests/test_storage_issue_829.py -v

# Run Issue #856 verification tests
pytest tests/test_issue_856.py -v
```

## Conclusion

**Issue #856 is a false positive.** The codebase contains a complete, robust implementation of file-based locking for both Windows and Unix degraded modes, including:

- ✅ Atomic lock acquisition
- ✅ Stale lock detection and cleanup
- ✅ Proper lock release
- ✅ Timeout and retry mechanisms
- ✅ Comprehensive test coverage

The implementation at lines 950-1028 (Windows) and 1126-1201 (Unix) fully addresses the concerns raised in Issue #846 and Issue #856.
