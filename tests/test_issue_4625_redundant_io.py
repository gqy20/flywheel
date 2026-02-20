"""Regression test for issue #4625: redundant I/O in load method.

The load() method was calling path.exists() and then path.stat(),
which caused two stat system calls when the file exists. The fix
consolidates this into a single stat() call with try/except.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage


class TestLoadMethodSingleStatCall:
    """Test that load() makes only one stat system call."""

    def test_load_single_stat_call_when_file_exists(self, tmp_path: Path) -> None:
        """Verify load() calls stat only once when file exists.

        Previously, load() would call:
        1. self.path.exists() - which internally calls stat
        2. self.path.stat() - which calls stat again

        After the fix, it should call stat only once.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a valid todo file
        todos = [{"id": 1, "text": "test"}]
        db.write_text(json.dumps(todos), encoding="utf-8")

        # Track how many times stat is called
        stat_call_count = 0
        original_stat = Path.stat

        def tracked_stat(self, *args, **kwargs):
            nonlocal stat_call_count
            stat_call_count += 1
            return original_stat(self, *args, **kwargs)

        with patch.object(Path, "stat", tracked_stat):
            result = storage.load()

        # Verify behavior
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].text == "test"

        # The key assertion: load should call stat exactly once
        assert stat_call_count == 1, (
            f"Expected 1 stat call, got {stat_call_count}. "
            "load() should consolidate exists() and stat() into single stat call."
        )

    def test_load_returns_empty_list_when_file_not_exists(self, tmp_path: Path) -> None:
        """Verify load() returns empty list when file doesn't exist.

        This ensures the fix maintains correct behavior for missing files.
        """
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # File should not exist
        assert not db.exists()

        # load() should return empty list without raising
        result = storage.load()
        assert result == []

    def test_load_single_stat_call_count_via_os_stat(self, tmp_path: Path) -> None:
        """Alternative test: count os.stat calls directly.

        This tests at the os.stat level to catch any path-based stat calls.
        """
        db = tmp_path / "todo2.json"
        storage = TodoStorage(str(db))

        # Create a valid todo file
        todos = [{"id": 1, "text": "test2"}]
        db.write_text(json.dumps(todos), encoding="utf-8")

        # Track os.stat calls for our specific file
        stat_call_count = 0
        original_os_stat = os.stat

        def tracked_os_stat(path, *args, **kwargs):
            nonlocal stat_call_count
            result = original_os_stat(path, *args, **kwargs)
            # Only count stat calls for our database file
            if str(path) == str(db):
                stat_call_count += 1
            return result

        with patch("os.stat", tracked_os_stat):
            result = storage.load()

        # Verify behavior
        assert len(result) == 1
        assert result[0].text == "test2"

        # Should be exactly 1 os.stat call for the db file
        assert stat_call_count == 1, (
            f"Expected 1 os.stat call for db file, got {stat_call_count}"
        )
