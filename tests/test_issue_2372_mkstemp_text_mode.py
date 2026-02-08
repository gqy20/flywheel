"""Regression test for issue #2372: tempfile.mkstemp text=False mismatched with fdopen encoding='utf-8'.

This test verifies that UTF-8 content is written correctly when saving todos,
and that the mkstemp text mode parameter matches the fdopen mode.

Issue: https://github.com/gqy20/flywheel/issues/2372
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_utf8_unicode_saved_correctly(tmp_path) -> None:
    """Test that UTF-8 unicode characters are saved and loaded correctly.

    This test verifies that the text mode mismatch between mkstemp(text=False)
    and fdopen(mode="w", encoding="utf-8") doesn't cause encoding issues.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test various UTF-8 characters that could break with incorrect encoding
    todos = [
        Todo(id=1, text="Chinese characters: 你好世界"),
        Todo(id=2, text="Emoji: 🎉🚀✅"),
        Todo(id=3, text="Japanese: こんにちは"),
        Todo(id=4, text="Arabic: مرحبا"),
        Todo(id=5, text="Cyrillic: Привет"),
        Todo(id=6, text="Greek: Γεια σας"),
        Todo(id=7, text="Mixed: Hello 🌍 世界 🚀"),
    ]

    # Save todos
    storage.save(todos)

    # Verify file contains valid UTF-8 encoded JSON
    raw_content = db.read_bytes()
    decoded_content = raw_content.decode("utf-8")

    # Parse as JSON to verify it's valid
    parsed = json.loads(decoded_content)

    assert len(parsed) == 7
    assert parsed[0]["text"] == "Chinese characters: 你好世界"
    assert parsed[1]["text"] == "Emoji: 🎉🚀✅"
    assert parsed[2]["text"] == "Japanese: こんにちは"
    assert parsed[3]["text"] == "Arabic: مرحبا"
    assert parsed[4]["text"] == "Cyrillic: Привет"
    assert parsed[5]["text"] == "Greek: Γεια σας"
    assert parsed[6]["text"] == "Mixed: Hello 🌍 世界 🚀"

    # Verify we can load todos back correctly
    loaded = storage.load()
    assert len(loaded) == 7
    assert loaded[0].text == "Chinese characters: 你好世界"
    assert loaded[1].text == "Emoji: 🎉🚀✅"


def test_mkstemp_text_parameter_matches_fdopen_mode(tmp_path) -> None:
    """Test that mkstemp text parameter matches fdopen text mode.

    This test enforces consistency between mkstemp's text mode setting
    and fdopen's mode to prevent platform-specific issues.

    On Windows, mkstemp with text=False opens fd in binary mode, which
    can cause issues when fdopen is called with text mode "w".

    This test will FAIL until the bug is fixed, making it a proper RED test.
    """
    import tempfile

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="Test content")]

    # Track the arguments passed to mkstemp
    original_mkstemp = tempfile.mkstemp
    mkstemp_calls = []

    def tracking_mkstemp(*args, **kwargs):
        mkstemp_calls.append({"args": args, "kwargs": kwargs})
        return original_mkstemp(*args, **kwargs)

    from unittest.mock import patch

    with patch.object(tempfile, "mkstemp", tracking_mkstemp):
        storage.save(todos)

    # Verify mkstemp was called
    assert len(mkstemp_calls) == 1

    # Get the text parameter from mkstemp call
    text_param = mkstemp_calls[0]["kwargs"].get("text")

    # FAILING ASSERTION - This enforces the fix:
    # Since fdopen uses mode="w" (text mode) with encoding="utf-8",
    # mkstemp should use text=True for consistency.
    # Currently the code uses text=False, which is incorrect.
    assert text_param is True, (
        f"mkstemp called with text={text_param}, but fdopen uses text mode 'w'. "
        "For consistency, mkstemp should use text=True when fdopen is called "
        "with text mode."
    )


def test_file_encoding_is_utf8(tmp_path) -> None:
    """Test that saved files are properly encoded as UTF-8."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="UTF-8 test: 你好世界 🚀")]
    storage.save(todos)

    # Read as bytes and verify it's valid UTF-8
    raw_bytes = db.read_bytes()

    # Should be decodable as UTF-8 without errors
    try:
        decoded = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        pytest.fail(f"File is not valid UTF-8: {e}")

    # Verify content includes our unicode text
    assert "UTF-8 test: 你好世界 🚀" in decoded

    # Verify it's valid JSON
    parsed = json.loads(decoded)
    assert parsed[0]["text"] == "UTF-8 test: 你好世界 🚀"
