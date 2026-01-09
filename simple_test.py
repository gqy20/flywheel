import sys
sys.path.insert(0, '/home/runner/work/flywheel/flywheel')

from src.flywheel.cli import sanitize_for_security_context

# Test the format context
result1 = sanitize_for_security_context("{", context="format")
print(f"'{{' -> '{result1}' (expected: '{{{{')")

result2 = sanitize_for_security_context("}", context="format")
print(f"'}}' -> '{result2}' (expected: '}}}}')")

result3 = sanitize_for_security_context("%", context="format")
print(f"'%' -> '{result3}' (expected: '%%')")

result4 = sanitize_for_security_context("\\", context="format")
print(f"'\\' -> '{result4}' (expected: '\\\\')")

result5 = sanitize_for_security_context("Use {var} for 100%", context="format")
print(f"'Use {{var}} for 100%' -> '{result5}' (expected: 'Use {{{{var}}}} for 100%%')")

# Verify all tests pass
if result1 == "{{" and result2 == "}}" and result3 == "%%" and result4 == "\\\\" and result5 == "Use {{var}} for 100%%":
    print("\n✓ All tests passed! Issue #1169 is already fixed.")
    sys.exit(0)
else:
    print("\n✗ Some tests failed!")
    sys.exit(1)
