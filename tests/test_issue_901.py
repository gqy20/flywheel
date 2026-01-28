"""测试 Issue #901: from_dict 方法中 created_at=None 会覆盖 default_factory."""

import pytest
from flywheel.todo import Todo


def test_from_dict_with_created_at_none_should_use_default_factory():
    """测试当 created_at 为 None 时，应该使用 default_factory 自动生成时间戳。

    Issue #901: 如果输入数据包含 'created_at': None，
    会覆盖 dataclass 的 default_factory，导致对象创建后 created_at 仍为 None。
    """
    # 准备测试数据，包含 created_at: None
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test Description",
        "status": "todo",
        "priority": "medium",
        "created_at": None,  # 这是问题的关键
    }

    # 调用 from_dict 创建对象
    todo = Todo.from_dict(data)

    # 期望：created_at 应该自动生成（不为 None）
    # 实际：由于 bug，created_at 会是 None
    assert todo.created_at is not None, (
        "created_at 不应该是 None。当输入为 None 时，"
        "应该利用 dataclass 的 default_factory 自动生成时间戳。"
    )
    assert isinstance(todo.created_at, str), "created_at 应该是字符串类型"


def test_from_dict_without_created_at_should_use_default_factory():
    """测试当 created_at 字段不存在时，应该使用 default_factory 自动生成时间戳。"""
    data = {
        "id": 2,
        "title": "Test Todo 2",
    }

    todo = Todo.from_dict(data)

    assert todo.created_at is not None
    assert isinstance(todo.created_at, str)


def test_from_dict_with_valid_created_at_should_preserve_value():
    """测试当 created_at 有有效值时，应该保留该值。"""
    valid_timestamp = "2025-01-07T10:30:00"
    data = {
        "id": 3,
        "title": "Test Todo 3",
        "created_at": valid_timestamp,
    }

    todo = Todo.from_dict(data)

    assert todo.created_at == valid_timestamp
