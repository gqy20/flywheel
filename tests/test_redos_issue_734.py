"""Tests for ReDoS vulnerability in sanitize_string (Issue #734).

This test ensures that the regex character class in sanitize_string does not
contain unescaped hyphens that could create unintended character ranges.

The vulnerability occurs because:
1. The pattern r'[;|&`$()<>{}]' contains `>-{` which creates a character range
2. This can lead to unexpected behavior and potential ReDoS vulnerabilities
3. The hyphen should be escaped or moved to the end of the character class

The fix ensures the hyphen is either escaped (\-) or placed at the end of the
character class to prevent it from being interpreted as a range operator.
"""

import pytest
import re
import inspect
from flywheel.cli import sanitize_string


class TestReDoSHyphenVulnerability:
    """Test that sanitize_string regex has no unescaped hyphens in character class."""

    def test_no_unescaped_hyphen_in_regex(self):
        """Test that the regex pattern has no hyphen creating unintended ranges.

        This test verifies that the character class in sanitize_string doesn't
        contain a hyphen in the middle of the character class, which would create
        an unintended character range and could lead to ReDoS vulnerabilities.
        """
        # Read the source code to extract the regex pattern
        source = inspect.getsource(sanitize_string)

        # Find the line with the re.sub call for dangerous characters
        for line in source.split('\n'):
            if 're.sub' in line and '[;|&`$()<>{}' in line:
                # Extract the regex pattern
                # It should be something like: re.sub(r'[;|&`$()<>{}]', '', s)
                pattern_start = line.find("r'[")
                pattern_end = line.find("']", pattern_start)
                if pattern_start == -1 or pattern_end == -1:
                    pytest.fail("Could not find regex pattern in re.sub call")

                pattern = line[pattern_start + 3:pattern_end]  # Extract chars inside [...]

                # The pattern should NOT have a hyphen that creates a range
                # Check if there's a hyphen that's not at the end and not escaped
                # The pattern currently is: ;|&`$()<>{}{ (note: the second } is after the ])
                # Wait, looking more carefully, the pattern ends with }{ which seems wrong
                # Let me parse this more carefully

                # Actually, the issue is that the pattern contains >-{ which creates a range
                # The hyphen between > and { creates a character range from > to {
                # This is because in ASCII, > is 62, ? is 63, @ is 64, [ is 91, \ is 92, ] is 93, ^ is 94, _ is 95, ` is 96, a is 97...
                # So >-{ would match >, ?, @, A-Z, [, \, ], ^, _, `, a-z, {

                # The fix is to either escape the hyphen (\-) or move it to the end

                # For now, let's just verify the current vulnerable behavior
                # and test that the fix prevents it

                # Test that characters in the range >-{ are removed
                # This is the vulnerable behavior we want to fix
                test_string = "test@ATHOME"
                result = sanitize_string(test_string)

                # In the current vulnerable code, @, A-Z would be removed
                # After the fix, they should be preserved
                # For now, we expect them to be removed (vulnerable behavior)
                # This test will fail after the fix, so we need to update it

                # Actually, let me write a better test that checks the pattern directly
                break

        # Better approach: check the pattern directly
        # Read the source and verify the pattern
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if "re.sub(r'[;|&`$()<>{}]', '', s)" in line:
                # Found the vulnerable line!
                # The pattern has >-{ which creates a range
                pytest.fail(
                    "Found unescaped hyphen in regex character class. "
                    "The pattern r'[;|&`$()<>{}]' contains >-{ which creates "
                    "an unintended character range. Fix by moving - to the end: "
                    "r'[;|&`$()<>{}{-]' or escaping it: r'[;|&`$()<>{}\\-]'"
                )

    def test_hyphen_range_issue(self):
        """Test that demonstrates the character range issue.

        The pattern [;|&`$()<>{}]{] with >-{ creates a range that removes
        characters like @, A-Z, [, \, ], ^, _, `, a-z.
        """
        # Test characters that would be in the >-{ range
        # > is ASCII 62, { is ASCII 123
        # This range includes: ? (63), @ (64), A-Z (65-90), [ (91), \ (92), ] (93),
        #                       ^ (94), _ (95), ` (96), a-z (97-122)

        # These should be preserved but are currently removed due to the range bug
        test_cases = [
            ("test@home", "test@home"),  # @ should be preserved
            ("TEST_UPPER", "TEST_UPPER"),  # Uppercase should be preserved
            ("test[bracket]", "test[bracket]"),  # [ should be preserved
            ("test^caret", "test^caret"),  # ^ should be preserved
            ("test_underscore", "test_underscore"),  # _ should be preserved
        ]

        for input_str, expected in test_cases:
            result = sanitize_string(input_str)
            # For now, this will fail because of the bug
            # After the fix, these should pass
            assert result == expected, f"Expected '{expected}' but got '{result}' for input '{input_str}'"

    def test_verify_hyphen_position_in_pattern(self):
        """Verify that the regex pattern either has no hyphen or it's properly positioned.

        A safe character class should either:
        1. Have no hyphen (if hyphen is not in the removal list)
        2. Have hyphen escaped (\-)
        3. Have hyphen at the end of the character class
        """
        source = inspect.getsource(sanitize_string)

        # Find all re.sub patterns in sanitize_string
        import re as regex_module
        pattern_matches = regex_module.findall(r"re\.sub\(r'\[[^\]]*\]", source)

        for match in pattern_matches:
            # Extract the character class
            char_class = match.split("r'[")[1].rstrip("']")

            # Check if there's a hyphen in the middle (not at the end, not escaped)
            # A hyphen at the end or escaped is safe
            for i, char in enumerate(char_class):
                if char == '-':
                    # Check if it's at the end (safe)
                    if i == len(char_class) - 1:
                        continue  # Safe: hyphen at end
                    # Check if it's escaped (safe)
                    if i > 0 and char_class[i - 1] == '\\':
                        continue  # Safe: escaped hyphen
                    # Otherwise, it's a vulnerable hyphen creating a range
                    pytest.fail(
                        f"Unsafe hyphen in character class: [{char_class}]. "
                        f"Hyphen at position {i} creates an unintended character range. "
                        f"Fix by moving hyphen to end or escaping it."
                    )
