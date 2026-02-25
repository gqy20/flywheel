"""Tests for error handling and exception preservation in TodoStorage.

This test suite verifies that TodoStorage.save() preserves specific exception
types and context when errors occur, rather than catching all OSError broadly
and hiding important error information from the caller.

Regression test for issue #5694.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_preserves_permission_error_type(tmp_path) -> None:
    """Test that PermissionError is raised, not generic OSError.

    When os.replace() fails with PermissionError, the caller should receive
    PermissionError, not a generic OSError that would hide the specific cause.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="test")]

    # Mock os.replace to raise PermissionError specifically
    with (
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(PermissionError),  # Should raise PermissionError, not OSError
    ):
        mock_replace.side_effect = PermissionError("Permission denied")
        storage.save(todos)


def test_save_preserves_file_not_found_error_type(tmp_path) -> None:
    """Test that FileNotFoundError is raised, not generic OSError.

    FileNotFoundError is a subclass of OSError. When it occurs, it should
    be preserved to provide accurate error context to the caller.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Mock os.replace to raise FileNotFoundError specifically
    with (
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(FileNotFoundError),  # Should raise FileNotFoundError, not OSError
    ):
        mock_replace.side_effect = FileNotFoundError("Target directory missing")
        storage.save(todos)


def test_save_preserves_exception_message(tmp_path) -> None:
    """Test that the original exception message is preserved.

    The caller should be able to see the specific error message from the
    original exception, not a generic wrapper message.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    original_message = "Custom permission error message test_12345"

    with (
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(PermissionError, match=r"Custom permission error message"),
    ):
        mock_replace.side_effect = PermissionError(original_message)
        storage.save(todos)


def test_save_cleanup_on_error_does_not_suppress_main_exception(tmp_path) -> None:
    """Test that cleanup errors don't suppress the main exception.

    The temp file cleanup silently ignores cleanup failures. This should
    not affect the main exception that caused the save to fail.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    cleanup_attempts = []

    # Mock os.unlink to track cleanup attempts and fail
    def tracking_unlink(path, *args, **kwargs):
        cleanup_attempts.append(str(path))
        # Simulate cleanup failure (which should be suppressed)
        raise OSError("Cleanup failed")

    with (
        patch("flywheel.storage.os.unlink", tracking_unlink),
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(PermissionError) as exc_info,
    ):
        mock_replace.side_effect = PermissionError("Write failed")
        storage.save(todos)

    # The main exception should be PermissionError, not the cleanup error
    assert "Write failed" in str(exc_info.value)
    # Cleanup should have been attempted
    assert len(cleanup_attempts) >= 1


def test_save_preserves_exception_traceback_context(tmp_path) -> None:
    """Test that exception context/traceback is preserved.

    Using bare 'raise' should preserve the full exception context including
    the traceback, which helps with debugging.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    with (
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(PermissionError) as exc_info,
    ):
        mock_replace.side_effect = PermissionError("Test error context")
        storage.save(todos)

    # Verify the exception type is exactly PermissionError
    assert type(exc_info.value) is PermissionError
    # Verify the message is preserved
    assert "Test error context" in str(exc_info.value)


def test_save_exception_includes_tempfile_cleanup_status_success(tmp_path) -> None:
    """Test that exception includes temp file cleanup status when cleanup succeeds.

    When save() fails and temp file cleanup succeeds, the exception should
    have a _tempfile_cleanup attribute set to True to help with debugging.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    with (
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(PermissionError) as exc_info,
    ):
        mock_replace.side_effect = PermissionError("Write failed")
        storage.save(todos)

    # Exception should indicate temp file was cleaned up
    assert hasattr(exc_info.value, "_tempfile_cleanup")
    assert exc_info.value._tempfile_cleanup is True


def test_save_exception_includes_tempfile_cleanup_status_failed(tmp_path) -> None:
    """Test that exception includes temp file cleanup status when cleanup fails.

    When save() fails AND temp file cleanup also fails, the exception should
    have a _tempfile_cleanup attribute set to False to help with debugging.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    def failing_unlink(path, *args, **kwargs):
        raise OSError("Cleanup failed")

    with (
        patch("flywheel.storage.os.unlink", failing_unlink),
        patch("flywheel.storage.os.replace") as mock_replace,
        pytest.raises(PermissionError) as exc_info,
    ):
        mock_replace.side_effect = PermissionError("Write failed")
        storage.save(todos)

    # Exception should indicate temp file cleanup failed
    assert hasattr(exc_info.value, "_tempfile_cleanup")
    assert exc_info.value._tempfile_cleanup is False
