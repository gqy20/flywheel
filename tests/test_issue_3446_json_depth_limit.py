"""Tests for JSON depth limit to prevent stack overflow (Issue #3446).

Security: These tests verify that deeply nested JSON structures are rejected
to prevent stack overflow attacks, even if the file size is within limits.

A small file (< 10MB) with deeply nested JSON can cause excessive memory
consumption or stack overflow during JSON parsing if not limited.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def create_deeply_nested_json(depth: int) -> str:
    """Create a deeply nested JSON structure.

    Example for depth=3: {"a": {"a": {"a": 1}}}
    """
    inner = "1"
    for _ in range(depth):
        inner = f'{{"a": {inner}}}'
    return inner


def test_storage_load_rejects_deeply_nested_json(tmp_path) -> None:
    """Security: Deeply nested JSON should be rejected to prevent stack overflow.

    Issue #3446: A small file with deeply nested JSON can exhaust stack memory.
    """
    db = tmp_path / "deep.json"
    storage = TodoStorage(str(db))

    # Create a deeply nested JSON (> 1000 levels)
    # This is still small in bytes but causes deep recursion during parsing
    # Wrap in a list to pass the TodoStorage list check
    deep_json = f'[{create_deeply_nested_json(1500)}]'

    # Write the deeply nested JSON
    db.write_text(deep_json, encoding="utf-8")

    # Verify file size is small (< 10MB limit)
    assert db.stat().st_size < 10 * 1024 * 1024

    # Should raise ValueError for deeply nested JSON
    with pytest.raises(ValueError, match=r"nested|depth|recursion"):
        storage.load()


def test_storage_load_accepts_normal_nesting_depth(tmp_path) -> None:
    """Verify that normal JSON nesting levels are still accepted."""
    db = tmp_path / "normal_nested.json"
    storage = TodoStorage(str(db))

    # Create a normal JSON with reasonable nesting (e.g., 20 levels)
    # This simulates typical business data structures
    normal_nesting = create_deeply_nested_json(20)

    # Wrap it in a list to match TodoStorage expected format
    db.write_text(f'[{normal_nesting}]', encoding="utf-8")

    # Verify file size is small
    assert db.stat().st_size < 10 * 1024 * 1024

    # This should NOT raise an error - it should fail on validation
    # because the structure doesn't match Todo schema, not because of depth
    with pytest.raises(ValueError, match=r"missing.*'id'|missing.*'text'|required"):
        storage.load()


def test_storage_load_accepts_valid_todos_with_normal_nesting(tmp_path) -> None:
    """Verify valid todos with some nested structure work correctly."""
    db = tmp_path / "valid_nested.json"
    storage = TodoStorage(str(db))

    # Create valid todos with some reasonable nesting in metadata
    todos_data = [
        {
            "id": 1,
            "text": "Task with nested metadata",
            "done": False,
            "metadata": {
                "level1": {
                    "level2": {
                        "level3": {
                            "value": "nested value"
                        }
                    }
                }
            },
        }
    ]

    db.write_text(json.dumps(todos_data), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "Task with nested metadata"
