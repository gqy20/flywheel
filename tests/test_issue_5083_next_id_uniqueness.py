"""Regression tests for issue #5083: next_id may generate duplicate IDs (non-atomic).

This test suite verifies that:
1. The concurrency limitation is clearly documented in next_id's docstring
2. Sequential ID generation works correctly for single-process scenarios
3. The race condition behavior is understood and documented
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdConcurrencyDocumentation:
    """Tests verifying that issue #5083 is addressed via documentation."""

    def test_next_id_has_concurrency_warning_in_docstring(self):
        """Verify next_id documents its concurrency limitations."""
        docstring = TodoStorage.next_id.__doc__
        assert docstring is not None, "next_id should have a docstring"
        docstring_lower = docstring.lower()

        # Check for key documentation elements
        assert "concurrency" in docstring_lower or "concurrent" in docstring_lower, (
            "next_id docstring should mention concurrency"
        )
        assert "warning" in docstring_lower or "not atomic" in docstring_lower, (
            "next_id docstring should contain a warning about atomicity"
        )

    def test_next_id_references_issue_5083(self):
        """Verify next_id docstring references issue #5083 for traceability."""
        docstring = TodoStorage.next_id.__doc__
        assert docstring is not None, "next_id should have a docstring"
        assert "5083" in docstring, (
            "next_id docstring should reference issue #5083 for context"
        )


class TestNextIdSequentialBehavior:
    """Tests verifying sequential ID generation works correctly."""

    def test_next_id_empty_list(self):
        """Test that next_id returns 1 for empty list."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_single_item(self):
        """Test that next_id returns max + 1 for list with one item."""
        storage = TodoStorage()
        todos = [Todo(id=5, text="test")]
        assert storage.next_id(todos) == 6

    def test_next_id_multiple_items(self):
        """Test that next_id returns max + 1 for list with multiple items."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=3, text="c")]
        assert storage.next_id(todos) == 6

    def test_next_id_with_gap(self):
        """Test that next_id handles gaps in ID sequence correctly."""
        storage = TodoStorage()
        todos = [Todo(id=100, text="a"), Todo(id=200, text="b")]
        assert storage.next_id(todos) == 201


class TestNextIdRaceConditionDemonstration:
    """Tests demonstrating the race condition (documented limitation).

    These tests show that the race condition exists but is now documented.
    They serve as regression tests to ensure the behavior doesn't change
    unexpectedly.
    """

    def test_race_condition_exists_between_next_id_and_save(self, tmp_path: Path):
        """Demonstrate the race condition that issue #5083 documents.

        This test shows that next_id is calculated from in-memory state,
        which can differ from the final saved state in concurrent scenarios.
        The fix is documentation, not code changes.
        """
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Initial state
        initial_todos = [Todo(id=1, text="initial")]
        storage.save(initial_todos)

        # Load and calculate next_id (this is where race condition starts)
        loaded1 = storage.load()
        next_id_1 = storage.next_id(loaded1)

        # Simulate another process modifying the file
        loaded2 = storage.load()
        loaded2.append(Todo(id=2, text="concurrent"))
        storage.save(loaded2)

        # The calculated next_id is now stale
        # (In a real race condition, both processes would use ID 2)
        assert next_id_1 == 2, "next_id was calculated from stale state"

        # Reload and verify current state
        final_loaded = storage.load()
        current_next_id = storage.next_id(final_loaded)
        assert current_next_id == 3, "After concurrent write, next_id should be 3"

        # This demonstrates the race condition:
        # next_id_1 (2) != current_next_id (3)
        # If two processes both got ID 2 and saved, one would overwrite the other
