"""Tests for efficient ID generation in Storage.add() method.

This test ensures that ID generation doesn't use O(N) operations like max()
on every insert, which degrades performance as the todo list grows.
"""

import time
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_add_performance_efficient_id_generation():
    """Test that adding many todos doesn't degrade due to inefficient ID generation.

    The current implementation uses max() which is O(N), making adding N todos
    O(N²) overall. This test verifies that adding 1000 todos completes in
    reasonable time (should be much faster with O(1) ID generation).
    """
    # Create a temporary storage
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Time how long it takes to add 1000 todos
        start_time = time.time()
        num_todos = 1000

        for i in range(num_todos):
            todo = Todo(title=f"Todo {i}")
            storage.add(todo)

        elapsed = time.time() - start_time

        # With O(N) ID generation, this would take several seconds
        # With O(1) counter, this should be < 0.5 seconds
        # We use 2 seconds as a generous threshold
        assert elapsed < 2.0, f"Adding {num_todos} todos took {elapsed:.3f}s, suggesting inefficient ID generation"

        # Verify all todos were added with correct IDs
        todos = storage.list()
        assert len(todos) == num_todos

        # Verify IDs are sequential starting from 1
        ids = [t.id for t in todos]
        assert ids == list(range(1, num_todos + 1))


def test_add_with_counter_persistence():
    """Test that the ID counter persists across storage instances.

    This ensures that when storage is reloaded, it continues from the
    correct next ID rather than recalculating with max().
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create first storage and add todos
        storage1 = Storage(str(storage_path))
        storage1.add(Todo(title="First"))
        storage1.add(Todo(title="Second"))
        storage1.add(Todo(title="Third"))

        # Create new storage instance (simulates restart)
        storage2 = Storage(str(storage_path))

        # Add more todos - should get IDs 4, 5, 6
        todo4 = storage2.add(Todo(title="Fourth"))
        todo5 = storage2.add(Todo(title="Fifth"))

        assert todo4.id == 4, f"Expected ID 4, got {todo4.id}"
        assert todo5.id == 5, f"Expected ID 5, got {todo5.id}"

        # Verify all todos
        todos = storage2.list()
        assert len(todos) == 5
        assert [t.id for t in todos] == [1, 2, 3, 4, 5]
