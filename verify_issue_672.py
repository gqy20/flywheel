#!/usr/bin/env python3
"""Verification script for Issue #672: Auto-save timer mechanism.

This script verifies that the auto-save background timer is properly
implemented and functional.
"""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_auto_save_timer_exists():
    """Verify auto-save timer thread exists and is running."""
    print("Test 1: Checking if auto-save timer thread exists...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / 'todos.json'
        storage = FileStorage(str(storage_path))

        # Check thread exists
        assert hasattr(storage, '_auto_save_thread'), \
            "❌ FAIL: _auto_save_thread attribute not found"
        assert storage._auto_save_thread is not None, \
            "❌ FAIL: _auto_save_thread is None"
        assert storage._auto_save_thread.is_alive(), \
            "❌ FAIL: _auto_save_thread is not alive"
        assert storage._auto_save_thread.daemon, \
            "❌ FAIL: _auto_save_thread is not a daemon thread"

        # Check stop event exists
        assert hasattr(storage, '_auto_save_stop_event'), \
            "❌ FAIL: _auto_save_stop_event attribute not found"

        # Cleanup
        storage._auto_save_stop_event.set()
        storage._auto_save_thread.join(timeout=5)

    print("✅ PASS: Auto-save timer thread is running")


def test_auto_save_timer_works():
    """Verify auto-save timer actually persists data."""
    print("\nTest 2: Checking if auto-save timer persists data...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / 'todos.json'
        storage = FileStorage(str(storage_path))

        # Set short interval for testing
        storage.AUTO_SAVE_INTERVAL = 0.5  # 500ms

        # Add a todo (sets _dirty = True)
        todo = Todo(title='Test auto-save timer')
        storage.add(todo)

        # Wait for auto-save to trigger
        time.sleep(1.5)

        # Verify data was persisted
        assert storage_path.exists(), \
            "❌ FAIL: Storage file does not exist"

        import json
        with open(storage_path, 'r') as f:
            data = json.load(f)
            todos = data.get('todos', [])
            assert len(todos) >= 1, \
                f"❌ FAIL: Expected at least 1 todo, got {len(todos)}"
            assert any(t['title'] == 'Test auto-save timer' for t in todos), \
                "❌ FAIL: Added todo not found in file"

        # Cleanup
        storage._auto_save_stop_event.set()
        storage._auto_save_thread.join(timeout=5)

    print("✅ PASS: Auto-save timer persists data to disk")


def test_auto_save_timer_stops():
    """Verify auto-save timer stops on close."""
    print("\nTest 3: Checking if auto-save timer stops on close...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / 'todos.json'
        storage = FileStorage(str(storage_path))
        auto_save_thread = storage._auto_save_thread

        storage.close()

        assert not auto_save_thread.is_alive(), \
            "❌ FAIL: Auto-save thread still alive after close"

    print("✅ PASS: Auto-save timer stops on close")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Issue #672 Verification: Auto-save Timer Mechanism")
    print("=" * 60)

    try:
        test_auto_save_timer_exists()
        test_auto_save_timer_works()
        test_auto_save_timer_stops()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("Issue #672 is already implemented (via Issue #592)")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n{e}")
        print("\n" + "=" * 60)
        print("❌ Tests failed")
        print("=" * 60)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
