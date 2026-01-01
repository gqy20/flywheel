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
