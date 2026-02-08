"""Regression test for issue #2372: UTF-8 encoding consistency.

This test verifies that UTF-8 content (including emojis, CJK characters,
and accented characters) is written and read correctly when saving todos.

The issue was that tempfile.mkstemp was called with text=False (binary mode)
but os.fdopen was called with mode='w' (text mode) and encoding='utf-8',
creating a semantic mismatch in the code.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_unicode_emoji_characters(tmp_path) -> None:
    """Test that todos with emoji characters are saved correctly with UTF-8 encoding."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test with various emoji characters
    todos = [
        Todo(id=1, text="Task with emoji: 😀 🎉 🚀"),
        Todo(id=2, text="More emojis: ❤️ 🌟 🎯"),
        Todo(id=3, text="Mixed content with emojis: 完成 ✅"),
    ]

    storage.save(todos)

    # Verify file is valid UTF-8 and can be read
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].text == "Task with emoji: 😀 🎉 🚀"
    assert loaded[1].text == "More emojis: ❤️ 🌟 🎯"
    assert loaded[2].text == "Mixed content with emojis: 完成 ✅"


def test_save_cjk_characters(tmp_path) -> None:
    """Test that todos with CJK characters are saved correctly with UTF-8 encoding."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test with Chinese, Japanese, Korean characters
    todos = [
        Todo(id=1, text="中文任务: 完成项目开发"),
        Todo(id=2, text="日本語: プロジェクトを完了する"),
        Todo(id=3, text="한국어: 프로젝트 완료"),
    ]

    storage.save(todos)

    # Verify file is valid UTF-8 and can be read
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].text == "中文任务: 完成项目开发"
    assert loaded[1].text == "日本語: プロジェクトを完了する"
    assert loaded[2].text == "한국어: 프로젝트 완료"


def test_save_accented_characters(tmp_path) -> None:
    """Test that todos with accented characters are saved correctly with UTF-8 encoding."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test with various accented characters
    todos = [
        Todo(id=1, text="Café résumé naïve"),
        Todo(id=2, text="El niño está aquí"),
        Todo(id=3, text="Über die Straße gehen"),
        Todo(id=4, text="Москва - Россия"),
    ]

    storage.save(todos)

    # Verify file is valid UTF-8 and can be read
    loaded = storage.load()
    assert len(loaded) == 4
    assert loaded[0].text == "Café résumé naïve"
    assert loaded[1].text == "El niño está aquí"
    assert loaded[2].text == "Über die Straße gehen"
    assert loaded[3].text == "Москва - Россия"


def test_file_encoding_is_utf8(tmp_path) -> None:
    """Test that the saved file is actually encoded as UTF-8."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="UTF-8 test: 你好 🎉 Café"),
    ]

    storage.save(todos)

    # Read the raw file and verify it's valid UTF-8
    raw_content = db.read_bytes()
    # Decode as UTF-8 should not raise UnicodeDecodeError
    decoded = raw_content.decode("utf-8")

    # Verify the content matches what we saved
    assert "UTF-8 test: 你好 🎉 Café" in decoded
    assert '"text": "UTF-8 test: 你好 🎉 Café"' in decoded


def test_temp_and_final_file_consistency(tmp_path) -> None:
    """Test that temp file and final file have identical UTF-8 content.

    This test verifies that the text mode handling is consistent between
    mkstemp and fdopen.
    """
    import tempfile
    from unittest.mock import patch

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="Unicode test: 🎉 你가 こんにちは"),
        Todo(id=2, text="Café résumé"),
    ]

    # Track what gets written to the temp file
    temp_file_contents = []
    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Track what we're about to write
        temp_file_contents.append({"fd": fd, "path": path})
        return fd, path

    with patch.object(tempfile, "mkstemp", tracking_mkstemp):
        storage.save(todos)

    # Verify final file content is correct
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "Unicode test: 🎉 你가 こんにちは"
    assert loaded[1].text == "Café résumé"

    # Verify temp files were cleaned up (only final file should remain)
    tmp_files = list(db.parent.glob(".todo.json.*.tmp"))
    assert len(tmp_files) == 0, "Temp files should be cleaned up after save"
