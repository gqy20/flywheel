#!/usr/bin/env python3
"""Simple test to check if sanitize_string removes dangerous characters."""

import sys
sys.path.insert(0, '/home/runner/work/flywheel/flywheel/src')

try:
    from flywheel.cli import sanitize_string

    # Test basic dangerous characters
    test = "hello;world"
    result = sanitize_string(test)
    print(f"Input: {repr(test)}")
    print(f"Output: {repr(result)}")
    print(f"Expected: 'helloworld'")
    print(f"Match: {result == 'helloworld'}")
    print()

    # Test semicolon specifically (the issue mentions this)
    test2 = "test; rm -rf /"
    result2 = sanitize_string(test2)
    print(f"Input: {repr(test2)}")
    print(f"Output: {repr(result2)}")
    print(f"Semicolon removed: {';' not in result2}")
    print()

    # Test backslash
    test3 = "test\\evil"
    result3 = sanitize_string(test3)
    print(f"Input: {repr(test3)}")
    print(f"Output: {repr(result3)}")
    print(f"Backslash removed: {'\\\\' not in result3}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
