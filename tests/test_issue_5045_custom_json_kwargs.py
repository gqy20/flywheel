"""Tests for custom JSON serialization parameters in TodoStorage.

This test suite verifies the feature from issue #5045:
- TodoStorage accepts optional json_dumps_kwargs parameter
- Default behavior is preserved (indent=2, ensure_ascii=False)
- Users can override these parameters (e.g., indent=None for compact JSON)
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_json_dumps_behavior_unchanged(tmp_path: Path) -> None:
    """Test that default behavior remains indent=2, ensure_ascii=False."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test with unicode: 你好")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Default should use indent=2 (multi-line with 2-space indentation)
    assert "\n" in content, "Default should have newlines (indent=2)"
    assert "  " in content, "Default should have 2-space indentation"

    # Default should preserve unicode (ensure_ascii=False)
    assert "你好" in content, "Default should preserve unicode characters"

    # Verify it's valid JSON
    parsed = json.loads(content)
    assert len(parsed) == 1
    assert parsed[0]["text"] == "test with unicode: 你好"


def test_custom_indent_none_produces_compact_json(tmp_path: Path) -> None:
    """Test that indent=None produces compact single-line JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

    todos = [Todo(id=1, text="compact"), Todo(id=2, text="output")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # With indent=None, JSON should be on a single line (compact)
    assert "\n" not in content.strip(), "indent=None should produce single-line JSON"

    # Verify it's still valid JSON
    parsed = json.loads(content)
    assert len(parsed) == 2


def test_custom_json_dumps_kwargs_with_ensure_ascii_true(tmp_path: Path) -> None:
    """Test that ensure_ascii=True escapes unicode characters."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"ensure_ascii": True})

    todos = [Todo(id=1, text="unicode: 你好")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # With ensure_ascii=True, unicode should be escaped
    assert "你好" not in content, "ensure_ascii=True should escape unicode"
    assert "\\u" in content, "ensure_ascii=True should produce unicode escape sequences"

    # Verify it's still valid JSON when parsed
    parsed = json.loads(content)
    assert parsed[0]["text"] == "unicode: 你好"


def test_custom_json_dumps_kwargs_with_custom_separator(tmp_path: Path) -> None:
    """Test that separators parameter works."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(
        str(db),
        json_dumps_kwargs={"separators": (",", ":")},
    )

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # separators=(",", ":") removes spaces after comma and colon
    # This produces very compact output
    assert ":1," in content or ":1}" in content, "Custom separators should produce compact output"


def test_custom_json_dumps_kwargs_combined_with_defaults(tmp_path: Path) -> None:
    """Test that custom kwargs can override defaults partially."""
    db = tmp_path / "todo.json"
    # Only override indent, ensure_ascii should still default to False
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": 4})

    todos = [Todo(id=1, text="unicode: 你好")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # indent=4 should produce 4-space indentation
    assert "    " in content, "indent=4 should produce 4-space indentation"

    # ensure_ascii should still be False (preserving unicode)
    assert "你好" in content, "ensure_ascii=False should be default"


def test_json_dumps_kwargs_persists_across_multiple_saves(tmp_path: Path) -> None:
    """Test that json_dumps_kwargs setting persists across multiple save operations."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

    # First save
    storage.save([Todo(id=1, text="first")])
    content1 = db.read_text(encoding="utf-8")
    assert "\n" not in content1.strip(), "First save should be compact"

    # Second save
    storage.save([Todo(id=1, text="second"), Todo(id=2, text="third")])
    content2 = db.read_text(encoding="utf-8")
    assert "\n" not in content2.strip(), "Second save should also be compact"
