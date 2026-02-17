"""Regression tests for Issue #4048: TodoApp.remove() performance optimization.

This test file ensures that remove() method uses O(n) list comprehension
instead of O(n^2) enumerate+pop(i) pattern for better performance.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest  # noqa: F401 - used for tmp_path fixture

from flywheel.cli import TodoApp


class EnumeratePopDetector(ast.NodeVisitor):
    """AST visitor to detect enumerate + pop(i) pattern in a function."""

    def __init__(self) -> None:
        self.has_enumerate_pop_pattern = False
        self._in_for_loop_with_enumerate = False
        self._loop_index_var: str | None = None

    def visit_For(self, node: ast.For) -> None:
        """Check if for loop uses enumerate and track the index variable."""
        # Check if the iterator is a call to enumerate
        if (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "enumerate"
            and isinstance(node.target, ast.Tuple)
        ):
            elts = node.target.elts
            if len(elts) == 2:
                self._loop_index_var = elts[0].id  # type: ignore[attr-defined]
                self._in_for_loop_with_enumerate = True
                self.generic_visit(node)
                self._in_for_loop_with_enumerate = False
                self._loop_index_var = None
                return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check if pop is called with the enumerate index variable."""
        if (
            self._in_for_loop_with_enumerate
            and self._loop_index_var
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == self._loop_index_var
        ):
            self.has_enumerate_pop_pattern = True
        self.generic_visit(node)


def test_remove_does_not_use_enumerate_pop_pattern() -> None:
    """remove() should NOT use the O(n^2) enumerate+pop(i) pattern.

    The enumerate+pop(i) pattern has O(n^2) complexity because pop(i)
    shifts all elements after index i, making it inefficient.

    Instead, remove() should use list comprehension or filter which is O(n).
    """
    source = inspect.getsource(TodoApp.remove)
    # Dedent the source since inspect.getsource returns indented method
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    detector = EnumeratePopDetector()
    detector.visit(tree)
    assert not detector.has_enumerate_pop_pattern, (
        "remove() should not use enumerate+pop(i) pattern. "
        "Use list comprehension or filter instead for O(n) complexity."
    )


def test_remove_uses_single_pass_filtering(tmp_path) -> None:
    """remove() should use single-pass filtering (list comprehension).

    Verify the remove method works correctly after the performance fix.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    todo3 = app.add("third todo")

    # Remove the middle one
    app.remove(todo2.id)

    # Verify only the correct one was removed
    remaining = app.list()
    assert len(remaining) == 2
    remaining_ids = {t.id for t in remaining}
    assert todo1.id in remaining_ids
    assert todo3.id in remaining_ids
    assert todo2.id not in remaining_ids


def test_remove_performance_with_large_list(tmp_path) -> None:
    """Benchmark remove() with a large todo list to verify no regression.

    The list comprehension approach should handle large lists efficiently.
    """
    import time

    db = tmp_path / "perf.json"
    app = TodoApp(db_path=str(db))

    # Add 1000 todos
    for i in range(1000):
        app.add(f"todo {i}")

    # Remove a todo from the middle
    start = time.perf_counter()
    app.remove(500)
    elapsed = time.perf_counter() - start

    # Should complete quickly (< 1 second even on slow machines)
    assert elapsed < 1.0, f"remove() took too long: {elapsed:.3f}s"

    # Verify correct removal
    remaining = app.list()
    assert len(remaining) == 999
    assert all(t.id != 500 for t in remaining)
