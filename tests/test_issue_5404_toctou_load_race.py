"""Regression test for issue #5404: TOCTOU race condition in load().

This test ensures that load() handles the race condition where a file
exists when checked but is deleted before stat()/read_text() is called.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage


def test_load_handles_file_deleted_after_exists_check(tmp_path: Path) -> None:
    """Test that load() handles FileNotFoundError gracefully.

    Regression test for issue #5404: If a file is deleted between the
    exists() check and stat()/read_text(), load() should return an empty
    list rather than propagating FileNotFoundError to the caller.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock Path to simulate TOCTOU race condition:
    # exists() returns True, but stat() raises FileNotFoundError
    original_exists = Path.exists
    original_stat = Path.stat

    def mock_exists(self: Path) -> bool:
        if self == db:
            return True  # File "exists" at check time
        return original_exists(self)

    def mock_stat(self: Path):
        if self == db:
            raise FileNotFoundError("File deleted after exists() check")
        return original_stat(self)

    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat),
    ):
        # Should return empty list, not raise FileNotFoundError
        result = storage.load()
        assert result == []


def test_load_handles_file_deleted_before_read(tmp_path: Path) -> None:
    """Test that load() handles file deleted between stat() and read_text()."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_exists = Path.exists
    original_stat = Path.stat
    original_read_text = Path.read_text

    class MockStatResult:
        st_size = 100

    def mock_exists(self: Path) -> bool:
        if self == db:
            return True
        return original_exists(self)

    def mock_stat(self: Path):
        if self == db:
            return MockStatResult()
        return original_stat(self)

    def mock_read_text(self: Path, *args, **kwargs):
        if self == db:
            raise FileNotFoundError("File deleted after stat() check")
        return original_read_text(self, *args, **kwargs)

    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat),
        patch.object(Path, "read_text", mock_read_text),
    ):
        # Should return empty list, not raise FileNotFoundError
        result = storage.load()
        assert result == []


def test_load_returns_empty_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that load() returns empty list for nonexistent file (existing behavior)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_propagates_other_os_errors(tmp_path: Path) -> None:
    """Test that load() still raises other OSErrors (not FileNotFoundError)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_stat = Path.stat

    def mock_stat(self: Path):
        if self == db:
            raise PermissionError("Permission denied")
        return original_stat(self)

    with (
        patch.object(Path, "exists", lambda self: True),
        patch.object(Path, "stat", mock_stat),
        pytest.raises(PermissionError, match="Permission denied"),
    ):
        storage.load()
