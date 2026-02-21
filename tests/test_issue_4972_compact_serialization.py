"""Tests for compact serialization optimization (issue #4972).

This test suite verifies that large todo lists use compact serialization
to reduce file size, while small lists maintain human-readable formatting.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestCompactSerialization:
    """Tests for issue #4972: compact serialization for large todo lists."""

    def test_small_list_uses_pretty_format(self, tmp_path) -> None:
        """Small lists (<100 items) should use indent=2 for readability."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 50 todos (below threshold)
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 51)]
        storage.save(todos)

        # Verify the file uses indented format (contains newlines)
        content = db.read_text(encoding="utf-8")
        assert "\n" in content, "Small lists should use indented (pretty) format"
        assert "  " in content, "Small lists should use indent=2"

    def test_large_list_uses_compact_format(self, tmp_path) -> None:
        """Large lists (>=100 items) should use compact format to reduce file size."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 150 todos (above threshold)
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 151)]
        storage.save(todos)

        # Verify the file uses compact format (no indentation)
        content = db.read_text(encoding="utf-8")
        # Compact format should not have the double-space indentation
        assert "  " not in content, "Large lists should use compact format (no indentation)"

    def test_compact_format_reduces_file_size(self, tmp_path) -> None:
        """Verify compact format significantly reduces file size for large lists."""
        db_compact = tmp_path / "compact.json"
        db_pretty = tmp_path / "pretty.json"

        # Create identical large todo list
        todos = [Todo(id=i, text=f"task number {i} with some extra text") for i in range(1, 201)]

        # Save with compact format (via TodoStorage)
        storage = TodoStorage(str(db_compact))
        storage.save(todos)
        compact_size = db_compact.stat().st_size

        # Manually create pretty version for comparison
        payload = [todo.to_dict() for todo in todos]
        db_pretty.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        pretty_size = db_pretty.stat().st_size

        # Compact should be significantly smaller (at least 10% reduction)
        reduction_ratio = (pretty_size - compact_size) / pretty_size
        assert reduction_ratio >= 0.10, (
            f"Compact format should save at least 10% file size, "
            f"got {reduction_ratio*100:.1f}% ({compact_size} vs {pretty_size} bytes)"
        )

    def test_compact_format_loads_correctly(self, tmp_path) -> None:
        """Verify compact format can be loaded and parsed correctly."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create and save large list
        original_todos = [
            Todo(id=i, text=f"task {i}", done=(i % 2 == 0))
            for i in range(1, 151)
        ]
        storage.save(original_todos)

        # Load and verify
        loaded = storage.load()
        assert len(loaded) == 150
        for i, todo in enumerate(loaded, start=1):
            assert todo.id == i
            assert todo.text == f"task {i}"
            assert todo.done == (i % 2 == 0)

    def test_boundary_99_items_uses_pretty(self, tmp_path) -> None:
        """Exactly 99 items should still use pretty format (below threshold)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i, text="x") for i in range(1, 100)]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        assert "  " in content, "99 items should use pretty format"

    def test_boundary_100_items_uses_compact(self, tmp_path) -> None:
        """Exactly 100 items should use compact format (at threshold)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i, text="x") for i in range(1, 101)]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        assert "  " not in content, "100 items should use compact format"
