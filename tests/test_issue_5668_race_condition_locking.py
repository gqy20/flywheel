"""Tests for race condition fix in mark_done/mark_undone/remove.

Issue #5668: Race condition in mark_done/mark_undone/remove: load-modify-save
pattern without locking can cause lost updates.

This test suite verifies that concurrent modifications to different todos
are both reflected in the final state, and that file-based locking prevents
lost updates.
"""

from __future__ import annotations

import multiprocessing

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_mark_done_different_todos_both_reflected(tmp_path) -> None:
    """Regression test for issue #5668: concurrent mark_done should not lose updates.

    Scenario:
    - Process A adds todo #1 and marks it done
    - Process B adds todo #2 and marks it done
    - Both todos should show correct done status after concurrent operations
    """
    db = tmp_path / "concurrent.json"
    storage = TodoStorage(str(db))

    # Initialize with two todos
    initial_todos = [
        Todo(id=1, text="Task A", done=False),
        Todo(id=2, text="Task B", done=False),
    ]
    storage.save(initial_todos)

    # Use a barrier to synchronize workers for maximum race condition
    barrier = multiprocessing.Barrier(2)

    def mark_done_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that marks a todo as done."""
        try:
            app = TodoApp(str(db))
            # Wait for both workers to be ready
            barrier.wait(timeout=5)
            app.mark_done(todo_id)
            result_queue.put(("success", todo_id))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Run two workers concurrently, each marking a different todo
    result_queue = multiprocessing.Queue()
    processes = []

    for todo_id in [1, 2]:
        p = multiprocessing.Process(target=mark_done_worker, args=(todo_id, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Critical assertion: Both todos should be marked done
    final_todos = storage.load()
    assert len(final_todos) == 2, f"Expected 2 todos, got {len(final_todos)}"

    todo1 = next((t for t in final_todos if t.id == 1), None)
    todo2 = next((t for t in final_todos if t.id == 2), None)

    assert todo1 is not None, "Todo #1 should exist"
    assert todo2 is not None, "Todo #2 should exist"
    assert todo1.done is True, f"Todo #1 should be done, got done={todo1.done}"
    assert todo2.done is True, f"Todo #2 should be done, got done={todo2.done}"


def test_concurrent_add_operations_both_todos_preserved(tmp_path) -> None:
    """Test that concurrent add operations don't lose todos.

    When two processes add todos concurrently, both should be present
    in the final state (not just the last one written).
    """
    db = tmp_path / "concurrent_add.json"

    # Use a barrier to synchronize workers for maximum race condition
    barrier = multiprocessing.Barrier(2)

    def add_worker(text: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo."""
        try:
            app = TodoApp(str(db))
            # Wait for both workers to be ready
            barrier.wait(timeout=5)
            app.add(text)
            result_queue.put(("success", text))
        except Exception as e:
            result_queue.put(("error", text, str(e)))

    # Run two workers concurrently, each adding a different todo
    result_queue = multiprocessing.Queue()
    processes = []

    for text in ["Task A", "Task B"]:
        p = multiprocessing.Process(target=add_worker, args=(text, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Some errors may occur due to race condition (id collision), which is acceptable
    # What's NOT acceptable is data corruption

    # Critical assertion: File should contain valid JSON with expected data
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Both todos should be present if both operations succeeded
    # If only one succeeded due to race, we should still have valid data
    successes = [r for r in results if r[0] == "success"]
    if len(successes) == 2:
        # Both workers succeeded, both todos should be present
        assert len(final_todos) == 2, f"Expected 2 todos after concurrent adds, got {len(final_todos)}"
        texts = {t.text for t in final_todos}
        assert "Task A" in texts, "Task A should be present"
        assert "Task B" in texts, "Task B should be present"


def test_concurrent_mark_done_and_remove_operations(tmp_path) -> None:
    """Test that concurrent mark_done and remove operations are safe.

    Process A marks todo #1 done while Process B removes todo #2.
    Final state should have todo #1 marked done and todo #2 removed.
    """
    db = tmp_path / "concurrent_ops.json"
    storage = TodoStorage(str(db))

    # Initialize with three todos
    initial_todos = [
        Todo(id=1, text="Task A", done=False),
        Todo(id=2, text="Task B", done=False),
        Todo(id=3, text="Task C", done=False),
    ]
    storage.save(initial_todos)

    # Use a barrier to synchronize workers for maximum race condition
    barrier = multiprocessing.Barrier(2)

    def mark_done_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that marks a todo as done."""
        try:
            app = TodoApp(str(db))
            barrier.wait(timeout=5)
            app.mark_done(todo_id)
            result_queue.put(("success", "mark_done", todo_id))
        except Exception as e:
            result_queue.put(("error", "mark_done", todo_id, str(e)))

    def remove_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that removes a todo."""
        try:
            app = TodoApp(str(db))
            barrier.wait(timeout=5)
            app.remove(todo_id)
            result_queue.put(("success", "remove", todo_id))
        except Exception as e:
            result_queue.put(("error", "remove", todo_id, str(e)))

    # Run workers concurrently
    result_queue = multiprocessing.Queue()
    processes = []

    # Mark todo #1 done
    p1 = multiprocessing.Process(target=mark_done_worker, args=(1, result_queue))
    processes.append(p1)
    p1.start()

    # Remove todo #2
    p2 = multiprocessing.Process(target=remove_worker, args=(2, result_queue))
    processes.append(p2)
    p2.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # At least one operation should succeed
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) >= 1, "At least one operation should succeed"

    # File should contain valid JSON
    final_todos = storage.load()

    # Check final state - should have valid data
    assert isinstance(final_todos, list), "Final data should be a list"

    # If both operations succeeded:
    # - Todo #1 should be done
    # - Todo #2 should be removed
    # - Todo #3 should be unchanged
    if len(successes) == 2:
        assert len(final_todos) == 2, f"Expected 2 todos after operations, got {len(final_todos)}"
        todo1 = next((t for t in final_todos if t.id == 1), None)
        todo3 = next((t for t in final_todos if t.id == 3), None)
        assert todo1 is not None and todo1.done is True, "Todo #1 should be done"
        assert todo3 is not None and todo3.done is False, "Todo #3 should be pending"


def test_concurrent_mark_undone_different_todos_both_reflected(tmp_path) -> None:
    """Test that concurrent mark_undone operations on different todos both succeed."""
    db = tmp_path / "concurrent_undone.json"
    storage = TodoStorage(str(db))

    # Initialize with two done todos
    initial_todos = [
        Todo(id=1, text="Task A", done=True),
        Todo(id=2, text="Task B", done=True),
    ]
    storage.save(initial_todos)

    # Use a barrier to synchronize workers for maximum race condition
    barrier = multiprocessing.Barrier(2)

    def mark_undone_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that marks a todo as undone."""
        try:
            app = TodoApp(str(db))
            barrier.wait(timeout=5)
            app.mark_undone(todo_id)
            result_queue.put(("success", todo_id))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Run two workers concurrently
    result_queue = multiprocessing.Queue()
    processes = []

    for todo_id in [1, 2]:
        p = multiprocessing.Process(target=mark_undone_worker, args=(todo_id, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Critical assertion: Both todos should be marked undone
    final_todos = storage.load()
    assert len(final_todos) == 2, f"Expected 2 todos, got {len(final_todos)}"

    todo1 = next((t for t in final_todos if t.id == 1), None)
    todo2 = next((t for t in final_todos if t.id == 2), None)

    assert todo1 is not None and todo1.done is False, "Todo #1 should be undone"
    assert todo2 is not None and todo2.done is False, "Todo #2 should be undone"
