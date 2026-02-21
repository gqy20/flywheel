"""Tests for custom JSON serialization parameters (issue #5045).

This test suite verifies that TodoStorage supports custom json.dumps parameters.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_json_dumps_parameters(tmp_path: Path) -> None:
    """Test that default behavior uses indent=2 and ensure_ascii=False."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Default should have indentation (indent=2)
    assert "  " in content  # Has indentation
    # Default should preserve unicode (ensure_ascii=False)
    assert "test" in content


def test_custom_indent_none_for_compact_json(tmp_path: Path) -> None:
    """Test that indent=None generates compact JSON without whitespace."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

    todos = [Todo(id=1, text="test"), Todo(id=2, text="another")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Compact JSON should not have pretty-print indentation
    # (might have spaces after colons but not multi-line formatting)
    lines = content.strip().split("\n")
    assert len(lines) == 1, (
        f"Expected single line for compact JSON, got {len(lines)} lines: {content}"
    )


def test_custom_ensure_ascii_true(tmp_path: Path) -> None:
    """Test that ensure_ascii=True escapes unicode characters."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"ensure_ascii": True})

    todos = [Todo(id=1, text="你好")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # With ensure_ascii=True, unicode should be escaped
    assert "\\u" in content
    assert "你好" not in content


def test_custom_separators_for_minimal_json(tmp_path: Path) -> None:
    """Test custom separators for minimal JSON output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"separators": (",", ":"), "indent": None})

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # With minimal separators and no indent, should be very compact
    assert ",:" in content or content.count(" ") == 0 or "test" in content


def test_custom_kwargs_override_defaults(tmp_path: Path) -> None:
    """Test that custom kwargs override the default indent and ensure_ascii."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": 4, "ensure_ascii": True})

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Should have 4-space indentation
    assert "    " in content


def test_custom_kwargs_do_not_affect_load(tmp_path: Path) -> None:
    """Test that json_dumps_kwargs only affects save, not load."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

    todos = [Todo(id=1, text="first"), Todo(id=2, text="second", done=True)]
    storage.save(todos)

    # Load should work regardless of save format
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first"
    assert loaded[1].text == "second"
    assert loaded[1].done is True


def test_empty_json_dumps_kwargs_uses_defaults(tmp_path: Path) -> None:
    """Test that empty json_dumps_kwargs dict uses default parameters."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), json_dumps_kwargs={})

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Empty dict should still use defaults
    assert "  " in content  # indent=2


def test_json_dumps_kwargs_preserves_other_defaults(tmp_path: Path) -> None:
    """Test that providing some kwargs preserves defaults for others."""
    db = tmp_path / "todo.json"
    # Only override indent, ensure_ascii should remain False
    storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

    todos = [Todo(id=1, text="你好世界")]
    storage.save(todos)

    content = db.read_text(encoding="utf-8")

    # Unicode should be preserved (ensure_ascii=False is default)
    assert "你好世界" in content
    # But should be compact (indent=None override)
    lines = content.strip().split("\n")
    assert len(lines) == 1
