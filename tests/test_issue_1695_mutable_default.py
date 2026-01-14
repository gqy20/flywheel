"""Test ContextVar mutable default risk (Issue #1695).

This test verifies that set_storage_context does not mutate the default dict.

Note: This issue is a FALSE POSITIVE from an AI scanner. The code has already
been fixed (see line 157 in storage.py: "Fix for Issue #1725").

The current implementation correctly uses dict unpacking to create new dicts:
    current = _storage_context.get() or {}
    new_context = {**current, **kwargs}  # Creates NEW dict (no mutation)
    _storage_context.set(new_context)

This test verifies that the fix is in place and working correctly.
"""

import asyncio
import contextvars

from flywheel.storage import _storage_context, set_storage_context


class TestIssue1695MutableDefault:
    """Test that set_storage_context doesn't mutate default dict (Issue #1695).

    This is a regression test to ensure the bug described in the issue
    doesn't exist. The issue was a false positive, but we keep the test
    to prevent future regressions.
    """

    def test_set_storage_context_no_mutation(self):
        """Test that set_storage_context creates new dict instead of mutating.

        The bug was:
        ```python
        current = _storage_context.get({})
        current.update(kwargs)  # MUTATES the dict!
        _storage_context.set(current)
        ```

        If the default dict is passed to get() and then mutated,
        it would cause cross-context contamination.

        The fix should be:
        ```python
        current = _storage_context.get() or {}
        new_context = {**current, **kwargs}  # Creates new dict
        _storage_context.set(new_context)
        ```
        """
        # First, set a context
        set_storage_context(request_id="req-123")

        # Get the context
        ctx1 = _storage_context.get()
        id1 = id(ctx1)

        # Call set_storage_context again
        set_storage_context(user_id="user-456")

        # Get the new context
        ctx2 = _storage_context.get()
        id2 = id(ctx2)

        # The new context should be a different object (new dict)
        assert id1 != id2, \
            "set_storage_context should create a new dict, not mutate the existing one"

        # The new context should have both values
        assert ctx2.get('request_id') == 'req-123'
        assert ctx2.get('user_id') == 'user-456'

    def test_default_dict_not_shared(self):
        """Test that the default dict is not shared across calls.

        This test verifies that calling set_storage_context multiple times
        doesn't accumulate mutations in a shared default dict.
        """
        results = []

        async def task1():
            # Set context in task1
            set_storage_context(task="1", value="a")
            ctx = _storage_context.get()
            results.append(('task1', id(ctx), ctx.copy()))

        async def task2():
            # Set context in task2
            set_storage_context(task="2", value="b")
            ctx = _storage_context.get()
            results.append(('task2', id(ctx), ctx.copy()))

        async def run_test():
            await asyncio.gather(task1(), task2())

        asyncio.run(run_test())

        # Each task should have its own context
        _, id1, ctx1 = results[0]
        _, id2, ctx2 = results[1]

        # Different dict objects
        assert id1 != id2, "Each task should have its own context dict"

        # Each context should only have its own data
        assert ctx1.get('task') == '1'
        assert ctx2.get('task') == '2'

    def test_get_default_dict_not_mutated(self):
        """Test that getting default dict and calling set_storage_context doesn't mutate it.

        This is the core bug from the issue: if we call _storage_context.get({})
        and then call set_storage_context, it should not mutate the default dict.
        """
        # Get the default dict (if any)
        default_before = _storage_context.get()
        id_before = id(default_before) if default_before is not None else None

        # Set storage context
        set_storage_context(test_key="test_value")

        # Get the context again
        ctx_after = _storage_context.get()

        # If default_before was None, ctx_after should be a new dict
        # If default_before was a dict, ctx_after should be a different dict
        if default_before is None:
            assert ctx_after is not None, "Context should be set"
            assert ctx_after == {'test_key': 'test_value'}
        else:
            # Should be a different object (not mutated)
            assert id(ctx_after) != id_before, \
                "set_storage_context should create new dict, not mutate default"

    def test_isolated_context_with_get_default(self):
        """Test that contexts remain isolated when using get({}) pattern.

        This simulates the exact bug scenario from the issue.
        """
        results = {}

        async def context_a():
            # Simulate the buggy pattern: get({}) then mutate
            current = _storage_context.get({})
            current['key_a'] = 'value_a'
            # This would mutate the default if it's shared!
            _storage_context.set(current)
            results['a'] = _storage_context.get().copy()

        async def context_b():
            # In a clean context, should not see context_a's mutation
            ctx = _storage_context.get({})
            results['b_raw_get'] = ctx.copy()
            # Now set storage context properly
            set_storage_context(key_b='value_b')
            results['b'] = _storage_context.get().copy()

        async def run_test():
            # Ensure clean context
            _storage_context.set(None)
            await asyncio.gather(context_a(), context_b())

        asyncio.run(run_test())

        # Context B should NOT see context A's mutation in the raw get
        # (assuming the default dict is not shared)
        # If the bug exists, 'key_a' would be in b_raw_get
        assert 'key_a' not in results['b_raw_get'], \
            "Cross-context contamination detected! The default dict is being shared and mutated"
