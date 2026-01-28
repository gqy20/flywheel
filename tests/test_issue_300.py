"""Test for Issue #300 - Verify code is complete and not truncated.

This test validates that the storage.py file is complete and has no
truncated code or comments, refuting the incorrect issue report.
"""

from pathlib import Path
import ast


def test_storage_file_syntax_is_valid():
    """Verify that storage.py has valid Python syntax (no truncated code)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_path.read_text()

    # Parse as Python to verify syntax is valid
    # This will fail if code is truncated or has syntax errors
    try:
        ast.parse(content)
    except SyntaxError as e:
        raise AssertionError(
            f"storage.py has syntax error (code may be truncated as claimed in issue #300): {e}"
        )


def test_issue_239_comment_is_complete():
    """Verify that the Issue #239 comment is complete (not truncated to #23)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_path.read_text()

    # The issue claimed line 223 had "Issue #23" truncated
    # But it actually has "Issue #239" complete
    assert 'Issue #239' in content, "Issue #239 reference should be complete"

    # Find the exact line
    lines = content.split('\n')
    for i, line in enumerate(lines, start=1):
        if 'Use minimal permissions instead of FILE_ALL_ACCESS' in line:
            # Verify the full issue number is present
            assert 'Issue #239' in line, \
                f"Line {i} should have complete 'Issue #239' reference"
            # Verify it's NOT truncated
            assert not line.strip().endswith('(Issue #23'), \
                f"Line {i} should not be truncated with just 'Issue #23'"
            print(f"✓ Line {i} is complete: {line.strip()}")
            break


def test_secure_directory_method_is_complete():
    """Verify that _secure_directory method is complete with all brackets closed."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_path.read_text()

    # Parse the file to check structure
    tree = ast.parse(content)

    # Find the Storage class
    storage_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Storage":
            storage_class = node
            break

    assert storage_class is not None, "Storage class not found"

    # Find _secure_directory method
    secure_dir_method = None
    for item in storage_class.body:
        if isinstance(item, ast.FunctionDef) and item.name == "_secure_directory":
            secure_dir_method = item
            break

    assert secure_dir_method is not None, "_secure_directory method not found"

    # Verify method has a body (not empty or just pass/ellipsis)
    assert len(secure_dir_method.body) > 1, \
        "_secure_directory should have a complete implementation"

    # Verify proper structure
    assert secure_dir_method.returns is not None, \
        "_secure_directory should have return type annotation"

    print(f"✓ _secure_directory method is complete with {len(secure_dir_method.body)} statements")


def test_line_247_is_not_problematic():
    """The issue claimed line 247 had truncated code, but it's actually just a blank line."""
    storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    lines = storage_file.read_text().split('\n')

    # Line 247 (index 246) should be blank or valid code
    line_247 = lines[246]  # 0-indexed

    # It's either a blank line or valid code
    assert not line_247.strip().endswith('(Issue #23'), \
        f"Line 247 should not have truncated issue reference"

    print(f"✓ Line 247 is valid: {repr(line_247)}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
