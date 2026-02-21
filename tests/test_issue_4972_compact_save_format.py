"""Regression test for issue #4972: save method compact format for large todo lists.

This test verifies that:
1. Small lists (<100 items) use readable indented format (indent=2)
2. Large lists (>=100 items) use compact format (indent=None) to reduce file size
3. Compact format is still parseable by load()
4. Backward compatibility is maintained
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestCompactSaveFormat:
    """Tests for compact save format optimization (issue #4972)."""

    def test_small_list_uses_indented_format(self, tmp_path: Path) -> None:
        """Small lists (<100 items) should use readable indented format."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 99 todos (below threshold)
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 100)]
        storage.save(todos)

        # Read raw content
        raw_content = db.read_text(encoding="utf-8")

        # Should have newlines and indentation (indented format)
        assert "\n" in raw_content, "Small list should use indented format"
        assert "  " in raw_content, "Small list should have indentation"

    def test_large_list_uses_compact_format(self, tmp_path: Path) -> None:
        """Large lists (>=100 items) should use compact format to reduce file size."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 100 todos (at or above threshold)
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 101)]
        storage.save(todos)

        # Read raw content
        raw_content = db.read_text(encoding="utf-8")

        # Should NOT have pretty formatting (compact format)
        # Compact format is a single line or very few lines
        lines = raw_content.strip().split("\n")
        assert len(lines) < 5, (
            f"Large list should use compact format (got {len(lines)} lines)"
        )

    def test_compact_format_reduces_file_size(self, tmp_path: Path) -> None:
        """Compact format should significantly reduce file size for large lists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 100 todos
        todos = [Todo(id=i, text=f"task number {i}") for i in range(1, 101)]

        # Save with TodoStorage (should use compact)
        storage.save(todos)

        # Get compact size
        compact_size = db.stat().st_size

        # Calculate what indented size would be
        payload = [todo.to_dict() for todo in todos]
        indented_content = json.dumps(payload, ensure_ascii=False, indent=2)
        indented_size = len(indented_content.encode("utf-8"))

        # Compact should be smaller (at least 10% reduction expected)
        reduction_ratio = (indented_size - compact_size) / indented_size
        assert reduction_ratio >= 0.10, (
            f"Compact format should reduce file size by at least 10%, "
            f"got {reduction_ratio:.1%} reduction "
            f"(indented: {indented_size}, compact: {compact_size})"
        )

    def test_compact_format_is_parseable(self, tmp_path: Path) -> None:
        """Compact format should be correctly parsed by load()."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create and save 100 todos
        original_todos = [Todo(id=i, text=f"task {i}", done=i % 2 == 0) for i in range(1, 101)]
        storage.save(original_todos)

        # Load should work correctly
        loaded_todos = storage.load()

        # Verify all data is intact
        assert len(loaded_todos) == 100
        for i, todo in enumerate(loaded_todos, start=1):
            assert todo.id == i
            assert todo.text == f"task {i}"
            assert todo.done == (i % 2 == 0)

    def test_boundary_exactly_100_items_uses_compact(self, tmp_path: Path) -> None:
        """Exactly 100 items should trigger compact format."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create exactly 100 todos
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 101)]
        storage.save(todos)

        raw_content = db.read_text(encoding="utf-8")
        lines = raw_content.strip().split("\n")

        # Should use compact format at exactly 100 items
        assert len(lines) < 5, (
            f"Exactly 100 items should use compact format (got {len(lines)} lines)"
        )

    def test_boundary_99_items_uses_indented(self, tmp_path: Path) -> None:
        """99 items should still use indented format."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 99 todos
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 100)]
        storage.save(todos)

        raw_content = db.read_text(encoding="utf-8")

        # Should use indented format
        assert "\n" in raw_content, "99 items should use indented format"
        assert "  " in raw_content, "99 items should have indentation"

    def test_backward_compatibility_load_indented_format(self, tmp_path: Path) -> None:
        """Previously saved indented files should still load correctly."""
        db = tmp_path / "todo.json"

        # Write a file in the old indented format directly
        old_data = [
            {"id": 1, "text": "old task 1", "done": False},
            {"id": 2, "text": "old task 2", "done": True},
        ]
        indented_content = json.dumps(old_data, ensure_ascii=False, indent=2)
        db.write_text(indented_content, encoding="utf-8")

        # Should load correctly
        storage = TodoStorage(str(db))
        loaded = storage.load()

        assert len(loaded) == 2
        assert loaded[0].text == "old task 1"
        assert loaded[1].done is True
