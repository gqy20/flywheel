"""Tests for Todo negative ID validation (Issue #4382).

These tests verify that:
1. Todo constructor rejects negative IDs with ValueError
2. Todo.from_dict rejects negative IDs with ValueError
3. Todo accepts ID of 0 (edge case)
4. Existing tests with positive IDs continue to pass
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoNegativeIdValidation:
    """Tests for negative ID rejection in Todo constructor."""

    def test_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-1, text="test")
        assert "non-negative" in str(exc_info.value)

    def test_constructor_rejects_large_negative_id(self) -> None:
        """Todo with large negative ID should also raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-999, text="test")
        assert "non-negative" in str(exc_info.value)

    def test_constructor_accepts_zero_id(self) -> None:
        """Todo(id=0, text='test') should be accepted (edge case)."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0

    def test_constructor_accepts_positive_id(self) -> None:
        """Todo with positive ID should work normally."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1


class TestTodoFromDictNegativeIdValidation:
    """Tests for negative ID rejection in Todo.from_dict."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -1, "text": "test"})
        assert "non-negative" in str(exc_info.value)

    def test_from_dict_rejects_large_negative_id(self) -> None:
        """from_dict with large negative ID should also raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -999, "text": "test"})
        assert "non-negative" in str(exc_info.value)

    def test_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict with id=0 should be accepted (edge case)."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive ID should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1

    def test_from_dict_accepts_zero_id_string(self) -> None:
        """Todo.from_dict with id='0' (string) should be accepted."""
        todo = Todo.from_dict({"id": "0", "text": "test"})
        assert todo.id == 0

    def test_from_dict_rejects_negative_id_string(self) -> None:
        """Todo.from_dict with id='-1' (string) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": "-1", "text": "test"})
        assert "non-negative" in str(exc_info.value)
