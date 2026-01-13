"""Test log rotation for JSONFormatter (Issue #1637)."""
import logging
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import JSONFormatter


class TestLogRotation:
    """Test log rotation functionality for structured JSON logs."""

    def test_rotating_file_handler_configuration(self):
        """Test that DEBUG_STORAGE enables log rotation with RotatingFileHandler."""
        # This test verifies that when DEBUG_STORAGE is enabled,
        # the handler is a RotatingFileHandler with proper configuration

        from logging.handlers import RotatingFileHandler

        # Get the storage logger
        import flywheel.storage
        logger = logging.getLogger('flywheel.storage')

        # Check if any handler is a RotatingFileHandler with JSONFormatter
        has_rotating_json_handler = any(
            isinstance(h, RotatingFileHandler) and isinstance(h.formatter, JSONFormatter)
            for h in logger.handlers
        )

        # When DEBUG_STORAGE is enabled, should have rotating handler
        if os.environ.get('DEBUG_STORAGE'):
            assert has_rotating_json_handler, (
                "DEBUG_STORAGE enabled but no RotatingFileHandler with JSONFormatter found"
            )

            # Find the rotating handler and verify its configuration
            rotating_handler = next(
                h for h in logger.handlers
                if isinstance(h, RotatingFileHandler) and isinstance(h.formatter, JSONFormatter)
            )

            # Verify rotation parameters are configured
            assert rotating_handler.maxBytes > 0, "maxBytes should be configured"
            assert rotating_handler.backupCount >= 0, "backupCount should be configured"

    def test_rotating_file_handler_creates_backup_files(self):
        """Test that RotatingFileHandler creates backup files when size limit is reached."""
        from logging.handlers import RotatingFileHandler

        # Get the storage logger
        import flywheel.storage
        logger = logging.getLogger('flywheel.storage')

        # Only run this test if DEBUG_STORAGE is enabled with a rotating handler
        if not os.environ.get('DEBUG_STORAGE'):
            pytest.skip("DEBUG_STORAGE not enabled")

        rotating_handler = next(
            (h for h in logger.handlers
             if isinstance(h, RotatingFileHandler) and isinstance(h.formatter, JSONFormatter)),
            None
        )

        if not rotating_handler:
            pytest.skip("No RotatingFileHandler configured")

        # Get the base log file path
        base_file = rotating_handler.baseFilename

        # Create a temporary directory for testing if not already set
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_file = Path(tmpdir) / "test_rotation.log"

            # Create a rotating handler with small size limit for testing
            test_handler = RotatingFileHandler(
                str(test_log_file),
                maxBytes=1024,  # 1KB - very small for testing
                backupCount=3,
            )
            test_handler.setFormatter(JSONFormatter())

            # Create a test logger
            test_logger = logging.getLogger('test_rotation')
            test_logger.setLevel(logging.INFO)
            test_logger.addHandler(test_handler)

            # Generate enough logs to trigger rotation
            # Each log entry is roughly 200-300 bytes, so 5 entries should trigger rotation
            for i in range(10):
                test_logger.info(
                    "Test log message with enough content to trigger rotation",
                    extra={'iteration': i, 'data': 'x' * 100}
                )

            # Flush and close
            test_handler.flush()
            test_handler.close()

            # Verify that the base file exists
            assert test_log_file.exists(), "Base log file should exist"

            # Verify that at least one backup file was created
            backup_files = list(Path(tmpdir).glob("test_rotation.log.*"))
            assert len(backup_files) > 0, "At least one backup file should be created"

            # Verify backup count is respected
            assert len(backup_files) <= 3, "Should not exceed backupCount"

    def test_stream_handler_replaced_with_rotating_handler(self):
        """Test that StreamHandler is replaced with RotatingFileHandler."""
        from logging.handlers import RotatingFileHandler

        # Get the storage logger
        import flywheel.storage
        logger = logging.getLogger('flywheel.storage')

        if not os.environ.get('DEBUG_STORAGE'):
            pytest.skip("DEBUG_STORAGE not enabled")

        # Check that there are no StreamHandler instances with JSONFormatter
        # (they should be replaced with RotatingFileHandler)
        has_stream_json_handler = any(
            isinstance(h, logging.StreamHandler) and
            not isinstance(h, RotatingFileHandler) and
            isinstance(h.formatter, JSONFormatter)
            for h in logger.handlers
        )

        assert not has_stream_json_handler, (
            "StreamHandler with JSONFormatter should be replaced with RotatingFileHandler"
        )

        # Verify there's a RotatingFileHandler instead
        has_rotating_json_handler = any(
            isinstance(h, RotatingFileHandler) and isinstance(h.formatter, JSONFormatter)
            for h in logger.handlers
        )

        assert has_rotating_json_handler, (
            "Should have RotatingFileHandler with JSONFormatter when DEBUG_STORAGE is enabled"
        )
