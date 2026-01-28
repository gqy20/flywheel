"""Test for Issue #1426: Bug in __enter__ exception handling logic

This test verifies that the exception handling in __enter__ method does NOT
cause double release of the lock.

The problematic code was:
    try:
        return self
    except:
        self._lock.release()
        raise

The problem:
1. `return self` cannot normally raise an exception
2. If an exception somehow occurred, releasing the lock here would cause a
   double release when __exit__ is called, triggering RuntimeError

The correct behavior:
- The try-except block around `return self` should be removed
- If any exception could occur after lock acquisition, it should be handled
  differently to avoid double release
"""
import threading
import pytest

from flywheel.storage import FileStorage


class TestIssue1426:
    """Test that __enter__ does not have problematic exception handling."""

    def test_enter_does_not_have_bare_except_around_return(self):
        """Test that verifies the __enter__ method structure.

        This test verifies that the __enter__ method doesn't have a problematic
        try-except block around `return self` that could cause double release.

        The test checks the source code to ensure it's properly structured.
        """
        import inspect

        storage = FileStorage(":memory:", timeout=5)

        # Get the source code of __enter__ method
        source = inspect.getsource(storage.__enter__)

        # The problematic pattern we're checking for
        # We want to ensure there's no bare except around return self
        # that would release the lock

        # Check that the method acquires the lock
        assert "acquire(timeout=" in source or "acquire(timeout=" in source
        assert "_lock_timeout" in source

        # The method should return self at some point
        assert "return self" in source

        # Check that we're not using the problematic pattern
        # The problematic pattern would be:
        # try:
        #     return self
        # except:
        #     self._lock.release()
        #     raise

        # We verify by checking the structure doesn't have a bare except
        # that releases the lock right before or after return self
        lines = source.split('\n')

        # Find the "return self" line
        return_self_line = None
        for i, line in enumerate(lines):
            if 'return self' in line and 'try:' not in line:
                return_self_line = i
                break

        assert return_self_line is not None, "Could not find 'return self' in __enter__"

        # Check if there's a bare except block that releases the lock
        # This would be the problematic pattern
        problematic_pattern_found = False
        for i in range(max(0, return_self_line - 5), min(len(lines), return_self_line + 5)):
            line = lines[i].strip()
            # Look for the problematic pattern
            if (line.startswith('except:') or line.startswith('except Exception:') or
                line == 'except:'):
                # Check if this except block releases the lock
                for j in range(i, min(len(lines), i + 5)):
                    if '_lock.release()' in lines[j]:
                        problematic_pattern_found = True
                        break

        # The test will fail if the problematic pattern is found
        # This indicates the bug from issue #1426 is present
        assert not problematic_pattern_found, (
            "Found problematic exception handling in __enter__: "
            "try-except around 'return self' that releases the lock. "
            "This could cause double release. See issue #1426."
        )

    def test_lock_properly_managed_on_normal_exit(self):
        """Test that lock is properly acquired and released in normal case.

        This is a sanity check that the basic context manager behavior works.
        """
        storage = FileStorage(":memory:", timeout=5)

        # Lock should not be held initially
        assert not storage._lock.locked()

        # Enter context - lock should be held
        with storage:
            assert storage._lock.locked()

        # After exit - lock should be released
        assert not storage._lock.locked()

    def test_no_double_release_on_exception_in_context(self):
        """Test that there's no double release if exception occurs in context.

        If an exception occurs within the context (not in __enter__),
        __exit__ should release the lock exactly once without error.
        """
        storage = FileStorage(":memory:", timeout=5)

        # Use context manager and raise an exception
        with pytest.raises(ValueError):
            with storage:
                assert storage._lock.locked()
                raise ValueError("Test exception")

        # Lock should be released properly (no double release)
        assert not storage._lock.locked()

    def test_concurrent_context_managers_no_deadlock(self):
        """Test that concurrent context managers work without deadlock.

        This verifies that the lock management is correct and doesn't cause
        deadlocks or double releases.
        """
        storage = FileStorage(":memory:", timeout=5)
        results = []

        def worker(thread_id):
            """Worker that uses context manager multiple times."""
            for i in range(5):
                with storage:
                    # Verify we have the lock
                    assert storage._lock.locked()
                    results.append((thread_id, i))

        # Run multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All operations should have completed
        assert len(results) == 15  # 3 threads * 5 iterations

        # Lock should be released
        assert not storage._lock.locked()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
