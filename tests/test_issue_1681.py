"""
测试 Issue #1681: 序列化回退方法未定义

测试当日志数据包含非 JSON 可序列化的对象时，
_make_serializable 方法能够正确处理。
"""

import json
import logging
from io import StringIO
from flywheel.storage import StorageContextFormatter


class NonSerializableObject:
    """一个不可 JSON 序列化的测试对象"""
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"NonSerializableObject({self.value})"


def test_make_serializable_method_exists():
    """测试 _make_serializable 方法存在"""
    formatter = StorageContextFormatter()
    assert hasattr(formatter, '_make_serializable'), \
        "_make_serializable 方法应该存在"


def test_format_with_non_serializable_object():
    """测试格式化包含不可序列化对象的日志记录"""
    # 创建 formatter
    formatter = StorageContextFormatter()

    # 创建一个包含不可序列化对象的日志记录
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message with non-serializable object',
        args=(),
        exc_info=None
    )

    # 添加一个不可序列化的对象到日志记录中
    record.custom_object = NonSerializableObject("test_value")

    # 格式化日志记录
    try:
        result = formatter.format(record)

        # 验证结果可以被 JSON 解析
        parsed = json.loads(result)

        # 验证不可序列化对象被转换为字符串
        assert 'custom_object' in parsed
        assert isinstance(parsed['custom_object'], str)
        assert 'NonSerializableObject' in parsed['custom_object']

    except AttributeError as e:
        if '_make_serializable' in str(e):
            raise AssertionError(
                "_make_serializable 方法未定义。"
                "请实现该方法以处理非 JSON 可序列化的对象。"
            )
        raise


def test_format_with_nested_non_serializable_objects():
    """测试格式化包含嵌套不可序列化对象的日志记录"""
    formatter = StorageContextFormatter()

    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message with nested non-serializable objects',
        args=(),
        exc_info=None
    )

    # 添加包含嵌套不可序列化对象的字典
    record.nested_data = {
        'simple': 'value',
        'object': NonSerializableObject("nested"),
        'list': [1, 2, NonSerializableObject("in_list")]
    }

    result = formatter.format(record)

    # 验证结果可以被 JSON 解析
    parsed = json.loads(result)

    # 验证嵌套结构中的不可序列化对象被转换
    assert 'nested_data' in parsed
    assert parsed['nested_data']['simple'] == 'value'
    assert 'NonSerializableObject' in parsed['nested_data']['object']
    assert 'NonSerializableObject' in parsed['nested_data']['list'][2]


def test_format_with_various_non_serializable_types():
    """测试格式化包含各种不可序列化类型的日志记录"""
    formatter = StorageContextFormatter()

    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message with various non-serializable types',
        args=(),
        exc_info=None
    )

    # 添加各种不可序列化的类型
    record.set_obj = {1, 2, 3}  # set 不可序列化
    record.complex_obj = complex(1, 2)  # complex 不可序列化
    record.custom_obj = NonSerializableObject("test")

    result = formatter.format(record)

    # 验证结果可以被 JSON 解析
    parsed = json.loads(result)

    # 验证所有类型都被转换为字符串
    assert 'set_obj' in parsed
    assert 'complex_obj' in parsed
    assert 'custom_obj' in parsed
    assert isinstance(parsed['set_obj'], str)
    assert isinstance(parsed['complex_obj'], str)
    assert isinstance(parsed['custom_obj'], str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
