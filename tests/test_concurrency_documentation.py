"""Tests for concurrency behavior documentation.

This test suite verifies that the codebase properly documents
concurrent write semantics (last-writer-wins) so users are aware
of potential data loss in multi-process scenarios.

See issue #3874: Data loss risk from last-writer-wins semantics.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage


class TestConcurrencyDocumentation:
    """Test that concurrency limitations are properly documented."""

    def test_storage_class_documents_concurrency_semantics(self) -> None:
        """TodoStorage class docstring should mention concurrent write behavior."""
        class_doc = TodoStorage.__doc__
        assert class_doc is not None, "TodoStorage should have a docstring"

        # Check for key terms related to concurrency
        doc_lower = class_doc.lower()
        has_concurrency_term = any(
            term in doc_lower
            for term in [
                "concurrent",
                "concurrency",
                "last-writer-wins",
                "last writer",
                "multi-process",
                "multiprocess",
                "parallel",
                "locking",
                "lock",
            ]
        )
        assert has_concurrency_term, (
            "TodoStorage docstring should document concurrent write behavior. "
            "Users need to understand that this is a simple JSON file storage "
            "without database-level locking, and concurrent writes follow "
            "last-writer-wins semantics."
        )

    def test_storage_class_documents_limitations(self) -> None:
        """TodoStorage class docstring should mention limitations."""
        class_doc = TodoStorage.__doc__
        assert class_doc is not None, "TodoStorage should have a docstring"

        doc_lower = class_doc.lower()
        has_limitation_term = any(
            term in doc_lower
            for term in [
                "limitation",
                "limit",
                "not suitable",
                "single-user",
                "single user",
                "warning",
                "caution",
                "data loss",
                "dataloss",
            ]
        )
        assert has_limitation_term, (
            "TodoStorage docstring should warn about limitations. "
            "Users should be aware of potential data loss scenarios "
            "when using this storage in multi-process environments."
        )

    def test_save_method_documents_last_writer_wins(self) -> None:
        """The save() method docstring should explain last-writer-wins behavior."""
        save_doc = TodoStorage.save.__doc__
        assert save_doc is not None, "TodoStorage.save should have a docstring"

        doc_lower = save_doc.lower()

        # Check for explicit mention of concurrent/parallel write behavior
        mentions_concurrency = any(
            term in doc_lower
            for term in [
                "concurrent",
                "last-writer-wins",
                "last writer",
                "race",
                "overwrite",
                "overwrite",
                "multi-process",
            ]
        )
        assert mentions_concurrency, (
            "TodoStorage.save() docstring should document that concurrent writes "
            "follow last-writer-wins semantics and may result in data loss. "
            "This is a documented limitation for this simple JSON file storage."
        )


class TestReadmeConcurrencyWarning:
    """Test that README documents concurrency limitations."""

    def test_readme_has_concurrency_warning(self) -> None:
        """README.md should contain a warning about concurrent access."""
        # Read README content
        readme_content = ""
        try:
            with open("README.md") as f:
                readme_content = f.read()
        except FileNotFoundError:
            # Skip this test if README is not found
            return

        readme_lower = readme_content.lower()

        # Check for concurrency-related documentation
        has_concurrency_doc = any(
            term in readme_lower
            for term in [
                "concurrent",
                "concurrency",
                "last-writer-wins",
                "multi-process",
                "multiprocess",
                "parallel",
                "locking",
                "single-user",
                "single user",
            ]
        )
        assert has_concurrency_doc, (
            "README.md should document concurrency limitations. "
            "Users need to know this is a simple single-user tool "
            "and concurrent writes may cause data loss."
        )
