"""Regression tests for issue #5816: next_id should return positive IDs.

The bug: next_id returns negative values when only negative IDs exist in storage.
The fix: next_id should filter for positive IDs only.
"""

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdWithNegativeIds:
    """Test that next_id handles negative IDs correctly."""

    def test_next_id_empty_list_returns_1(self, tmp_path):
        """next_id([]) should return 1."""
        storage = TodoStorage(str(tmp_path / "test.json"))
        assert storage.next_id([]) == 1

    def test_next_id_only_negative_ids_returns_1(self, tmp_path):
        """next_id([Todo(id=-5), Todo(id=-10)]) should return 1, not -4."""
        storage = TodoStorage(str(tmp_path / "test.json"))
        todos = [Todo(id=-5, text="negative"), Todo(id=-10, text="negative")]
        assert storage.next_id(todos) == 1

    def test_next_id_mixed_positive_negative_returns_max_plus_1(self, tmp_path):
        """next_id([Todo(id=5), Todo(id=-10)]) should return 6."""
        storage = TodoStorage(str(tmp_path / "test.json"))
        todos = [Todo(id=5, text="positive"), Todo(id=-10, text="negative")]
        assert storage.next_id(todos) == 6

    def test_next_id_with_zero_id_returns_correct(self, tmp_path):
        """next_id([Todo(id=0), Todo(id=1)]) should return 2."""
        storage = TodoStorage(str(tmp_path / "test.json"))
        todos = [Todo(id=0, text="zero"), Todo(id=1, text="one")]
        # Zero is not positive, so max positive is 1, thus next_id = 2
        assert storage.next_id(todos) == 2
