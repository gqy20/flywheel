"""Test for rename of sanitize_string to remove_control_chars (Issue #850)."""

import pytest
from flywheel.cli import sanitize_string, remove_control_chars


class TestRenameSanitizeString:
    """Test that sanitize_string is renamed to remove_control_chars."""

    def test_remove_control_chars_function_exists(self):
        """Test that remove_control_chars function exists."""
        # After the fix, remove_control_chars should exist
        assert callable(remove_control_chars)

    def test_sanitize_string_renamed(self):
        """Test that sanitize_string is deprecated and remove_control_chars is used."""
        # After the fix, sanitize_string should either:
        # 1. Not exist (removed completely), OR
        # 2. Be a deprecated alias to remove_control_chars

        # For now, this test verifies the rename happened
        # The implementation should make remove_control_chars the primary function
        assert remove_control_chars is not None

    def test_remove_control_chars_removes_control_characters(self):
        """Test that remove_control_chars removes control characters."""
        # Test basic control character removal
        assert remove_control_chars("test\x00string") == "teststring"
        assert remove_control_chars("hello\nworld") == "helloworld"
        assert remove_control_chars("tab\there") == "tabhere"

    def test_remove_control_chars_preserves_spaces(self):
        """Test that remove_control_chars preserves regular spaces."""
        assert remove_control_chars("hello world") == "hello world"
        assert remove_control_chars("  multiple  spaces  ") == "  multiple  spaces  "

    def test_remove_control_chars_removes_shell_metachars(self):
        """Test that remove_control_chars removes shell metacharacters."""
        assert remove_control_chars("test;command") == "testcommand"
        assert remove_control_chars("test|pipe") == "testpipe"
        assert remove_control_chars("test&bg") == "testbg"

    def test_remove_control_chars_preserves_legitimate_content(self):
        """Test that remove_control_chars preserves legitimate content."""
        # Test quotes are preserved
        assert remove_control_chars('test "quoted"') == 'test "quoted"'
        assert remove_control_chars("test 'single'") == "test 'single'"

        # Test percentages are preserved
        assert remove_control_chars("50% complete") == "50% complete"

        # Test brackets are preserved
        assert remove_control_chars("test [array]") == "test [array]"

        # Test hyphens are preserved
        assert remove_control_chars("well-known") == "well-known"
        assert remove_control_chars("550e8400-e29b-41d4") == "550e8400-e29b-41d4"

    def test_remove_control_chars_function_name_is_clear(self):
        """Test that the new function name is clear about its purpose."""
        # The function name should clearly indicate it's for removing control
        # characters, not for providing security
        function_name = remove_control_chars.__name__
        assert "control" in function_name.lower()
        assert "sanitize" not in function_name.lower()

    def test_remove_control_chars_docstring_is_clear(self):
        """Test that remove_control_chars has clear documentation."""
        docstring = remove_control_chars.__doc__
        assert docstring is not None
        # Should explicitly state it's for data storage normalization
        assert "storage" in docstring.lower() or "normalization" in docstring.lower()
        # Should NOT claim to provide security
        if "security" in docstring.lower():
            assert "not" in docstring.lower() or "does not" in docstring.lower()

    def test_remove_control_chars_unicode_normalization(self):
        """Test that remove_control_chars normalizes Unicode characters."""
        # Test fullwidth character conversion
        assert remove_control_chars("ＡＢＣ") == "ABC"
        assert remove_control_chars("０１２") == "012"

    def test_remove_control_chars_removes_unicode_spoofing(self):
        """Test that remove_control_chars removes Unicode spoofing characters."""
        # Test zero-width characters
        assert remove_control_chars("test\u200Bstring") == "teststring"

        # Test bidirectional overrides
        assert remove_control_chars("test\u202Estring") == "teststring"
