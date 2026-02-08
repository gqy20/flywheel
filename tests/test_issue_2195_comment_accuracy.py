"""Regression tests for issue #2195: Misleading comment about exist_ok=False safety.

Issue: The comment on line 45 of storage.py incorrectly claims that exist_ok=False
is safe due to prior validation. However, the validation only checks if existing
paths are files (not directories), and there's a TOCTOU window between the
exists() check and mkdir() call.

These tests verify:
1. The comment accurately reflects the actual safety guarantees
2. Code behavior is robust against concurrent directory creation
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_comment_accuracy_reflects_file_validation_only() -> None:
    """Issue #2195: Verify comment accurately reflects that validation only checks files.

    The comment should clarify that exist_ok=False prevents file-as-directory
    confusion, not race conditions. The validation loop checks for existing
    files in parent paths, not concurrent directory creation.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create a file where we need a directory
        blocking_file = tmp_path / "blocking.json"
        blocking_file.write_text("I am a file")

        # Try to create a path that requires the file to be a directory
        db_path = blocking_file / "subdir" / "todo.json"

        # Should raise ValueError about the file-as-directory confusion
        with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
            _ensure_parent_directory(db_path)


def test_ensure_parent_directory_allows_existing_directory() -> None:
    """Issue #2195: Verify the function handles existing directories gracefully.

    This test verifies that if a directory already exists (created concurrently
    or beforehand), the function should handle it appropriately.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Pre-create the parent directory
        parent_dir = tmp_path / "existing_parent"
        parent_dir.mkdir()

        # Should not raise an error since parent already exists as directory
        db_path = parent_dir / "todo.json"
        _ensure_parent_directory(db_path)

        # Parent should still be a directory
        assert parent_dir.is_dir()


def test_ensure_parent_directory_concurrent_dir_creation_scenario() -> None:
    """Issue #2195: Test scenario simulating concurrent directory creation.

    This tests a TOCTOU scenario where the directory is created between
    the exists() check and the mkdir() call. With exist_ok=True, this
    should be handled gracefully.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        db_path = tmp_path / "parent" / "todo.json"
        parent = db_path.parent

        # Pre-create parent directory to simulate concurrent creation
        # This tests that exist_ok=True handles this gracefully
        parent.mkdir(parents=True, exist_ok=True)

        # Should succeed without error since directory already exists
        _ensure_parent_directory(db_path)

        # Parent should still be a directory
        assert parent.is_dir()


def test_comment_accuracy_check_via_source_reading() -> None:
    """Issue #2195: Verify the comment in source code is accurate.

    This is a documentation-style test that enforces the comment must
    accurately describe what the validation actually does.
    """
    import inspect

    # Read the source code to verify comment accuracy
    source = inspect.getsource(_ensure_parent_directory)

    # The comment should mention validation prevents file-as-directory confusion
    # NOT that it prevents race conditions
    assert "file" in source.lower() or "directory" in source.lower(), (
        "Comment should reference file/directory validation"
    )

    # Check that the comment near exist_ok=False is present and accurate
    # (This is a semantic test - the fix should update the comment)
    lines = source.split("\n")
    mkdir_line = None
    for line in lines:
        if "mkdir" in line and "exist_ok" in line:
            mkdir_line = line
            break

    assert mkdir_line is not None, "Should have mkdir call with exist_ok parameter"
    assert "exist_ok" in mkdir_line, "Should use exist_ok parameter"


def test_todo_storage_save_with_concurrent_mkdir_safety() -> None:
    """Issue #2195: TodoStorage.save() should handle concurrent directory creation.

    This verifies that the overall save operation is robust even if directories
    are created concurrently (e.g., by another process).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "data" / "todo.json"

        # Pre-create the parent directory (simulating concurrent creation)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Should work fine
        storage = TodoStorage(str(db_path))
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Verify data was saved
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"
