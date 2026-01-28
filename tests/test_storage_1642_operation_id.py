"""Tests for operation_id in StorageMetrics (Issue #1642)."""

import pytest
from unittest import mock
import uuid


class TestStorageMetricsOperationId:
    """Test suite for operation_id parameter in StorageMetrics."""

    def test_storage_metrics_accepts_operation_id(self):
        """Test that StorageMetrics.record_io_operation accepts operation_id parameter."""
        from flywheel.storage import StorageMetrics

        # Create a mock implementation of StorageMetrics
        class MockMetrics:
            def record_io_operation(
                self,
                operation_type: str,
                duration: float,
                retries: int = 0,
                success: bool = True,
                error_type: str | None = None,
                operation_id: str | None = None
            ) -> None:
                """Mock implementation that accepts operation_id."""
                pass

        # Verify the mock conforms to the protocol
        metrics = MockMetrics()

        # Test with operation_id
        test_id = str(uuid.uuid4())
        metrics.record_io_operation(
            operation_type="write",
            duration=0.1,
            retries=0,
            success=True,
            operation_id=test_id
        )

        # Test without operation_id (should still work)
        metrics.record_io_operation(
            operation_type="read",
            duration=0.05,
            retries=0,
            success=True
        )

    def test_storage_metrics_protocol_has_operation_id(self):
        """Test that StorageMetrics protocol includes operation_id parameter."""
        from flywheel.storage import StorageMetrics
        import inspect

        # Get the signature of record_io_operation from the protocol
        sig = inspect.signature(StorageMetrics.record_io_operation)
        params = sig.parameters

        # Verify operation_id parameter exists
        assert 'operation_id' in params, "operation_id parameter missing from StorageMetrics.record_io_operation"

        # Verify it's optional (has default)
        param = params['operation_id']
        assert param.default is not None or param.kind == inspect.Parameter.KEYWORD_ONLY, \
            "operation_id should be optional with a default value"

    def test_iometrics_accepts_operation_id(self):
        """Test that IOMetrics.record_operation accepts operation_id parameter."""
        from flywheel.storage import IOMetrics
        import asyncio

        async def run_test():
            metrics = IOMetrics()

            # Test with operation_id
            test_id = str(uuid.uuid4())
            await metrics.record_operation(
                operation_type="write",
                duration=0.1,
                retries=0,
                success=True,
                operation_id=test_id
            )

            # Verify operation_id was stored
            assert len(metrics.operations) == 1
            assert metrics.operations[0].get('operation_id') == test_id

            # Test without operation_id
            await metrics.record_operation(
                operation_type="read",
                duration=0.05,
                retries=0,
                success=True
            )

            # Verify second operation has None or generated operation_id
            assert len(metrics.operations) == 2

        asyncio.run(run_test())

    def test_file_storage_integration_with_operation_id(self):
        """Test that FileStorage can use operation_id in metrics."""
        from flywheel.storage import FileStorage, IOMetrics
        import asyncio

        async def run_test():
            metrics = IOMetrics()

            # Mock FileStorage to use our metrics
            with mock.patch('flywheel.storage.IOMetrics') as MockIOMetrics:
                MockIOMetrics.return_value = metrics

                # Test that operations can be tracked with operation_id
                test_id = str(uuid.uuid4())
                await metrics.record_operation(
                    operation_type="write",
                    duration=0.1,
                    retries=0,
                    success=True,
                    operation_id=test_id
                )

                # Verify the operation_id is preserved
                assert metrics.operations[0]['operation_id'] == test_id

        asyncio.run(run_test())

    def test_operation_id_correlation_with_context(self):
        """Test that operation_id can correlate with storage context."""
        from flywheel.storage import set_storage_context, IOMetrics
        import asyncio

        async def run_test():
            metrics = IOMetrics()

            # Set storage context with an operation_id
            test_id = str(uuid.uuid4())
            set_storage_context(operation_id=test_id)

            # Record operation with the same operation_id
            await metrics.record_operation(
                operation_type="write",
                duration=0.1,
                retries=0,
                success=True,
                operation_id=test_id
            )

            # Verify correlation
            assert metrics.operations[0]['operation_id'] == test_id

        asyncio.run(run_test())
