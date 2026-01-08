"""测试 issue #1054 - 潜在的二次截断风险

这个测试验证 sanitize_for_security_context 函数能够安全地截断包含
多字节字符的字符串，不会在字符中间截断导致无效的 UTF-8 序列。
"""

import pytest
from flywheel.cli import sanitize_for_security_context


def test_truncation_with_multibyte_characters():
    """测试截断多字节字符时的安全性"""
    # 创建一个包含多字节字符的长字符串
    # 每个中文字符在 UTF-8 中占用 3 个字节
    # 每个表情符号可能占用 4 个字节
    test_string = "测试" * 1000  # 大约 9000 字节

    # 尝试截断到一个较短的长度
    result = sanitize_for_security_context(test_string, max_length=100)

    # 结果应该是有效的 UTF-8 字符串
    assert isinstance(result, str)

    # 尝试编码和解码以确保没有无效的 UTF-8 序列
    try:
        encoded = result.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert decoded == result
    except UnicodeError as e:
        pytest.fail(f"截断后的字符串包含无效的 UTF-8 序列: {e}")

    # 结果长度应该不超过 max_length
    assert len(result) <= 100


def test_truncation_with_emoji():
    """测试截断包含表情符号的字符串"""
    # 表情符号通常是代理对或 4 字节 UTF-8 序列
    test_string = "😀😃😄😁😆" * 100  # 大约 15000 字节

    result = sanitize_for_security_context(test_string, max_length=50)

    # 应该是有效的字符串
    assert isinstance(result, str)

    # 尝试编码和解码
    try:
        encoded = result.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert decoded == result
    except UnicodeError as e:
        pytest.fail(f"截断后的字符串包含无效的 UTF-8 序列: {e}")


def test_truncation_with_combining_characters():
    """测试截断包含组合字符的字符串"""
    # e + combining acute accent = é
    test_string = "e\u0301" * 100  # 组合字符序列

    result = sanitize_for_security_context(test_string, max_length=50)

    # 应该是有效的字符串
    assert isinstance(result, str)

    # 验证 NFC 规范化
    import unicodedata
    normalized = unicodedata.normalize('NFC', result)
    assert isinstance(normalized, str)


def test_truncation_preserves_valid_utf8():
    """测试截断后的字符串可以被安全地编码为 UTF-8"""
    test_cases = [
        "这是一个测试字符串" * 100,
        "Test😀with🎉emoji" * 50,
        "Mixеd😊сontent" * 100,
        "🌟🌟🌟" * 100,
    ]

    for test_string in test_cases:
        result = sanitize_for_security_context(test_string, max_length=100)

        # 验证可以被编码为 UTF-8
        try:
            encoded = result.encode('utf-8')
            # 验证可以解码回原始字符串
            decoded = encoded.decode('utf-8')
            assert decoded == result
        except UnicodeError as e:
            pytest.fail(f"字符串 '{test_string[:50]}...' 截断后产生无效的 UTF-8: {e}")


def test_truncation_at_exact_boundaries():
    """测试在特定边界长度下的截断"""
    # 创建一个可以测试多种边界情况的字符串
    test_string = "ABC测试😀XYZ"

    # 测试不同的截断点
    for max_len in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        result = sanitize_for_security_context(test_string, max_length=max_len)

        # 验证结果
        assert isinstance(result, str)
        assert len(result) <= max_len

        # 验证可以安全编码
        try:
            encoded = result.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert decoded == result
        except UnicodeError as e:
            pytest.fail(f"在 max_length={max_len} 时产生无效的 UTF-8: {e}")
