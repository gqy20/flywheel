"""Tests for enhanced Storage.health_check() method with detailed status (issue #553)."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from flywheel.storage import Storage


def test_health_check_returns_dict_with_all_required_fields():
    """Test that health_check returns a dict with writable, disk_space, and permissions fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()

        assert isinstance(result, dict), "health_check should return a dictionary"
        assert "writable" in result, "health_check should include 'writable' field"
        assert "disk_space" in result, "health_check should include 'disk_space' field"
        assert "permissions" in result, "health_check should include 'permissions' field"
        assert "healthy" in result, "health_check should include 'healthy' field"
        storage.close()


def test_health_check_writable_field_for_writable_directory():
    """Test that health_check correctly identifies writable directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()

        assert result["writable"] is True, "writable should be True for writable directory"
        assert result["healthy"] is True, "healthy should be True when all checks pass"
        storage.close()


def test_health_check_writable_field_for_read_only_directory():
    """Test that health_check correctly identifies read-only directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)

        # Make directory read-only
        os.chmod(tmpdir, 0o444)

        try:
            result = storage.health_check()
            assert result["writable"] is False, "writable should be False for read-only directory"
            assert result["healthy"] is False, "healthy should be False when writable check fails"
        finally:
            # Restore permissions for cleanup
            os.chmod(tmpdir, 0o755)
            storage.close()


def test_health_check_disk_space_field():
    """Test that health_check includes disk space information."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()

        assert "disk_space" in result, "Result should include disk_space field"
        assert isinstance(result["disk_space"], dict), "disk_space should be a dictionary"

        # Check for expected disk space fields
        assert "total" in result["disk_space"], "disk_space should include 'total' field"
        assert "used" in result["disk_space"], "disk_space should include 'used' field"
        assert "free" in result["disk_space"], "disk_space should include 'free' field"
        assert result["disk_space"]["free"] > 0, "disk_space.free should be positive"

        storage.close()


def test_health_check_permissions_field():
    """Test that health_check includes permissions information."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()

        assert "permissions" in result, "Result should include permissions field"
        assert isinstance(result["permissions"], dict), "permissions should be a dictionary"

        # Check for expected permissions fields
        assert "readable" in result["permissions"], "permissions should include 'readable' field"
        assert "writable" in result["permissions"], "permissions should include 'writable' field"
        assert "executable" in result["permissions"], "permissions should include 'executable' field"

        assert result["permissions"]["readable"] is True, "Should be readable"
        assert result["permissions"]["writable"] is True, "Should be writable"
        storage.close()


def test_health_check_file_lock_functionality():
    """Test that health_check verifies file locking works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()

        assert "file_lock" in result, "health_check should include 'file_lock' field"
        assert isinstance(result["file_lock"], bool), "file_lock should be a boolean"
        assert result["file_lock"] is True, "file_lock should be True when locking works"
        storage.close()


def test_health_check_healthy_field_all_pass():
    """Test that healthy is True when all checks pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)
        result = storage.health_check()

        assert result["healthy"] is True, "healthy should be True when all checks pass"
        storage.close()


def test_health_check_healthy_field_single_failure():
    """Test that healthy is False when any check fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)

        # Make directory read-only
        os.chmod(tmpdir, 0o444)

        try:
            result = storage.health_check()
            assert result["healthy"] is False, "healthy should be False when writable check fails"
        finally:
            # Restore permissions for cleanup
            os.chmod(tmpdir, 0o755)
            storage.close()


def test_health_check_idempotent():
    """Test that health_check can be called multiple times with consistent results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(path=test_path)

        result1 = storage.health_check()
        result2 = storage.health_check()
        result3 = storage.health_check()

        assert result1["healthy"] is True, "First health_check should return healthy=True"
        assert result2["healthy"] is True, "Second health_check should return healthy=True"
        assert result3["healthy"] is True, "Third health_check should return healthy=True"
        storage.close()
