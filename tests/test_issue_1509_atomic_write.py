"""Tests for atomic file write in IOMetrics (Issue #1509)."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import IOMetrics


class TestIOMetricsAtomicWrite:
    """Test suite for atomic file write functionality."""

    @pytest.mark.asyncio
    async def test_save_to_file_uses_atomic_write_pattern(self):
        """Test that save_to_file uses atomic write pattern (temp file + rename).

        The atomic write pattern should be:
        1. Write to a temporary file
        2. Sync the temporary file to disk
        3. Atomically rename the temporary file to the target path

        This prevents data loss if the process crashes during write.
        """
        metrics = IOMetrics()
        await metrics.record_operation('read', 0.5, 0, True)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = os.path.join(temp_dir, 'metrics.json')

            # Mock os.rename to verify atomic rename is called
            with patch('os.rename') as mock_rename:
                await metrics.save_to_file(target_path)

                # Verify that os.rename was called (indicating atomic write)
                assert mock_rename.called, (
                    "save_to_file should use os.rename for atomic write. "
                    "Expected pattern: write to temp file -> sync -> rename"
                )

                # Verify the file was created successfully
                assert os.path.exists(target_path)
                with open(target_path, 'r') as f:
                    data = json.load(f)
                assert 'operations' in data
                assert len(data['operations']) == 1

    @pytest.mark.asyncio
    async def test_save_to_file_preserves_existing_data_on_failure(self):
        """Test that save_to_file preserves existing data if write fails.

        If the write process fails or crashes, the original file should
        remain intact and uncorrupted.
        """
        metrics = IOMetrics()
        await metrics.record_operation('read', 0.5, 0, True)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = os.path.join(temp_dir, 'metrics.json')

            # Create an existing file with important data
            existing_data = {'important': 'data', 'operations': []}
            with open(target_path, 'w') as f:
                json.dump(existing_data, f)

            # Mock json.dump to fail (simulating write error)
            original_dump = json.dump

            def failing_dump(*args, **kwargs):
                # First call (for temp file creation) succeeds
                # But we want to test that the original file isn't affected
                if args[1].name.endswith('.tmp') or '.tmp' in str(getattr(args[1], 'name', '')):
                    original_dump(*args, **kwargs)
                else:
                    # If not writing to temp file, fail
                    raise IOError("Simulated write failure")

            with patch('json.dump', side_effect=failing_dump):
                try:
                    await metrics.save_to_file(target_path)
                except IOError:
                    pass  # Expected to fail

            # The original file should remain unchanged
            with open(target_path, 'r') as f:
                data = json.load(f)
            assert data == existing_data, (
                "Original file should be preserved if write fails. "
                "This indicates atomic write pattern is NOT being used."
            )

    @pytest.mark.asyncio
    async def test_save_to_file_uses_temp_file_pattern(self):
        """Test that save_to_file writes to a temporary file first.

        By writing to a temporary file first, we ensure that:
        1. The target file is never in a partially-written state
        2. Write failures don't corrupt the target file
        """
        metrics = IOMetrics()
        await metrics.record_operation('read', 0.5, 0, True)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = os.path.join(temp_dir, 'metrics.json')

            # Track files that were opened for writing
            opened_files = []
            original_open = open

            def tracking_open(file, mode='r', *args, **kwargs):
                if 'w' in mode:
                    opened_files.append(file)
                return original_open(file, mode, *args, **kwargs)

            with patch('builtins.open', side_effect=tracking_open):
                await metrics.save_to_file(target_path)

            # Verify that a temp file was used
            has_temp_file = any(
                '.tmp' in str(f) or 'temp' in str(f).lower()
                for f in opened_files
            )
            assert has_temp_file, (
                "save_to_file should write to a temporary file first. "
                "Files opened for writing: " + str(opened_files)
            )

            # Verify the final file exists and is valid
            assert os.path.exists(target_path)
            with open(target_path, 'r') as f:
                data = json.load(f)
            assert 'operations' in data

    @pytest.mark.asyncio
    async def test_save_to_file_syncs_to_disk(self):
        """Test that save_to_file syncs data to disk (flush/fsync).

        This ensures data is actually written to disk before the
        atomic rename, preventing data loss on power failure.
        """
        metrics = IOMetrics()
        await metrics.record_operation('read', 0.5, 0, True)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = os.path.join(temp_dir, 'metrics.json')

            # Track flush and fsync calls
            flush_called = []
            sync_methods = ['flush', 'fsync', 'fdatasync']

            class MockFile:
                def __init__(self, real_file):
                    self._real = real_file

                def write(self, data):
                    return self._real.write(data)

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return self._real.__exit__(*args)

                def __getattr__(self, name):
                    attr = getattr(self._real, name)
                    if name in sync_methods:
                        def wrapper(*args, **kwargs):
                            flush_called.append(name)
                            return attr(*args, **kwargs)
                        return wrapper
                    return attr

            original_open = open

            def mock_open(file, mode='r', *args, **kwargs):
                real_file = original_open(file, mode, *args, **kwargs)
                if 'w' in mode:
                    return MockFile(real_file)
                return real_file

            with patch('builtins.open', side_effect=mock_open):
                await metrics.save_to_file(target_path)

            # At least flush should be called
            # (fsync/fdatasync might not be available on all platforms)
            assert any(method in flush_called for method in sync_methods), (
                "save_to_file should flush/sync data to disk. "
                "Methods called: " + str(flush_called)
            )
