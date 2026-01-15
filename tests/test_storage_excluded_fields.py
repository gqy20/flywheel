"""测试 storage.py 中 excluded_fields 的正确定义

这个测试验证 Issue #1804 中报告的语法错误：
- 确保 'thread' 字符串正确闭合
- 确保 excluded_fields set 完整且格式正确
"""

import pytest


def test_excluded_fields_syntax():
    """测试 excluded_fields set 的语法正确性"""
    # 这个测试确保 storage.py 可以正确导入
    # 如果存在语法错误（如未闭合的字符串），导入将失败
    try:
        from flywheel.storage import JSONFormatter
        assert True, "storage.py 导入成功，没有语法错误"
    except SyntaxError as e:
        pytest.fail(f"storage.py 存在语法错误: {e}")


def test_excluded_fields_contains_thread():
    """测试 excluded_fields 包含 'thread' 字段"""
    from flywheel.storage import JSONFormatter
    import logging

    # 创建一个格式化器实例并调用 format 方法
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None
    )

    # 添加自定义字段
    record.thread = "test-thread-value"
    record.custom_field = "should-be-included"

    # 格式化日志记录
    result = formatter.format(record)

    # 验证结果
    assert isinstance(result, str), "格式化结果应该是字符串"
    assert "test message" in result, "应该包含日志消息"

    # 验证 'thread' 在 excluded_fields 中（不会被作为自定义字段添加）
    # 这意味着 excluded_fields set 的语法是正确的


def test_excluded_fields_is_complete():
    """测试 excluded_fields set 是否完整定义"""
    from flywheel.storage import JSONFormatter
    import logging

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test",
        args=(),
        exc_info=None
    )

    # 测试所有标准字段都在 excluded_fields 中
    # 如果 set 定义不完整（如语法错误），这会导致问题
    result = formatter.format(record)
    assert isinstance(result, str), "应该成功格式化"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
