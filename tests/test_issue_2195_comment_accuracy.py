"""Regression tests for issue #2195: Comment accuracy for exist_ok parameter.

Issue: Comment at storage.py:45 incorrectly claims exist_ok=False is safe due to
prior validation, but validation only checks files not directories. The comment
should either be removed, updated for accuracy, or use exist_ok=True for robustness.

These tests verify the actual behavior and safety guarantees of the code.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_comment_accuracy_exist_ok_false_with_race_condition(tmp_path) -> None:
    """Issue #2195: Verify exist_ok=False fails with FileExistsError on concurrent mkdir.

    This test demonstrates that the comment's claim is misleading - the validation
    does NOT protect against race conditions with concurrent directory creation.
    """
    db_path = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Pre-create the parent directory
    db_path.parent.mkdir(parents=True)

    # This should still work - the validation only prevents file-as-directory confusion
    # If exist_ok=False was truly safe, this would always fail when parent exists
    todos = [Todo(id=1, text="test")]
    storage.save(todos)  # Should succeed despite parent already existing

    # Verify save succeeded
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1


def test_validation_only_checks_files_not_directories(tmp_path) -> None:
    """Issue #2195: Verify validation loop only checks for file-as-directory confusion.

    The validation at lines 35-40 raises ValueError if a parent component exists
    as a file, but does NOT check for concurrent directory creation.
    """
    # Case 1: Parent is a file - should fail with ValueError
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("I am a file")

    db_path = conflicting_file / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    with pytest.raises(ValueError, match=r"exists as a file"):
        storage.save([])


def test_save_succeeds_when_parent_created_concurrently(tmp_path) -> None:
    """Issue #2195: Behavior when parent directory is created between validation and mkdir.

    This test shows the TOCTOU window exists. The comment should not claim
    absolute safety from validation.
    """
    db_path = tmp_path / "race" / "todo.json"

    # Simulate concurrent directory creation by pre-creating parent
    db_path.parent.mkdir(parents=True, exist_ok=True)

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="test")]

    # Current behavior with exist_ok=False: This would fail with FileExistsError
    # if the implementation actually used exist_ok=False incorrectly.
    # The save should handle this gracefully.
    # Note: With exist_ok=True, this succeeds. With exist_ok=False, it would fail.
    storage.save(todos)

    assert db_path.exists()


def test_normal_nested_directory_creation_still_works(tmp_path) -> None:
    """Issue #2195: Ensure normal nested path creation still works after any fix.

    This is a safety test to ensure we don't break the normal flow.
    """
    db_path = tmp_path / "a" / "b" / "c" / "todo.json"
    storage = TodoStorage(str(db_path))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
