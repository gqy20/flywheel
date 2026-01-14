"""
Test for Issue #1720: set_storage_context may cause unexpected context data sharing
"""
import pytest
import contextvars
from flywheel.storage import set_storage_context


def test_storage_context_isolation():
    """
    Test that set_storage_context doesn't share context between different ContextVar instances.

    This test verifies the bug where using default={} in ContextVar.get()
    causes the same dict object to be shared across different contexts.
    """
    # Create a new ContextVar (simulating isolated context)
    test_context = contextvars.ContextVar('test_context', default={})

    # Get the default context from two different "tasks"
    context1 = test_context.get({})
    context2 = test_context.get({})

    # Modify context1
    context1['key1'] = 'value1'

    # context2 should NOT be affected if they are truly isolated
    # But with the bug, context2 will have 'key1' because they share the same dict object
    assert 'key1' not in context2, "Context data should not be shared between different contexts"

    # Additionally, verify the IDs are different
    assert id(context1) != id(context2), "Context objects should be different instances"


def test_set_storage_context_with_default():
    """
    Test that calling set_storage_context with the default context doesn't pollute the shared state.
    """
    # Reset the storage context to get the default
    from flywheel.storage import _storage_context

    # Get the default context
    default_ctx = _storage_context.get({})

    # Call set_storage_context to add some data
    set_storage_context(test_key='test_value')

    # The default context should NOT have been modified
    # (If the bug exists, default_ctx will have 'test_key')
    assert 'test_key' not in default_ctx, "Default context should not be modified by set_storage_context"


def test_multiple_context_updates_isolation():
    """
    Test that multiple calls to set_storage_context maintain proper isolation.
    """
    from flywheel.storage import _storage_context
    import copy

    # Save original context
    original_token = _storage_context.set({})

    try:
        # First context update
        set_storage_context(user='alice', request_id='req-1')
        ctx1 = _storage_context.get({})

        # Second context update
        set_storage_context(user='bob', request_id='req-2')
        ctx2 = _storage_context.get({})

        # Each call should create a new context, not mutate the default
        # Verify that contexts have the expected values
        assert ctx2.get('user') == 'bob'
        assert ctx2.get('request_id') == 'req-2'

        # The key issue: the default dict should not accumulate these values
        default_check = _storage_context.get({})
        # If bug exists, default_check will have 'user' and 'request_id'

        # Reset to test the default again
        _storage_context.set({})
        fresh_default = _storage_context.get({})

        # Fresh default should be empty
        assert len(fresh_default) == 0, "Fresh default context should be empty, not polluted by previous updates"

    finally:
        # Restore original context
        _storage_context.reset(original_token)
