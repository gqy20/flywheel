#!/usr/bin/env python
"""Test to verify issue #360 is a false positive."""

import ast
import sys

def test_storage_file_complete():
    """Verify that storage.py has no syntax errors and is complete."""
    try:
        with open('src/flywheel/storage.py', 'r') as f:
            code = f.read()
        # Try to parse the file as valid Python
        ast.parse(code)
        print("✅ PASS: storage.py is syntactically valid Python")
        return True
    except SyntaxError as e:
        print(f"❌ FAIL: Syntax error at line {e.lineno}: {e.msg}")
        return False

def test_line_229_complete():
    """Verify that line 229 and surrounding context are complete."""
    with open('src/flywheel/storage.py', 'r') as f:
        lines = f.readlines()

    # Line 229 is index 228 (0-based)
    line_229 = lines[228].strip()
    print(f"Line 229: {line_229}")

    # Check if line 229 ends the RuntimeError properly
    expected_end = '"Install pywin32: pip install pywin32"'
    if expected_end in line_229:
        print("✅ PASS: Line 229 completes the RuntimeError properly")
        return True
    else:
        print(f"❌ FAIL: Line 229 doesn't match expected pattern")
        return False

def test_context_around_229():
    """Check the context around line 229."""
    with open('src/flywheel/storage.py', 'r') as f:
        lines = f.readlines()

    # Show lines 220-235 (context around the issue)
    print("\nContext around line 229:")
    print("=" * 60)
    for i in range(219, min(235, len(lines))):
        print(f"{i+1:4d} | {lines[i]}", end='')
    print("=" * 60)

    # Verify the complete error raising structure
    context = ''.join(lines[222:229])  # Lines 223-229
    if 'raise RuntimeError(' in context and 'Install pywin32' in context:
        print("✅ PASS: Complete RuntimeError structure found")
        return True
    else:
        print("❌ FAIL: RuntimeError structure is incomplete")
        return False

if __name__ == '__main__':
    results = [
        test_storage_file_complete(),
        test_line_229_complete(),
        test_context_around_229()
    ]

    print(f"\n{'='*60}")
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print(f"{'='*60}")

    if all(results):
        print("\n✅ Issue #360 is a FALSE POSITIVE - code is complete and correct")
        sys.exit(0)
    else:
        print("\n❌ Issue #360 appears to be valid - code is incomplete")
        sys.exit(1)
