#!/usr/bin/env python3
"""Validate that issue #322 is a false positive."""

import ast
from pathlib import Path


def validate():
    """Validate that line 227 is NOT truncated."""
    storage_path = Path("src/flywheel/storage.py")

    if not storage_path.exists():
        print("✗ storage.py file not found")
        return False

    # Read the file and get line 227 (1-indexed, so index 226)
    lines = storage_path.read_text().splitlines()
    line_227 = lines[226]  # 0-indexed

    print(f"Line 227 content: '{line_227}'")

    # The issue claimed this line was truncated to "Bui" or incomplete
    # Verify the line is complete and contains the expected code
    if "dc_parts" not in line_227:
        print("✗ Line 227 appears to be incomplete (missing 'dc_parts')")
        return False

    if "startswith('DC=')" not in line_227:
        print("✗ Line 227 appears to be incomplete (missing domain extraction logic)")
        return False

    # Verify the file has valid Python syntax
    source_code = storage_path.read_text()
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        print(f"✗ storage.py has syntax error at line {e.lineno}: {e}")
        return False

    print("✓ Line 227 is NOT truncated")
    print("✓ Domain extraction logic is complete")
    print("✓ Code has valid Python syntax")
    print("✓ Issue #322 is a FALSE POSITIVE")
    return True


if __name__ == "__main__":
    success = validate()
    exit(0 if success else 1)
