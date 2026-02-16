"""Regression tests for issue #3662: Symlink protection in load().

Issue: load() follows symlinks without validation, allowing read of arbitrary file content.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_pointing_to_json_file(tmp_path) -> None:
    """Issue #3662: load() should reject symlinks pointing to JSON files.

    Security: An attacker could create a symlink to a sensitive JSON file
    and trick the application into loading it.

    Before fix: load() follows symlink and reads target file content
    After fix: load() raises ValueError when path is a symlink
    """
    # Create a target file that attacker wants us to read
    attack_target = tmp_path / "sensitive_data.json"
    attack_target.write_text('[{"id": 1, "text": "secret data", "done": false}]')

    # Create a symlink that the app will try to load
    symlink_path = tmp_path / "todo.json"
    symlink_path.symlink_to(attack_target)

    storage = TodoStorage(str(symlink_path))

    # Should raise ValueError, not follow the symlink
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink, but load() succeeded")
    except ValueError as e:
        assert "symlink" in str(e).lower(), f"Error message should mention symlink: {e}"


def test_load_rejects_symlink_pointing_to_arbitrary_file(tmp_path) -> None:
    """Issue #3662: load() should reject symlinks pointing to any file type.

    Security: An attacker could create a symlink to /etc/passwd or other
    sensitive files to read their contents through error messages or parsing.
    """
    # Create a target file with non-JSON content
    attack_target = tmp_path / "sensitive.txt"
    attack_target.write_text("root:x:0:0:root:/root:/bin/bash\n")

    # Create a symlink that the app will try to load
    symlink_path = tmp_path / "todo.json"
    symlink_path.symlink_to(attack_target)

    storage = TodoStorage(str(symlink_path))

    # Should raise ValueError about symlink, not about invalid JSON
    try:
        storage.load()
        raise AssertionError("Expected ValueError for symlink, but load() succeeded")
    except ValueError as e:
        # Should reject symlink before even trying to parse JSON
        assert "symlink" in str(e).lower(), f"Error message should mention symlink: {e}"


def test_load_succeeds_with_regular_file(tmp_path) -> None:
    """Issue #3662: load() should continue to work with regular files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a regular file with valid content
    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]
    storage.save(todos)

    # Should succeed normally
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_succeeds_when_file_does_not_exist(tmp_path) -> None:
    """Issue #3662: load() should return empty list for non-existent files."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list without error
    loaded = storage.load()
    assert loaded == []
