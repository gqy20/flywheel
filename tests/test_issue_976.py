"""测试修复 Issue #976 - 反斜杠在 general 上下文中不应被移除."""

import pytest
from flywheel.cli import sanitize_for_security_context


def test_backslash_preserved_in_general_context():
    """测试反斜杠在 'general' 上下文中应被保留."""
    # Windows 路径测试
    windows_path = r"C:\Users\test\file.txt"
    result = sanitize_for_security_context(windows_path, context="general")
    assert "\\" in result, f"反斜杠应在 general 上下文中被保留, 但得到: {result}"
    assert result == "C:Users estfile.txt" or result == r"C:\Users\test\file.txt"

    # 转义字符测试
    escaped_text = "Line 1\\nLine 2"
    result = sanitize_for_security_context(escaped_text, context="general")
    assert "\\" in result, f"反斜杠转义应被保留, 但得到: {result}"

    # 相对路径测试
    relative_path = "..\\..\\config\\settings.json"
    result = sanitize_for_security_context(relative_path, context="general")
    assert "\\" in result, f"相对路径中的反斜杠应被保留, 但得到: {result}"


def test_backslash_removed_in_security_contexts():
    """测试反斜杠在安全敏感上下文中应被移除."""
    # URL 上下文应移除反斜杠
    url = "http://example.com\\path"
    result = sanitize_for_security_context(url, context="url")
    assert "\\" not in result, f"反斜杠应在 URL 上下文中被移除, 但得到: {result}"

    # filename 上下文应移除反斜杠
    filename = "file\\name.txt"
    result = sanitize_for_security_context(filename, context="filename")
    assert "\\" not in result, f"反斜杠应在 filename 上下文中被移除, 但得到: {result}"

    # shell 上下文应移除反斜杠
    shell_arg = "arg\\ument"
    result = sanitize_for_security_context(shell_arg, context="shell")
    assert "\\" not in result, f"反斜杠应在 shell 上下文中被移除, 但得到: {result}"
