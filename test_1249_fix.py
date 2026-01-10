#!/usr/bin/env python3
"""Quick test to verify Issue #1249 fix."""

import sys
sys.path.insert(0, 'src')

from flywheel.cli import sanitize_for_security_context
import shlex

# Test cases
test_cases = [
    ("test\x00\x01\x02string", "teststring"),
    ("line1\nline2\nline3", "line1line2line3"),
    ("echo $HOME\nwhoami", "echo $HOMEwhoami"),
    ("cmd1; cmd2\x00cmd3 | cmd4\ncmd5", "cmd1; cmd2cmd3 | cmd4cmd5"),
]

print("Testing Issue #1249 fix:\n")
all_passed = True

for test_input, expected_cleaned in test_cases:
    result = sanitize_for_security_context(test_input, context="shell")
    expected = shlex.quote(expected_cleaned)

    if result == expected:
        print(f"✓ PASS: {repr(test_input)} → {repr(result)}")
    else:
        print(f"✗ FAIL: {repr(test_input)}")
        print(f"  Expected: {repr(expected)}")
        print(f"  Got:      {repr(result)}")
        all_passed = False

print("\n" + "="*60)
if all_passed:
    print("All tests PASSED! ✓")
    sys.exit(0)
else:
    print("Some tests FAILED! ✗")
    sys.exit(1)
