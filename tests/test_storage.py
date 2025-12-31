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
