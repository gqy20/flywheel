"""Tests for concurrency documentation in TodoStorage.

This test suite verifies that the race condition limitation for multi-process
usage is properly documented, as per issue #6673.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage


def test_next_id_documents_single_process_limitation() -> None:
    """Regression test for issue #6673: Verify next_id documents race condition.

    The next_id method has a TOCTOU (time-of-check to time-of-use) race condition
    when used by multiple processes. Each process reads the current todos,
    calculates the next ID, and saves. Two processes could read the same state
    and generate duplicate IDs.

    This test verifies that the method documents this limitation.
    """
    docstring = TodoStorage.next_id.__doc__

    assert docstring is not None, (
        "next_id() must have a docstring documenting its behavior and limitations"
    )

    doc_lower = docstring.lower()

    # Check for mention of race condition or concurrency limitation
    has_race_doc = any(
        term in doc_lower
        for term in ["race", "concurrent", "single-process", "multi-process", "multiprocess"]
    )

    assert has_race_doc, (
        "next_id() docstring must document the race condition or single-process limitation"
    )


def test_storage_class_documents_concurrency_limitations() -> None:
    """Verify TodoStorage class docstring documents concurrent access behavior."""
    docstring = TodoStorage.__doc__

    assert docstring is not None, (
        "TodoStorage class must have a docstring"
    )

    doc_lower = docstring.lower()

    # Check for documentation of concurrent access behavior
    has_concurrency_doc = any(
        term in doc_lower
        for term in ["concurrent", "process", "lock", "single", "atomic"]
    )

    assert has_concurrency_doc, (
        "TodoStorage class docstring must document concurrent access behavior or limitations"
    )
