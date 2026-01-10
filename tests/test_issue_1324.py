"""测试 Issue #1324 - general 上下文不应移除格式化字符串字符

这个测试验证 sanitize_for_security_context 的 'general' 上下文应该
保留用户数据中的 {, }, %, \ 字符，而不是移除它们。

Issue #1324 指出：
- 当前的 'general' 上下文会移除这些字符以防止格式化字符串注入
- 但这会破坏用户数据（如 'Progress: 50%' 变为 'Progress: 50'）
- 与函数声称的 'preserve user intent'（保留用户意图）相悖
"""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestGeneralContextPreservesFormatChars:
    """测试 general 上下文应该保留格式化字符串字符"""

    def test_percent_sign_preserved_in_general_context(self):
        """百分号应该在 general 上下文中被保留"""
        # 用户数据：进度百分比
        input_str = "Progress: 50%"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == "Progress: 50%", f"Expected 'Progress: 50%', got '{result}'"

    def test_curly_braces_preserved_in_general_context(self):
        """花括号应该在 general 上下文中被保留"""
        # 用户数据：包含花括号的文本
        input_str = "Use {key} for configuration"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == "Use {key} for configuration", f"Expected braces preserved, got '{result}'"

    def test_backslash_preserved_in_general_context(self):
        """反斜杠应该在 general 上下文中被保留"""
        # 用户数据：Windows 路径
        input_str = "Path: C:\\Users\\Documents"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == "Path: C:\\Users\\Documents", f"Expected backslashes preserved, got '{result}'"

    def test_combined_format_chars_preserved(self):
        """多个格式化字符组合应该被保留"""
        # 用户数据：包含多种格式化字符的复杂文本
        input_str = "Template: {name} - {value}% (use \\n for newline)"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == "Template: {name} - {value}% (use \\n for newline)", \
            f"Expected all format chars preserved, got '{result}'"

    def test_format_context_still_escapes_chars(self):
        """format 上下文应该仍然转义这些字符（回归测试）"""
        # 确保 format 上下文的行为没有改变
        input_str = "Use {var} for 100%"
        result = sanitize_for_security_context(input_str, context="format")
        assert result == "Use {{var}} for 100%%", f"Expected escaped format, got '{result}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
