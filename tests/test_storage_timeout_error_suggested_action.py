"""Tests for StorageTimeoutError suggested_action feature (Issue #1553)."""

import pytest

from flywheel.storage import StorageTimeoutError


class TestStorageTimeoutErrorSuggestedAction:
    """Test suite for StorageTimeoutError suggested_action functionality."""

    def test_suggested_action_attribute_exists(self):
        """Test that suggested_action attribute exists."""
        error = StorageTimeoutError("Test error")
        assert hasattr(error, "suggested_action")

    def test_suggested_action_for_lock_timeout(self):
        """Test suggested_action for lock timeout scenarios."""
        error = StorageTimeoutError(
            message="Lock acquisition timeout",
            operation="acquire_lock"
        )
        assert error.suggested_action is not None
        assert "retry" in error.suggested_action.lower() or "wait" in error.suggested_action.lower()

    def test_suggested_action_for_io_timeout(self):
        """Test suggested_action for I/O timeout scenarios."""
        error = StorageTimeoutError(
            message="I/O operation timeout",
            operation="load_cache"
        )
        assert error.suggested_action is not None
        # I/O timeout should suggest checking disk space or retrying
        assert any(keyword in error.suggested_action.lower()
                  for keyword in ["retry", "disk", "space", "check"])

    def test_suggested_action_custom_provided(self):
        """Test that custom suggested_action can be provided."""
        custom_action = "Check network connectivity"
        error = StorageTimeoutError(
            message="Custom error",
            suggested_action=custom_action
        )
        assert error.suggested_action == custom_action

    def test_str_includes_suggested_action(self):
        """Test that __str__ includes suggested_action when present."""
        error = StorageTimeoutError(
            message="Timeout occurred",
            operation="save_data"
        )
        error_str = str(error)
        # The suggested action should be visible in the string representation
        if error.suggested_action:
            assert error.suggested_action in error_str or "suggested" in error_str.lower()

    def test_suggested_action_default_empty_string(self):
        """Test that suggested_action defaults to empty string when not applicable."""
        error = StorageTimeoutError("Generic timeout")
        assert error.suggested_action == ""
