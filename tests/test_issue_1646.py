"""Tests for Issue #1646 - JSONFormatter.format 方法缺少返回值处理"""

import logging
import pytest
from flywheel.storage import JSONFormatter


class TestJSONFormatterErrorHandling:
    """测试 JSONFormatter 的错误处理能力"""

    def test_format_with_non_serializable_object(self, caplog):
        """测试当日志包含不可序列化对象时，format 方法应该优雅处理"""
        formatter = JSONFormatter()

        # 创建一个包含不可序列化对象的日志记录
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message with object",
            args=(),
            exc_info=None,
        )

        # 添加一个不可序列化的对象（例如自定义类实例）
        class CustomObject:
            def __str__(self):
                return "custom_object"

        record.custom_field = CustomObject()

        # 这应该不会抛出异常，而是返回一个有效的 JSON 字符串
        result = formatter.format(record)

        # 验证返回的是一个有效的 JSON 字符串
        assert result is not None
        assert isinstance(result, str)

        # 验证可以解析为 JSON
        import json
        parsed = json.loads(result)
        assert parsed is not None
        assert 'message' in parsed or 'custom_field' in parsed

    def test_format_with_circular_reference(self, caplog):
        """测试当日志包含循环引用时，format 方法应该优雅处理"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # 创建循环引用
        obj = {}
        obj['self'] = obj
        record.circular = obj

        # 这应该不会抛出异常
        result = formatter.format(record)

        # 验证返回结果
        assert result is not None
        assert isinstance(result, str)

    def test_format_with_lambda(self, caplog):
        """测试当日志包含 lambda 函数时，format 方法应该优雅处理"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # 添加 lambda 函数
        record.func = lambda x: x + 1

        # 这应该不会抛出异常
        result = formatter.format(record)

        # 验证返回结果
        assert result is not None
        assert isinstance(result, str)

    def test_format_normal_case(self, caplog):
        """测试正常情况下 format 方法应该正常工作"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # 验证返回结果
        assert result is not None
        assert isinstance(result, str)

        # 验证可以解析为 JSON
        import json
        parsed = json.loads(result)
        assert parsed['message'] == "Test message"
