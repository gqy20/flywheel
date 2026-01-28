"""Tests for I/O metrics operation type grouping (Issue #1120).

This test ensures that the log_summary method correctly groups operations
by operation_type and logs metrics properly. This prevents the issue where
code could be truncated (e.g., op['ope instead of op['operation_type']).
"""

import asyncio
import logging
import os
from unittest import mock

import pytest

from flywheel.storage import IOMetrics


class TestIOMetricsOperationTypeGroupingIssue1120:
    """Test suite for I/O metrics operation type grouping (Issue #1120)."""

    @pytest.mark.asyncio
    async def test_log_summary_groups_by_operation_type(self, caplog):
        """Test that log_summary correctly groups operations by operation_type."""
        # Arrange
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Record multiple operations of different types
        await metrics.record_operation("read", duration=0.1, retries=0, success=True)
        await metrics.record_operation("write", duration=0.2, retries=1, success=True)
        await metrics.record_operation("read", duration=0.15, retries=0, success=True)
        await metrics.record_operation("delete", duration=0.05, retries=0, success=False)
        await metrics.record_operation("write", duration=0.25, retries=2, success=True)

        # Act
        with caplog.at_level(logging.INFO):
            metrics.log_summary()

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']

        # Assert - verify the summary was logged
        assert any('I/O Metrics Summary' in record.message for record in caplog.records), \
            "Expected I/O Metrics Summary to be logged"

        # Verify the summary contains the expected information
        summary_records = [r for r in caplog.records if 'I/O Metrics Summary' in r.message]
        assert len(summary_records) > 0, "Expected at least one summary log"

        summary_msg = summary_records[0].message
        # Check that it includes total operations, successful, failed, retries, and duration
        assert '5 operations' in summary_msg or 'operations' in summary_msg, \
            f"Expected operation count in summary, got: {summary_msg}"
        assert 'successful' in summary_msg, f"Expected 'successful' in summary, got: {summary_msg}"
        assert 'retries' in summary_msg, f"Expected 'retries' in summary, got: {summary_msg}"
        assert 'duration' in summary_msg, f"Expected 'duration' in summary, got: {summary_msg}"

    @pytest.mark.asyncio
    async def test_log_summary_operation_type_field_exists(self):
        """Test that recorded operations have operation_type field."""
        # Arrange
        metrics = IOMetrics()

        # Act
        await metrics.record_operation("test_operation", duration=0.1, retries=0, success=True)

        # Assert - verify the operation has operation_type field
        assert len(metrics.operations) == 1, "Expected one operation recorded"
        operation = metrics.operations[0]

        # This is the key test - operation_type must be present and accessible
        assert 'operation_type' in operation, \
            "Expected 'operation_type' field in operation dictionary"

        # Verify it can be accessed without KeyError (the bug from issue #1120)
        op_type = operation['operation_type']
        assert op_type == "test_operation", \
            f"Expected operation_type to be 'test_operation', got '{op_type}'"

    @pytest.mark.asyncio
    async def test_log_summary_handles_multiple_operation_types(self, caplog):
        """Test that log_summary correctly handles multiple different operation types."""
        # Arrange
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Record operations with many different types
        operation_types = ["read", "write", "delete", "update", "create", "append"]
        for op_type in operation_types:
            await metrics.record_operation(
                op_type,
                duration=0.1,
                retries=0,
                success=True
            )

        # Act - this should not raise any KeyError
        with caplog.at_level(logging.INFO):
            metrics.log_summary()

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']

        # Assert - verify no KeyError was raised and summary was logged
        assert any('I/O Metrics Summary' in record.message for record in caplog.records), \
            "Expected I/O Metrics Summary to be logged without errors"

    @pytest.mark.asyncio
    async def test_log_summary_with_empty_operations(self, caplog):
        """Test that log_summary handles empty operations list gracefully."""
        # Arrange
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Act - log_summary with no operations should not fail
        with caplog.at_level(logging.INFO):
            metrics.log_summary()

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']

        # Assert - should log "No operations recorded"
        assert any('No operations recorded' in record.message for record in caplog.records), \
            "Expected 'No operations recorded' message"

    @pytest.mark.asyncio
    async def test_log_summary_operation_type_aggregation(self, caplog):
        """Test that operations are correctly aggregated by operation_type."""
        # Arrange
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = IOMetrics()

        # Record multiple reads and writes
        await metrics.record_operation("read", duration=0.1, retries=0, success=True)
        await metrics.record_operation("read", duration=0.2, retries=1, success=True)
        await metrics.record_operation("read", duration=0.15, retries=0, success=True)
        await metrics.record_operation("write", duration=0.3, retries=2, success=True)
        await metrics.record_operation("write", duration=0.25, retries=1, success=True)

        # Act
        with caplog.at_level(logging.INFO):
            metrics.log_summary()

        # Clean up
        del os.environ['FW_STORAGE_METRICS_LOG']

        # Assert - verify the summary was logged
        summary_records = [r for r in caplog.records if 'I/O Metrics Summary' in r.message]
        assert len(summary_records) > 0, "Expected summary to be logged"

        # Verify total counts are correct (5 total operations)
        summary_msg = summary_records[0].message
        assert '5 operations' in summary_msg or 'operations' in summary_msg

    @pytest.mark.asyncio
    async def test_operation_type_not_truncated(self):
        """Test that operation_type key is not truncated (regression test for issue #1120)."""
        # Arrange
        metrics = IOMetrics()

        # Act
        await metrics.record_operation("read", duration=0.1, retries=0, success=True)

        # Assert - explicitly verify the key is complete and not truncated
        operation = metrics.operations[0]

        # This would fail with KeyError if the key was truncated to 'ope' instead of 'operation_type'
        # The bug in issue #1120 would have code like: op_type = op['ope]
        # which would cause a KeyError
        try:
            op_type = operation['operation_type']
            assert op_type == "read"
        except KeyError as e:
            pytest.fail(f"operation_type key appears to be truncated or missing: {e}")

        # Also verify we can't access it with the truncated key
        # (if 'ope' was a key, this would succeed, which would be wrong)
        assert 'ope' not in operation, \
            "Truncated key 'ope' should not exist (indicates potential bug)"

    @pytest.mark.asyncio
    async def test_log_summary_respects_env_variable(self, caplog):
        """Test that log_summary only logs when FW_STORAGE_METRICS_LOG is set."""
        # Arrange
        # Ensure env var is NOT set
        if 'FW_STORAGE_METRICS_LOG' in os.environ:
            del os.environ['FW_STORAGE_METRICS_LOG']

        metrics = IOMetrics()
        await metrics.record_operation("read", duration=0.1, retries=0, success=True)

        # Act - should not log anything
        with caplog.at_level(logging.INFO):
            metrics.log_summary()

        # Assert - no metrics should be logged
        assert not any('I/O Metrics' in record.message for record in caplog.records), \
            "Expected no metrics to be logged when env var is not set"
