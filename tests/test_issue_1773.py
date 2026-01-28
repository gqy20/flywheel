"""Tests for debug log sampling functionality (Issue #1773)."""

import logging
import pytest
from unittest.mock import Mock, patch

from flywheel.storage import sample_debug_log


class TestDebugLogSampling:
    """Test sampling functionality for high-frequency debug logs."""

    def test_sample_debug_log_respects_rate_limit(self):
        """Test that sampling respects the rate_limit parameter."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        # Create a sampler with 10% rate (1 in 10)
        sampler = sample_debug_log(rate_limit=0.1)

        # Call 100 times
        for _ in range(100):
            sampler(mock_logger, "Test message %d", 1)

        # With 10% rate, should log approximately 10 times (allow 5-15 range)
        call_count = mock_logger.debug.call_count
        assert 5 <= call_count <= 15, f"Expected ~10 calls, got {call_count}"

    def test_sample_debug_log_rate_limit_one(self):
        """Test that rate_limit=1.0 logs every message."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        sampler = sample_debug_log(rate_limit=1.0)

        for i in range(10):
            sampler(mock_logger, "Test message %d", i)

        # Should log all 10 times
        assert mock_logger.debug.call_count == 10

    def test_sample_debug_log_rate_limit_zero(self):
        """Test that rate_limit=0 logs no messages."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        sampler = sample_debug_log(rate_limit=0.0)

        for i in range(10):
            sampler(mock_logger, "Test message %d", i)

        # Should log 0 times
        assert mock_logger.debug.call_count == 0

    def test_sample_debug_log_with_string_formatting(self):
        """Test that message formatting works correctly."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        sampler = sample_debug_log(rate_limit=1.0)

        # Use string formatting in message
        sampler(mock_logger, "Value: %s, attempts: %d", "test", 5)

        # Check that the message was formatted correctly
        mock_logger.debug.assert_called_once_with("Value: %s, attempts: %d", "test", 5)

    def test_sample_debug_log_with_kwargs(self):
        """Test that extra kwargs are passed through."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        sampler = sample_debug_log(rate_limit=1.0)

        # Call with extra kwargs
        sampler(mock_logger, "Test message", extra={'key': 'value'})

        # Check that kwargs were passed through
        mock_logger.debug.assert_called_once_with("Test message", extra={'key': 'value'})

    def test_sample_debug_log_is_deterministic(self):
        """Test that sampling is deterministic with same random seed."""
        import random

        mock_logger1 = Mock()
        mock_logger1.debug = Mock()
        mock_logger2 = Mock()
        mock_logger2.debug = Mock()

        # Set seed for reproducibility
        random.seed(42)
        sampler1 = sample_debug_log(rate_limit=0.5)

        random.seed(42)
        sampler2 = sample_debug_log(rate_limit=0.5)

        # Call both samplers 100 times
        for i in range(100):
            sampler1(mock_logger1, "Message %d", i)
            sampler2(mock_logger2, "Message %d", i)

        # Should have same call counts
        assert mock_logger1.debug.call_count == mock_logger2.debug.call_count

    def test_sample_debug_log_default_rate_limit(self):
        """Test that default rate_limit is reasonable."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        # Create sampler without specifying rate_limit
        sampler = sample_debug_log()

        # Call 100 times
        for _ in range(100):
            sampler(mock_logger, "Test message")

        # Default should be around 10% (0.1)
        # Allow reasonable range: 5-15 calls
        call_count = mock_logger.debug.call_count
        assert 5 <= call_count <= 15, f"Expected ~10 calls with default rate, got {call_count}"
