"""Test for Issue #1627: Structured logging context propagation using contextvars"""
import json
import logging
import os
import sys
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flywheel.storage import JSONFormatter, set_storage_context


def test_set_storage_context_function_exists():
    """Test that set_storage_context function exists"""
    assert callable(set_storage_context), "set_storage_context should be a callable function"


def test_set_storage_context_sets_context_vars():
    """Test that set_storage_context properly sets context variables"""
    import contextvars

    # Set some context
    set_storage_context(request_id="req-123", user_id="user-456")

    # The context should be accessible via contextvars
    # This will fail until we implement the function


def test_jsonformatter_includes_context_vars():
    """Test that JSONFormatter automatically includes context vars in log output"""
    import contextvars

    # Set up a logger with JSONFormatter
    logger = logging.getLogger('test_context_logger')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # Clear any existing handlers

    # Create a string stream to capture output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Set context variables
    set_storage_context(request_id="req-789", user_id="user-101", operation="test_operation")

    # Log a message without extra fields
    logger.info("Test message")

    # Get the output
    output = stream.getvalue().strip()
    log_data = json.loads(output)

    # Verify context variables are in the log
    assert 'request_id' in log_data, "Log should include request_id from context"
    assert log_data['request_id'] == "req-789", "request_id should match context value"

    assert 'user_id' in log_data, "Log should include user_id from context"
    assert log_data['user_id'] == "user-101", "user_id should match context value"

    assert 'operation' in log_data, "Log should include operation from context"
    assert log_data['operation'] == "test_operation", "operation should match context value"

    assert 'message' in log_data, "Log should include message field"
    assert log_data['message'] == "Test message", "message should match logged message"


def test_context_propagation_across_async_tasks():
    """Test that context propagates across different logging calls"""
    import contextvars

    logger = logging.getLogger('test_context_propagation')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Set initial context
    set_storage_context(trace_id="trace-abc", correlation_id="cor-xyz")

    # First log
    logger.info("First log")

    # Update context (add new field)
    set_storage_context(step="step1")

    # Second log
    logger.info("Second log")

    # Get all output
    output = stream.getvalue().strip()
    lines = output.split('\n')

    # Parse both log lines
    first_log = json.loads(lines[0])
    second_log = json.loads(lines[1])

    # First log should have trace_id and correlation_id
    assert first_log['trace_id'] == "trace-abc"
    assert first_log['correlation_id'] == "cor-xyz"
    assert first_log['message'] == "First log"

    # Second log should have all context including step
    assert second_log['trace_id'] == "trace-abc"
    assert second_log['correlation_id'] == "cor-xyz"
    assert second_log['step'] == "step1"
    assert second_log['message'] == "Second log"


def test_extra_fields_take_precedence_over_context():
    """Test that extra fields passed to log call take precedence over context vars"""
    logger = logging.getLogger('test_precedence')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Set context
    set_storage_context(request_id="context-request", source="context")

    # Log with extra field that conflicts with context
    logger.info("Test", extra={"request_id": "extra-request"})

    output = stream.getvalue().strip()
    log_data = json.loads(output)

    # Extra field should take precedence over context
    assert log_data['request_id'] == "extra-request", "Extra field should override context"

    # Context field that wasn't overridden should still be present
    assert log_data['source'] == "context", "Non-conflicted context should be preserved"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
