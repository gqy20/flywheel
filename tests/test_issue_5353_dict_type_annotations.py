"""Tests for to_dict() and from_dict() type annotations (Issue #5353).

These tests verify that:
1. to_dict() returns a properly typed dict
2. from_dict() accepts properly typed dict
3. Roundtrip to_dict -> from_dict works correctly
4. mypy --strict passes on the module
"""

from __future__ import annotations

import subprocess
import sys

from flywheel.todo import Todo


def test_to_dict_returns_dict_with_correct_structure() -> None:
    """to_dict() should return dict with all Todo fields."""
    todo = Todo(id=1, text="test task", done=True)
    result = todo.to_dict()

    assert isinstance(result, dict)
    assert result["id"] == 1
    assert result["text"] == "test task"
    assert result["done"] is True
    assert "created_at" in result
    assert "updated_at" in result


def test_from_dict_accepts_dict_with_correct_types() -> None:
    """from_dict() should accept dict with int, str, bool values."""
    data: dict[str, int | str | bool] = {
        "id": 42,
        "text": "sample task",
        "done": False,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    todo = Todo.from_dict(data)

    assert todo.id == 42
    assert todo.text == "sample task"
    assert todo.done is False


def test_roundtrip_to_dict_from_dict() -> None:
    """to_dict() -> from_dict() roundtrip should preserve data."""
    original = Todo(id=99, text="roundtrip test", done=True)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done


def test_mypy_strict_passes_on_todo_module() -> None:
    """mypy --strict should pass on todo.py with proper type annotations."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "src/flywheel/todo.py"],
        capture_output=True,
        text=True,
    )

    # mypy should exit with 0 (no errors)
    assert result.returncode == 0, (
        f"mypy --strict failed with return code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
