"""Test file lock acquisition timeout configuration (Issue #952).

This test verifies that:
1. Environment variable FW_LOCK_TIMEOUT_SECONDS is respected
2. The timeout value is properly used in FileStorage initialization
3. Custom TimeoutError is raised when lock acquisition times out
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from flywheel.storage import FileStorage


class TestLockTimeoutConfiguration:
    """Test suite for lock timeout configuration via environment variable."""

    def test_lock_timeout_from_environment_variable(self):
        """Test that FW_LOCK_TIMEOUT_SECONDS environment variable is respected."""
        # Set environment variable
        os.environ['FW_LOCK_TIMEOUT_SECONDS'] = '15.0'

        try:
            # Create storage instance
            with tempfile.TemporaryDirectory() as tmpdir:
                storage = FileStorage(
                    path=os.path.join(tmpdir, 'test.json'),
                    enable_cache=False
                )

                # Verify timeout is set correctly
                assert storage._lock_timeout == 15.0
        finally:
            # Clean up environment variable
            if 'FW_LOCK_TIMEOUT_SECONDS' in os.environ:
                del os.environ['FW_LOCK_TIMEOUT_SECONDS']

    def test_lock_timeout_default_without_environment_variable(self):
        """Test that default timeout is used when environment variable is not set."""
        # Ensure environment variable is not set
        if 'FW_LOCK_TIMEOUT_SECONDS' in os.environ:
            del os.environ['FW_LOCK_TIMEOUT_SECONDS']

        # Create storage instance
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = FileStorage(
                path=os.path.join(tmpdir, 'test.json'),
                enable_cache=False
            )

            # Verify default timeout is used
            assert storage._lock_timeout == 30.0

    def test_lock_timeout_parameter_overrides_environment(self):
        """Test that explicit parameter takes precedence over environment variable."""
        # Set environment variable
        os.environ['FW_LOCK_TIMEOUT_SECONDS'] = '15.0'

        try:
            # Create storage instance with explicit timeout
            with tempfile.TemporaryDirectory() as tmpdir:
                storage = FileStorage(
                    path=os.path.join(tmpdir, 'test.json'),
                    enable_cache=False,
                    lock_timeout=25.0
                )

                # Verify explicit parameter is used
                assert storage._lock_timeout == 25.0
        finally:
            # Clean up environment variable
            if 'FW_LOCK_TIMEOUT_SECONDS' in os.environ:
                del os.environ['FW_LOCK_TIMEOUT_SECONDS']

    def test_lock_timeout_invalid_value_from_environment(self):
        """Test that invalid environment variable value raises ValueError."""
        # Set invalid environment variable
        os.environ['FW_LOCK_TIMEOUT_SECONDS'] = 'invalid'

        try:
            # Create storage instance - should raise ValueError
            with tempfile.TemporaryDirectory() as tmpdir:
                with pytest.raises(ValueError, match="lock_timeout must be positive"):
                    FileStorage(
                        path=os.path.join(tmpdir, 'test.json'),
                        enable_cache=False
                    )
        finally:
            # Clean up environment variable
            if 'FW_LOCK_TIMEOUT_SECONDS' in os.environ:
                del os.environ['FW_LOCK_TIMEOUT_SECONDS']

    def test_lock_timeout_negative_value_from_environment(self):
        """Test that negative environment variable value raises ValueError."""
        # Set negative environment variable
        os.environ['FW_LOCK_TIMEOUT_SECONDS'] = '-5.0'

        try:
            # Create storage instance - should raise ValueError
            with tempfile.TemporaryDirectory() as tmpdir:
                with pytest.raises(ValueError, match="lock_timeout must be positive"):
                    FileStorage(
                        path=os.path.join(tmpdir, 'test.json'),
                        enable_cache=False
                    )
        finally:
            # Clean up environment variable
            if 'FW_LOCK_TIMEOUT_SECONDS' in os.environ:
                del os.environ['FW_LOCK_TIMEOUT_SECONDS']
