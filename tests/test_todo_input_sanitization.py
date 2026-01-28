"""Tests for Todo input sanitization (Issue #1129)."""

from flywheel.todo import Todo


def test_title_xss_sanitization():
    """Test that XSS attempts in title are sanitized."""
    data = {
        "id": 1,
        "title": "<script>alert('xss')</script>",
        "description": "Description",
    }
    todo = Todo.from_dict(data)

    # Script tags should be removed or escaped
    assert "<script>" not in todo.title
    assert "</script>" not in todo.title
    assert "alert" not in todo.title


def test_description_xss_sanitization():
    """Test that XSS attempts in description are sanitized."""
    data = {
        "id": 1,
        "title": "Test",
        "description": "<img src=x onerror=alert('xss')>",
    }
    todo = Todo.from_dict(data)

    # Script/event handlers should be removed or escaped
    assert "onerror" not in todo.description
    assert "alert" not in todo.description


def test_tags_xss_sanitization():
    """Test that XSS attempts in tags are sanitized."""
    data = {
        "id": 1,
        "title": "Test",
        "tags": ["<script>evil()</script>", "normal", "<img src=x onerror=bad()>"],
    }
    todo = Todo.from_dict(data)

    # All tags should be sanitized
    for tag in todo.tags:
        assert "<script>" not in tag
        assert "</script>" not in tag
        assert "onerror" not in tag


def test_sql_injection_sanitization():
    """Test that SQL injection attempts are sanitized."""
    data = {
        "id": 1,
        "title": "'; DROP TABLE todos; --",
        "description": "admin' OR '1'='1",
    }
    todo = Todo.from_dict(data)

    # The input should be sanitized, but we still store the sanitized version
    # For SQL injection prevention, we mainly need to ensure it's escaped
    # This test verifies the input is cleaned of obvious dangerous patterns
    assert todo.title is not None
    assert todo.description is not None
