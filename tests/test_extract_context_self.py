"""Tests for _extract_context handling self parameter (Issue #1018)."""

import pytest
from pathlib import Path
from flywheel.storage import _extract_context


class TestExtractContextWithSelf:
    """Test that _extract_context correctly skips 'self' parameter in class methods."""

    def test_method_with_path_as_second_param(self):
        """Test method signature: load(self, path)"""
        class Storage:
            def load(self, path):
                pass

        storage = Storage()
        args = (storage, "/tmp/file.json")
        kwargs = {}

        result = _extract_context(args, kwargs, storage.load)

        # Should extract path, not self
        assert result == " on /tmp/file.json"

    def test_method_with_id_as_second_param(self):
        """Test method signature: get_item(self, id)"""
        class Storage:
            def get_item(self, id):
                pass

        storage = Storage()
        args = (storage, 12345)
        kwargs = {}

        result = _extract_context(args, kwargs, storage.get_item)

        # Should extract id, not self
        assert result == " on 12345"

    def test_method_with_path_object(self):
        """Test method with Path object as second parameter."""
        class Storage:
            def load(self, path):
                pass

        storage = Storage()
        args = (storage, Path("/tmp/file.json"))
        kwargs = {}

        result = _extract_context(args, kwargs, storage.load)

        # Should convert Path to string
        assert result == " on /tmp/file.json"

    def test_static_function_without_self(self):
        """Test regular function without self parameter."""
        def load(path):
            pass

        args = ("/tmp/file.json",)
        kwargs = {}

        result = _extract_context(args, kwargs, load)

        # Should extract path normally
        assert result == " on /tmp/file.json"

    def test_method_with_kwargs(self):
        """Test method with path as keyword argument."""
        class Storage:
            def load(self, path):
                pass

        storage = Storage()
        args = (storage,)
        kwargs = {'path': "/tmp/file.json"}

        result = _extract_context(args, kwargs, storage.load)

        # Should extract path from kwargs
        assert result == " on /tmp/file.json"

    def test_method_path_as_third_param(self):
        """Test method signature: save(self, data, path)"""
        class Storage:
            def save(self, data, path):
                pass

        storage = Storage()
        args = (storage, "data", "/tmp/file.json")
        kwargs = {}

        result = _extract_context(args, kwargs, storage.save)

        # Should extract path from third position
        assert result == " on /tmp/file.json"

    def test_method_with_multiple_params(self):
        """Test method with multiple parameters where path is not first."""
        class Storage:
            def process(self, id, name, path):
                pass

        storage = Storage()
        args = (storage, 123, "test", "/tmp/file.json")
        kwargs = {}

        result = _extract_context(args, kwargs, storage.process)

        # Should extract path from fourth position (index 3)
        assert result == " on /tmp/file.json"
