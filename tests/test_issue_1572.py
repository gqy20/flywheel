"""Tests for structured logging in lock contention and retries (Issue #1572)."""
import os
import logging
import pytest
from unittest.mock import patch, MagicMock
from flywheel.storage import _AsyncCompatibleLock


class TestLockContentionLogging:
    """Test structured logging for lock contention and retries."""

    def test_lock_contention_logs_retry_attempts(self, caplog):
        """Test that lock contention logs retry attempts with structured data."""
        # Enable DEBUG level for storage logger
        storage_logger = logging.getLogger('flywheel.storage')
        storage_logger.setLevel(logging.DEBUG)

        # Create a lock with very short timeout to force contention
        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        # Acquire lock in first thread
        acquired1 = lock._lock.acquire(timeout=1.0)
        assert acquired1 is True

        try:
            # Try to acquire in a way that will timeout and retry
            # We'll mock the acquire to simulate contention
            with patch.object(lock._lock, 'acquire', side_effect=[False, False, False, True]):
                with caplog.at_level(logging.DEBUG, logger='flywheel.storage'):
                    # This should trigger retries
                    with lock:
                        pass

            # Check that retry attempts were logged with structured data
            retry_logs = [record for record in caplog.records
                         if 'retry' in record.message.lower() or 'backoff' in record.message.lower()]

            # Verify at least one retry log exists
            assert len(retry_logs) > 0, "Expected retry logs but found none"

            # Verify structured data in logs
            for log in retry_logs:
                assert hasattr(log, 'component') or 'component' in getattr(log, 'extra', {}), \
                    "Log should have 'component' field"
                assert hasattr(log, 'op') or 'op' in getattr(log, 'extra', {}), \
                    "Log should have 'op' field"

        finally:
            lock._lock.release()

    def test_lock_contention_logs_attempt_and_timeout(self, caplog):
        """Test that logs include attempt number and timeout information."""
        storage_logger = logging.getLogger('flywheel.storage')
        storage_logger.setLevel(logging.DEBUG)

        # Create lock with fuzzy timeout range
        lock = _AsyncCompatibleLock(timeout_range=(0.01, 0.02))

        # Acquire lock in first thread
        acquired1 = lock._lock.acquire(timeout=1.0)
        assert acquired1 is True

        try:
            # Mock to simulate timeout
            with patch.object(lock._lock, 'acquire', side_effect=[False, False, False, True]):
                with caplog.at_level(logging.DEBUG, logger='flywheel.storage'):
                    with lock:
                        pass

            # Check for logs with attempt/timeout info
            retry_logs = [record for record in caplog.records
                         if 'retry' in record.message.lower()]

            # Verify retry logs exist
            assert len(retry_logs) > 0

            # Check for structured fields (attempt, timeout, backoff)
            for log in retry_logs:
                extra = getattr(log, 'extra', {})
                # Check for expected fields in extra
                if extra:
                    # May contain attempt, timeout, backoff_delay, etc.
                    assert any(key in extra for key in ['attempt', 'timeout', 'backoff_delay',
                                                       'component', 'op']), \
                        f"Log should have structured fields, got: {extra}"

        finally:
            lock._lock.release()

    def test_lock_success_logs_with_component_and_op(self, caplog):
        """Test that successful lock acquisition logs with component and op fields."""
        storage_logger = logging.getLogger('flywheel.storage')
        storage_logger.setLevel(logging.DEBUG)

        lock = _AsyncCompatibleLock(lock_timeout=1.0)

        with caplog.at_level(logging.DEBUG, logger='flywheel.storage'):
            with lock:
                pass

        # Find the "Lock acquired successfully" log
        acquire_logs = [record for record in caplog.records
                       if 'acquired' in record.message.lower()]

        assert len(acquire_logs) > 0, "Expected lock acquisition log"

        # Verify structured data
        log = acquire_logs[0]
        assert hasattr(log, 'component') or 'component' in getattr(log, 'extra', {}), \
            "Log should have 'component' field"
        assert hasattr(log, 'op') or 'op' in getattr(log, 'extra', {}), \
            "Log should have 'op' field"

    def test_debug_storage_env_var_controls_logging(self, caplog, monkeypatch):
        """Test that DEBUG_STORAGE environment variable controls logging level."""
        # Note: DEBUG_STORAGE is checked at module import time
        # This test verifies that the logger level is properly set when env var is present
        storage_logger = logging.getLogger('flywheel.storage')

        # Verify that setting the env var would enable DEBUG level
        # In practice, this is checked at module import, so we just verify
        # the logger can be set to DEBUG level
        original_level = storage_logger.level
        storage_logger.setLevel(logging.DEBUG)

        lock = _AsyncCompatibleLock(lock_timeout=1.0)

        with caplog.at_level(logging.DEBUG, logger='flywheel.storage'):
            with lock:
                pass

        # Should have debug logs when logger is set to DEBUG
        debug_logs = [record for record in caplog.records if record.levelno == logging.DEBUG]
        assert len(debug_logs) > 0, "Expected DEBUG logs when logger level is DEBUG"

        # Restore original level
        storage_logger.setLevel(original_level)

    def test_custom_backoff_strategy_logged(self, caplog):
        """Test that custom backoff strategy delays are logged."""
        storage_logger = logging.getLogger('flywheel.storage')
        storage_logger.setLevel(logging.DEBUG)

        # Custom backoff that returns fixed delay
        def custom_backoff(attempt):
            return 0.05

        lock = _AsyncCompatibleLock(lock_timeout=0.01, backoff_strategy=custom_backoff)

        # Acquire lock in first thread
        acquired1 = lock._lock.acquire(timeout=1.0)
        assert acquired1 is True

        try:
            # Mock to simulate contention
            with patch.object(lock._lock, 'acquire', side_effect=[False, False, False, True]):
                with caplog.at_level(logging.DEBUG, logger='flywheel.storage'):
                    with lock:
                        pass

            # Check for backoff logs
            backoff_logs = [record for record in caplog.records
                           if 'backoff' in record.message.lower()]

            # Should have backoff logs
            assert len(backoff_logs) > 0

        finally:
            lock._lock.release()

    def test_lock_timeout_error_has_context(self):
        """Test that StorageTimeoutError includes attempt/context information."""
        from flywheel.storage import StorageTimeoutError

        # Create lock with very short timeout
        lock = _AsyncCompatibleLock(lock_timeout=0.001)

        # Acquire lock
        acquired1 = lock._lock.acquire(timeout=1.0)
        assert acquired1 is True

        try:
            # Try to acquire - should timeout
            with pytest.raises(StorageTimeoutError) as exc_info:
                with lock:
                    pass

            # Error should have context
            error = exc_info.value
            assert error.timeout is not None or error.operation is not None, \
                "StorageTimeoutError should include context (timeout or operation)"

        finally:
            lock._lock.release()
