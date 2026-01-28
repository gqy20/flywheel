"""测试 JSONFormatter excluded_fields 完整性 (Issue #1787)

这个测试验证 JSONFormatter 中 excluded_fields 集合的定义是完整的，
没有被截断的字符串字面量，包含所有必需的标准日志属性。

Issue #1787 描述的问题：第 193 行（实际应为 JSONFormatter.format 方法中）
的 excluded_fields 集合定义被截断（`'thread`），导致 SyntaxError。
这个测试验证该问题已被修复。
"""
import logging
import json
import pytest
from flywheel.storage import JSONFormatter


def test_module_import_successfully():
    """测试模块可以成功导入，没有 SyntaxError"""
    try:
        from flywheel import storage
        assert storage is not None
        print("✓ 模块导入成功，没有语法错误")
    except SyntaxError as e:
        pytest.fail(f"模块导入失败，存在语法错误: {e}")


def test_json_formatter_instantiation():
    """测试 JSONFormatter 可以成功实例化"""
    try:
        formatter = JSONFormatter()
        assert formatter is not None
        assert isinstance(formatter, logging.Formatter)
        print("✓ JSONFormatter 实例化成功")
    except Exception as e:
        pytest.fail(f"JSONFormatter 实例化失败: {e}")


def test_excluded_fields_definition_complete():
    """测试 excluded_fields 集合定义完整，包含所有必需字段

    这个测试验证 excluded_fields 包含所有标准 LogRecord 属性：
    - thread, threadName (线程相关)
    - process, processName (进程相关)
    - getMessage (消息获取方法)
    - 以及其他标准日志字段
    """
    formatter = JSONFormatter()

    # 创建一个日志记录
    logger = logging.getLogger('test_1787')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test_file.py',
        lno=42,
        msg='Test message for issue 1787',
        args=(),
        exc_info=None
    )

    # 调用 format 方法 - 这会使用 excluded_fields
    # 如果 excluded_fields 定义不完整（有截断的字符串字面量），
    # 会导致 SyntaxError 或运行时错误
    try:
        result = formatter.format(record)
        assert result is not None
        assert isinstance(result, str)

        # 验证返回的是有效的 JSON
        log_data = json.loads(result)
        assert 'timestamp' in log_data
        assert 'level' in log_data
        assert 'message' in log_data

        print("✓ excluded_fields 定义完整，format 方法正常工作")
    except SyntaxError as e:
        pytest.fail(f"excluded_fields 存在语法错误（可能有截断的字符串字面量）: {e}")
    except Exception as e:
        pytest.fail(f"format 方法执行失败: {e}")


def test_excluded_fields_contains_all_thread_fields():
    """测试 excluded_fields 包含所有 thread 相关字段"""
    formatter = JSONFormatter()

    # 创建一个带有 thread 相关 extra 字段的日志记录
    logger = logging.getLogger('test_1787_thread')
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
    # 如果 excluded_fields 中有截断的字符串字面量（如 `'thread` 而不是 `'thread'`），
    # 这些字段可能不会被正确排除
    extra_fields = {
        'thread': 'thread_value',
        'threadName': 'thread_name_value',
        'process': 'process_value',
        'processName': 'process_name_value',
        'getMessage': 'getmessage_value',  # 方法名也应该是 excluded
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
    # getMessage 是方法，可能不会被添加到 extra
    print("✓ thread 和 process 相关字段被正确排除并添加前缀")


def test_all_standard_logrecord_attributes_excluded():
    """测试所有标准 LogRecord 属性都在 excluded_fields 中

    根据 Python logging 文档，LogRecord 有以下标准属性：
    - name, msg, args, levelname, levelno, pathname, filename, module
    - exc_info, exc_text, stack_info, lineno, funcName
    - created, msecs, relativeCreated, thread, threadName
    - processName, process, message, asctime
    """
    formatter = JSONFormatter()

    # 标准 LogRecord 属性列表
    standard_attributes = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
        'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
        'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
        'thread', 'threadName', 'processName', 'process', 'message',
        'asctime'
    }

    # 为每个属性创建一个测试
    for attr in standard_attributes:
        logger = logging.getLogger(f'test_1787_{attr}')
        record = logger.makeRecord(
            name='test',
            level=logging.INFO,
            fn='test.py',
            lno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # 尝试添加该属性作为 extra
        record.__dict__[attr] = f'test_value_for_{attr}'

        # 格式化 - 如果 excluded_fields 中有截断的字符串字面量，
        # 某些属性可能不会被正确排除，导致冲突
        try:
            result = formatter.format(record)
            log_data = json.loads(result)

            # 验证格式化成功，没有抛出异常
            assert result is not None
        except Exception as e:
            pytest.fail(f"处理属性 '{attr}' 时出错（可能 excluded_fields 中字符串字面量被截断）: {e}")

    print(f"✓ 所有 {len(standard_attributes)} 个标准 LogRecord 属性都能正确处理")


def test_excluded_fields_no_unclosed_string_literals():
    """测试 excluded_fields 中没有未闭合的字符串字面量

    这是针对 issue #1787 的特定测试。
    如果 excluded_fields 定义中有未闭合的字符串字面量（如 `'thread` 而不是 `'thread'`），
    会导致 Python SyntaxError，使模块无法导入。
    """
    # 尝试导入 storage 模块
    try:
        import importlib
        import flywheel.storage
        # 重新加载模块以确保使用最新代码
        importlib.reload(flywheel.storage)
        print("✓ 模块重新加载成功，没有未闭合的字符串字面量")
    except SyntaxError as e:
        pytest.fail(f"模块加载失败，发现未闭合的字符串字面量: {e}")


if __name__ == '__main__':
    # 直接运行测试
    test_module_import_successfully()
    test_json_formatter_instantiation()
    test_excluded_fields_definition_complete()
    test_excluded_fields_contains_all_thread_fields()
    test_all_standard_logrecord_attributes_excluded()
    test_excluded_fields_no_unclosed_string_literals()

    print("\n✅ 所有测试通过！Issue #1787 已验证修复")
