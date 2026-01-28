"""测试 Issue #1841 - 验证代码语法完整性

Issue #1841 声称代码在 src/flywheel/todo.py 第 236 行被截断。
这个测试验证文件实际上具有正确的语法。
"""

import pytest


def test_todo_file_syntax_is_valid():
    """验证 todo.py 文件语法是正确的。"""
    # 尝试导入模块，如果有语法错误会失败
    from flywheel.todo import Todo

    # 验证类可以正常实例化
    todo = Todo(id=1, title="Test Todo")
    assert todo.id == 1
    assert todo.title == "Test Todo"


def test_from_dict_with_invalid_due_date():
    """测试 from_dict 方法对无效 due_date 格式的处理。"""
    from flywheel.todo import Todo
    from datetime import datetime

    # 测试有效的 due_date
    valid_data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "2026-01-15T10:00:00"
    }
    todo = Todo.from_dict(valid_data)
    assert todo.due_date == "2026-01-15T10:00:00"

    # 测试无效的 due_date 格式应该抛出 ValueError
    invalid_data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "invalid-date-format"
    }
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(invalid_data)
    assert "Invalid ISO 8601 date format" in str(exc_info.value)
    assert "due_date" in str(exc_info.value)


def test_from_dict_complete_method():
    """测试 from_dict 方法完整执行，没有被截断。"""
    from flywheel.todo import Todo

    # 测试完整的 from_dict 流程
    complete_data = {
        "id": 1,
        "title": "Complete Todo",
        "description": "Test description",
        "status": "in_progress",
        "priority": "high",
        "due_date": "2026-12-31T23:59:59",
        "created_at": "2026-01-15T10:00:00",
        "completed_at": None,
        "tags": ["tag1", "tag2"]
    }

    todo = Todo.from_dict(complete_data)

    # 验证所有字段都正确设置
    assert todo.id == 1
    assert todo.title == "Complete Todo"
    assert todo.description == "Test description"
    assert todo.status.value == "in_progress"
    assert todo.priority.value == "high"
    assert todo.due_date == "2026-12-31T23:59:59"
    assert todo.created_at == "2026-01-15T10:00:00"
    assert todo.completed_at is None
    assert todo.tags == ["tag1", "tag2"]
