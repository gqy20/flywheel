"""Test for Issue #996 - Verify regex patterns are precompiled.

This test ensures that regex patterns in cli.py are precompiled at module
load time to prevent ReDoS (Regular Expression Denial of Service) attacks.

Issue: #996
"""

import re
import sys
from pathlib import Path

# Add src to path so we can import flywheel module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import flywheel.cli as cli_module


def test_regex_patterns_are_precompiled():
    """Test that regex patterns used in remove_control_chars are precompiled.

    This test checks for precompiled regex patterns at module level.
    Precompiled patterns improve performance and prevent ReDoS attacks
    by ensuring the regex engine doesn't re-parse patterns on every call.

    Security: Addresses Issue #996 - ReDoS prevention through regex precompilation
    """
    # Check that common regex patterns are defined as compiled patterns at module level
    # Look for precompiled patterns (they should be re.Pattern objects)

    # The regex pattern from line 121 that should be precompiled:
    # r'[\u200B-\u200D\u2060\uFEFF]'
    zero_width_pattern = r'[\u200B-\u200D\u2060\uFEFF]'

    # Check if this pattern exists as a precompiled constant in the module
    # We expect to find compiled patterns at module level
    module_vars = vars(cli_module)

    # Look for compiled regex patterns
    compiled_patterns = {
        name: value for name, value in module_vars.items()
        if isinstance(value, re.Pattern) and not name.startswith('_')
    }

    # Verify that the zero-width characters pattern is precompiled
    zero_width_found = False
    for pattern_name, pattern_obj in compiled_patterns.items():
        if pattern_obj.pattern == zero_width_pattern:
            zero_width_found = True
            break

    # This assertion should FAIL initially, motivating the fix
    assert zero_width_found, (
        f"Regex pattern '{zero_width_pattern}' should be precompiled at module level. "
        f"Found {len(compiled_patterns)} compiled patterns: {list(compiled_patterns.keys())}"
    )


def test_bidirectional_override_pattern_precompiled():
    """Test that bidirectional override regex pattern is precompiled."""
    bidirectional_pattern = r'[\u202A-\u202E\u2066-\u2069]'

    module_vars = vars(cli_module)
    compiled_patterns = {
        name: value for name, value in module_vars.items()
        if isinstance(value, re.Pattern) and not name.startswith('_')
    }

    bidirectional_found = False
    for pattern_name, pattern_obj in compiled_patterns.items():
        if pattern_obj.pattern == bidirectional_pattern:
            bidirectional_found = True
            break

    assert bidirectional_found, (
        f"Regex pattern '{bidirectional_pattern}' should be precompiled at module level"
    )


def test_remove_control_chars_still_works():
    """Ensure remove_control_chars function still works after refactoring."""
    test_string = "Hello\u200B\u200C\u200DWorld\x00\x1F"
    result = cli_module.remove_control_chars(test_string)

    # Should remove zero-width characters and control characters
    assert "\u200B" not in result
    assert "\u200C" not in result
    assert "\u200D" not in result
    assert "\x00" not in result
    assert "\x1F" not in result
    assert "HelloWorld" in result
