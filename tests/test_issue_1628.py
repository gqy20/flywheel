"""Tests for dry_run mode on delete_batch and delete_many with environment variable support (Issue #1628)."""

import os
import tempfile
from pathlib import Path

from flywheel.storage import FileStorage
from flywheel.todo import Status, Todo


def test_delete_batch_dry_run_parameter():
    """Test that delete_batch method accepts dry_run parameter (Issue #1628)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # First add some real todos
        todos = [
            Todo(id=1, title="Todo 1", status=Status.TODO),
            Todo(id=2, title="Todo 2", status=Status.TODO),
            Todo(id=3, title="Todo 3", status=Status.TODO),
        ]
        storage.add_batch(todos)

        # Delete batch with dry_run=True
        result = storage.delete_batch([1, 2], dry_run=True)

        # The result should indicate success (simulating deletion)
        assert result == [True, True]

        # But the todos should still exist
        assert storage.get(1) is not None, "Todo 1 should not be deleted in dry_run mode"
        assert storage.get(2) is not None, "Todo 2 should not be deleted in dry_run mode"
        assert storage.get(3) is not None, "Todo 3 should still exist"
        assert len(storage.list()) == 3, "All todos should still exist in dry_run mode"


def test_delete_many_dry_run_parameter():
    """Test that delete_many method accepts dry_run parameter (Issue #1628)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # First add some real todos
        todos = [
            Todo(id=1, title="Todo 1", status=Status.TODO),
            Todo(id=2, title="Todo 2", status=Status.TODO),
            Todo(id=3, title="Todo 3", status=Status.TODO),
        ]
        storage.add_batch(todos)

        # Delete many with dry_run=True
        result = storage.delete_many([1, 2], dry_run=True)

        # The result should indicate success (simulating deletion)
        assert result == [True, True]

        # But the todos should still exist
        assert storage.get(1) is not None, "Todo 1 should not be deleted in dry_run mode"
        assert storage.get(2) is not None, "Todo 2 should not be deleted in dry_run mode"
        assert storage.get(3) is not None, "Todo 3 should still exist"
        assert len(storage.list()) == 3, "All todos should still exist in dry_run mode"


def test_delete_batch_dry_run_with_nonexistent_ids():
    """Test delete_batch dry_run mode with some non-existent IDs (Issue #1628)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # First add some real todos
        todos = [
            Todo(id=1, title="Todo 1", status=Status.TODO),
            Todo(id=2, title="Todo 2", status=Status.TODO),
        ]
        storage.add_batch(todos)

        # Delete batch with mix of existent and non-existent IDs
        result = storage.delete_batch([1, 99, 2], dry_run=True)

        # The result should indicate success for existing IDs
        assert result == [True, False, True]

        # But no todos should actually be deleted
        assert storage.get(1) is not None, "Todo 1 should not be deleted in dry_run mode"
        assert storage.get(2) is not None, "Todo 2 should not be deleted in dry_run mode"
        assert len(storage.list()) == 2, "All todos should still exist in dry_run mode"


def test_delete_batch_dry_run_false_performs_actual_deletion():
    """Test that delete_batch with dry_run=False performs actual deletion (Issue #1628)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # First add some real todos
        todos = [
            Todo(id=1, title="Todo 1", status=Status.TODO),
            Todo(id=2, title="Todo 2", status=Status.TODO),
            Todo(id=3, title="Todo 3", status=Status.TODO),
        ]
        storage.add_batch(todos)

        # Delete batch with dry_run=False (explicit)
        result = storage.delete_batch([1, 2], dry_run=False)

        # The result should indicate success
        assert result == [True, True]

        # The todos should actually be deleted
        assert storage.get(1) is None, "Todo 1 should be deleted"
        assert storage.get(2) is None, "Todo 2 should be deleted"
        assert storage.get(3) is not None, "Todo 3 should still exist"
        assert len(storage.list()) == 1, "Only one todo should remain"


def test_env_var_dry_run_storage_enables_dry_run():
    """Test that DRY_RUN_STORAGE=1 environment variable enables dry_run mode globally (Issue #1628)."""
    # Set environment variable
    os.environ['DRY_RUN_STORAGE'] = '1'

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(f"{tmpdir}/test.json")
            storage = FileStorage(path=str(test_file))

            # First add some real todos
            todos = [
                Todo(id=1, title="Todo 1", status=Status.TODO),
                Todo(id=2, title="Todo 2", status=Status.TODO),
                Todo(id=3, title="Todo 3", status=Status.TODO),
            ]
            storage.add_batch(todos)

            # Delete batch without explicit dry_run parameter
            # Environment variable should enable dry_run mode
            result = storage.delete_batch([1, 2])

            # The result should indicate success (simulating deletion)
            assert result == [True, True]

            # But the todos should still exist due to env var
            assert storage.get(1) is not None, "Todo 1 should not be deleted when DRY_RUN_STORAGE=1"
            assert storage.get(2) is not None, "Todo 2 should not be deleted when DRY_RUN_STORAGE=1"
            assert len(storage.list()) == 3, "All todos should still exist when DRY_RUN_STORAGE=1"

            # Test delete_many as well
            result_many = storage.delete_many([1, 3])
            assert result_many == [True, True]
            assert len(storage.list()) == 3, "All todos should still exist when DRY_RUN_STORAGE=1"
    finally:
        # Clean up environment variable
        del os.environ['DRY_RUN_STORAGE']


def test_env_var_dry_run_storage_overridden_by_explicit_false():
    """Test that explicit dry_run=False overrides DRY_RUN_STORAGE environment variable (Issue #1628)."""
    # Set environment variable
    os.environ['DRY_RUN_STORAGE'] = '1'

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(f"{tmpdir}/test.json")
            storage = FileStorage(path=str(test_file))

            # First add some real todos
            todos = [
                Todo(id=1, title="Todo 1", status=Status.TODO),
                Todo(id=2, title="Todo 2", status=Status.TODO),
                Todo(id=3, title="Todo 3", status=Status.TODO),
            ]
            storage.add_batch(todos)

            # Delete batch with explicit dry_run=False
            # This should override the environment variable
            result = storage.delete_batch([1, 2], dry_run=False)

            # The result should indicate success
            assert result == [True, True]

            # The todos should actually be deleted (explicit False overrides env var)
            assert storage.get(1) is None, "Todo 1 should be deleted with explicit dry_run=False"
            assert storage.get(2) is None, "Todo 2 should be deleted with explicit dry_run=False"
            assert storage.get(3) is not None, "Todo 3 should still exist"
            assert len(storage.list()) == 1, "Only one todo should remain"
    finally:
        # Clean up environment variable
        del os.environ['DRY_RUN_STORAGE']


def test_env_var_dry_run_storage_zero_disabled():
    """Test that DRY_RUN_STORAGE=0 does not enable dry_run mode (Issue #1628)."""
    # Set environment variable to 0
    os.environ['DRY_RUN_STORAGE'] = '0'

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(f"{tmpdir}/test.json")
            storage = FileStorage(path=str(test_file))

            # First add some real todos
            todos = [
                Todo(id=1, title="Todo 1", status=Status.TODO),
                Todo(id=2, title="Todo 2", status=Status.TODO),
                Todo(id=3, title="Todo 3", status=Status.TODO),
            ]
            storage.add_batch(todos)

            # Delete batch without explicit dry_run parameter
            result = storage.delete_batch([1, 2])

            # The todos should actually be deleted (env var is 0, not 1)
            assert storage.get(1) is None, "Todo 1 should be deleted when DRY_RUN_STORAGE=0"
            assert storage.get(2) is None, "Todo 2 should be deleted when DRY_RUN_STORAGE=0"
            assert len(storage.list()) == 1, "Only one todo should remain"
    finally:
        # Clean up environment variable
        del os.environ['DRY_RUN_STORAGE']
