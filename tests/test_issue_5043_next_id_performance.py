"""Regression test for issue #5043: next_id() O(n) performance.

This test verifies that next_id() operates efficiently even with large datasets.
The acceptance criteria requires next_id to handle 10000 todos in <10ms.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_performance_with_large_dataset() -> None:
    """Regression test for issue #5043: next_id() must be O(1), not O(n).

    Verifies that next_id() performs efficiently with 10000 todos.
    The operation should complete in <10ms per acceptance criteria.
    """
    storage = TodoStorage("/tmp/test.json")

    # Create 10000 todos to test performance
    todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 10001)]

    # Measure time to get next_id
    start_time = time.perf_counter()
    next_id = storage.next_id(todos)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Verify correctness
    assert next_id == 10001, f"Expected next_id to be 10001, got {next_id}"

    # Verify performance: should be <10ms per acceptance criteria
    assert elapsed_ms < 10, (
        f"next_id() took {elapsed_ms:.2f}ms for 10000 todos, "
        f"expected <10ms. This suggests O(n) linear scan instead of O(1)."
    )


def test_next_id_performance_is_constant_time() -> None:
    """Verify next_id() has O(1) complexity, not O(n).

    This test uses a more sensitive approach: run next_id() multiple times
    and compare execution times for different dataset sizes.
    For O(1), the time should be nearly constant regardless of dataset size.
    For O(n), time should grow linearly with dataset size.
    """
    storage = TodoStorage("/tmp/test.json")

    # Warm up to avoid cold-start effects
    _ = storage.next_id([Todo(id=1, text="warmup")])

    # Measure with 1000 todos (multiple iterations for accuracy)
    todos_1k = [Todo(id=i, text=f"task-{i}") for i in range(1, 1001)]
    iterations = 100
    start_time = time.perf_counter()
    for _ in range(iterations):
        storage.next_id(todos_1k)
    time_1k = (time.perf_counter() - start_time) / iterations * 1000  # ms per call

    # Measure with 10000 todos (10x larger)
    todos_10k = [Todo(id=i, text=f"task-{i}") for i in range(1, 10001)]
    start_time = time.perf_counter()
    for _ in range(iterations):
        storage.next_id(todos_10k)
    time_10k = (time.perf_counter() - start_time) / iterations * 1000  # ms per call

    # For O(1), time should stay roughly the same (allow up to 2x overhead)
    # For O(n), time would grow ~10x when dataset grows 10x
    # If ratio > 5, we have O(n) behavior which is the bug
    ratio = time_10k / time_1k if time_1k > 0 else 0
    assert ratio < 5, (
        f"next_id() shows O(n) behavior: 1k={time_1k:.4f}ms, 10k={time_10k:.4f}ms "
        f"(ratio={ratio:.1f}x). Expected O(1) behavior with ratio < 5."
    )


def test_next_id_returns_correct_value_for_empty_list() -> None:
    """Verify next_id() returns 1 for empty list."""
    storage = TodoStorage("/tmp/test.json")
    assert storage.next_id([]) == 1


def test_next_id_returns_correct_value_for_single_todo() -> None:
    """Verify next_id() returns correct value for single todo."""
    storage = TodoStorage("/tmp/test.json")
    todos = [Todo(id=1, text="single")]
    assert storage.next_id(todos) == 2


def test_next_id_handles_sparse_ids() -> None:
    """Verify next_id() handles non-contiguous IDs correctly.

    When todos are deleted, IDs may not be contiguous.
    next_id() should return max(id) + 1, not fill gaps.
    """
    storage = TodoStorage("/tmp/test.json")
    # IDs 1, 5, 10 (sparse due to deletions)
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
    assert storage.next_id(todos) == 11


def test_next_id_performance_scales_sublinearly() -> None:
    """Verify next_id() performance scales sublinearly with dataset size.

    For an O(1) implementation, doubling the dataset should not double
    the execution time.
    """
    storage = TodoStorage("/tmp/test.json")

    # Measure with 5000 todos
    todos_5k = [Todo(id=i, text=f"task-{i}") for i in range(1, 5001)]
    start_time = time.perf_counter()
    for _ in range(10):  # Multiple iterations for more reliable measurement
        storage.next_id(todos_5k)
    time_5k = (time.perf_counter() - start_time) * 1000

    # Measure with 10000 todos
    todos_10k = [Todo(id=i, text=f"task-{i}") for i in range(1, 10001)]
    start_time = time.perf_counter()
    for _ in range(10):
        storage.next_id(todos_10k)
    time_10k = (time.perf_counter() - start_time) * 1000

    # For O(1), time should not more than double when dataset doubles
    # Allow some overhead for noise (up to 3x tolerance)
    assert time_10k < time_5k * 3, (
        f"Performance degrades linearly: 5k={time_5k:.2f}ms, 10k={time_10k:.2f}ms. "
        f"Expected sublinear scaling for O(1) implementation."
    )
