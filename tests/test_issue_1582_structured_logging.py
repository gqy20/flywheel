"""Tests for structured logging in _AsyncCompatibleLock (Issue #1582)."""
import asyncio
import logging
import os
import threading
import time
from unittest.mock import patch

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestStructuredLogging:
    """Test suite for structured logging context in _AsyncCompatibleLock."""

    def test_sync_lock_logs_wait_time_and_attempts(self):
        """Test that sync lock acquisition logs wait_time and attempts."""
        # Enable DEBUG_STORAGE
        os.environ['DEBUG_STORAGE'] = '1'

        lock = _AsyncCompatibleLock()

        # Hold the lock to create contention
        lock.acquire()

        # Track log calls
        log_records = []

        def capture_log(logger_instance, level, msg, *args, **kwargs):
            """Capture log records for verification."""
            if 'extra' in kwargs:
                log_records.append({
                    'msg': msg,
                    'extra': kwargs['extra']
                })

        # Try to acquire in another thread (will cause contention)
        def try_acquire():
            try:
                with patch('flywheel.storage.logger.debug', side_effect=capture_log):
                    with lock:
                        pass
            except Exception:
                pass

        thread = threading.Thread(target=try_acquire)
        thread.start()

        # Wait a bit then release
        time.sleep(0.2)
        lock.release()
        thread.join(timeout=5)

        # Clean up
        del os.environ['DEBUG_STORAGE']

        # Verify that we got a log with lock_wait_time and attempts
        acquisition_logs = [
            r for r in log_records
            if r['extra'].get('op') == 'lock_acquire'
        ]

        assert len(acquisition_logs) > 0, "Should have at least one lock acquisition log"

        # Check that the log contains the expected structured data
        log = acquisition_logs[0]
        assert 'lock_wait_time' in log['extra'], "Log should contain 'lock_wait_time'"
        assert 'attempts' in log['extra'], "Log should contain 'attempts'"
        assert log['extra']['lock_wait_time'] >= 0, "wait_time should be non-negative"
        assert log['extra']['attempts'] >= 1, "attempts should be at least 1"

    def test_sync_lock_logs_wait_time_on_contention(self):
        """Test that wait_time is logged when there is actual contention."""
        # Enable DEBUG_STORAGE
        os.environ['DEBUG_STORAGE'] = '1'

        lock = _AsyncCompatibleLock()

        # Hold the lock to create contention
        lock.acquire()

        # Track log calls
        log_records = []

        def capture_log(msg, *args, **kwargs):
            """Capture log records for verification."""
            if 'extra' in kwargs:
                log_records.append({
                    'msg': msg,
                    'extra': kwargs['extra']
                })

        # Try to acquire in another thread (will cause contention)
        def try_acquire():
            try:
                with patch('flywheel.storage.logger.debug', side_effect=capture_log):
                    with lock:
                        pass
            except Exception:
                pass

        thread = threading.Thread(target=try_acquire)
        thread.start()

        # Wait to ensure there is actual wait time
        time.sleep(0.3)
        lock.release()
        thread.join(timeout=5)

        # Clean up
        del os.environ['DEBUG_STORAGE']

        # Verify that we got a log with positive wait_time
        acquisition_logs = [
            r for r in log_records
            if r['extra'].get('op') == 'lock_acquire'
        ]

        if acquisition_logs:
            log = acquisition_logs[0]
            if 'lock_wait_time' in log['extra']:
                # With contention, wait_time should be > 0
                assert log['extra']['lock_wait_time'] > 0, "wait_time should be positive with contention"

    def test_async_lock_logs_wait_time_and_attempts(self):
        """Test that async lock acquisition logs wait_time and attempts."""
        # Enable DEBUG_STORAGE
        os.environ['DEBUG_STORAGE'] = '1'

        async def test_async():
            lock = _AsyncCompatibleLock()

            # Hold the lock to create contention
            await lock.__aenter__()

            # Track log calls
            log_records = []

            def capture_log(msg, *args, **kwargs):
                """Capture log records for verification."""
                if 'extra' in kwargs:
                    log_records.append({
                        'msg': msg,
                        'extra': kwargs['extra']
                    })

            # Try to acquire in another task (will cause contention)
            async def try_acquire():
                try:
                    with patch('flywheel.storage.logger.debug', side_effect=capture_log):
                        async with lock:
                            pass
                except Exception:
                    pass

            task = asyncio.create_task(try_acquire())

            # Wait a bit then release
            await asyncio.sleep(0.2)
            await lock.__aexit__(None, None, None)

            await task

            # Clean up
            del os.environ['DEBUG_STORAGE']

            # Verify that we got a log with lock_wait_time and attempts
            acquisition_logs = [
                r for r in log_records
                if r['extra'].get('op') == 'async_lock_acquire'
            ]

            assert len(acquisition_logs) > 0, "Should have at least one async lock acquisition log"

            # Check that the log contains the expected structured data
            log = acquisition_logs[0]
            assert 'lock_wait_time' in log['extra'], "Log should contain 'lock_wait_time'"
            assert 'attempts' in log['extra'], "Log should contain 'attempts'"
            assert log['extra']['lock_wait_time'] >= 0, "wait_time should be non-negative"
            assert log['extra']['attempts'] >= 1, "attempts should be at least 1"

        # Run the async test
        asyncio.run(test_async())

    def test_no_logging_when_debug_storage_disabled(self):
        """Test that structured logging is not active when DEBUG_STORAGE is disabled."""
        # Ensure DEBUG_STORAGE is not set
        if 'DEBUG_STORAGE' in os.environ:
            del os.environ['DEBUG_STORAGE']

        lock = _AsyncCompatibleLock()

        # This should not raise any errors
        with lock:
            pass

        # If no exception, the test passes
        assert True

    def test_immediate_acquisition_logs_zero_wait_time(self):
        """Test that immediate lock acquisition logs wait_time near zero."""
        # Enable DEBUG_STORAGE
        os.environ['DEBUG_STORAGE'] = '1'

        lock = _AsyncCompatibleLock()

        # Track log calls
        log_records = []

        def capture_log(msg, *args, **kwargs):
            """Capture log records for verification."""
            if 'extra' in kwargs:
                log_records.append({
                    'msg': msg,
                    'extra': kwargs['extra']
                })

        # Acquire immediately without contention
        with patch('flywheel.storage.logger.debug', side_effect=capture_log):
            with lock:
                pass

        # Clean up
        del os.environ['DEBUG_STORAGE']

        # Verify that we got a log with wait_time near zero
        acquisition_logs = [
            r for r in log_records
            if r['extra'].get('op') == 'lock_acquire'
        ]

        if acquisition_logs:
            log = acquisition_logs[0]
            if 'lock_wait_time' in log['extra']:
                # Immediate acquisition should have very small wait_time
                assert log['extra']['lock_wait_time'] < 0.1, "wait_time should be near zero for immediate acquisition"
            if 'attempts' in log['extra']:
                # Should succeed on first attempt
                assert log['extra']['attempts'] == 1, "attempts should be 1 for immediate acquisition"
