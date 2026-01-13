"""
Test for Issue #1577: Verify that _AsyncCompatibleLock has comprehensive docstrings.

This test verifies that the _AsyncCompatibleLock class has a detailed class-level
docstring explaining:
1. Why the class exists (the hybrid synchronization model)
2. How the threading.Lock + Event hybrid works
3. References to specific deadlock issues it solves
"""

import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockDocstring:
    """Tests for _AsyncCompatibleLock documentation quality."""

    def test_class_has_docstring(self):
        """Verify that _AsyncCompatibleLock has a class-level docstring."""
        assert _AsyncCompatibleLock.__doc__ is not None, (
            "_AsyncCompatibleLock must have a class-level docstring"
        )
        assert len(_AsyncCompatibleLock.__doc__) > 100, (
            "_AsyncCompatibleLock docstring should be comprehensive (>100 chars)"
        )

    def test_docstring_explains_why_it_exists(self):
        """Verify docstring explains why the class exists."""
        docstring = _AsyncCompatibleLock.__doc__

        # Should mention the sync/async compatibility problem
        assert any(keyword in docstring for keyword in [
            "sync and async",
            "synchronous and asynchronous",
            "threading.Lock doesn't support async",
            "asyncio.Lock doesn't support sync"
        ]), (
            "Docstring should explain why _AsyncCompatibleLock exists: "
            "to support both sync and async context managers"
        )

    def test_docstring_explains_how_it_works(self):
        """Verify docstring explains the threading.Lock + Event hybrid mechanism."""
        docstring = _AsyncCompatibleLock.__doc__

        # Should mention the hybrid mechanism
        assert any(keyword in docstring for keyword in [
            "threading.Lock",
            "asyncio.Event",
            "hybrid",
            "unified lock"
        ]), (
            "Docstring should explain the threading.Lock + Event hybrid mechanism"
        )

    def test_docstring_references_bug_fixes(self):
        """Verify docstring references specific deadlock issues it solves."""
        docstring = _AsyncCompatibleLock.__doc__

        # Should reference the specific issues mentioned in the GitHub issue
        # Issue #1097: unified lock interface
        # Issue #1166: single lock with thread-safe synchronization
        # Issue #1290: threading.Lock for sync contexts
        assert any(issue in docstring for issue in [
            "#1097",
            "#1166",
            "#1290",
            "Issue #1097",
            "Issue #1166",
            "Issue #1290"
        ]), (
            "Docstring should reference Issues #1097, #1166, or #1290 "
            "mentioned in the GitHub issue"
        )

    def test_docstring_comprehensive_quality(self):
        """Verify docstring is comprehensive and high quality."""
        docstring = _AsyncCompatibleLock.__doc__

        # Should be multi-line and detailed
        assert len(docstring.split("\n")) >= 5, (
            "Docstring should be multi-line and detailed"
        )

        # Should explain the synchronization model
        assert any(word in docstring for word in [
            "synchronization",
            "mutual exclusion",
            "event loop",
            "blocking"
        ]), (
            "Docstring should explain the synchronization model concepts"
        )
