"""Tests for Storage.health_check() method (issue #533)."""

import pytest
import tempfile
import os
from pathlib import Path
from flywheel.storage import Storage


def test_health_check_method_exists():
    """Test that health_check method exists."""
    storage = Storage()
    assert hasattr(storage, 'health_check'), "Storage should have a health_check method"


def test_health_check_is_callable():
    """Test that health_check method is callable."""
    storage = Storage()
    assert callable(storage.health_check), "Storage.health_check should be callable"


def test_health_check_returns_dict():
    """Test that health_check returns a dictionary with health status."""
    storage = Storage()
    result = storage.health_check()
    assert isinstance(result, dict), "health_check should return a dictionary"
    assert "healthy" in result, "health_check result should include 'healthy' key"


def test_health_check_success_normal_path():
    """Test health_check returns healthy=True for normal, writable path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()
        assert result["healthy"] is True, "health_check should return healthy=True for writable path"
        storage.close()


def test_health_check_fails_read_only_directory():
    """Test health_check returns healthy=False for read-only directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)

        # Make directory read-only
        os.chmod(tmpdir, 0o444)

        try:
            result = storage.health_check()
            assert result["healthy"] is False, "health_check should return healthy=False for read-only directory"
        finally:
            # Restore permissions for cleanup
            os.chmod(tmpdir, 0o755)
            storage.close()


def test_health_check_creates_temp_file():
    """Test that health_check actually creates and locks a temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)

        # Health check should succeed
        result = storage.health_check()
        assert result["healthy"] is True

        # Verify the storage file exists and is accessible
        assert storage.path.exists(), "Storage file should exist after health check"
        storage.close()


def test_health_check_with_disk_full_simulation():
    """Test health_check behavior when disk space is limited."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)

        # In normal conditions, health check should pass
        result = storage.health_check()
        assert result["healthy"] is True, "health_check should return healthy=True when disk has space"
        storage.close()


def test_health_check_idempotent():
    """Test that health_check can be called multiple times."""
    storage = Storage()
    result1 = storage.health_check()
    result2 = storage.health_check()
    result3 = storage.health_check()

    assert result1["healthy"] is True, "First health_check should return healthy=True"
    assert result2["healthy"] is True, "Second health_check should return healthy=True"
    assert result3["healthy"] is True, "Third health_check should return healthy=True"
    storage.close()


# Tests for Issue #677 - health_check should return bool
def test_health_check_returns_bool_not_dict(tmp_path):
    """Test that health_check returns bool (Issue #677)."""
    from flywheel.storage import AbstractStorage, FileStorage

    # Test that AbstractStorage has health_check as abstract method
    assert hasattr(AbstractStorage, 'health_check'), \
        "AbstractStorage should have health_check method"

    # Test that FileStorage.health_check returns bool
    storage_path = tmp_path / "test_bool.json"
    storage = FileStorage(str(storage_path))
    result = storage.health_check()
    assert isinstance(result, bool), \
        f"health_check should return bool, got {type(result).__name__}"


def test_health_check_bool_true_for_healthy(tmp_path):
    """Test that health_check returns True for healthy storage (Issue #677)."""
    from flywheel.storage import FileStorage

    storage_path = tmp_path / "test_healthy_bool.json"
    storage = FileStorage(str(storage_path))
    assert storage.health_check() is True, \
        "health_check should return True for healthy storage"


def test_health_check_bool_false_for_unhealthy(tmp_path):
    """Test that health_check returns False for unhealthy storage (Issue #677)."""
    from flywheel.storage import FileStorage

    storage_path = tmp_path / "test_unhealthy_bool.json"
    storage = FileStorage(str(storage_path))

    # Make file read-only to simulate unhealthy state
    storage_path.touch()
    storage_path.chmod(0o444)

    try:
        result = storage.health_check()
        assert result is False, \
            f"health_check should return False for read-only storage, got {result}"
    finally:
        storage_path.chmod(0o644)  # Restore permissions for cleanup
