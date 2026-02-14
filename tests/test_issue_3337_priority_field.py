"""Regression tests for Issue #3337: Todo priority field support.

This test file ensures that todos can have an optional priority field
(1-3 or None) that is properly serialized and supports sorting.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.todo import Todo


class TestPriorityField:
    """Tests for priority field on Todo."""

    def test_todo_priority_optional_field_default_none(self) -> None:
        """Todo should accept optional priority parameter, defaulting to None."""
        todo = Todo(id=1, text="Test task")
        assert hasattr(todo, "priority")
        assert todo.priority is None

    def test_todo_priority_can_be_set_1_to_3(self) -> None:
        """Todo should accept priority values 1, 2, or 3."""
        todo1 = Todo(id=1, text="High priority task", priority=1)
        todo2 = Todo(id=2, text="Medium priority task", priority=2)
        todo3 = Todo(id=3, text="Low priority task", priority=3)

        assert todo1.priority == 1
        assert todo2.priority == 2
        assert todo3.priority == 3

    def test_todo_priority_roundtrip_to_dict_from_dict(self) -> None:
        """priority should serialize/deserialize correctly via to_dict/from_dict."""
        todo = Todo(id=1, text="Test task", priority=2)
        data = todo.to_dict()
        assert data["priority"] == 2

        restored = Todo.from_dict(data)
        assert restored.priority == 2

    def test_todo_priority_none_roundtrip(self) -> None:
        """priority None should serialize/deserialize correctly."""
        todo = Todo(id=1, text="Test task", priority=None)
        data = todo.to_dict()
        assert data["priority"] is None

        restored = Todo.from_dict(data)
        assert restored.priority is None

    def test_from_dict_handles_missing_priority(self) -> None:
        """from_dict should handle data without priority field (backwards compat)."""
        data = {"id": 1, "text": "Legacy task"}
        todo = Todo.from_dict(data)
        assert todo.priority is None


class TestSetPriorityMethod:
    """Tests for set_priority method."""

    def test_set_priority_changes_value(self) -> None:
        """set_priority should change the priority value."""
        todo = Todo(id=1, text="Test task")
        assert todo.priority is None

        todo.set_priority(1)
        assert todo.priority == 1

        todo.set_priority(3)
        assert todo.priority == 3

    def test_set_priority_updates_timestamp(self) -> None:
        """set_priority should update the updated_at timestamp."""
        import time

        todo = Todo(id=1, text="Test task")
        original_updated_at = todo.updated_at
        time.sleep(0.01)  # Small delay to ensure timestamp difference

        todo.set_priority(2)
        assert todo.updated_at != original_updated_at

    def test_set_priority_validates_range(self) -> None:
        """set_priority should validate priority is in valid range (1-3 or None)."""
        todo = Todo(id=1, text="Test task")

        # Valid values
        todo.set_priority(None)
        assert todo.priority is None
        todo.set_priority(1)
        assert todo.priority == 1
        todo.set_priority(2)
        assert todo.priority == 2
        todo.set_priority(3)
        assert todo.priority == 3

        # Invalid values
        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(0)
        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(4)
        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(-1)


class TestCLIListSortByPriority:
    """Tests for CLI list --sort=priority option."""

    def test_list_sort_by_priority_option(self, tmp_path, monkeypatch) -> None:
        """CLI list should support --sort=priority to sort by priority."""
        db_path = tmp_path / ".todo.json"

        # Add todos with different priorities
        app = TodoApp(db_path=str(db_path))
        app.add("Low priority task")  # priority None
        app.add("High priority task")
        app.add("Medium priority task")

        # Set priorities
        todos = app._load()
        for todo in todos:
            if "High" in todo.text:
                todo.set_priority(1)
            elif "Medium" in todo.text:
                todo.set_priority(2)
            # Low priority task stays None
        app._save(todos)

        # Test --sort=priority parsing (db is a global option, must come before subcommand)
        parser = build_parser()
        args = parser.parse_args(["--db", str(db_path), "list", "--sort=priority"])
        assert args.sort == "priority"

    def test_list_sort_priority_orders_correctly(self, tmp_path, monkeypatch) -> None:
        """Todos with --sort=priority should be ordered by priority (1 first, None last)."""
        import io
        import sys

        db_path = tmp_path / ".todo.json"

        # Create app and add todos
        app = TodoApp(db_path=str(db_path))
        app.add("None priority")
        app.add("Priority 2")
        app.add("Priority 1")
        app.add("Priority 3")

        # Set priorities
        todos = app._load()
        for todo in todos:
            if "Priority 1" in todo.text:
                todo.set_priority(1)
            elif "Priority 2" in todo.text:
                todo.set_priority(2)
            elif "Priority 3" in todo.text:
                todo.set_priority(3)
        app._save(todos)

        # Capture output
        stdout_capture = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stdout_capture)

        args = parser.parse_args(["--db", str(db_path), "list", "--sort=priority"])
        run_command(args)

        output = stdout_capture.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # With --sort=priority, order should be: Priority 1, Priority 2, Priority 3, None
        # Priority 1 should appear before Priority 2, etc.
        p1_idx = next(i for i, line in enumerate(lines) if "Priority 1" in line)
        p2_idx = next(i for i, line in enumerate(lines) if "Priority 2" in line)
        p3_idx = next(i for i, line in enumerate(lines) if "Priority 3" in line)
        none_idx = next(i for i, line in enumerate(lines) if "None priority" in line)

        assert p1_idx < p2_idx < p3_idx < none_idx, (
            f"Priority sort failed: p1={p1_idx}, p2={p2_idx}, p3={p3_idx}, none={none_idx}"
        )


parser = build_parser()
