"""测试 Issue #1686: _SimpleAsyncFile.__aexit__ 异常处理

这个测试验证当 to_thread 在 __aexit__ 方法中抛出异常时，
文件句柄仍然能够正确关闭。
"""
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest

# 添加 src 到路径以便导入
import sys
sys.path.insert(0, 'src')

from flywheel.storage import aiofiles


class TestSimpleAsyncFileAexit:
    """测试 _SimpleAsyncFile.__aexit__ 的异常处理"""

    @pytest.mark.asyncio
    async def test_aexit_closes_file_even_when_to_thread_fails(self):
        """
        测试当 to_thread 抛出异常时，文件仍然被关闭。

        这是 Issue #1686 的核心问题：
        当前实现中，如果 to_thread 抛出异常，close 不会被调用。
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            # 创建 _SimpleAsyncFile 实例
            async_file = await aiofiles.open(tmp_path, 'r')
            file_obj = await async_file.__aenter__()

            # 跟踪 close 是否被调用
            close_called = False
            original_close = file_obj.close

            def tracking_close():
                nonlocal close_called
                close_called = True
                return original_close()

            file_obj.close = tracking_close

            # 模拟 to_thread 在 close 时抛出异常
            with patch('asyncio.to_thread', side_effect=RuntimeError("to_thread error")):
                with pytest.raises(RuntimeError, match="to_thread error"):
                    await async_file.__aexit__(None, None, None)

            # 验证：即使 to_thread 失败，close 也应该被调用
            # 当前实现会失败于此（这就是 bug）
            assert close_called, "File should be closed even when to_thread fails"

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_aexit_handles_normal_close(self):
        """
        测试正常情况下文件能够正确关闭。
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            async_file = await aiofiles.open(tmp_path, 'r')
            file_obj = await async_file.__aenter__()

            # 正常关闭应该不抛出异常
            await async_file.__aexit__(None, None, None)

            # 验证文件已关闭
            assert file_obj.closed

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_aexit_with_none_file(self):
        """
        测试当 _file 为 None 时不会抛出异常。
        """
        # 创建 _SimpleAsyncFile 但不进入
        async_file = await aiofiles.open('/tmp/nonexistent', 'r')

        # 不调用 __aenter__，所以 _file 为 None
        async_file._file = None

        # 应该不抛出异常
        await async_file.__aexit__(None, None, None)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
