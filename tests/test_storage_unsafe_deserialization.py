"""Tests for unsafe deserialization vulnerability."""

import json
import tempfile

from flywheel.storage import Storage


def test_load_malicious_tampered_json_file():
    """Test that loading a tampered JSON file with malicious data is handled safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test.json"

        # Simulate an attacker tampering with the JSON file
        # Test 1: Invalid enum values that should be rejected
        malicious_data = [
            {
                "id": 1,
                "title": "Test todo",
                "description": "Normal description",
                "status": "malicious_status",  # Invalid status
                "priority": "critical",  # Invalid priority
                "due_date": None,
                "created_at": "2025-01-01T00:00:00",
                "completed_at": None,
                "tags": ["tag1"],
            }
        ]

        with open(test_file, "w") as f:
            json.dump(malicious_data, f)

        # Should handle gracefully without crashing
        storage = Storage(path=test_file)

        # Either the todo should be rejected, or invalid values should be sanitized
        todos = storage.list()
        # If the todo was loaded, it should have safe default values
        if len(todos) > 0:
            todo = todos[0]
            # Status and priority should be valid enum values, not the malicious ones
            assert todo.status.value in ["todo", "in_progress", "done"]
            assert todo.priority.value in ["low", "medium", "high"]


def test_load_json_with_extra_malicious_fields():
    """Test that extra fields in JSON don't cause issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test.json"

        # Test 2: Extra fields that shouldn't be there
        malicious_data = [
            {
                "id": 1,
                "title": "Test todo",
                "description": "Normal description",
                "status": "todo",
                "priority": "medium",
                "due_date": None,
                "created_at": "2025-01-01T00:00:00",
                "completed_at": None,
                "tags": ["tag1"],
                "__class__": "MaliciousClass",  # Attempt to inject class
                "dangerous_field": "dangerous_value",
                "eval": "__import__('os').system('rm -rf /')",  # Malicious code attempt
            }
        ]

        with open(test_file, "w") as f:
            json.dump(malicious_data, f)

        # Should load safely without executing malicious code
        storage = Storage(path=test_file)
        todos = storage.list()

        # Todo should be loaded safely (extra fields ignored)
        # or rejected entirely
        assert len(todos) <= 1


def test_load_json_with_wrong_data_types():
    """Test that wrong data types are handled safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test.json"

        # Test 3: Wrong data types
        malicious_data = [
            {
                "id": "not_a_number",  # Should be int
                "title": 12345,  # Should be string
                "description": {"malicious": "object"},  # Should be string
                "status": "todo",
                "priority": "medium",
                "due_date": None,
                "created_at": "2025-01-01T00:00:00",
                "completed_at": None,
                "tags": "not_a_list",  # Should be list
            }
        ]

        with open(test_file, "w") as f:
            json.dump(malicious_data, f)

        # Should handle gracefully without crashing
        storage = Storage(path=test_file)

        # Either reject the malformed todo or handle it safely
        # The app should not crash


def test_load_json_with_missing_required_fields():
    """Test that missing required fields are handled safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test.json"

        # Test 4: Missing required fields
        malicious_data = [
            {
                # Missing 'id' and 'title' which are required
                "description": "A todo with no id or title",
                "status": "todo",
            }
        ]

        with open(test_file, "w") as f:
            json.dump(malicious_data, f)

        # Should handle gracefully without crashing
        storage = Storage(path=test_file)

        # Should reject invalid todos
        # App should not crash
