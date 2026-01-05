#!/usr/bin/env python3
"""Test current behavior of sanitize_string."""

import sys
sys.path.insert(0, '/home/runner/work/flywheel/flywheel/src')

from flywheel.cli import sanitize_string

# Test cases
test_cases = [
    ("hello;world", "helloworld"),  # semicolon
    ("hello|world", "helloworld"),  # pipe
    ("hello&world", "helloworld"),  # ampersand
    ("hello`world", "helloworld"),  # backtick
    ("hello$world", "helloworld"),  # dollar
    ("hello(world)", "helloworld"),  # parentheses
    ("hello<world>", "helloworld"),  # angle brackets
    ("hello{world}", "helloworld"),  # curly braces
    ("hello\\world", "helloworld"),  # backslash
    ("hello\nworld", "helloworld"),  # newline
    ("hello\tworld", "helloworld"),  # tab
]

print("Testing current sanitize_string implementation:")
print("=" * 60)

all_passed = True
for input_str, expected in test_cases:
    result = sanitize_string(input_str)
    passed = result == expected
    all_passed = all_passed and passed

    status = "✓" if passed else "✗"
    print(f"{status} Input: {repr(input_str)}")
    print(f"  Expected: {repr(expected)}")
    print(f"  Got:      {repr(result)}")
    if not passed:
        print(f"  FAILED!")
    print()

print("=" * 60)
if all_passed:
    print("All tests passed!")
else:
    print("Some tests failed!")
