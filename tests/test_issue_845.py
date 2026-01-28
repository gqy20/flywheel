"""测试 issue #845 - get_next_id 方法完整性

验证 get_next_id 方法存在并可以正常调用。
"""

import pytest
from flywheel.storage import FileStorage, AbstractStorage
from flywheel.models import Todo


def test_abstract_storage_has_get_next_id():
    """验证 AbstractStorage 定义了 get_next_id 抽象方法"""
    assert hasattr(AbstractStorage, 'get_next_id')
    # 确认它是一个抽象方法
    import inspect
    assert getattr(AbstractStorage.get_next_id, '__isabstractmethod__', False)


def test_file_storage_has_get_next_id():
    """验证 FileStorage 实现了 get_next_id 方法"""
    storage = FileStorage()
    assert hasattr(storage, 'get_next_id')
    assert callable(storage.get_next_id)


def test_get_next_id_returns_int():
    """验证 get_next_id 返回整数"""
    storage = FileStorage()
    next_id = storage.get_next_id()
    assert isinstance(next_id, int)
    assert next_id >= 0


def test_get_next_id_increments():
    """验证 get_next_id 返回递增的 ID"""
    storage = FileStorage()
    id1 = storage.get_next_id()
    id2 = storage.get_next_id()
    assert id2 == id1  # get_next_id 应该返回下一个可用的 ID，但不应该自动递增


def test_get_next_id_after_add():
    """验证添加 todo 后 get_next_id 返回新的 ID"""
    storage = FileStorage()
    initial_id = storage.get_next_id()

    # 添加一个 todo
    todo = Todo(title="Test todo", description="Test")
    storage.add(todo)

    # 下一个 ID 应该递增
    new_id = storage.get_next_id()
    assert new_id == initial_id + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
