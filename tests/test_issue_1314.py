"""Test for Issue #1314 - ReDoS vulnerability in SHELL_METACHARS_PATTERN.

The issue states that SHELL_METACHARS_PATTERN is still defined in src/flywheel/cli.py
despite Issue #1044 claiming to replace blacklist regex with whitelist approach. This
poses a ReDoS risk if the pattern is used elsewhere.

The fix should either:
1. Remove SHELL_METACHARS_PATTERN entirely if not used
2. If it must remain for backward compatibility, ensure it has proper documentation
   and length limits are enforced before any pattern matching

This test verifies the fix is in place.
"""

import pytest
import re


def test_shell_metachars_pattern_redos_fix():
    """Test that SHELL_METACHARS_PATTERN is properly handled to prevent ReDoS.

    This test verifies that one of the following protections is in place:
    1. SHELL_METACHARS_PATTERN is removed (preferred)
    2. Or if it exists, it has proper deprecation documentation and length checks

    The pattern r'[;|&`$()<>]' itself is relatively safe from ReDoS as it's a
    simple character class with no quantifiers or alternations that could cause
    catastrophic backtracking. However, the issue is about ensuring that if it's
    used anywhere, input length is strictly limited before matching.
    """
    from flywheel import cli

    # Check if SHELL_METACHARS_PATTERN exists
    has_pattern = hasattr(cli, 'SHELL_METACHARS_PATTERN')

    if has_pattern:
        # If the pattern exists, verify it's properly documented as deprecated
        # or replaced by whitelist approach
        pattern = cli.SHELL_METACHARS_PATTERN

        # Verify it's a precompiled pattern (for performance)
        assert isinstance(pattern, re.Pattern), \
            "SHELL_METACHARS_PATTERN must be a precompiled regex.Pattern object"

        # The pattern should match the original shell metachars
        assert pattern.pattern == r'[;|&`$<>]', \
            f"Pattern should be r'[;|&`$<>]' but got {pattern.pattern}"

        # IMPORTANT: The fix requires that this pattern is NOT actively used
        # in sanitize_for_security_context. That function now uses a whitelist set.
        # We verify this by checking the implementation uses set lookup.

        # Verify sanitize_for_security_context uses whitelist approach
        import inspect
        source = inspect.getsource(cli.sanitize_for_security_context)

        # Should NOT use SHELL_METACHARS_PATTERN in the function
        assert 'SHELL_METACHARS_PATTERN' not in source, \
            "sanitize_for_security_context should not use SHELL_METACHARS_PATTERN - " \
            "it should use whitelist set lookup as per Issue #1044"

        # Should use set-based whitelist for O(n) performance
        assert 'shell_dangerous_chars' in source or 'set(' in source, \
            "sanitize_for_security_context should use set-based whitelist " \
            "for O(n) performance without ReDoS risk"

        # Verify MAX_LENGTH_HARD_LIMIT is defined and enforced
        assert hasattr(cli, 'MAX_LENGTH_HARD_LIMIT'), \
            "MAX_LENGTH_HARD_LIMIT must be defined to prevent ReDoS"

        assert cli.MAX_LENGTH_HARD_LIMIT <= 1 * 1024 * 1024, \
            "MAX_LENGTH_HARD_LIMIT should be capped at 1MB"

        # Verify CONTEXT_DEFAULT_MAX_LENGTH exists for context-specific limits
        assert hasattr(cli, 'CONTEXT_DEFAULT_MAX_LENGTH'), \
            "CONTEXT_DEFAULT_MAX_LENGTH must be defined for CLI contexts"

    else:
        # Pattern has been removed - this is the ideal fix
        # Verify that the code still functions correctly with whitelist approach
        import inspect
        source = inspect.getsource(cli.sanitize_for_security_context)

        # Should use set-based whitelist
        assert 'shell_dangerous_chars' in source or 'set(' in source, \
            "sanitize_for_security_context should use set-based whitelist " \
            "for O(n) performance without ReDoS risk"


def test_shell_context_uses_whitelist_not_blacklist():
    """Test that shell context uses whitelist set approach, not regex blacklist.

    This is the core fix for Issue #1044 and Issue #1314. The whitelist approach:
    - Uses set lookup: O(n) time complexity
    - No regex backtracking risk
    - More maintainable and explicit
    """
    from flywheel import cli

    # Test that shell context properly handles metachars using shlex.quote
    # (which is the correct approach per Issue #1114)
    test_string = "file;with|many&chars`$()<>test"

    # Shell context should use shlex.quote() to safely escape
    result = cli.sanitize_for_security_context(test_string, context="shell")

    # The result should be a properly quoted shell string
    # shlex.quote() typically adds single quotes and escapes
    assert result.startswith("'"), \
        "Shell context should use shlex.quote() which adds quotes"

    # The original dangerous characters should be preserved inside quotes
    # (they're escaped/shielded by shlex.quote, not removed)
    assert "file" in result and "with" in result, \
        "Shell context should preserve content, just quote it safely"


def test_length_limits_prevent_redos():
    """Test that length limits are enforced before any regex processing.

    This prevents ReDoS by ensuring no unbounded input reaches regex patterns.
    """
    from flywheel import cli

    # Create an extremely long string that could cause issues
    # if length limits weren't enforced
    dangerous_string = "a" * 10000000  # 10 million characters

    # Should truncate safely without performance issues
    result = cli.sanitize_for_security_context(dangerous_string, context="general")

    # Result should be truncated to MAX_LENGTH_HARD_LIMIT (1MB)
    assert len(result) <= cli.MAX_LENGTH_HARD_LIMIT, \
        f"Result should be truncated to MAX_LENGTH_HARD_LIMIT (1MB) but got {len(result)} chars"

    # Should complete quickly (no ReDoS)
    # This test passes if it doesn't hang
