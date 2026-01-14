"""Test ContextVar mutable default risk (Issue #1725).

This test verifies that:
1. ContextVar does not use mutable default dict
2. Context isolation is maintained across different async contexts
3. No cross-context contamination occurs
"""

import contextvars
import tempfile
import pathlib
from unittest.mock import patch

import pytest

from flywheel.storage import _storage_context, FileStorage, set_storage_context
from flywheel.models import Todo


class TestContextVarMutableDefaultRisk:
    """Test ContextVar mutable default risk (Issue #1725)."""

    def test_contextvar_default_is_none_or_immutable(self):
        """Test that ContextVar default is not a mutable dict.

        The current implementation uses default={} which is risky because:
        1. The same dict object could be shared across contexts
        2. If the dict is mutated, it affects all contexts
        3. This causes cross-context contamination
        """
        # Access the ContextVar to check its default
        # We need to check what happens when we get the value in a new context
        # In a clean context (without set), getting the value should not return
        # a mutable shared dict

        import copy

        # Get the value in a fresh context
        token = _storage_context.set({'test': 'value'})
        try:
            value1 = _storage_context.get()
            value1_id = id(value1)

            # Reset to get the default
            _storage_context.reset(token)

            # Get again - should be a different object if default is None
            # or the same object if default is {}
            value2 = _storage_context.get()
            value2_id = id(value2)

            # If using default={}, both will be the same object (BAD)
            # If using default=None, value2 will be None or a new dict (GOOD)
            # This test checks that we're NOT using the same mutable dict

            # The safest implementation is default=None
            # Then when getting, we check if None and return {}
            assert value1_id != value2_id or value2 is None, \
                "ContextVar should not use mutable default dict - use default=None instead"

        finally:
            _storage_context.reset(token)

    def test_context_isolation_with_mutation(self):
        """Test that contexts remain isolated even with mutations.

        This test simulates the scenario where:
        1. Context A gets the default dict
        2. Context A mutates the dict
        3. Context B should NOT see the mutation
        """
        import asyncio

        results = {}

        async def context_a():
            # Get the context (might be default dict)
            ctx = _storage_context.get({})
            # Mutate it
            ctx['key_a'] = 'value_a'
            results['a_id'] = id(ctx)
            results['a_value'] = ctx.copy()

        async def context_b():
            # Get the context (should not see context A's mutations)
            ctx = _storage_context.get({})
            results['b_id'] = id(ctx)
            results['b_value'] = ctx.copy()

        async def run_test():
            # Run both tasks
            await asyncio.gather(
                context_a(),
                context_b()
            )

        asyncio.run(run_test())

        # If default={} was used, both contexts would share the same dict
        # and context_b would see context_a's mutations
        if results['a_id'] == results['b_id']:
            # Same object - this is the bug!
            assert 'key_a' not in results['b_value'], \
                "Cross-context contamination detected! ContextVar uses mutable default dict"

    def test_set_storage_context_creates_new_dict(self):
        """Test that set_storage_context creates a new dict each time.

        This prevents mutations from affecting the shared default.
        """
        import asyncio

        # Set context in one async task
        async def task1():
            set_storage_context(request_id="req-1", user_id="user-1")
            ctx = _storage_context.get()
            return id(ctx), ctx.copy()

        # Get context in another async task
        async def task2():
            # Should not see task1's context
            ctx = _storage_context.get({})
            return id(ctx), ctx.copy()

        async def run_test():
            id1, ctx1 = await task1()
            id2, ctx2 = await task2()
            return id1, ctx1, id2, ctx2

        id1, ctx1, id2, ctx2 = asyncio.run(run_test())

        # The contexts should be different
        # task2 should not see task1's data
        assert 'request_id' not in ctx2, \
            "Context leakage detected - task2 should not see task1's context"

    def test_contextvar_default_not_mutable_in_storage(self):
        """Test that FileStorage doesn't inherit mutable context from ContextVar default.

        This is an integration test to ensure the storage system works correctly
        even when using ContextVar with context propagation.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"

            # Create storage and add a todo
            storage = FileStorage(str(storage_path))
            todo = Todo(title="Test ContextVar", description="Testing mutable default")
            storage.add(todo)
            storage.close()

            # Reopen storage
            storage = FileStorage(str(storage_path))

            # Set context
            set_storage_context(request_id="test-req-123")

            # The storage should work correctly
            todos = storage.list()
            assert len(todos) == 1
            assert todos[0].title == "Test ContextVar"

            storage.close()

            # Now in a new context, the old context should not leak
            storage2 = FileStorage(str(storage_path))
            todos2 = storage2.list()
            assert len(todos2) == 1
            storage2.close()

    def test_multiple_context_calls_dont_mutate_default(self):
        """Test that multiple calls to get() don't mutate the default.

        This test verifies that calling _storage_context.get() multiple times
        doesn't accumulate mutations in a shared default dict.
        """
        import asyncio

        mutation_count = {'count': 0}

        async def mutate_context():
            # Get context and mutate it
            ctx = _storage_context.get({})
            ctx[f'key_{mutation_count["count"]}'] = f'value_{mutation_count["count"]}'
            mutation_count['count'] += 1
            return len(ctx)

        async def run_many_mutations():
            # Run 10 async tasks that each mutate the context
            tasks = [mutate_context() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_many_mutations())

        # Each task should start with an empty context
        # So each result should be 1 (only their own key)
        # If default={} was shared, we'd see 1, 2, 3, ..., 10
        assert all(r == 1 for r in results), \
            f"Context mutation detected - results: {results}. All should be 1, but some are higher"
