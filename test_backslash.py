#!/usr/bin/env python
"""Quick test of backslash removal in sanitize_string."""

from src.flywheel.cli import sanitize_string

# Test cases
test_cases = [
    ("hello\\nworld", "hellonworld"),
    ("C:\\Users\\test\\file.txt", "C:Users estfile.txt"),
    ("path\\", "path"),
    ("it\\'s", "its"),
    ("say \\"hello\\"", "say hello"),
]

print("Testing sanitize_string backslash removal:")
print("-" * 50)

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

if all_passed:
    print("✓ All tests passed!")
else:
    print("✗ Some tests failed!")
