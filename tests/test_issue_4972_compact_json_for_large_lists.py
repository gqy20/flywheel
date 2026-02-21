"""Regression test for issue #4972: Compact JSON for large todo lists.

This test verifies that the save method dynamically chooses JSON formatting
based on list size to reduce file size bloat for large datasets while
maintaining readability for small lists.

Acceptance criteria:
- Small lists (<100 items) keep readable format (indent=2)
- Large lists (>=100 items) use compact format (indent=None)
- Compact format still parses correctly with load()
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_small_list_uses_pretty_format(tmp_path: Path) -> None:
    """Small lists (<100 items) should use indent=2 for readability."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create exactly 99 items (below threshold)
    todos = [Todo(id=i, text=f"task {i}") for i in range(1, 100)]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Should contain newlines and indentation (pretty format)
    assert "\n" in content, "Small lists should use pretty format with newlines"
    assert "  " in content, "Small lists should use indent=2"

    # Verify content parses correctly
    loaded = storage.load()
    assert len(loaded) == 99


def test_large_list_uses_compact_format(tmp_path: Path) -> None:
    """Large lists (>=100 items) should use compact format (no indent)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create exactly 100 items (at threshold)
    todos = [Todo(id=i, text=f"task {i}") for i in range(1, 101)]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Should NOT contain pretty formatting - compact format
    # In compact format, array is on a single line (no indent-induced newlines)
    lines = content.strip().split("\n")
    # Compact JSON should have very few lines (just wrapping, not per-item)
    assert len(lines) < 10, (
        f"Large lists should use compact format, but got {len(lines)} lines"
    )

    # Verify content parses correctly
    loaded = storage.load()
    assert len(loaded) == 100


def test_compact_format_significantly_reduces_file_size(tmp_path: Path) -> None:
    """Verify that compact format reduces file size for large lists."""
    db_compact = tmp_path / "compact.json"
    db_pretty = tmp_path / "pretty.json"

    # Create 500 items - well above threshold
    todos = [Todo(id=i, text=f"This is a longer task description number {i}") for i in range(1, 501)]

    # Save with the actual storage (should use compact for 500 items)
    storage = TodoStorage(str(db_compact))
    storage.save(todos)

    # For comparison, create the same data with pretty format manually
    payload = [todo.to_dict() for todo in todos]
    pretty_content = json.dumps(payload, ensure_ascii=False, indent=2)
    db_pretty.write_text(pretty_content, encoding="utf-8")

    compact_size = db_compact.stat().st_size
    pretty_size = db_pretty.stat().st_size

    # Compact should be at least 10% smaller than pretty
    size_reduction = (pretty_size - compact_size) / pretty_size
    assert size_reduction >= 0.1, (
        f"Expected at least 10% size reduction, got {size_reduction:.1%} "
        f"(compact: {compact_size} bytes, pretty: {pretty_size} bytes)"
    )


def test_compact_format_loads_correctly(tmp_path: Path) -> None:
    """Verify that compact-formatted JSON can be loaded correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create 100 items and save
    original_todos = [
        Todo(id=i, text=f"Task {i} with some content", done=(i % 2 == 0))
        for i in range(1, 101)
    ]
    storage.save(original_todos)

    # Load back and verify all data is preserved
    loaded_todos = storage.load()
    assert len(loaded_todos) == len(original_todos)

    for original, loaded in zip(original_todos, loaded_todos, strict=True):
        assert loaded.id == original.id
        assert loaded.text == original.text
        assert loaded.done == original.done
