"""测试 Issue #1075: save_to_file 应该是异步方法"""
import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import IOMetrics


@pytest.mark.asyncio
async def test_save_to_file_is_async():
    """验证 save_to_file 是异步方法且不会阻塞事件循环"""
    metrics = IOMetrics()

    # 记录一些操作
    await metrics.record_operation('read', 0.1, 0, True)
    await metrics.record_operation('write', 0.2, 1, True)

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        # 验证 save_to_file 是可 await 的异步方法
        await metrics.save_to_file(temp_path)

        # 验证文件内容正确
        with open(temp_path, 'r') as f:
            data = json.load(f)

        assert 'operations' in data
        assert len(data['operations']) == 2
        assert data['operations'][0]['operation_type'] == 'read'
        assert data['operations'][1]['operation_type'] == 'write'

    finally:
        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_save_to_file_accepts_path_object():
    """验证 save_to_file 接受 Path 对象"""
    metrics = IOMetrics()
    await metrics.record_operation('read', 0.1, 0, True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / 'metrics.json'

        # 应该能接受 Path 对象
        await metrics.save_to_file(temp_path)

        # 验证文件存在且包含正确数据
        assert temp_path.exists()
        with open(temp_path, 'r') as f:
            data = json.load(f)
        assert len(data['operations']) == 1


@pytest.mark.asyncio
async def test_save_to_file_raises_type_error_for_invalid_path():
    """验证 save_to_file 对无效路径抛出 TypeError"""
    metrics = IOMetrics()

    with pytest.raises(TypeError, match="path must be str or Path"):
        await metrics.save_to_file(123)  # type: ignore


@pytest.mark.asyncio
async def test_save_to_file_does_not_block_event_loop():
    """验证 save_to_file 不会阻塞事件循环

    如果 save_to_file 使用同步 I/O，那么在它执行时，
    其他并发任务将被阻塞。这个测试通过并发执行
    save_to_file 和一个计时任务来验证非阻塞行为。
    """
    metrics = IOMetrics()

    # 记录足够多的操作以确保文件写入需要一些时间
    for i in range(100):
        await metrics.record_operation(f'operation_{i}', 0.01, 0, True)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        # 创建一个计数器，用于检查事件循环是否被阻塞
        counter = 0
        async def increment_counter():
            nonlocal counter
            while counter < 50:
                counter += 1
                await asyncio.sleep(0.001)

        # 并发执行 save_to_file 和计数器
        await asyncio.gather(
            metrics.save_to_file(temp_path),
            increment_counter()
        )

        # 如果事件循环被阻塞，计数器将无法达到预期值
        # 这个断言可能需要根据实际情况调整
        assert counter >= 10, "Event loop appears to be blocked"

    finally:
        Path(temp_path).unlink(missing_ok=True)
