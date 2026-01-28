"""
Tests for Issue #739: 正则表达式字符类中包含未转义的连字符

这个测试确保 sanitize_string 函数中的正则表达式不会因为未转义的连字符
而产生意外的字符范围匹配。
"""

import pytest
from flywheel.cli import sanitize_string


class TestRegexHyphenEscaping:
    """测试正则表达式中连字符的正确转义"""

    def test_dangerous_chars_are_removed(self):
        """测试所有危险字符都被正确移除"""
        # 包含所有需要移除的危险字符
        dangerous_input = "test;semi|pipe&amp`dollar$(paren)<less>{brace}"
        result = sanitize_string(dangerous_input)
        # 所有危险字符应该被移除
        assert ";" not in result
        assert "|" not in result
        assert "&" not in result
        assert "`" not in result
        assert "$" not in result
        assert "(" not in result
        assert ")" not in result
        assert "<" not in result
        assert ">" not in result
        assert "{" not in result
        assert "}" not in result

    def test_hyphen_preserved_when_safe(self):
        """测试安全的连字符被保留"""
        # 带连字符的正常文本
        safe_input = "user-name_123"
        result = sanitize_string(safe_input)
        assert result == "user-name_123"

    def test_hyphen_in_brace_context(self):
        """测试花括号被移除但连字符保留"""
        # {- 组合中 { 应该被移除，但连字符应该保留
        input_with_brace_hyphen = "test{-value"
        result = sanitize_string(input_with_brace_hyphen)
        assert "{" not in result  # 花括号应该被移除
        assert "-" in result  # 连字符应该保留（根据 Issue #725）
        assert result == "test-value"

    def test_range_not_created_by_unescaped_hyphen(self):
        """
        测试未转义的连字符不会创建意外的字符范围

        如果正则表达式 r'[;|&`$()<>{}{-]' 被错误解释，
        它可能会创建一个范围匹配意外的字符。
        这个测试确保没有意外的字符被移除。
        """
        # 测试范围边界附近的字符
        test_input = "abc123XYZ!@#%"
        result = sanitize_string(test_input)
        # 这些字符都不应该被移除（它们不在危险字符列表中）
        assert "a" in result
        assert "Z" in result
        assert "0" in result
        assert "!" in result

    def test_multiple_hyphens_in_safe_context(self):
        """测试多个连字符在安全上下文中被保留"""
        input_with_hyphens = "test-value-with-many-hyphens"
        result = sanitize_string(input_with_hyphens)
        assert result == "test-value-with-many-hyphens"
