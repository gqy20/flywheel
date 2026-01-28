"""Test for Issue #1690: Context data loss due to dictionary unpacking"""

import pytest
from flywheel.storage import set_storage_context, _storage_context


def test_set_storage_context_preserves_existing_keys():
    """Test that set_storage_context preserves existing keys not in kwargs.

    This test verifies the fix for Issue #1690. The bug was that using
    dictionary unpacking {**current, **kwargs} would lose any existing keys
    that are not present in kwargs. The correct behavior is to merge kwargs
    into the existing context without losing old keys.
    """
    # Set initial context with two keys
    set_storage_context(request_id="req-123", user_id="user-456")
    initial_context = _storage_context.get({})
    assert initial_context == {"request_id": "req-123", "user_id": "user-456"}

    # Update context with only one key (the other should be preserved)
    set_storage_context(session_id="session-789")
    updated_context = _storage_context.get({})

    # Both old keys should still be present, plus the new key
    assert "request_id" in updated_context, "Existing key 'request_id' was lost!"
    assert "user_id" in updated_context, "Existing key 'user_id' was lost!"
    assert "session_id" in updated_context, "New key 'session_id' was not added!"

    assert updated_context["request_id"] == "req-123"
    assert updated_context["user_id"] == "user-456"
    assert updated_context["session_id"] == "session-789"


def test_set_storage_context_updates_existing_keys():
    """Test that set_storage_context can update existing keys."""
    # Set initial context
    set_storage_context(request_id="req-123", user_id="user-456")

    # Update one of the existing keys
    set_storage_context(request_id="req-999")
    updated_context = _storage_context.get({})

    assert updated_context["request_id"] == "req-999"
    assert updated_context["user_id"] == "user-456"


def test_set_storage_context_empty_then_add():
    """Test that we can start with empty context and add keys."""
    # Clear context by getting empty
    _storage_context.set({})

    # Add first key
    set_storage_context(key1="value1")
    assert _storage_context.get({}) == {"key1": "value1"}

    # Add second key (first should be preserved)
    set_storage_context(key2="value2")
    context = _storage_context.get({})
    assert context == {"key1": "value1", "key2": "value2"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
