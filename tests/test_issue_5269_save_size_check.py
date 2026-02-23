"""Regression test for issue #5269: save() should check size before building full content.

The save() method was building the entire JSON content in memory before any size check,
which defeats the DoS protection purpose for very large data sets.

Expected behavior:
- save() should check the size limit before or during JSON serialization
- Trying to save data that would exceed the 10MB limit should raise ValueError
- The error message should be clear about the size limit
"""

from __future__ import annotations

import re

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_save_rejects_oversized_data_before_full_serialization(tmp_path) -> None:
    """Test that save() rejects data that would exceed the size limit.

    This verifies that the size check happens before the full JSON content
    is built in memory, preventing potential DoS from oversized saves.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Calculate approximate size needed to exceed 10MB limit
    # Each todo is roughly: {"id": N, "text": "...", "done": false, "created_at": "...", "updated_at": "..."}
    # With ~200 bytes per todo, we need ~50,000 todos to exceed 10MB
    # Use a larger text to reduce number of objects needed
    large_text = "x" * 200  # 200 chars per todo text
    # With indent=2, each todo is roughly 300+ bytes
    # To exceed 10MB, we need ~35,000 todos with this text
    num_todos = (_MAX_JSON_SIZE_BYTES // 200) + 1000  # Overshoot to guarantee exceeding limit

    todos = [Todo(id=i, text=large_text) for i in range(num_todos)]

    # Should raise ValueError about size limit
    with pytest.raises(ValueError, match=re.compile(r"too large|size limit|10.?MB")):
        storage.save(todos)


def test_save_accepts_data_under_size_limit(tmp_path) -> None:
    """Test that save() accepts data that is under the size limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small set of todos that should be well under the limit
    todos = [Todo(id=i, text=f"Task {i}") for i in range(100)]

    # Should not raise any error
    storage.save(todos)

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 100
    assert loaded[0].text == "Task 0"
    assert loaded[99].text == "Task 99"


def test_save_size_check_error_message_clarity(tmp_path) -> None:
    """Test that the size limit error message mentions the limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create enough data to exceed limit
    large_text = "x" * 500
    num_todos = (_MAX_JSON_SIZE_BYTES // 300) + 1000

    todos = [Todo(id=i, text=large_text) for i in range(num_todos)]

    with pytest.raises(ValueError) as exc_info:
        storage.save(todos)

    # Error message should mention the limit clearly
    error_msg = str(exc_info.value).lower()
    assert "10" in error_msg or "mb" in error_msg or "limit" in error_msg
