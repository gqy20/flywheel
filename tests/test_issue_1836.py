"""测试 Issue #1836: aiofiles 占位符实现中缺少异步上下文管理器方法

这个测试验证 _SimpleAsyncFile 类应该支持异步 read/write 方法。
"""
import asyncio
import tempfile
import os

from flywheel.storage import _AiofilesPlaceholder


async def test_simple_async_file_has_async_read():
    """测试 _SimpleAsyncFile 支持 await file.read()"""
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('test content')
        temp_path = f.name

    try:
        # 使用 _AiofilesPlaceholder.open 获取异步文件对象
        async_file = _AiofilesPlaceholder.open(temp_path, 'rb')

        # 在异步上下文中使用
        async with async_file as f:
            # 这里应该能调用 await f.read()
            content = await f.read()
            assert content == b'test content'
    finally:
        # 清理临时文件
        os.unlink(temp_path)


async def test_simple_async_file_has_async_write():
    """测试 _SimpleAsyncFile 支持 await file.write()"""
    # 创建临时文件路径
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
        temp_path = f.name

    try:
        # 使用 _AiofilesPlaceholder.open 获取异步文件对象
        async_file = _AiofilesPlaceholder.open(temp_path, 'wb')

        # 在异步上下文中使用
        async with async_file as f:
            # 这里应该能调用 await f.write()
            await f.write(b'async write test')

        # 验证写入内容
        with open(temp_path, 'rb') as f:
            content = f.read()
            assert content == b'async write test'
    finally:
        # 清理临时文件
        os.unlink(temp_path)


def test_sync_wrapper_for_async_tests():
    """同步包装器用于运行异步测试"""
    asyncio.run(test_simple_async_file_has_async_read())
    asyncio.run(test_simple_async_file_has_async_write())
