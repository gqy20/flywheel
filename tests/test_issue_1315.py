"""Test for Issue #1315 - Verify IOMetrics lock initialization."""

import threading

from flywheel.storage import IOMetrics


def test_iometrics_init_lock_initialization():
    """Test that IOMetrics properly initializes _init_lock (Issue #1315)."""
    metrics = IOMetrics()

    # Verify that _init_lock is initialized and is a threading.Lock
    assert hasattr(metrics, '_init_lock'), "IOMetrics should have _init_lock attribute"
    assert isinstance(metrics._init_lock, threading.Lock), (
        "_init_lock should be an instance of threading.Lock"
    )

    # Verify that _sync_operation_lock is also initialized
    assert hasattr(metrics, '_sync_operation_lock'), (
        "IOMetrics should have _sync_operation_lock attribute"
    )
    assert isinstance(metrics._sync_operation_lock, threading.Lock), (
        "_sync_operation_lock should be an instance of threading.Lock"
    )

    # Verify that _locks dictionary is initialized
    assert hasattr(metrics, '_locks'), "IOMetrics should have _locks attribute"
    assert isinstance(metrics._locks, dict), "_locks should be a dictionary"
    assert len(metrics._locks) == 0, "_locks should be empty initially"


def test_iometrics_locks_are_different_instances():
    """Test that _init_lock and _sync_operation_lock are different lock instances."""
    metrics = IOMetrics()

    # The locks should be different instances for their different purposes
    assert metrics._init_lock is not metrics._sync_operation_lock, (
        "_init_lock and _sync_operation_lock should be different lock instances"
    )
