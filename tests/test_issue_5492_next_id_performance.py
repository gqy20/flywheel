"""Tests for next_id O(1) performance optimization.

This test suite verifies that TodoStorage.next_id() operates in O(1) time
regardless of the number of todos, addressing the performance issue where
the original max() scan caused O(n) overhead on every add operation.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Tests for O(1) next_id performance."""

    def test_next_id_returns_correct_value_for_empty_list(self, tmp_path) -> None:
        """next_id should return 1 for empty todo list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        assert storage.next_id([]) == 1

    def test_next_id_returns_correct_value_with_todos(self, tmp_path) -> None:
        """next_id should return max_id + 1 for existing todos."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="first"),
            Todo(id=5, text="second"),
            Todo(id=3, text="third"),
        ]

        assert storage.next_id(todos) == 6

    def test_next_id_is_constant_time_for_large_lists(self, tmp_path) -> None:
        """next_id should complete in O(1) time regardless of list size.

        This is a regression test for issue #5492.
        The benchmark verifies that next_id takes roughly the same time
        for 10, 1000, and 10000 todos.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Test sizes as specified in the acceptance criteria
        sizes = [10, 1000, 10000]
        timings = {}

        for size in sizes:
            todos = [Todo(id=i + 1, text=f"todo-{i}") for i in range(size)]

            # Warm up
            for _ in range(3):
                storage.next_id(todos)

            # Measure time
            iterations = 100
            start = time.perf_counter()
            for _ in range(iterations):
                storage.next_id(todos)
            end = time.perf_counter()

            avg_time = (end - start) / iterations
            timings[size] = avg_time

        # The key assertion: time should NOT grow linearly with size
        # Allow for some variance, but time for 10000 items should not be
        # significantly more than time for 10 items (O(1) vs O(n))
        # We use a factor of 10 as tolerance (10000/10 = 1000, but O(1) would be ~same)
        # If O(n), time for 10000 would be ~1000x time for 10
        # If O(1), time for 10000 would be ~same as time for 10

        ratio_large_to_small = timings[10000] / timings[10]

        # With O(1) implementation, ratio should be close to 1
        # With O(n) implementation, ratio would be ~1000
        # We allow up to 5x as tolerance for measurement noise
        assert ratio_large_to_small < 5, (
            f"next_id appears to be O(n), not O(1). "
            f"Time ratio for 10000 vs 10 items: {ratio_large_to_small:.2f} "
            f"(timings: {timings}). "
            f"Expected O(1) behavior with ratio < 5."
        )

    def test_next_id_correctness_after_max_id_caching(self, tmp_path) -> None:
        """next_id should maintain correctness with cached max_id.

        Verifies that for a fresh storage instance, next_id correctly
        computes the initial max_id and then increments properly.
        Each test case uses a NEW storage instance to ensure independence.
        """
        # Test various edge cases - each with a fresh storage instance
        test_cases = [
            ([], 1),
            ([Todo(id=1, text="a")], 2),
            ([Todo(id=1, text="a"), Todo(id=2, text="b")], 3),
            ([Todo(id=5, text="a"), Todo(id=3, text="b"), Todo(id=1, text="c")], 6),
            ([Todo(id=100, text="a")], 101),
        ]

        for todos, expected_id in test_cases:
            db = tmp_path / f"todo_{expected_id}.json"
            storage = TodoStorage(str(db))
            actual_id = storage.next_id(todos)
            assert actual_id == expected_id, (
                f"next_id({todos}) = {actual_id}, expected {expected_id}"
            )

    def test_next_id_with_persistent_max_id_tracking(self, tmp_path) -> None:
        """next_id should track max_id persistently across calls.

        This tests the real-world usage pattern where next_id is called
        multiple times to allocate IDs for a growing list, simulating
        the add() operation flow without reloading from disk each time.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Start with an empty list
        todos: list[Todo] = []

        # Allocate first ID
        id1 = storage.next_id(todos)
        assert id1 == 1

        # Add todo with ID 1
        todos.append(Todo(id=id1, text="first"))

        # Allocate second ID - should be 2, using cached max_id
        id2 = storage.next_id(todos)
        assert id2 == 2

        # Add todo with ID 2
        todos.append(Todo(id=id2, text="second"))

        # Continue adding todos
        for i in range(3, 10):
            new_id = storage.next_id(todos)
            assert new_id == i
            todos.append(Todo(id=new_id, text=f"todo-{i}"))

        # Verify all IDs are unique
        all_ids = [t.id for t in todos]
        assert len(set(all_ids)) == len(all_ids), "All IDs should be unique"
        assert max(all_ids) == 9

    def test_next_id_realistic_add_flow_with_save_load(self, tmp_path) -> None:
        """next_id should work correctly in realistic add flow with save/load.

        This simulates the actual usage pattern from cli.py where:
        1. todos = storage.load()
        2. new_id = storage.next_id(todos)
        3. todos.append(Todo(id=new_id, ...))
        4. storage.save(todos)

        The key insight is that load() returns a NEW list object each time,
        so caching by list id(todos) doesn't help across load() calls.
        The storage should maintain persistent max_id tracking.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First add - empty storage
        todos = storage.load()
        new_id = storage.next_id(todos)
        assert new_id == 1
        todos.append(Todo(id=new_id, text="first"))
        storage.save(todos)

        # Second add - load from saved storage
        todos = storage.load()
        new_id = storage.next_id(todos)
        assert new_id == 2
        todos.append(Todo(id=new_id, text="second"))
        storage.save(todos)

        # Third add
        todos = storage.load()
        new_id = storage.next_id(todos)
        assert new_id == 3
        todos.append(Todo(id=new_id, text="third"))
        storage.save(todos)

        # Verify final state
        todos = storage.load()
        assert len(todos) == 3
        assert [t.id for t in todos] == [1, 2, 3]
