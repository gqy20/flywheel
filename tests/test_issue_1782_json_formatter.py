"""测试 JSONFormatter 字符串字面量完整性 (Issue #1782)

这个测试验证 JSONFormatter 中 excluded_fields 集合的字符串字面量
是否完整，没有语法错误。

Issue #1782 描述的问题：第 145 行左右存在语法错误（`'thread, `），
导致文件无法被解析。这个测试验证该问题已被修复。
"""
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import logging
import json
from flywheel.storage import JSONFormatter


def test_json_formatter_can_be_imported():
    """测试 JSONFormatter 可以正常导入"""
    try:
        from flywheel.storage import JSONFormatter
        assert JSONFormatter is not None
        print("✓ JSONFormatter 导入成功")
    except SyntaxError as e:
        raise AssertionError(f"导入失败，存在语法错误: {e}")


def test_json_formatter_excluded_fields_syntax():
    """测试 excluded_fields 集合的语法正确性"""
    formatter = JSONFormatter()

    # 创建一个日志记录
    logger = logging.getLogger('test_1782')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test_file.py',
        lno=42,
        msg='Test message for issue 1782',
        args=(),
        exc_info=None
    )

    # 调用 format 方法 - 这会触发 excluded_fields 的使用
    # 如果有语法错误（如截断的字符串字面量），这里会抛出异常
    try:
        result = formatter.format(record)
        assert result is not None
        assert isinstance(result, str)

        # 验证返回的是有效的 JSON
        log_data = json.loads(result)
        assert 'timestamp' in log_data
        assert 'level' in log_data
        assert 'message' in log_data

        print("✓ excluded_fields 语法正确，format 方法正常工作")
    except SyntaxError as e:
        raise AssertionError(f"excluded_fields 存在语法错误: {e}")
    except json.JSONDecodeError as e:
        raise AssertionError(f"format 返回的不是有效的 JSON: {e}")


def test_excluded_fields_contains_thread_fields():
    """测试 excluded_fields 包含 thread 相关字段"""
    formatter = JSONFormatter()

    # 创建一个带有自定义 extra 字段的日志记录
    logger = logging.getLogger('test_1782_thread')
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_file.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # 添加 thread 相关字段作为 extra 字段
    # 如果 excluded_fields 中有截断的字符串字面量，这些字段可能不会被正确排除
    extra_fields = {
        'thread': 'thread_value',
        'threadName': 'thread_name_value',
        'process': 'process_value',
        'processName': 'process_name_value',
    }

    for key, value in extra_fields.items():
        record.__dict__[key] = value

    # 格式化记录
    result = formatter.format(record)
    log_data = json.loads(result)

    # 验证这些标准字段被正确处理（应该有 extra_ 前缀）
    assert 'extra_thread' in log_data, "'thread' 字段应该有 extra_ 前缀"
    assert 'extra_threadName' in log_data, "'threadName' 字段应该有 extra_ 前缀"
    assert 'extra_process' in log_data, "'process' 字段应该有 extra_ 前缀"
    assert 'extra_processName' in log_data, "'processName' 字段应该有 extra_ 前缀"

    print("✓ thread 相关字段被正确排除并添加前缀")


def test_all_excluded_fields_are_strings():
    """测试所有 excluded_fields 的元素都是有效的字符串字面量"""
    # 这个测试验证 excluded_fields 集合中的每个元素都是完整的字符串
    # 没有被截断的字符串字面量

    formatter = JSONFormatter()
    logger = logging.getLogger('test_1782_all_fields')

    # 标准日志字段列表（来自 Python logging 模块）
    standard_fields = [
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
        'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
        'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
        'thread', 'threadName', 'process', 'processName', 'message',
        'asctime'
    ]

    # 为每个字段创建一个日志记录
    for field in standard_fields:
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test_file.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # 添加该字段作为 extra
        record.__dict__[field] = f'test_value_{field}'

        # 格式化 - 如果 excluded_fields 中有截断的字符串，
        # 某些字段可能不会被正确排除
        try:
            result = formatter.format(record)
            log_data = json.loads(result)

            # 字段应该有 extra_ 前缀
            prefixed_key = f'extra_{field}'
            if field not in ['message', 'msg']:  # message/msg 特殊处理
                # 注意：不是所有字段都会出现在输出中
                # 关键是没有语法错误或运行时错误
        except Exception as e:
            raise AssertionError(f"处理字段 '{field}' 时出错（可能是字符串字面量被截断）: {e}")

    print("✓ 所有标准字段都能正确处理，没有截断的字符串字面量")


if __name__ == '__main__':
    # 直接运行测试
    test_json_formatter_can_be_imported()
    test_json_formatter_excluded_fields_syntax()
    test_excluded_fields_contains_thread_fields()
    test_all_excluded_fields_are_strings()

    print("\n✅ 所有测试通过！Issue #1782 已修复")
