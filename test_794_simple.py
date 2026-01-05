#!/usr/bin/env python3
"""Simple test script for Issue #794 fix."""

import sys
sys.path.insert(0, 'src')

from flywheel.cli import sanitize_string

def test_basic():
    """Test basic Latin characters are preserved."""
    print("Testing basic Latin characters...")
    result = sanitize_string("admin")
    assert result == "admin", f"Expected 'admin', got '{result}'"
    print("✓ Basic Latin works")

def test_latin_extended():
    """Test Latin extended characters are preserved."""
    print("\nTesting Latin extended characters...")
    test_cases = [
        ("āăąĉċč", "Latin Extended-A"),
        ("ƀƁƂ", "Latin Extended-B"),
        ("ḁḃḅ", "Latin Extended Additional"),
        ("ⱠⱡⱢ", "Latin Extended-C"),
        ("꜠꜡Ꜣ", "Latin Extended-D"),
        ("ꝰꝱꝲ", "Latin Extended-E"),
        ("àñü", "Latin-1 Supplement"),
    ]

    for chars, name in test_cases:
        result = sanitize_string(chars)
        if result == chars:
            print(f"✓ {name}: {chars} preserved")
        else:
            print(f"✗ {name}: Expected '{chars}', got '{result}'")
            return False

    return True

def test_cyrillic_blocked():
    """Test that Cyrillic characters are blocked."""
    print("\nTesting Cyrillic blocking...")
    # Cyrillic 'а' looks like Latin 'a' but should be blocked
    result = sanitize_string("аdmin")
    if result == "dmin":
        print("✓ Cyrillic 'а' blocked, Latin 'dmin' preserved")
        return True
    else:
        print(f"✗ Expected 'dmin', got '{result}'")
        return False

def test_mathematical_blocked():
    """Test that mathematical symbols are blocked."""
    print("\nTesting mathematical symbol blocking...")
    # Mathematical bold capital A (U+1D400)
    math_a = "𝐀"
    result = sanitize_string(math_a)
    if result == "":
        print(f"✓ Mathematical symbol blocked")
        return True
    else:
        print(f"✗ Expected empty, got '{result}'")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Issue #794 Fix: Unicode Script Filtering")
    print("=" * 60)

    tests = [
        test_basic,
        test_latin_extended,
        test_cyrillic_blocked,
        test_mathematical_blocked,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test() is False:
                failed += 1
            else:
                passed += 1
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
