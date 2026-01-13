"""Test for issue #1622: Ensure no duplicate class definitions."""

import ast
import re
from pathlib import Path


def test_no_duplicate_aiofiles_protocol():
    """Test that _AiofilesProtocol is defined only once in storage.py.

    This test checks for the duplicate class definition reported in issue #1622.
    The _AiofilesProtocol class should only be defined once, not twice.
    """
    storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_file.read_text()

    # Count occurrences of class _AiofilesProtocol definition
    pattern = r'^class _AiofilesProtocol\(Protocol\):'
    matches = re.findall(pattern, content, re.MULTILINE)

    # Assert that the class is defined exactly once
    assert len(matches) == 1, (
        f"_AiofilesProtocol class is defined {len(matches)} times. "
        f"It should be defined only once to avoid code duplication."
    )


def test_no_duplicate_aiofiles_comments():
    """Test that aiofiles import comments are not duplicated.

    This test checks for the duplicate import comments reported in issue #1622.
    """
    storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_file.read_text()

    # Count occurrences of the specific comment block
    comment_pattern = r"# Import aiofiles with fallback for graceful degradation \(Issue #1032\)"
    matches = re.findall(comment_pattern, content)

    # Assert that the comment appears exactly once
    assert len(matches) == 1, (
        f"Aiofiles import comment appears {len(matches)} times. "
        f"It should appear only once to avoid code duplication."
    )


def test_storage_file_syntax():
    """Test that storage.py has valid Python syntax after removing duplicates."""
    storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_file.read_text()

    # Try to parse the file as valid Python
    try:
        ast.parse(content)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error: {e}")
