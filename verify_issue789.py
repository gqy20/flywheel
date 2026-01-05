#!/usr/bin/env python3
"""Verification script for Issue #789.

This script verifies whether the sanitize_string function in cli.py
properly implements the regex replacement logic to remove dangerous
characters as required by Issue #789.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flywheel.cli import sanitize_string

def test_dangerous_chars():
    """Test that dangerous characters are removed."""
    print("=" * 70)
    print("Testing Issue #789: Regex replacement for dangerous characters")
    print("=" * 70)
    print()

    test_cases = [
        ("Shell metacharacters", [
            ("hello;world", "helloworld", "semicolon"),
            ("hello|world", "helloworld", "pipe"),
            ("hello&world", "helloworld", "ampersand"),
            ("hello`world", "helloworld", "backtick"),
            ("hello$world", "helloworld", "dollar"),
            ("hello(world)", "helloworld", "parentheses"),
            ("hello<world>", "helloworld", "angle brackets"),
            ("hello{world}", "helloworld", "curly braces"),
            ("hello\\world", "helloworld", "backslash"),
        ]),
        ("Control characters", [
            ("hello\nworld", "helloworld", "newline"),
            ("hello\tworld", "helloworld", "tab"),
            ("hello\rworld", "helloworld", "carriage return"),
            ("hello\x00world", "helloworld", "null byte"),
        ]),
        ("Combined attacks", [
            ("test;cmd|evil&bad`rm${}\n\t\\",
             "testcmdevilbadrm",
             "combined dangerous characters"),
        ]),
    ]

    all_passed = True
    total_tests = 0
    passed_tests = 0

    for category, tests in test_cases:
        print(f"Category: {category}")
        print("-" * 70)

        for input_str, expected, description in tests:
            total_tests += 1
            result = sanitize_string(input_str)
            passed = result == expected

            if passed:
                passed_tests += 1
                print(f"  ✓ {description}")
                print(f"    Input:    {repr(input_str)}")
                print(f"    Expected: {repr(expected)}")
                print(f"    Got:      {repr(result)}")
            else:
                all_passed = False
                print(f"  ✗ {description}")
                print(f"    Input:    {repr(input_str)}")
                print(f"    Expected: {repr(expected)}")
                print(f"    Got:      {repr(result)}")
                print(f"    FAILED!")
            print()

    print("=" * 70)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print("=" * 70)

    if all_passed:
        print("\n✓ All tests passed! Issue #789 is already FIXED.")
        print("  The regex replacement logic is present and working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed! Issue #789 needs to be fixed.")
        return 1

if __name__ == "__main__":
    sys.exit(test_dangerous_chars())
