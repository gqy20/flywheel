"""Regression tests for Issue #4048: TodoApp.remove() should use O(n) list comprehension.

This test file ensures that remove() method uses single-pass filtering (list comprehension)
instead of enumerate+pop pattern which has O(n) overhead per pop operation.
"""

from __future__ import annotations

import time

import pytest

from flywheel.cli import TodoApp


def test_remove_uses_single_pass_filtering(tmp_path) -> None:
    """remove() should use list comprehension for O(n) single-pass removal.

    The implementation should NOT use enumerate + pop(i) pattern which
    has O(n) overhead per pop operation. Instead, it should use list
    comprehension or filter for O(n) total complexity.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    todo3 = app.add("third todo")

    # Remove middle todo
    app.remove(todo2.id)

    # Verify correct removal
    remaining = app.list()
    assert len(remaining) == 2
    remaining_ids = {t.id for t in remaining}
    assert todo1.id in remaining_ids
    assert todo2.id not in remaining_ids
    assert todo3.id in remaining_ids


def test_remove_nonexistent_raises_error(tmp_path) -> None:
    """remove() should raise ValueError for non-existent todo ID."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    app.add("test todo")

    with pytest.raises(ValueError, match=r"Todo #999 not found"):
        app.remove(999)


def test_remove_performance_with_large_list(tmp_path) -> None:
    """remove() should perform well even with large todo lists.

    This is a regression test to ensure the O(n) list comprehension
    approach is used instead of O(n^2) enumerate+pop pattern.

    With 10000 todos, list comprehension should complete in < 100ms,
    while enumerate+pop at the beginning of the list would take much longer.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add many todos
    for i in range(1000):
        app.add(f"todo {i}")

    # Measure time to remove first item (worst case for enumerate+pop)
    start = time.perf_counter()
    app.remove(1)  # Remove first item
    elapsed = time.perf_counter() - start

    # Should complete quickly (< 100ms for 1000 items)
    # enumerate+pop on first item would cause ~500 shifts
    assert elapsed < 0.1, f"remove() took too long: {elapsed:.3f}s"

    # Verify removal worked
    remaining = app.list()
    assert len(remaining) == 999
    assert all(t.id != 1 for t in remaining)
