"""Regression tests for issue #1883: Path traversal vulnerability via user-controlled db_path.

Issue: User-controlled --db argument allows path traversal attacks (e.g., '../../../etc/passwd')
that could read arbitrary files or write files outside the intended directory.

Fix approach: Add opt-in validate parameter to TodoStorage that ensures the resolved
path is within the current working directory when validation is enabled.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_fails_with_path_traversal_dotdot_slash(tmp_path) -> None:
    """Issue #1883: Should reject paths with '../' sequences that escape working directory."""
    # Change to tmp_path so we have a controlled working directory
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Try to load from a path that escapes the working directory
        # This should fail during __init__ when validation is enabled
        with pytest.raises(ValueError, match=r"(invalid|unsafe|outside|traversal)"):
            TodoStorage("../../../etc/passwd", validate=True)
    finally:
        os.chdir(original_cwd)


def test_storage_save_fails_with_path_traversal_dotdot_slash(tmp_path) -> None:
    """Issue #1883: Should reject saving to paths with '../' sequences."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Try to save to a path that escapes the working directory
        # This should fail during __init__ when validation is enabled
        with pytest.raises(ValueError, match=r"(invalid|unsafe|outside|traversal)"):
            TodoStorage("../../../tmp/escaped.json", validate=True)
    finally:
        os.chdir(original_cwd)


def test_storage_load_fails_with_absolute_path_outside_cwd(tmp_path) -> None:
    """Issue #1883: Should reject absolute paths outside current working directory."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Try to load from an absolute path outside the working directory
        # This should fail during __init__ when validation is enabled
        with pytest.raises(ValueError, match=r"(invalid|unsafe|outside|traversal)"):
            TodoStorage("/tmp/test.json", validate=True)
    finally:
        os.chdir(original_cwd)


def test_storage_save_fails_with_absolute_path_outside_cwd(tmp_path) -> None:
    """Issue #1883: Should reject saving to absolute paths outside working directory."""
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Try to save to an absolute path outside the working directory
        # This should fail during __init__ when validation is enabled
        with pytest.raises(ValueError, match=r"(invalid|unsafe|outside|traversal)"):
            TodoStorage("/tmp/escaped.json", validate=True)
    finally:
        os.chdir(original_cwd)


def test_storage_allows_relative_path_within_cwd(tmp_path) -> None:
    """Issue #1883: Should allow relative paths that stay within working directory."""
    import os
    from flywheel.todo import Todo
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Normal relative path should work
        storage = TodoStorage("subdir/todo.json", validate=True)

        # Save should work
        todo = Todo(id=1, text="test todo")
        storage.save([todo])

        # Load should return the saved todo
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_storage_allows_absolute_path_within_cwd(tmp_path) -> None:
    """Issue #1883: Should allow absolute paths that are within working directory."""
    import os
    from flywheel.todo import Todo
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Absolute path within the working directory should work
        db_path = str(tmp_path / "todo.json")
        storage = TodoStorage(db_path, validate=True)

        # Save should work
        todo = Todo(id=1, text="test todo")
        storage.save([todo])

        # Load should return the saved todo
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_storage_validation_disabled_by_default(tmp_path) -> None:
    """Issue #1883: Validation should be opt-in (validate=False by default).

    This ensures backward compatibility for programmatic usage.
    """
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Without validate=True, path traversal should still work (backward compatibility)
        # This test documents the existing behavior for backward compatibility
        storage = TodoStorage("test.json")  # validate defaults to False

        # Should not raise for normal usage
        storage.load()  # File doesn't exist, returns empty list
    finally:
        os.chdir(original_cwd)


def test_storage_normalizes_dotdot_paths_before_validation(tmp_path) -> None:
    """Issue #1883: Paths that normalize to within cwd should be allowed.

    E.g., 'subdir/../todo.json' should resolve to just 'todo.json' within cwd.
    """
    import os
    from flywheel.todo import Todo
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Path with ../ that normalizes to stay within cwd
        storage = TodoStorage("subdir/../todo.json", validate=True)

        # Save should work
        todo = Todo(id=1, text="test todo")
        storage.save([todo])

        # Load should return the saved todo
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_storage_detects_symlink_escape(tmp_path) -> None:
    """Issue #1883: Should detect symlinks pointing outside allowed directory.

    The _validate_path method uses resolve() which follows symlinks, so it
    will detect when a symlink points outside the working directory during
    initialization, not during save().
    """
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create a symlink pointing outside the working directory
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir()
        symlink_path = tmp_path / "escape_link"
        symlink_path.symlink_to(outside_dir)

        # Try to use the symlink as the database location
        # Validation happens in __init__ and follows symlinks
        db_via_symlink = str(symlink_path / "todo.json")
        with pytest.raises(ValueError, match=r"(invalid|unsafe|outside|traversal)"):
            TodoStorage(db_via_symlink, validate=True)
    finally:
        os.chdir(original_cwd)
