"""Test to verify IOMetrics class is complete and functional (Issue #1335).

This test verifies that the IOMetrics class is NOT truncated and is fully
implemented with all expected methods and functionality.
"""

import asyncio
import tempfile
from pathlib import Path

from flywheel.storage import IOMetrics


def test_iometrics_init():
    """Test that IOMetrics can be instantiated."""
    metrics = IOMetrics()
    assert metrics is not None
    assert hasattr(metrics, 'operations')
    assert hasattr(metrics, '_locks')
    assert hasattr(metrics, '_init_lock')
    assert hasattr(metrics, '_sync_operation_lock')
    assert hasattr(metrics, '_event_loops')
    print("✓ IOMetrics.__init__ works correctly")


def test_iometrics_record_operation():
    """Test that record_operation method works."""
    metrics = IOMetrics()
    metrics.record_operation('read', 0.5, 0, True, None)
    assert metrics.total_operation_count() == 1
    print("✓ IOMetrics.record_operation works correctly")


def test_iometrics_record_operation_async():
    """Test that record_operation_async method works."""
    async def test_async():
        metrics = IOMetrics()
        await metrics.record_operation_async('write', 0.3, 1, True, None)
        count = await metrics.total_operation_count_async()
        assert count == 1

    asyncio.run(test_async())
    print("✓ IOMetrics.record_operation_async works correctly")


def test_iometrics_total_operation_count():
    """Test that total_operation_count method works."""
    metrics = IOMetrics()
    metrics.record_operation('read', 0.5, 0, True)
    metrics.record_operation('write', 0.3, 1, True)
    count = metrics.total_operation_count()
    assert count == 2
    print("✓ IOMetrics.total_operation_count works correctly")


def test_iometrics_total_operation_count_async():
    """Test that total_operation_count_async method works."""
    async def test_async():
        metrics = IOMetrics()
        await metrics.record_operation_async('read', 0.5, 0, True)
        await metrics.record_operation_async('write', 0.3, 1, True)
        count = await metrics.total_operation_count_async()
        assert count == 2

    asyncio.run(test_async())
    print("✓ IOMetrics.total_operation_count_async works correctly")


def test_iometrics_total_duration():
    """Test that total_duration method works."""
    metrics = IOMetrics()
    metrics.record_operation('read', 0.5, 0, True)
    metrics.record_operation('write', 0.3, 1, True)
    duration = metrics.total_duration()
    assert duration == 0.8
    print("✓ IOMetrics.total_duration works correctly")


def test_iometrics_total_duration_async():
    """Test that total_duration_async method works."""
    async def test_async():
        metrics = IOMetrics()
        await metrics.record_operation_async('read', 0.5, 0, True)
        await metrics.record_operation_async('write', 0.3, 1, True)
        duration = await metrics.total_duration_async()
        assert duration == 0.8

    asyncio.run(test_async())
    print("✓ IOMetrics.total_duration_async works correctly")


def test_iometrics_export_to_dict():
    """Test that export_to_dict method works."""
    metrics = IOMetrics()
    metrics.record_operation('read', 0.5, 0, True)
    metrics.record_operation('write', 0.3, 1, False, 'ENOENT')

    data = metrics.export_to_dict()
    assert isinstance(data, dict)
    assert 'operations' in data
    assert 'total_operation_count' in data
    assert 'total_duration' in data
    assert 'successful_operations' in data
    assert 'failed_operations' in data
    assert 'total_retries' in data
    assert data['total_operation_count'] == 2
    assert data['total_duration'] == 0.8
    assert data['successful_operations'] == 1
    assert data['failed_operations'] == 1
    assert data['total_retries'] == 1
    print("✓ IOMetrics.export_to_dict works correctly")


def test_iometrics_save_to_file():
    """Test that save_to_file method works."""
    async def test_async():
        metrics = IOMetrics()
        await metrics.record_operation_async('read', 0.5, 0, True)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = Path(f.name)

        try:
            await metrics.save_to_file(temp_path)
            assert temp_path.exists()
            content = temp_path.read_text()
            assert '"total_operation_count": 1' in content
            print("✓ IOMetrics.save_to_file works correctly")
        finally:
            if temp_path.exists():
                temp_path.unlink()


    asyncio.run(test_async())


def test_iometrics_reset():
    """Test that reset method works."""
    metrics = IOMetrics()
    metrics.record_operation('read', 0.5, 0, True)
    metrics.record_operation('write', 0.3, 1, True)
    assert metrics.total_operation_count() == 2

    metrics.reset()
    assert metrics.total_operation_count() == 0
    print("✓ IOMetrics.reset works correctly")


def test_iometrics_track_operation():
    """Test that track_operation context manager works."""
    async def test_async():
        metrics = IOMetrics()

        async with metrics.track_operation('read'):
            await asyncio.sleep(0.01)

        count = await metrics.total_operation_count_async()
        assert count == 1
        print("✓ IOMetrics.track_operation works correctly")

    asyncio.run(test_async())


def test_iometrics_all_methods_exist():
    """Test that all expected methods exist on IOMetrics class."""
    metrics = IOMetrics()

    # Check all expected methods exist
    expected_methods = [
        '__init__',
        '_get_async_lock',
        '_cleanup_stale_locks',
        'record_operation',
        'record_operation_async',
        'total_operation_count',
        'total_operation_count_async',
        'total_duration',
        'total_duration_async',
        'log_summary',
        'track_operation',
        'export_to_dict',
        'save_to_file',
        '_write_to_file_sync',
        'reset',
    ]

    for method_name in expected_methods:
        assert hasattr(metrics, method_name), f"Missing method: {method_name}"
        assert callable(getattr(metrics, method_name)), f"{method_name} is not callable"

    print(f"✓ All {len(expected_methods)} expected methods exist and are callable")


def test_iometrics_class_is_complete():
    """Verify that IOMetrics class is complete and not truncated."""
    import inspect

    # Get all methods of IOMetrics
    methods = inspect.getmembers(IOMetrics, predicate=inspect.isfunction)

    # Verify we have a substantial number of methods (not a truncated class)
    assert len(methods) >= 15, f"Expected at least 15 methods, got {len(methods)}"

    # Verify key methods have docstrings and implementations
    key_methods = [
        'record_operation',
        'record_operation_async',
        'total_operation_count',
        'total_duration',
        'export_to_dict',
        'save_to_file',
        'reset',
        'track_operation',
    ]

    for method_name in key_methods:
        method = getattr(IOMetrics, method_name)
        assert method.__doc__ is not None, f"{method_name} missing docstring"
        assert len(method.__doc__) > 20, f"{method_name} has incomplete docstring"

    print(f"✓ IOMetrics class is complete with {len(methods)} methods")
    print("✓ Issue #1335 appears to be a FALSE POSITIVE - the class is NOT truncated")


if __name__ == '__main__':
    # Run all tests
    test_iometrics_init()
    test_iometrics_record_operation()
    test_iometrics_record_operation_async()
    test_iometrics_total_operation_count()
    test_iometrics_total_operation_count_async()
    test_iometrics_total_duration()
    test_iometrics_total_duration_async()
    test_iometrics_export_to_dict()
    test_iometrics_save_to_file()
    test_iometrics_reset()
    test_iometrics_track_operation()
    test_iometrics_all_methods_exist()
    test_iometrics_class_is_complete()

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
    print("\nCONCLUSION:")
    print("  The IOMetrics class is COMPLETE and FULLY FUNCTIONAL.")
    print("  Issue #1335 is a FALSE POSITIVE.")
    print("  The class has all its methods implemented correctly.")
    print("="*60)
