"""Tests for issue #5045: Custom JSON serialization parameters.

This test suite verifies that TodoStorage accepts optional json_dumps_kwargs
parameter to customize JSON serialization behavior while maintaining default
behavior (indent=2, ensure_ascii=False).
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestJsonDumpsKwargs:
    """Tests for custom json_dumps_kwargs parameter in TodoStorage."""

    def test_default_behavior_indent_2(self, tmp_path: Path) -> None:
        """Test that default behavior uses indent=2 and ensure_ascii=False."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # Should have newlines and indentation (indent=2)
        assert "\n" in content
        assert "  " in content
        # Should preserve unicode characters (ensure_ascii=False)
        assert "test" in content

    def test_custom_indent_none_produces_compact_json(self, tmp_path: Path) -> None:
        """Test that setting indent=None produces compact JSON without newlines."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

        todos = [Todo(id=1, text="compact test")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # Compact JSON should be on a single line (no indentation)
        assert "\n" not in content
        # Verify it's still valid JSON
        parsed = json.loads(content)
        assert len(parsed) == 1
        assert parsed[0]["text"] == "compact test"

    def test_custom_ensure_ascii_true(self, tmp_path: Path) -> None:
        """Test that setting ensure_ascii=True encodes unicode as ASCII escapes."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), json_dumps_kwargs={"ensure_ascii": True})

        todos = [Todo(id=1, text="你好世界")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # With ensure_ascii=True, unicode should be escaped
        assert "\\u" in content
        # The raw unicode characters should NOT appear
        assert "你好世界" not in content
        # But when parsed back, it should be correct
        parsed = json.loads(content)
        assert parsed[0]["text"] == "你好世界"

    def test_multiple_custom_kwargs(self, tmp_path: Path) -> None:
        """Test that multiple custom kwargs work together."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(
            str(db), json_dumps_kwargs={"indent": None, "ensure_ascii": True, "separators": (",", ":")}
        )

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # Should be compact (no whitespace around separators)
        assert "\n" not in content
        assert ", " not in content  # No space after comma
        assert ": " not in content  # No space after colon

    def test_default_ensure_ascii_false_preserves_unicode(self, tmp_path: Path) -> None:
        """Test that default ensure_ascii=False preserves unicode characters."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))  # Using defaults

        todos = [Todo(id=1, text="中文测试 日本語 한국어")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # Unicode should be preserved directly (not escaped)
        assert "中文测试" in content
        assert "日本語" in content
        assert "한국어" in content

    def test_partial_kwargs_override(self, tmp_path: Path) -> None:
        """Test that providing only some kwargs keeps defaults for others."""
        db = tmp_path / "todo.json"
        # Only override indent, ensure_ascii should still be False
        storage = TodoStorage(str(db), json_dumps_kwargs={"indent": 4})

        todos = [Todo(id=1, text="test 你好")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # indent=4 should create 4-space indentation
        assert "    " in content  # 4 spaces
        # ensure_ascii=False should still preserve unicode
        assert "你好" in content

    def test_empty_json_dumps_kwargs_uses_defaults(self, tmp_path: Path) -> None:
        """Test that passing empty dict still uses default behavior."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), json_dumps_kwargs={})

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        content = db.read_text(encoding="utf-8")
        # Should behave exactly like defaults
        assert "\n" in content
        assert "  " in content  # indent=2

    def test_load_still_works_with_custom_kwargs(self, tmp_path: Path) -> None:
        """Test that load() works correctly regardless of custom kwargs used in save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), json_dumps_kwargs={"indent": None})

        todos = [
            Todo(id=1, text="first", done=False),
            Todo(id=2, text="second", done=True),
        ]
        storage.save(todos)

        # Load should work regardless of how the file was saved
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "first"
        assert loaded[0].done is False
        assert loaded[1].text == "second"
        assert loaded[1].done is True
