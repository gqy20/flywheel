"""测试 Issue #1721 - 验证 JSONFormatter._make_serializable 方法存在且工作正常

这个测试验证 JSONFormatter 类确实有 _make_serializable 方法定义，
并且该方法能够正确地将非 JSON 可序列化的对象转换为可序列化的字符串。
"""
import json
import logging
from flywheel.storage import JSONFormatter


def test_make_serializable_method_exists():
    """验证 _make_serializable 方法存在"""
    formatter = JSONFormatter()
    assert hasattr(formatter, '_make_serializable'), \
        "JSONFormatter 应该有 _make_serializable 方法"


def test_make_serializable_with_non_serializable_objects():
    """验证 _make_serializable 能处理非 JSON 可序列化的对象"""
    formatter = JSONFormatter()

    # 创建包含非可序列化对象的日志数据
    class CustomClass:
        def __str__(self):
            return "CustomClass instance"

    log_data = {
        'string': 'test',
        'number': 42,
        'custom_object': CustomClass(),
        'lambda': lambda x: x + 1,
        'nested_dict': {
            'inner_object': CustomClass(),
        }
    }

    # 调用 _make_serializable
    result = formatter._make_serializable(log_data)

    # 验证结果可以被 JSON 序列化
    json_output = json.dumps(result)
    assert json_output is not None

    # 验证非可序列化对象被转换为字符串
    assert 'CustomClass instance' in result['custom_object']
    assert '<function' in result['lambda'] or 'lambda' in result['lambda']


def test_json_formatter_integration():
    """验证 JSONFormatter 在完整流程中正确处理非可序列化对象"""
    formatter = JSONFormatter()

    # 创建日志记录
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # 添加非可序列化的额外字段
    class CustomClass:
        def __str__(self):
            return "CustomObject"

    record.custom_object = CustomClass()
    record.normal_field = 'normal_value'

    # 格式化日志 - 这应该调用 _make_serializable
    output = formatter.format(record)

    # 验证输出是有效的 JSON
    parsed = json.loads(output)
    assert 'custom_object' in parsed or 'extra_custom_object' in parsed
    assert parsed.get('normal_field') or parsed.get('extra_normal_field') == 'normal_value'


if __name__ == '__main__':
    test_make_serializable_method_exists()
    test_make_serializable_with_non_serializable_objects()
    test_json_formatter_integration()
    print("✅ 所有测试通过")
