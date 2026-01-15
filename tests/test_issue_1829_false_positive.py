"""Test for Issue #1829 - FALSE POSITIVE ReDoS risk in FORMAT_STRING_PATTERN.

This test verifies that the reported ReDoS vulnerability in FORMAT_STRING_PATTERN
is a FALSE POSITIVE because:

1. FORMAT_STRING_PATTERN is defined but NEVER USED in the codebase
2. The pattern itself [\\%{}] is a simple character class with no backtracking risk
3. Even if it were used, max_length limits prevent DoS attacks

The scanner incorrectly flagged this as a vulnerability without checking if
the pattern is actually used in any regex operations (search, sub, match, etc.).

Related issues:
    #1829 (false positive - pattern not used)
    #1304 (previous false positive - pattern already safe)
    #1334 (previous false positive - pattern already safe)
"""

import re
import time
import pytest


def test_format_string_pattern_not_used():
    """Test that FORMAT_STRING_PATTERN is defined but NOT used in cli.py.

    This confirms that Issue #1829 is a FALSE POSITIVE - the pattern exists
    but is never called with any regex operations, so it cannot cause ReDoS.
    """
    import flywheel.cli as cli_module

    # Verify the pattern exists
    assert hasattr(cli_module, 'FORMAT_STRING_PATTERN'), \
        "FORMAT_STRING_PATTERN should be defined"

    pattern = cli_module.FORMAT_STRING_PATTERN
    assert isinstance(pattern, re.Pattern), \
        "FORMAT_STRING_PATTERN should be a compiled regex"

    # Read the source code to verify it's never used
    import inspect
    source = inspect.getsource(cli_module)

    # Count definitions vs usages
    definitions = source.count('FORMAT_STRING_PATTERN =')
    usages = source.count('FORMAT_STRING_PATTERN.')

    # The pattern should be defined once (definition)
    assert definitions == 1, \
        f"FORMAT_STRING_PATTERN should be defined exactly once, found {definitions}"

    # The pattern should NOT be used in any regex operations
    # (search, sub, match, findall, finditer, split, etc.)
    assert usages == 0, \
        f"FORMAT_STRING_PATTERN should not be used (found {usages} usages). " \
        f"Issue #1829 is a FALSE POSITIVE because the pattern is never called."

    # Verify the pattern is safe for future use
    # The pattern [\\%{}] matches literal characters only (no quantifiers, no alternation)
    assert pattern.pattern == r'[\\%{}]', \
        "Pattern should match backslash, percent, and curly braces"

    # Verify it's a simple character class (no nested quantifiers that cause ReDoS)
    pattern_str = pattern.pattern
    assert '*' not in pattern_str, \
        "Pattern should not contain Kleene star (quantifier)"
    assert '+' not in pattern_str, \
        "Pattern should not contain plus (quantifier)"
    assert '?' not in pattern_str, \
        "Pattern should not contain question mark (quantifier)"
    assert '{' not in pattern_str or pattern_str.startswith('['), \
        "If pattern contains {, it should only be in character class [..] as literal"


def test_format_string_pattern_no_redos_risk():
    """Test that FORMAT_STRING_PATTERN has no ReDoS vulnerability characteristics.

    Even though the pattern is not used, this test verifies that the pattern
    itself is safe and would not cause ReDoS even if used in the future.
    """
    import flywheel.cli as cli_module

    pattern = cli_module.FORMAT_STRING_PATTERN

    # Test with various inputs that could trigger ReDoS in vulnerable patterns
    test_cases = [
        # Long strings with mixed characters
        'a' * 10000 + '%' + 'b' * 10000,
        '{' * 10000 + '}' * 10000,
        '\\' * 10000 + '%' * 10000,

        # Alternating patterns that could cause backtracking
        ('{}' * 5000),
        ('%{}' * 5000),
        ('\\%{}' * 3333),

        # Edge cases
        '',
        '\\',
        '%',
        '{}',
        '\\%{}',
    ]

    for test_input in test_cases:
        # Time the regex operation - should complete instantly
        start = time.time()

        # search() - most common operation
        result = pattern.search(test_input)

        elapsed = time.time() - start

        # Should complete in under 1ms even for worst-case input
        # (vulnerable patterns can take seconds or minutes)
        assert elapsed < 0.001, \
            f"Pattern took {elapsed:.4f}s for input length {len(test_input)}, " \
            f"indicating potential ReDoS vulnerability. Input: {test_input[:50]}..."


def test_format_string_pattern_matches_correctly():
    """Test that FORMAT_STRING_PATTERN matches the intended characters.

    This verifies the pattern works correctly for its intended purpose
    (even though it's currently unused).
    """
    import flywheel.cli as cli_module

    pattern = cli_module.FORMAT_STRING_PATTERN

    # Should match these format string characters
    assert pattern.search('\\') is not None, "Should match backslash"
    assert pattern.search('%') is not None, "Should match percent"
    assert pattern.search('{') is not None, "Should match opening brace"
    assert pattern.search('}') is not None, "Should match closing brace"

    # Should match in strings containing these characters
    assert pattern.search('Use {var} for values') is not None
    assert pattern.search('50% complete') is not None
    assert pattern.search('C:\\Users\\path') is not None

    # Should NOT match safe characters
    assert pattern.search('abc') is None, "Should not match letters"
    assert pattern.search('123') is None, "Should not match digits"
    assert pattern.search('normal text') is None, "Should not match normal text"
    assert pattern.search('hello-world') is None, "Should not match hyphens"


def test_issue_1829_summary():
    """Summary test documenting why Issue #1829 is a FALSE POSITIVE.

    This test documents all the reasons why the ReDoS report is incorrect:
    1. Pattern is defined but NEVER USED
    2. Pattern is a simple character class with no backtracking risk
    3. Code has max_length limits preventing DoS
    4. Pattern has been reviewed multiple times (issues #1304, #1334)
    """
    import flywheel.cli as cli_module

    # Fact 1: Pattern exists but is unused
    assert hasattr(cli_module, 'FORMAT_STRING_PATTERN')
    import inspect
    source = inspect.getsource(cli_module)
    assert source.count('FORMAT_STRING_PATTERN.') == 0, \
        "Pattern is not used in any regex operations"

    # Fact 2: Pattern is a simple character class
    pattern = cli_module.FORMAT_STRING_PATTERN
    assert pattern.pattern == r'[\\%{}]', \
        "Pattern is [\\%{}] - matches 4 literal characters only"

    # Fact 3: No quantifiers or alternation that cause backtracking
    for quantifier in ['*', '+', '?', '{', '|']:
        # Only { in pattern is inside character class as literal
        if quantifier == '{':
            assert pattern.pattern.startswith('['), \
                "Curly braces in pattern are literal characters in character class"
        else:
            assert quantifier not in pattern.pattern, \
                f"Pattern should not contain {quantifier} (quantifier/alternation)"

    # Fact 4: Code has DoS protections
    assert hasattr(cli_module, 'MAX_LENGTH_HARD_LIMIT'), \
        "Code defines MAX_LENGTH_HARD_LIMIT to prevent DoS"
    assert cli_module.MAX_LENGTH_HARD_LIMIT == 1024 * 1024, \
        "Hard limit is 1MB, preventing memory exhaustion"

    # Conclusion: Issue #1829 is a FALSE POSITIVE
    # The scanner incorrectly flagged a safe, unused pattern as vulnerable
    assert True, "Issue #1829 is FALSE POSITIVE - pattern unused and safe"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
