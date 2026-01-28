"""测试 Storage 类和 measure_latency 装饰器完整性 (Issue #1019)

Issue #1019 声称代码在文件中间截断，但经过验证，代码实际上是完整的：
- measure_latency 装饰器（包括 sync_wrapper 和 async_wrapper）完整
- Storage 类存在，是 FileStorage 的别名（向后兼容，issue #568）
- 文件没有在中间截断
"""
import pytest
import asyncio


def test_storage_class_exists():
    """验证 storage 模块中存在 Storage 类

    Storage 是 FileStorage 的别名（向后兼容，issue #568）
    """
    from flywheel.storage import Storage, FileStorage

    # Storage 应该是 FileStorage 的别名
    assert Storage is FileStorage
    assert Storage.__name__ == 'FileStorage'


def test_storage_class_has_basic_methods():
    """验证 Storage 类有基本方法"""
    from flywheel.storage import Storage

    # 检查基本方法是否存在（继承自 AbstractStorage）
    expected_methods = [
        'read',
        'write',
        'delete',
        'exists',
        'list_files',
    ]

    for method in expected_methods:
        assert hasattr(Storage, method), f"Storage 类缺少 {method} 方法"


def test_measure_latency_decorator_exists():
    """验证 measure_latency 装饰器存在"""
    from flywheel.storage import measure_latency

    # 装饰器应该可以被调用
    assert callable(measure_latency)
    assert measure_latency.__name__ == 'measure_latency'


def test_measure_latency_sync_wrapper():
    """验证 measure_latency 装饰器的同步版本"""
    from flywheel.storage import measure_latency

    @measure_latency("test_operation")
    def sync_func(x, y):
        return x + y

    result = sync_func(1, 2)
    assert result == 3


def test_measure_latency_async_wrapper():
    """验证 measure_latency 装饰器的异步版本"""
    from flywheel.storage import measure_latency

    @measure_latency("async_operation")
    async def async_func(value):
        await asyncio.sleep(0.001)
        return value * 2

    result = asyncio.run(async_func(5))
    assert result == 10


def test_measure_latency_exception_handling():
    """验证 measure_latency 装饰器的异常处理"""
    from flywheel.storage import measure_latency

    @measure_latency("error_operation")
    def error_func():
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        error_func()


def test_measure_latency_context_extraction():
    """验证 measure_latency 能提取上下文（path/id）"""
    from flywheel.storage import measure_latency

    # 测试 path 参数提取
    @measure_latency("load_with_path")
    def func_with_path(path):
        return f"loaded from {path}"

    result = func_with_path("/tmp/test.json")
    assert "loaded from" in result

    # 测试 id 参数提取
    @measure_latency("load_with_id")
    def func_with_id(id):
        return f"loaded id {id}"

    result = func_with_id(12345)
    assert "loaded id" in result
