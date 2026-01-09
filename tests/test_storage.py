"""Tests for Storage backend."""

import os
import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_windows_acl_no_delete_permission():
    """Test that Windows ACL does not include DELETE permission (Issue #249)."""
    if os.name != 'nt':
        return  # Skip on non-Windows systems

    try:
        import win32security
        import win32con
    except ImportError:
        return  # Skip if pywin32 is not installed

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance which will apply Windows ACL
        storage = Storage(path=f"{tmpdir}/test.json")

        # Get the security descriptor of the directory
        security_descriptor = win32security.GetFileSecurity(
            tmpdir,
            win32security.DACL_SECURITY_INFORMATION
        )

        # Get the DACL
        dacl = security_descriptor.GetSecurityDescriptorDacl()

        if dacl is None:
            return  # No DACL, skip test

        # Check each ACE in the DACL
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            access_mask = ace[2]

            # Verify that DELETE permission is not granted
            # DELETE has the value 0x00010000
            assert (access_mask & win32con.DELETE) == 0, (
                f"DELETE permission found in ACE {i} with access mask {hex(access_mask)}. "
                "This violates the principle of least privilege (Issue #249)."
            )


def test_storage_add_and_get():
    """Test adding and retrieving todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        todo = Todo(id=1, title="Test todo")
        storage.add(todo)

        retrieved = storage.get(1)
        assert retrieved is not None
        assert retrieved.title == "Test todo"
        assert retrieved.id == 1


def test_storage_list():
    """Test listing todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        storage.add(Todo(id=1, title="First", status=Status.TODO))
        storage.add(Todo(id=2, title="Second", status=Status.DONE))

        all_todos = storage.list()
        assert len(all_todos) == 2

        pending = storage.list(status="todo")
        assert len(pending) == 1
        assert pending[0].title == "First"


def test_storage_update():
    """Test updating a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        todo = Todo(id=1, title="Original", status=Status.TODO)
        storage.add(todo)

        todo.title = "Updated"
        todo.status = Status.DONE
        storage.update(todo)

        retrieved = storage.get(1)
        assert retrieved.title == "Updated"
        assert retrieved.status == Status.DONE


def test_storage_delete():
    """Test deleting a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        storage.add(Todo(id=1, title="Test"))
        assert storage.get(1) is not None

        result = storage.delete(1)
        assert result is True

        assert storage.get(1) is None


def test_storage_get_next_id():
    """Test getting next available ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        assert storage.get_next_id() == 1

        storage.add(Todo(id=1, title="First"))
        assert storage.get_next_id() == 2

        storage.add(Todo(id=2, title="Second"))
        assert storage.get_next_id() == 3


def test_storage_file_not_truncated():
    """Verify that storage.py is complete and not truncated (Issue #289)."""
    import ast
    import inspect

    # Parse the storage.py file to verify it's syntactically complete
    storage_path = inspect.getfile(Storage)
    with open(storage_path, 'r') as f:
        source_code = f.read()

    # Verify the file can be parsed as valid Python
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(
            f"storage.py has syntax errors (file may be truncated): {e}"
        )

    # Verify the Storage class has all expected methods
    expected_methods = [
        '__init__',
        '_get_windows_lock_range',
        '_acquire_file_lock',
        '_release_file_lock',
        '_secure_directory',
        '_create_backup',
        '_cleanup',
        '_calculate_checksum',
        '_validate_storage_schema',
        '_load',
        '_save',
        '_save_with_todos',
        'add',
        'list',
        'get',
        'update',
        'delete',
        'get_next_id',
        'close',
    ]

    for method_name in expected_methods:
        assert hasattr(Storage, method_name), (
            f"Storage class is missing method '{method_name}'. "
            f"File may be truncated (Issue #289)."
        )

    # Verify the file has a reasonable length (not cut off mid-function)
    # The complete file should be around 876 lines
    line_count = len(source_code.split('\n'))
    assert line_count > 800, (
        f"storage.py appears to be truncated: only {line_count} lines. "
        f"Expected at least 800 lines (Issue #289)."
    )


def test_decorator_exception_handling_complete():
    """Verify that the decorator exception handling logic is complete (Issue #1025)."""
    import inspect

    # Get the source code of the _with_retry decorator
    storage_source = inspect.getsource(Storage._with_retry)

    # Verify that both async and sync wrappers have complete exception handling
    # Check for the presence of key exception handling components

    # 1. Verify async wrapper exists and has exception handling
    assert 'async def async_wrapper' in storage_source, (
        "Missing async_wrapper in decorator (Issue #1025)"
    )

    # 2. Verify sync wrapper exists and has exception handling
    assert 'def sync_wrapper' in storage_source, (
        "Missing sync_wrapper in decorator (Issue #1025)"
    )

    # 3. Verify both wrappers have complete exception handling blocks
    # Check for the try-except structure
    assert storage_source.count('try:') >= 2, (
        "Decorator should have try blocks for both async and sync wrappers (Issue #1025)"
    )

    assert storage_source.count('except Exception as e:') >= 2, (
        "Decorator should have exception handlers for both async and sync wrappers (Issue #1025)"
    )

    # 4. Verify the context handling logic is present in both wrappers
    assert storage_source.count('if context and not str(e).count(context) > 0:') >= 2, (
        "Missing context handling logic in decorator (Issue #1025)"
    )

    # 5. Verify add_note is used for Python 3.11+
    assert storage_source.count("if hasattr(e, 'add_note'):") >= 2, (
        "Missing add_note check for Python 3.11+ (Issue #1025)"
    )

    # 6. Verify fallback for older Python versions
    assert storage_source.count("if e.args:") >= 2, (
        "Missing fallback for older Python versions (Issue #1025)"
    )

    # 7. Verify the comment about appending context is complete
    assert '# Append context to the first argument' in storage_source, (
        "Missing or incomplete comment about context handling (Issue #1025)"
    )

    # 8. Verify both wrappers return the wrapper function
    assert 'return async_wrapper' in storage_source, (
        "Missing return statement for async_wrapper (Issue #1025)"
    )

    assert 'return sync_wrapper' in storage_source, (
        "Missing return statement for sync_wrapper (Issue #1025)"
    )


def test_async_lock_error_message_includes_both_thread_ids():
    """Verify that _AsyncCompatibleLock error message includes both thread IDs (Issue #1226)."""
    import asyncio
    import inspect
    import threading

    # Import the private _AsyncCompatibleLock class
    from flywheel.storage import _AsyncCompatibleLock

    # Get the source code of the __aenter__ method where the error is raised
    lock_source = inspect.getsource(_AsyncCompatibleLock.__aenter__)

    # Verify that the error message includes both thread IDs
    # The error message should contain:
    # 1. "Event loop thread ID:" followed by the event_loop_thread_id variable
    # 2. "current thread ID:" followed by the current_thread_id variable

    assert 'Event loop thread ID: {event_loop_thread_id}' in lock_source, (
        "Error message missing event loop thread ID (Issue #1226)"
    )

    assert 'current thread ID: {current_thread_id}' in lock_source, (
        "Error message missing current thread ID (Issue #1226)"
    )

    # Verify both variables are referenced in the f-string
    assert 'event_loop_thread_id' in lock_source, (
        "Error message should reference event_loop_thread_id variable (Issue #1226)"
    )

    assert 'current_thread_id' in lock_source, (
        "Error message should reference current_thread_id variable (Issue #1226)"
    )
