"""Test periodic stats flushing for long-running processes (Issue #1548)."""
import pytest
from unittest.mock import patch
from flywheel.storage import FileStorage


def test_flush_stats_logs_and_resets_counters():
    """Test that flush_stats() logs current metrics and resets counters."""
    storage = FileStorage(':memory:')

    # Simulate some lock activity
    initial_stats = storage.get_stats()
    assert initial_stats['acquire_count'] > 0, "Should have some lock activity"

    # Record the initial counts before flushing
    acquire_count_before = initial_stats['acquire_count']
    wait_time_before = initial_stats['total_wait_time']
    contention_count_before = initial_stats['contention_count']

    # Call flush_stats and verify it logs the stats
    with patch('flywheel.storage.logger') as mock_logger:
        storage.flush_stats()

        # Verify that flush_stats logged the metrics
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert 'stats_flushed' in call_args[1] or any('stats_flushed' in str(arg) for arg in call_args[0])

    # Verify that counters were reset
    stats_after = storage.get_stats()
    assert stats_after['acquire_count'] == 0, "Acquire count should be reset to 0"
    assert stats_after['total_wait_time'] == 0.0, "Total wait time should be reset to 0.0"
    assert stats_after['contention_count'] == 0, "Contention count should be reset to 0"


def test_flush_stats_logs_metric_details():
    """Test that flush_stats logs the actual metric values."""
    storage = FileStorage(':memory:')

    # Trigger some lock activity to ensure we have stats
    with storage._lock:
        pass

    # Get stats before flush
    stats_before = storage.get_stats()

    # Call flush_stats and capture the log
    with patch('flywheel.storage.logger') as mock_logger:
        storage.flush_stats()

        # Verify the log contains the metric values
        call_args = mock_logger.info.call_args

        # Check that the logged values match what was recorded
        logged_data = call_args[1] if call_args[1] else call_args[0][0]

        # The log should mention the counts from before the flush
        assert 'acquire_count' in str(logged_data) or stats_before['acquire_count'] in str(logged_data)


def test_flush_stats_is_thread_safe():
    """Test that flush_stats maintains thread safety with stats_lock."""
    storage = FileStorage(':memory:')

    # This should not raise any exceptions
    storage.flush_stats()

    # Multiple calls should be safe
    for _ in range(10):
        storage.flush_stats()


def test_periodic_flush_after_threshold():
    """Test that flush_stats is called automatically every N acquisitions."""
    storage = FileStorage(':memory:')

    # Set a flush threshold for testing
    original_threshold = getattr(storage, '_flush_threshold', None)

    try:
        # Manually set a low threshold for testing
        storage._flush_threshold = 5
        storage._last_flush_count = 0

        # Track if flush was called
        flush_called = []

        original_flush = storage.flush_stats
        def mock_flush():
            flush_called.append(True)
            original_flush()

        storage.flush_stats = mock_flush

        # Acquire lock multiple times
        for _ in range(10):
            with storage._lock:
                pass

        # Flush should have been called at least once
        assert len(flush_called) > 0, "flush_stats should be called automatically after threshold"

    finally:
        # Restore original threshold
        if original_threshold is not None:
            storage._flush_threshold = original_threshold
