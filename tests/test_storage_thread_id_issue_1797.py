"""测试 JSONFormatter 包含 thread_id 字段 (Issue #1797).

这个测试验证：
1. JSONFormatter 输出包含 thread_id 字段
2. thread_id 的值是线程标识符
3. threading 模块被正确使用
"""

import json
import logging
import threading
import pytest


def test_json_formatter_contains_thread_id():
    """测试 JSONFormatter 输出包含 thread_id 字段"""
    from flywheel.storage import JSONFormatter

    # 创建一个格式化器实例
    formatter = JSONFormatter()

    # 创建日志记录
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None
    )

    # 格式化日志记录
    result = formatter.format(record)

    # 解析 JSON 输出
    log_data = json.loads(result)

    # 验证 thread_id 字段存在
    assert 'thread_id' in log_data, "JSON 输出应该包含 'thread_id' 字段"

    # 验证 thread_id 是整数（线程标识符）
    assert isinstance(log_data['thread_id'], int), "thread_id 应该是整数类型"

    # 验证 thread_id 是当前线程的标识符
    assert log_data['thread_id'] == threading.get_ident(), "thread_id 应该等于当前线程的标识符"


def test_json_formatter_thread_id_excluded_from_custom_fields():
    """测试 thread 和 threadName 字段被正确排除在自定义字段之外"""
    from flywheel.storage import JSONFormatter

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

    # 尝试添加 thread 和 threadName 作为自定义字段
    record.thread = "custom-thread"
    record.threadName = "custom-thread-name"

    # 格式化日志记录
    result = formatter.format(record)

    # 解析 JSON 输出
    log_data = json.loads(result)

    # 验证 thread_id 字段存在（来自 threading.get_ident()）
    assert 'thread_id' in log_data, "应该包含 thread_id 字段"

    # 验证自定义的 thread 和 threadName 被排除
    # 它们不应该出现在 JSON 中（因为它们在 excluded_fields 中）
    assert 'thread' not in log_data or log_data.get('thread') != "custom-thread", \
        "自定义的 'thread' 字段应该被排除"


def test_json_formatter_threading_module_used():
    """测试 JSONFormatter 使用 threading 模块获取线程 ID"""
    from flywheel.storage import JSONFormatter

    # 验证 threading 模块可以被正确导入
    import threading
    assert hasattr(threading, 'get_ident'), "threading 模块应该有 get_ident 方法"

    # 创建格式化器并验证它使用 threading.get_ident()
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

    result = formatter.format(record)
    log_data = json.loads(result)

    # 验证 thread_id 的值等于 threading.get_ident() 的返回值
    expected_thread_id = threading.get_ident()
    assert log_data['thread_id'] == expected_thread_id, \
        "thread_id 应该使用 threading.get_ident() 获取"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
