"""Test for issue #1024 - sanitize_for_security_context should preserve shell metachars in general mode."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1024:
    """Test that sanitize_for_security_context preserves shell metachars in general mode.

    Issue #1024: sanitize_for_security_context in 'general' mode should preserve
    shell metacharacters (semicolons, pipes, ampersands, backticks, dollar signs,
    parentheses, angle brackets) as they are legitimate characters in user text,
    as documented in Issue #979.

    These characters should only be removed in security-sensitive contexts
    ("shell", "url", "filename") where use_nfkc=True.
    """

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            # Semicolons are legitimate in text
            ("Note: this is important; remember it", "Note: this is important; remember it"),
            ("Item 1; Item 2; Item 3", "Item 1; Item 2; Item 3"),

            # Pipes are used in documentation
            ("Use | for separating options", "Use | for separating options"),
            ("A | B | C", "A | B | C"),

            # Ampersands in company names
            ("Johnson & Johnson", "Johnson & Johnson"),
            ("AT&T", "AT&T"),

            # Dollar signs for prices
            ("Cost: $100", "Cost: $100"),
            ("Price: $50.00", "Price: $50.00"),

            # Parentheses for references
            ("See chapter (5) for details", "See chapter (5) for details"),
            ("(note: important)", "(note: important)"),

            # Angle brackets for placeholders
            ("Enter your <name> here", "Enter your <name> here"),
            ("Replace <file> with path", "Replace <file> with path"),

            # Backticks for code
            ("Use `print('hello')` for output", "Use `print('hello')` for output"),
            ("Run `test.sh` to start", "Run `test.sh` to start"),

            # Mixed examples
            ("Cost: $100 (discount) & save; use `code` | see <docs>",
             "Cost: $100 (discount) & save; use `code` | see <docs>"),
        ]
    )
    def test_general_mode_preserves_shell_metachars(self, input_text, expected):
        """Test that general context preserves shell metacharacters."""
        result = sanitize_for_security_context(input_text, context="general")
        assert result == expected, (
            f"In general mode, expected '{expected}' but got '{result}'. "
            f"Shell metachars should be preserved in general context (Issue #1024)."
        )

    @pytest.mark.parametrize(
        "context,input_text,expected_chars_removed",
        [
            # In security contexts, shell metachars should be removed
            ("shell", "cmd; ls", ";"),
            ("shell", "ls | grep", "|"),
            ("shell", "a & b", "&"),
            ("shell", "echo `test`", "`"),
            ("shell", "cost $100", "$"),
            ("shell", "func(arg)", "()"),
            ("shell", "file > out", "><"),

            ("url", "page;param", ";"),
            ("url", "path/file", "/"),  # Note: / is not in SHELL_METACHARS_PATTERN but tested
            ("filename", "file;name", ";"),
        ]
    )
    def test_security_context_removes_shell_metachars(self, context, input_text, expected_chars_removed):
        """Test that security contexts remove shell metacharacters."""
        result = sanitize_for_security_context(input_text, context=context)
        # Verify that expected characters were removed
        for char in expected_chars_removed:
            assert char not in result, (
                f"In {context} mode, '{char}' should be removed but got '{result}'"
            )

    def test_general_mode_default_context(self):
        """Test that 'general' is the default context."""
        text = "Cost: $100; see (docs)"
        result = sanitize_for_security_context(text)  # No context specified
        assert result == text, "Default context should be 'general' and preserve shell metachars"
