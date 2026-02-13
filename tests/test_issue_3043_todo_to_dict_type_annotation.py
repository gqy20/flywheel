"""Regression test for issue #3043: to_dict return type annotation is imprecise.

This test verifies that the Todo class methods have precise type annotations
using generic type parameters (dict[str, Any] instead of bare dict).
"""

import subprocess
import sys

import pytest


def test_mypy_strict_passes_on_todo_py():
    """Test that mypy --strict passes on todo.py with precise type annotations.

    Issue #3043: The to_dict and from_dict methods should use dict[str, Any]
    instead of bare dict to satisfy mypy --strict.
    """
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "src/flywheel/todo.py"],
        capture_output=True,
        text=True,
    )

    # Check for the specific error about missing type parameters
    assert (
        'Missing type parameters for generic type "dict"' not in result.stdout
    ), f"mypy --strict failed with: {result.stdout}"

    # Also ensure mypy exit code is 0 (success)
    assert result.returncode == 0, (
        f"mypy --strict failed with exit code {result.returncode}:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_to_dict_returns_dict_with_any():
    """Test that to_dict returns a dict[str, Any] with correct values."""
    from flywheel.todo import Todo

    todo = Todo(id=1, text="Test todo")
    result = todo.to_dict()

    # Verify structure
    assert isinstance(result, dict)
    assert result["id"] == 1
    assert result["text"] == "Test todo"
    assert result["done"] is False
    assert "created_at" in result
    assert "updated_at" in result


def test_from_dict_accepts_dict_with_any():
    """Test that from_dict accepts dict[str, Any] and creates a Todo."""
    from flywheel.todo import Todo

    data = {
        "id": 2,
        "text": "Another todo",
        "done": True,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-02T00:00:00+00:00",
    }
    todo = Todo.from_dict(data)

    assert todo.id == 2
    assert todo.text == "Another todo"
    assert todo.done is True
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-02T00:00:00+00:00"
