"""Tests for Issue #1339 - Verify IOMetrics class is complete and functional."""

import pytest

from flywheel.storage import IOMetrics


class TestIssue1339:
    """Test that IOMetrics class is complete and all methods are implemented."""

    def test_iometrics_class_exists(self):
        """Test that IOMetrics class can be imported."""
        from flywheel.storage import IOMetrics
        assert IOMetrics is not None

    def test_iometrics_instantiation(self):
        """Test that IOMetrics can be instantiated."""
        metrics = IOMetrics()
        assert metrics is not None
        assert hasattr(metrics, 'operations')
        assert hasattr(metrics, '_locks')
        assert hasattr(metrics, '_init_lock')
        assert hasattr(metrics, '_sync_operation_lock')

    def test_iometrics_has_init_method(self):
        """Test that IOMetrics has __init__ method."""
        assert hasattr(IOMetrics, '__init__')
        metrics = IOMetrics()
        # Verify initialization worked correctly
        assert len(metrics.operations) == 0

    def test_iometrics_has_record_operation(self):
        """Test that IOMetrics has record_operation method."""
        assert hasattr(IOMetrics, 'record_operation')
        metrics = IOMetrics()
        # Test the method exists and is callable
        assert callable(metrics.record_operation)
        # Test calling it
        metrics.record_operation('read', 0.5, 0, True)
        assert len(metrics.operations) == 1

    def test_iometrics_has_record_operation_async(self):
        """Test that IOMetrics has record_operation_async method."""
        assert hasattr(IOMetrics, 'record_operation_async')
        metrics = IOMetrics()
        # Test the method exists and is callable
        assert callable(metrics.record_operation_async)

    def test_iometrics_has_total_operation_count(self):
        """Test that IOMetrics has total_operation_count method."""
        assert hasattr(IOMetrics, 'total_operation_count')
        metrics = IOMetrics()
        assert callable(metrics.total_operation_count)
        # Test it works
        metrics.record_operation('read', 0.5, 0, True)
        assert metrics.total_operation_count() == 1

    def test_iometrics_has_total_duration(self):
        """Test that IOMetrics has total_duration method."""
        assert hasattr(IOMetrics, 'total_duration')
        metrics = IOMetrics()
        assert callable(metrics.total_duration)
        # Test it works
        metrics.record_operation('read', 0.5, 0, True)
        assert metrics.total_duration() == 0.5

    def test_iometrics_has_log_summary(self):
        """Test that IOMetrics has log_summary method."""
        assert hasattr(IOMetrics, 'log_summary')
        metrics = IOMetrics()
        assert callable(metrics.log_summary)

    def test_iometrics_has_track_operation(self):
        """Test that IOMetrics has track_operation method."""
        assert hasattr(IOMetrics, 'track_operation')
        metrics = IOMetrics()
        assert callable(metrics.track_operation)

    def test_iometrics_has_export_to_dict(self):
        """Test that IOMetrics has export_to_dict method."""
        assert hasattr(IOMetrics, 'export_to_dict')
        metrics = IOMetrics()
        assert callable(metrics.export_to_dict)
        # Test it works
        metrics.record_operation('read', 0.5, 0, True)
        data = metrics.export_to_dict()
        assert isinstance(data, dict)
        assert 'operations' in data
        assert len(data['operations']) == 1

    def test_iometrics_has_save_to_file(self):
        """Test that IOMetrics has save_to_file method."""
        assert hasattr(IOMetrics, 'save_to_file_async')
        metrics = IOMetrics()
        assert callable(metrics.save_to_file_async)

    def test_iometrics_has_reset(self):
        """Test that IOMetrics has reset method."""
        assert hasattr(IOMetrics, 'reset')
        metrics = IOMetrics()
        assert callable(metrics.reset)
        # Test it works
        metrics.record_operation('read', 0.5, 0, True)
        assert metrics.total_operation_count() == 1
        metrics.reset()
        assert metrics.total_operation_count() == 0

    @pytest.mark.asyncio
    async def test_iometrics_async_functionality(self):
        """Test that IOMetrics async methods work correctly."""
        metrics = IOMetrics()
        # Test async record operation
        await metrics.record_operation_async('read', 0.5, 0, True)
        assert metrics.total_operation_count() == 1
        # Test async save
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        try:
            await metrics.save_to_file_async(temp_path)
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_iometrics_max_operations_constant(self):
        """Test that IOMetrics has MAX_OPERATIONS constant."""
        assert hasattr(IOMetrics, 'MAX_OPERATIONS')
        assert IOMetrics.MAX_OPERATIONS == 1000

    def test_iometrics_all_required_methods_present(self):
        """Test that all expected methods are present on IOMetrics class."""
        expected_methods = [
            '__init__',
            'record_operation',
            'record_operation_async',
            'total_operation_count',
            'total_operation_count_async',
            'total_duration',
            'total_duration_async',
            'log_summary',
            'track_operation',
            'export_to_dict',
            'save_to_file_async',
            'reset',
            '_get_async_lock',
            '_cleanup_stale_locks',
        ]

        for method_name in expected_methods:
            assert hasattr(IOMetrics, method_name), f"IOMetrics missing method: {method_name}"
            method = getattr(IOMetrics, method_name)
            assert callable(method), f"IOMetrics.{method_name} is not callable"
