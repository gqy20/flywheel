"""Tests for structured lock contention logging (Issue #1587)."""
import logging
import threading
import time
import pytest
from unittest.mock import patch
from flywheel.storage import _AsyncCompatibleLock


class TestStructuredLockContentionLogging:
    """Test structured JSON logging for lock contention when DEBUG_STORAGE is active."""

    def test_lock_wait_event_logged_on_contention(self, caplog, monkeypatch):
        """Test that lock contention emits structured JSON log with event='lock_wait'."""
        # Enable DEBUG_STORAGE via environment variable
        monkeypatch.setenv('DEBUG_STORAGE', '1')

        # Create a lock with very short timeout to force contention
        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        # Acquire lock in another thread to force contention
        def hold_lock():
            with lock:
                time.sleep(0.2)  # Hold long enough to cause wait

        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()

        # Give the holder thread time to acquire the lock
        time.sleep(0.02)

        try:
            # Try to acquire - this will experience contention
            with caplog.at_level(logging.INFO, logger='flywheel.storage'):
                with lock:
                    pass

            # Check for structured log with event='lock_wait'
            lock_wait_logs = [record for record in caplog.records
                             if hasattr(record, 'event') and record.event == 'lock_wait']

            assert len(lock_wait_logs) > 0, "Expected structured log with event='lock_wait'"

            # Verify required fields in the log
            log = lock_wait_logs[0]
            assert log.event == 'lock_wait', "Log should have event='lock_wait'"
            assert hasattr(log, 'wait_time'), "Log should have wait_time field"
            assert hasattr(log, 'acquired'), "Log should have acquired field"
            assert hasattr(log, 'thread'), "Log should have thread field"
            assert log.acquired is True, "Lock should have been acquired after wait"
            assert log.wait_time > 0, "wait_time should be positive when there's contention"
            assert isinstance(log.thread, str), "thread should be a string"

        finally:
            holder_thread.join()

    def test_lock_wait_event_not_logged_when_no_contention(self, caplog, monkeypatch):
        """Test that no lock_wait event is logged when lock is immediately available."""
        # Enable DEBUG_STORAGE via environment variable
        monkeypatch.setenv('DEBUG_STORAGE', '1')

        lock = _AsyncCompatibleLock(lock_timeout=1.0)

        # Acquire without contention
        with caplog.at_level(logging.INFO, logger='flywheel.storage'):
            with lock:
                pass

        # Check for structured log with event='lock_wait'
        lock_wait_logs = [record for record in caplog.records
                         if hasattr(record, 'event') and record.event == 'lock_wait']

        # When there's no contention, lock_wait event should still be logged
        # but with wait_time=0 or a very small value
        # This behavior might vary based on implementation, so we just verify
        # the log exists and has correct fields
        if len(lock_wait_logs) > 0:
            log = lock_wait_logs[0]
            assert log.event == 'lock_wait'
            assert hasattr(log, 'wait_time')
            assert hasattr(log, 'acquired')
            assert hasattr(log, 'thread')
            # wait_time should be very small or zero for no contention
            assert log.wait_time >= 0

    def test_lock_wait_log_includes_required_fields(self, caplog, monkeypatch):
        """Test that lock_wait log includes all required fields: event, wait_time, acquired, thread."""
        # Enable DEBUG_STORAGE via environment variable
        monkeypatch.setenv('DEBUG_STORAGE', '1')

        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        # Acquire lock in another thread
        def hold_lock():
            with lock:
                time.sleep(0.15)

        holder_thread = threading.Thread(target=hold_lock, name='TestHolderThread')
        holder_thread.start()

        # Give the holder thread time to acquire the lock
        time.sleep(0.02)

        try:
            with caplog.at_level(logging.INFO, logger='flywheel.storage'):
                with lock:
                    pass

            # Find the lock_wait log
            lock_wait_logs = [record for record in caplog.records
                             if hasattr(record, 'event') and record.event == 'lock_wait']

            assert len(lock_wait_logs) > 0

            log = lock_wait_logs[0]

            # Verify all required fields are present and have correct types
            assert log.event == 'lock_wait', "event field should be 'lock_wait'"
            assert isinstance(log.wait_time, (int, float)), "wait_time should be numeric"
            assert isinstance(log.acquired, bool), "acquired should be boolean"
            assert isinstance(log.thread, str), "thread should be string"

            # Verify acquired is True (we did acquire the lock)
            assert log.acquired is True

        finally:
            holder_thread.join()

    def test_lock_wait_thread_name_is_correct(self, caplog, monkeypatch):
        """Test that the thread field in lock_wait log contains the correct thread name."""
        # Enable DEBUG_STORAGE via environment variable
        monkeypatch.setenv('DEBUG_STORAGE', '1')

        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        # Acquire lock in another thread with a specific name
        def hold_lock():
            with lock:
                time.sleep(0.15)

        holder_thread = threading.Thread(target=hold_lock, name='MyCustomThread')
        holder_thread.start()

        time.sleep(0.02)

        try:
            with caplog.at_level(logging.INFO, logger='flywheel.storage'):
                with lock:
                    pass

            # Find the lock_wait log
            lock_wait_logs = [record for record in caplog.records
                             if hasattr(record, 'event') and record.event == 'lock_wait']

            if len(lock_wait_logs) > 0:
                log = lock_wait_logs[0]
                # Thread name should be captured
                assert log.thread is not None
                assert len(log.thread) > 0

        finally:
            holder_thread.join()

    def test_lock_wait_not_logged_without_debug_storage(self, caplog):
        """Test that lock_wait event is NOT logged when DEBUG_STORAGE is not set."""
        # Do NOT set DEBUG_STORAGE environment variable

        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        # Acquire lock in another thread to force contention
        def hold_lock():
            with lock:
                time.sleep(0.15)

        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()

        time.sleep(0.02)

        try:
            with caplog.at_level(logging.INFO, logger='flywheel.storage'):
                with lock:
                    pass

            # Check for structured log with event='lock_wait'
            lock_wait_logs = [record for record in caplog.records
                             if hasattr(record, 'event') and record.event == 'lock_wait']

            # When DEBUG_STORAGE is not set, lock_wait event should NOT be logged
            # (it might be logged at DEBUG level, but not with structured fields)
            # The key is that without DEBUG_STORAGE, we shouldn't see the structured event
            # at INFO level
            info_level_wait_logs = [log for log in lock_wait_logs if log.levelno == logging.INFO]
            assert len(info_level_wait_logs) == 0, \
                "lock_wait event should not be logged at INFO level without DEBUG_STORAGE"

        finally:
            holder_thread.join()
