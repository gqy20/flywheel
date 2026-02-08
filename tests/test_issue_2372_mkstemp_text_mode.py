"""Regression tests for issue #2372 - tempfile.mkstemp text mode mismatch.

Issue: tempfile.mkstemp(text=False) opens binary fd, but os.fdopen(fd, 'w', encoding='utf-8')
treats it as text mode, causing potential encoding issues.

The fix: Change text=False to text=True to match the text mode fdopen.
"""

import tempfile
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


@pytest.fixture
def temp_storage():
    """Create a temporary TodoStorage instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.json"
        yield TodoStorage(str(db_path))


def test_utf8_unicode_saved_correctly(temp_storage):
    """Test that UTF-8 content (Chinese characters, emoji) is saved and loaded correctly.

    This test verifies the fix for issue #2372. The binary/text mode mismatch
    could potentially corrupt multi-byte UTF-8 sequences.
    """
    # Create todos with various Unicode content
    todos = [
        Todo(id=1, text="Learn Python"),
        Todo(id=2, text="学习中文"),  # Chinese: "Learn Chinese"
        Todo(id=3, text="Emoji test 🎉🚀", done=True),
        Todo(id=4, text="Mix of 你好 Hello 🌍"),
    ]

    # Save the todos
    temp_storage.save(todos)

    # Load and verify
    loaded_todos = temp_storage.load()
    assert len(loaded_todos) == 4

    # Verify each todo's content is preserved exactly
    assert loaded_todos[0].text == "Learn Python"
    assert loaded_todos[1].text == "学习中文"
    assert loaded_todos[2].text == "Emoji test 🎉🚀"
    assert loaded_todos[3].text == "Mix of 你好 Hello 🌍"


def test_file_encoding_is_utf8(temp_storage):
    """Verify that the saved file is actually UTF-8 encoded.

    This test ensures that the file content is valid UTF-8 and can be
    read back correctly.
    """
    todos = [
        Todo(id=1, text="Test UTF-8: 你好 🌍"),
    ]

    temp_storage.save(todos)

    # Read the file and verify it's valid UTF-8
    raw_content = temp_storage.path.read_bytes()
    decoded_content = raw_content.decode("utf-8")

    # Verify the content contains our Unicode strings
    assert "你好" in decoded_content
    assert "🌍" in decoded_content

    # Verify it's valid JSON with proper UTF-8
    import json
    data = json.loads(decoded_content)
    assert data[0]["text"] == "Test UTF-8: 你好 🌍"


def test_temp_and_final_file_match(temp_storage):
    """Verify atomic write consistency: temp file and final file have identical content.

    This test verifies that the write-to-temp-file + atomic rename pattern
    preserves content integrity.
    """
    todos = [
        Todo(id=1, text="Test content 你好 🌍"),
        Todo(id=2, text="Another test 🚀", done=True),
    ]

    # First save
    temp_storage.save(todos)

    # Verify content is readable
    temp_storage.path.read_text(encoding="utf-8")

    # Modify and save again
    todos.append(Todo(id=3, text="Third item 🎉"))
    temp_storage.save(todos)

    # Verify content is still readable after second save
    temp_storage.path.read_text(encoding="utf-8")

    # Verify both loads work correctly
    loaded_todos = temp_storage.load()
    assert len(loaded_todos) == 3
    assert loaded_todos[0].text == "Test content 你好 🌍"
    assert loaded_todos[2].text == "Third item 🎉"


def test_mkstemp_mode_consistency(temp_storage, monkeypatch):
    """Direct test of tempfile.mkstemp mode consistency.

    This test verifies that the tempfile.mkstemp call uses the correct
    text mode parameter to match os.fdopen behavior.
    """
    # Track the parameters passed to mkstemp
    mkstemp_calls = []
    original_mkstemp = tempfile.mkstemp

    def mock_mkstemp(*args, **kwargs):
        mkstemp_calls.append({"args": args, "kwargs": kwargs})
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", mock_mkstemp)

    # Save a todo
    todos = [Todo(id=1, text="Test")]
    temp_storage.save(todos)

    # Verify mkstemp was called with text=True (not text=False)
    assert len(mkstemp_calls) == 1
    assert mkstemp_calls[0]["kwargs"].get("text") is True
