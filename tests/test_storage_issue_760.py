"""Test that FileStorage.__init__ docstring is complete (Issue #760).

This test verifies that the FileStorage.__init__ method has a complete
docstring with all parameters documented.

Issue #760 claimed that the code was truncated and the docstring was incomplete,
but this was a false positive. The code is complete and working correctly.
"""

import tempfile
from flywheel.storage import FileStorage


def test_filestorage_init_docstring_complete():
    """Verify that FileStorage.__init__ has a complete docstring."""
    docstring = FileStorage.__init__.__doc__

    # Check that docstring exists
    assert docstring is not None, "FileStorage.__init__ should have a docstring"

    # Check main description
    assert "Initialize FileStorage" in docstring, (
        "Docstring should contain 'Initialize FileStorage'"
    )

    # Check that all parameters are documented
    assert "path:" in docstring, "Docstring should document 'path' parameter"
    assert "compression:" in docstring, "Docstring should document 'compression' parameter"
    assert "backup_count:" in docstring, "Docstring should document 'backup_count' parameter"
    assert "enable_cache:" in docstring, "Docstring should document 'enable_cache' parameter"

    # Check that parameter descriptions are meaningful
    assert "Path to the storage file" in docstring, "path parameter should be described"
    assert "gzip compression" in docstring or "compression" in docstring, (
        "compression parameter should be described"
    )
    assert "backup" in docstring.lower(), "backup_count parameter should be described"
    assert "cache" in docstring.lower(), "enable_cache parameter should be described"


def test_filestorage_init_all_parameters_work():
    """Verify that FileStorage.__init__ accepts all documented parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with all parameters
        storage = FileStorage(
            path=f"{tmpdir}/test.json",
            compression=True,
            backup_count=5,
            enable_cache=True
        )

        # Verify all attributes are set correctly
        assert storage.compression is True
        assert storage.backup_count == 5
        assert storage._cache_enabled is True
        assert str(storage.path).endswith('.json.gz')


def test_filestorage_init_default_parameters():
    """Verify that FileStorage.__init__ works with default parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with default parameters
        storage = FileStorage(path=f"{tmpdir}/test.json")

        # Verify defaults
        assert storage.compression is False
        assert storage.backup_count == 0
        assert storage._cache_enabled is False
        assert not str(storage.path).endswith('.gz')


def test_issue_760_false_positive():
    """Confirm that Issue #760 is a false positive.

    The issue claimed the code was truncated at:
    'path: Path to the sto'

    This test confirms that the docstring is actually complete and contains
    the full text 'Path to the storage file.' not 'Path to the sto'.
    """
    docstring = FileStorage.__init__.__doc__

    # The issue claimed it was truncated at "sto", but it should say "storage file"
    assert "Path to the storage file" in docstring, (
        "Docstring should contain complete text 'Path to the storage file', "
        "not truncated at 'Path to the sto' as claimed in Issue #760"
    )

    # Verify the docstring is not truncated
    assert docstring.count('\n') > 3, "Docstring should be multi-line and complete"
    assert len(docstring) > 100, "Docstring should be substantial and complete"
