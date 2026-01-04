"""测试 Issue #615 - 验证 FileStorage 类完整性

此测试验证：
1. __del__ 方法存在（用于 atexit 清理注册）
2. 核心业务方法（add, list, update, delete）正常工作
"""
import os
import tempfile
import pytest
from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_filestorage_has_del_method():
    """验证 FileStorage 类有 __del__ 方法用于清理"""
    storage = FileStorage()
    assert hasattr(storage, '__del__'), "FileStorage 应该有 __del__ 方法用于 atexit 清理"


def test_filestorage_del_method_is_callable():
    """验证 __del__ 方法是可调用的"""
    storage = FileStorage()
    assert callable(storage.__del__), "__del__ 应该是可调用的方法"


def test_filestorage_core_methods_exist():
    """验证核心业务方法存在"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(path=os.path.join(tmpdir, "test.json"))

        # 验证方法存在
        assert hasattr(storage, 'add'), "FileStorage 应该有 add 方法"
        assert hasattr(storage, 'list'), "FileStorage 应该有 list 方法"
        assert hasattr(storage, 'update'), "FileStorage 应该有 update 方法"
        assert hasattr(storage, 'delete'), "FileStorage 应该有 delete 方法"


def test_filestorage_core_methods_work():
    """验证核心业务方法正常工作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(path=os.path.join(tmpdir, "test.json"))

        # 测试 add 方法
        todo = Todo(title="Test task")
        added_todo = storage.add(todo)
        assert added_todo.id == 1, "add 方法应该返回带有正确 id 的 todo"

        # 测试 list 方法
        todos = storage.list()
        assert len(todos) == 1, "list 方法应该返回 1 个 todo"
        assert todos[0].title == "Test task", "返回的 todo 应该有正确的标题"

        # 测试 update 方法
        added_todo.title = "Updated task"
        updated_todo = storage.update(added_todo)
        assert updated_todo is not None, "update 方法应该返回更新后的 todo"
        assert updated_todo.title == "Updated task", "todo 标题应该已更新"

        # 测试 delete 方法
        result = storage.delete(1)
        assert result is True, "delete 方法应该返回 True 表示成功"

        # 验证删除后 list 返回空列表
        todos = storage.list()
        assert len(todos) == 0, "删除后 list 应该返回空列表"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
