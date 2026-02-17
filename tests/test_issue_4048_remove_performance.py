"""Regression tests for Issue #4048: TodoApp.remove() should use O(n) single-pass.

This test file ensures that remove() method uses single-pass filtering
(list comprehension or filter) instead of enumerate+pop(i) which has
O(n) overhead for each pop operation due to element shifting.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest

from flywheel.cli import TodoApp


def test_remove_uses_list_comprehension_not_enumerate_pop(tmp_path) -> None:
    """remove() should use list comprehension, not enumerate+pop(i).

    The implementation should use single-pass filtering (list comprehension
    or filter) instead of enumerate + pop(i) which adds O(n) overhead for
    each pop operation due to element shifting.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Verify the implementation uses list comprehension pattern
    source = inspect.getsource(app.remove)
    source = textwrap.dedent(source)
    tree = ast.parse(source)

    # Should NOT use enumerate pattern
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "enumerate"
        ):
            pytest.fail(
                "remove() uses enumerate() - should use list comprehension instead"
            )

    # Should NOT use pop() on the list
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "pop"
            and isinstance(node.value, ast.Name)
            and node.value.id == "todos"
        ):
            pytest.fail(
                "remove() uses todos.pop(i) - should use list comprehension instead"
            )


def test_remove_functionally_correct_single_removal(tmp_path) -> None:
    """remove() should correctly remove a single todo by ID.

    Functional test to ensure the new implementation works correctly.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    todo3 = app.add("third todo")

    # Remove the middle one
    app.remove(todo2.id)

    # Verify correct todos remain
    remaining = app.list()
    assert len(remaining) == 2
    assert remaining[0].id == todo1.id
    assert remaining[1].id == todo3.id


def test_remove_functionally_correct_from_middle(tmp_path) -> None:
    """remove() should correctly remove todo from middle of list.

    This specifically tests that the O(n) improvement works correctly
    when removing from the middle of the list.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add 5 todos
    todos = [app.add(f"todo {i}") for i in range(5)]

    # Remove the middle one (index 2)
    app.remove(todos[2].id)

    # Verify correct todos remain
    remaining = app.list()
    assert len(remaining) == 4
    remaining_ids = {t.id for t in remaining}
    assert todos[2].id not in remaining_ids
    assert todos[0].id in remaining_ids
    assert todos[1].id in remaining_ids
    assert todos[3].id in remaining_ids
    assert todos[4].id in remaining_ids


def test_remove_raises_valueerror_for_nonexistent_id(tmp_path) -> None:
    """remove() should raise ValueError for non-existent ID."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    app.add("test todo")

    with pytest.raises(ValueError, match=r"Todo #999 not found"):
        app.remove(999)


def test_remove_uses_single_pass_no_element_shifting(tmp_path) -> None:
    """Verify remove() implementation does not cause element shifting overhead.

    This test verifies that the implementation creates a new list via
    comprehension/filter rather than modifying in place with pop(i).
    """
    source = inspect.getsource(TodoApp.remove)
    source = textwrap.dedent(source)
    tree = ast.parse(source)

    # Should contain a list comprehension
    has_list_comp = any(isinstance(node, ast.ListComp) for node in ast.walk(tree))

    # Or should use filter() call
    has_filter = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "filter"
        ):
            has_filter = True
            break

    assert has_list_comp or has_filter, (
        "remove() should use list comprehension or filter() for single-pass removal"
    )
