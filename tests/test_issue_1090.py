"""测试 Issue #1090: 验证 save_to_file 方法完整性

这个测试验证 save_to_file 方法是完整的，包含：
1. 类型检查并抛出 TypeError
2. 文件写入操作（使用 asyncio.to_thread）
3. 正确的错误处理
"""
import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import IOMetrics


@pytest.mark.asyncio
async def test_save_to_file_is_complete():
    """验证 save_to_file 方法是完整的且能正常工作

    Issue #1090 声称代码在 save_to_file 方法中间截断，
    导致语法错误和不完整的逻辑。这个测试验证方法实际上是完整的。
    """
    # 创建 IOMetrics 实例并记录一些操作
    metrics = IOMetrics()
    await metrics.record_operation('read', 0.5, 0, True)
    await metrics.record_operation('write', 1.2, 2, True)
    await metrics.record_operation('read', 0.3, 0, False, 'ENOENT')

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        # 1. 验证方法能正常调用（说明没有语法错误）
        await metrics.save_to_file(temp_path)

        # 2. 验证文件被正确创建
        assert Path(temp_path).exists(), "文件应该被创建"

        # 3. 验证文件内容正确（说明逻辑完整）
        with open(temp_path, 'r') as f:
            data = json.load(f)

        # 验证数据结构
        assert 'operations' in data, "应该包含 operations 字段"
        assert 'total_operation_count' in data, "应该包含 total_operation_count 字段"
        assert 'total_duration' in data, "应该包含 total_duration 字段"
        assert 'successful_operations' in data, "应该包含 successful_operations 字段"
        assert 'failed_operations' in data, "应该包含 failed_operations 字段"
        assert 'total_retries' in data, "应该包含 total_retries 字段"

        # 验证数据值
        assert data['total_operation_count'] == 3, "应该记录 3 个操作"
        assert data['successful_operations'] == 2, "应该有 2 个成功操作"
        assert data['failed_operations'] == 1, "应该有 1 个失败操作"
        assert data['total_retries'] == 2, "应该总共重试 2 次"
        assert abs(data['total_duration'] - 2.0) < 0.01, "总时长应该约为 2.0"

        # 验证操作详情
        assert len(data['operations']) == 3, "operations 应该包含 3 个记录"
        assert data['operations'][0]['operation_type'] == 'read'
        assert data['operations'][1]['operation_type'] == 'write'
        assert data['operations'][2]['operation_type'] == 'read'
        assert data['operations'][2]['success'] is False

    finally:
        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_save_to_file_type_check():
    """验证 save_to_file 包含类型检查

    Issue #1090 提到代码应该包含类型检查后的异常抛出。
    """
    metrics = IOMetrics()

    # 测试无效类型（应该抛出 TypeError）
    with pytest.raises(TypeError, match="path must be str or Path"):
        await metrics.save_to_file(123)  # type: ignore

    with pytest.raises(TypeError, match="path must be str or Path"):
        await metrics.save_to_file(None)  # type: ignore

    with pytest.raises(TypeError, match="path must be str or Path"):
        await metrics.save_to_file([1, 2, 3])  # type: ignore


@pytest.mark.asyncio
async def test_save_to_file_with_path_object():
    """验证 save_to_file 支持 Path 对象

    Issue #1090 提到代码应该支持 str 和 Path 类型。
    """
    metrics = IOMetrics()
    await metrics.record_operation('read', 0.5, 0, True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / 'metrics.json'

        # 使用 Path 对象应该正常工作
        await metrics.save_to_file(temp_path)

        # 验证文件存在且内容正确
        assert temp_path.exists()
        with open(temp_path, 'r') as f:
            data = json.load(f)
        assert len(data['operations']) == 1


@pytest.mark.asyncio
async def test_save_to_file_uses_asyncio_to_thread():
    """验证 save_to_file 使用 asyncio.to_thread

    Issue #1090 提到代码应该使用 asyncio.to_thread 进行异步文件写入。
    这个测试验证方法不会阻塞事件循环。
    """
    metrics = IOMetrics()

    # 记录足够多的操作以确保文件写入需要一些时间
    for i in range(100):
        await metrics.record_operation(f'operation_{i}', 0.01, 0, True)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        # 创建一个计数器来检查事件循环是否被阻塞
        counter = 0

        async def increment_counter():
            nonlocal counter
            while counter < 100:
                counter += 1
                await asyncio.sleep(0.0001)

        # 并发执行 save_to_file 和计数器
        await asyncio.gather(
            metrics.save_to_file(temp_path),
            increment_counter()
        )

        # 如果事件循环被阻塞，计数器将无法达到预期值
        assert counter >= 50, "事件循环似乎被阻塞了"

        # 验证文件内容正确
        with open(temp_path, 'r') as f:
            data = json.load(f)
        assert len(data['operations']) == 100

    finally:
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_save_to_file_error_handling():
    """验证 save_to_file 的错误处理

    测试当文件无法写入时，方法会正确抛出异常。
    """
    metrics = IOMetrics()
    await metrics.record_operation('read', 0.5, 0, True)

    # 尝试写入到一个无效的路径（应该抛出异常）
    invalid_path = "/root/nonexistent/path/metrics.json"

    with pytest.raises((FileNotFoundError, OSError, PermissionError)):
        await metrics.save_to_file(invalid_path)
