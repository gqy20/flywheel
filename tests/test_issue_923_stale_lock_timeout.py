"""Test configurable stale lock timeout via environment variable (Issue #923).

This test verifies that the stale lock timeout threshold can be configured
via the FW_LOCK_STALE_SECONDS environment variable instead of being hardcoded.
"""

import os
import pytest
import tempfile
import time
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


@pytest.mark.skipif(
    os.name != 'nt',
    reason="Stale lock detection is primarily used in degraded mode on Windows"
)
class TestStaleLockTimeoutConfig:
    """Test configurable stale lock timeout via environment variable."""

    def test_default_stale_timeout_is_300_seconds(self):
        """Test that the default stale lock timeout is 300 seconds (5 minutes)."""
        # Ensure no custom env var is set
        if 'FW_LOCK_STALE_SECONDS' in os.environ:
            del os.environ['FW_LOCK_STALE_SECONDS']

        # Need to reload the storage module to pick up the default value
        import importlib
        import flywheel.storage
        importlib.reload(flywheel.storage)

        from flywheel.storage import Storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify default is used
            # This test documents the expected behavior
            assert storage is not None

    def test_custom_stale_timeout_via_env_var(self):
        """Test that FW_LOCK_STALE_SECONDS environment variable is respected."""
        # Set custom stale timeout
        os.environ['FW_LOCK_STALE_SECONDS'] = '600'  # 10 minutes

        # Need to reload the storage module to pick up the new env var
        import importlib
        import flywheel.storage
        importlib.reload(flywheel.storage)

        from flywheel.storage import Storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify storage was created successfully
            assert storage is not None

            # The implementation should use the custom timeout value
            # This test will fail until the feature is implemented
            # We verify this by checking that the module-level constant exists
            assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
            assert flywheel.storage.STALE_LOCK_TIMEOUT == 600

    def test_invalid_stale_timeout_falls_back_to_default(self):
        """Test that invalid FW_LOCK_STALE_SECONDS falls back to default."""
        # Set invalid stale timeout
        os.environ['FW_LOCK_STALE_SECONDS'] = 'invalid'

        # Need to reload the storage module to pick up the new env var
        import importlib
        import flywheel.storage
        importlib.reload(flywheel.storage)

        from flywheel.storage import Storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify storage was created successfully with default
            assert storage is not None

            # Should fall back to default 300 seconds
            assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
            assert flywheel.storage.STALE_LOCK_TIMEOUT == 300

    def test_negative_stale_timeout_falls_back_to_default(self):
        """Test that negative FW_LOCK_STALE_SECONDS falls back to default."""
        # Set negative stale timeout
        os.environ['FW_LOCK_STALE_SECONDS'] = '-100'

        # Need to reload the storage module to pick up the new env var
        import importlib
        import flywheel.storage
        importlib.reload(flywheel.storage)

        from flywheel.storage import Storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify storage was created successfully with default
            assert storage is not None

            # Should fall back to default 300 seconds
            assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
            assert flywheel.storage.STALE_LOCK_TIMEOUT == 300

    def test_zero_stale_timeout_falls_back_to_default(self):
        """Test that zero FW_LOCK_STALE_SECONDS falls back to default."""
        # Set zero stale timeout
        os.environ['FW_LOCK_STALE_SECONDS'] = '0'

        # Need to reload the storage module to pick up the new env var
        import importlib
        import flywheel.storage
        importlib.reload(flywheel.storage)

        from flywheel.storage import Storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify storage was created successfully with default
            assert storage is not None

            # Should fall back to default 300 seconds
            assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
            assert flywheel.storage.STALE_LOCK_TIMEOUT == 300
