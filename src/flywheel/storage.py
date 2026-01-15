"""Todo storage backend."""

import abc
import asyncio
import atexit
import contextvars
import errno
import functools
import gzip
import hashlib
import inspect
import json
import logging
import os
import random
import re
import threading
import time
import weakref
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

from flywheel.todo import Todo

# Import aiofiles with fallback for graceful degradation (Issue #1032)
# If aiofiles is not available, we'll use asyncio.to_thread with built-in open
# Define protocol for aiofiles-like objects to avoid using # type: ignore (Issue #1565)


class _AiofilesProtocol(Protocol):
    """Protocol for aiofiles-like objects to ensure type safety.

    This protocol defines the interface that both real aiofiles and our
    fallback implementation must satisfy, eliminating the need for
    # type: ignore comments (Issue #1565).
    """

    @staticmethod
    def open(path: str, mode: str = 'rb') -> Any:
        """Open a file asynchronously.

        Args:
            path: File path to open
            mode: File open mode (defaults to 'rb' for binary read)

        Returns:
            An async context manager for file operations
        """
        ...


try:
    import aiofiles as _aiofiles_real
    HAS_AIOFILES = True
    # Always assign aiofiles, never leave it as None (Issue #1613)
    aiofiles: _AiofilesProtocol = _aiofiles_real
except ImportError:
    HAS_AIOFILES = False
    # Simple fallback that implements _AiofilesProtocol
    # This provides a basic async file context manager that will be
    # replaced with the full _AiofilesFallback implementation after
    # _retry_io_operation is defined (Issue #1624, #1631)
    class _AiofilesPlaceholder:
        """Simple placeholder implementing _AiofilesProtocol.

        This placeholder provides a minimal working implementation
        to prevent RuntimeError if it's accidentally called before
        being replaced with the full _AiofilesFallback (Issue #1631).
        """

        @staticmethod
        def open(path: str, mode: str = 'rb'):
            """Minimal async file context manager.

            This provides a basic fallback that uses asyncio.to_thread
            if called before the full implementation is ready.

            This should normally be replaced with _AiofilesFallback,
            but this implementation ensures the code won't crash
            if the replacement fails for any reason (Issue #1631).

            Note: asyncio is already imported at module level (line 4),
            and asyncio.to_thread is available since Python 3.9. The project
            requires Python >=3.13, so it's always available (Issue #1730).
            """
            class _SimpleAsyncFile:
                """Simple async file wrapper."""

                def __init__(self, path, mode):
                    self.path = path
                    self.mode = mode
                    self._file = None

                async def __aenter__(self):
                    self._file = await asyncio.to_thread(open, self.path, self.mode)
                    return self

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if self._file:
                        try:
                            await asyncio.to_thread(self._file.close)
                        except Exception as close_exc:
                            # Log the close exception but don't suppress it
                            # If there's already an exception from the context body,
                            # log the close exception and re-raise the original exception
                            if exc_type is not None:
                                logging.getLogger(__name__).warning(
                                    f"Exception during file close: {close_exc}"
                                )
                                # Re-raise the original exception from the context body
                                raise
                            else:
                                # No other exception, so re-raise the close exception
                                raise close_exc

                async def read(self, size=-1):
                    """Read content from file asynchronously."""
                    return await asyncio.to_thread(self._file.read, size)

                async def write(self, data):
                    """Write data to file asynchronously."""
                    return await asyncio.to_thread(self._file.write, data)

            return _SimpleAsyncFile(path, mode)

    aiofiles: _AiofilesProtocol = _AiofilesPlaceholder()

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)


# Fix for Issue #1627: Context propagation for structured logging
# ContextVar to hold storage context that propagates across async tasks
# Fix for Issue #1725: Use default=None to avoid mutable default dict risk
_storage_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    '_storage_context', default=None
)


def set_storage_context(**kwargs: Any) -> None:
    """Set storage context variables for automatic log propagation.

    This function sets context variables that will be automatically included
    in all log messages formatted by JSONFormatter, without needing to pass
    'extra=' to every log call.

    Context variables propagate across async tasks and threads, making them
    ideal for tracing request IDs, user IDs, and other metadata in
    microservices and complex async applications.

    Args:
        **kwargs: Arbitrary key-value pairs to include in log context.
                  These will be merged into the log data by JSONFormatter.

    Example:
        >>> set_storage_context(request_id="req-123", user_id="user-456")
        >>> logger.info("Processing request")  # Automatically includes request_id and user_id

    Note:
        Context can be updated by calling this function again - new keys are added
        and existing keys are updated. The context propagates to child tasks
        automatically.
    """
    # Get current context and merge with new values
    # Fix for Issue #1725: Handle None default to avoid mutable dict sharing
    current = _storage_context.get() or {}
    new_context = {**current, **kwargs}
    _storage_context.set(new_context)


# Fix for Issue #1773: Sampling for high-frequency debug logs
def sample_debug_log(rate_limit: float = 0.1):
    """Create a sampling wrapper for high-frequency debug log calls.

    This function returns a wrapper that only logs a fraction of debug messages,
    which is useful for high-frequency logs (like retries or lock contention)
    that can degrade performance and explode log volume when logged in tight loops.

    Args:
        rate_limit: Fraction of messages to log (0.0 to 1.0).
                   0.1 = log 10% of messages (default)
                   1.0 = log all messages
                   0.0 = log no messages

    Returns:
        A function that takes (logger, message, *args, **kwargs) and
        conditionally logs based on the rate limit.

    Example:
        >>> sampler = sample_debug_log(rate_limit=0.1)  # Log 10% of messages
        >>> sampler(logger, "Retrying operation", attempt=3)
        >>> # Only ~10% of such calls will actually log

    Note:
        Sampling uses random.random() for probabilistic sampling.
        For reproducible sampling in tests, set random.seed() beforehand.
    """
    def sampler(log_obj, msg, *args, **kwargs):
        # Only log if random check passes
        if random.random() < rate_limit:
            log_obj.debug(msg, *args, **kwargs)
    return sampler


# Fix for Issue #1603: JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.

    This formatter converts log records into JSON format with all fields
    at the top level (not nested) for easy parsing by monitoring tools
    like Datadog, ELK, and other log aggregators.

    Fix for Issue #1603: Provides machine-readable JSON logs for lock
    contention monitoring and analysis.

    Fix for Issue #1633: Automatically redacts sensitive fields like
    'password', 'token', and 'api_key' to prevent sensitive information
    leakage in structured logs.

    Fix for Issue #1643: Implements size limit for log data to prevent
    massive strings from breaking log parsers or increasing ingestion costs.

    Fix for Issue #1722: Implements final JSON size check to prevent
    log system congestion from large aggregated log entries.
    """

    # Sensitive field names that should be redacted (case-insensitive)
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'credential',
        'private_key', 'access_token', 'auth_token', 'api_secret',
        'password_hash', 'passphrase', 'credentials'
    }

    # Maximum size for string values in log data (10KB)
    # This prevents large strings (e.g., stack traces, data dumps) from
    # breaking log parsers or significantly increasing ingestion costs
    MAX_LOG_SIZE = 10 * 1024  # 10KB in bytes

    # Maximum size for final JSON output (1MB)
    # This prevents the entire log entry from being too large even after
    # individual field truncation, protecting log systems from congestion
    MAX_JSON_SIZE = 1 * 1024 * 1024  # 1MB in bytes

    def format(self, record):
        """Format log record as JSON.

        Args:
            record: The logging record to format

        Returns:
            JSON string with all log fields at top level
        """

        # Standard fields that should never be overridden by custom fields
        standard_fields = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'thread_id': threading.get_ident(),
        }

        # Fields to exclude from custom fields (standard logging attributes)
        excluded_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
            'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'message',
            'asctime'
        }

        # Build log data with standard fields first
        log_data = standard_fields.copy()

        # Add custom fields from the record's extra dict
        # These are set using logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in excluded_fields:
                # Check if custom field conflicts with standard fields
                if key in standard_fields:
                    # Prefix conflicting fields with 'extra_' to preserve them
                    # while protecting standard fields
                    log_data[f'extra_{key}'] = value
                else:
                    log_data[key] = value

        # Fix for Issue #1627: Merge context variables into log data
        # Context vars are added first, so extra fields can override them
        # Fix for Issue #1725: Handle None default to avoid mutable dict sharing
        storage_context = _storage_context.get() or {}
        for key, value in storage_context.items():
            # Only add context var if not already present in log_data
            # (extra fields take precedence over context)
            if key not in log_data:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Fix for Issue #1633: Redact sensitive fields
        # Check all field names (case-insensitive) and redact sensitive values
        log_data = self._redact_sensitive_fields(log_data)

        # Fix for Issue #1643: Truncate large string values
        # Iterate through log_data and truncate string values that exceed MAX_LOG_SIZE
        log_data = self._truncate_large_values(log_data)

        # Fix for Issue #1646: Handle JSON serialization errors
        # Try to serialize log_data to JSON, falling back to safe serialization
        # if non-serializable objects are present
        try:
            json_output = json.dumps(log_data)
        except (TypeError, ValueError):
            # If serialization fails, convert all values to safe strings
            safe_log_data = self._make_serializable(log_data)
            json_output = json.dumps(safe_log_data)

        # Fix for Issue #1722: Check final JSON size
        # Even after truncating individual fields, the overall JSON might be too large
        # (e.g., many fields). This prevents log system congestion.
        if len(json_output) > self.MAX_JSON_SIZE:
            # Step 1: Truncate the message field to reduce size
            # Message is often the largest field after field-level truncation
            if 'message' in log_data and isinstance(log_data['message'], str):
                excess_bytes = len(json_output) - self.MAX_JSON_SIZE
                # Truncate message to fit within MAX_JSON_SIZE
                max_message_len = len(log_data['message']) - excess_bytes - 20
                if max_message_len > 0:
                    log_data['message'] = log_data['message'][:max_message_len] + '...[truncated]'
                    # Re-serialize with truncated message
                    try:
                        json_output = json.dumps(log_data)
                    except (TypeError, ValueError):
                        safe_log_data = self._make_serializable(log_data)
                        json_output = json.dumps(safe_log_data)

            # Fix for Issue #1757: If still too large after message truncation,
            # remove non-critical fields in priority order
            if len(json_output) > self.MAX_JSON_SIZE:
                # Define priority order for field removal (lowest priority first)
                # Fields that are less critical for log analysis should be removed first
                removal_priority = [
                    'exception',  # Stack traces are useful but can be very large
                    'extra_',     # Fields that conflicted with standard fields
                ]

                # Remove fields in priority order until JSON fits
                for priority_field in removal_priority:
                    if len(json_output) <= self.MAX_JSON_SIZE:
                        break

                    # Find and remove matching fields
                    fields_to_remove = []
                    for key in log_data.keys():
                        if key == priority_field or key.startswith(priority_field):
                            fields_to_remove.append(key)

                    # Remove the fields
                    for field in fields_to_remove:
                        del log_data[field]

                    # Re-serialize after removing fields
                    if fields_to_remove:
                        try:
                            json_output = json.dumps(log_data)
                        except (TypeError, ValueError):
                            safe_log_data = self._make_serializable(log_data)
                            json_output = json.dumps(safe_log_data)

                # Fix for Issue #1827: If still too large, remove custom fields
                # Keep only the most critical standard fields
                if len(json_output) > self.MAX_JSON_SIZE:
                    critical_fields = {'timestamp', 'level', 'logger', 'message'}
                    fields_to_remove = [k for k in log_data.keys() if k not in critical_fields]
                    for field in fields_to_remove:
                        del log_data[field]

                    # Re-serialize after removing custom fields
                    try:
                        json_output = json.dumps(log_data)
                    except (TypeError, ValueError):
                        safe_log_data = self._make_serializable(log_data)
                        json_output = json.dumps(safe_log_data)

                    # Fix for Issue #1824: Final enforcement - truncate message if still too large
                    # This is the last resort to ensure JSON output never exceeds MAX_JSON_SIZE
                    # Even if it means losing most of the message content
                    if len(json_output) > self.MAX_JSON_SIZE and 'message' in log_data:
                        # Calculate how much we need to remove
                        excess_bytes = len(json_output) - self.MAX_JSON_SIZE

                        # Estimate message max length (conservative, accounting for JSON encoding)
                        # JSON encoding adds ~2 chars per special char, so we use a safety factor
                        estimated_overhead = len(json_output) - len(log_data.get('message', ''))
                        max_message_length = max(0, self.MAX_JSON_SIZE - estimated_overhead - 100)  # 100 byte safety margin

                        if max_message_length > 0:
                            # Truncate message to fit
                            original_message = log_data['message']
                            if isinstance(original_message, str):
                                log_data['message'] = original_message[:max_message_length] + '...[truncated]'
                            else:
                                # Convert to string if not already
                                log_data['message'] = str(original_message)[:max_message_length] + '...[truncated]'

                            # Final re-serialize
                            try:
                                json_output = json.dumps(log_data)
                            except (TypeError, ValueError):
                                safe_log_data = self._make_serializable(log_data)
                                json_output = json.dumps(safe_log_data)
                        else:
                            # Extreme case: Even empty message is too large with other fields
                            # This should never happen with current critical fields, but handle it gracefully
                            log_data['message'] = ''
                            try:
                                json_output = json.dumps(log_data)
                            except (TypeError, ValueError):
                                safe_log_data = self._make_serializable(log_data)
                                json_output = json.dumps(safe_log_data)

                        # Fix for Issue #1824: Final absolute enforcement - ensure valid JSON
                        # If all truncation attempts fail, use a minimal safe message
                        # This ensures we NEVER output invalid JSON
                        if len(json_output) > self.MAX_JSON_SIZE:
                            # Absolute last resort: Replace with minimal safe log entry
                            # This ensures we always return valid JSON within size limit
                            minimal_log = {
                                'timestamp': log_data.get('timestamp', ''),
                                'level': log_data.get('level', 'ERROR'),
                                'logger': log_data.get('logger', ''),
                                'message': '[LOG TRUNCATED - Original message exceeded maximum size]',
                            }
                            json_output = json.dumps(minimal_log)

                            # Double-check the minimal log fits (it always should)
                            if len(json_output) > self.MAX_JSON_SIZE:
                                # This should never happen, but if it does, use even more minimal
                                json_output = json.dumps({'error': 'Log exceeded maximum size'})

        return json_output

    def _redact_sensitive_fields(self, log_data):
        """Redact sensitive field values by fully masking them.

        All sensitive values are completely redacted with '***REDACTED***'
        regardless of length or type. This prevents partial hash exposure which
        can be a security vulnerability in high-security contexts.

        This method recursively processes all levels of nested dictionaries and lists
        to ensure sensitive fields are redacted at any depth.

        Args:
            log_data: Dictionary of log fields

        Returns:
            Dictionary with sensitive field values redacted
        """
        return self._redact_sensitive_fields_recursive(log_data)

    def _redact_sensitive_fields_recursive(self, data):
        """Recursively redact sensitive field values at all nesting levels.

        Fix for Issue #1758: Enhanced to:
        1. Parse and redact sensitive data in JSON strings
        2. Parse and redact sensitive data in URL parameters
        3. Scan large strings for sensitive keyword patterns

        Args:
            data: Any data structure (dict, list, or primitive value)

        Returns:
            Data structure with sensitive field values redacted
        """
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                # Check if field name matches any sensitive field (case-insensitive)
                if key.lower() in self.SENSITIVE_FIELDS:
                    # Redact the sensitive value
                    redacted[key] = self._redact_value(value)
                else:
                    # Recursively process non-sensitive fields
                    redacted[key] = self._redact_sensitive_fields_recursive(value)
            return redacted
        elif isinstance(data, list):
            # Recursively process each item in the list
            return [self._redact_sensitive_fields_recursive(item) for item in data]
        elif isinstance(data, str):
            # Fix for Issue #1758: Enhanced string value processing
            return self._redact_string_value(data)
        else:
            # Return primitive values as-is
            return data

    def _redact_string_value(self, value):
        """Redact sensitive data in string values.

        Fix for Issue #1758: Attempts to:
        1. Parse as JSON and recursively redact
        2. Parse as URL and redact sensitive parameters
        3. Scan for sensitive patterns in large strings

        Args:
            value: String value to check for sensitive data

        Returns:
            Redacted or original string value
        """
        # Try parsing as JSON
        json_result = self._try_redact_json_string(value)
        if json_result is not None:
            return json_result

        # Try parsing/redacting as URL
        url_result = self._try_redact_url_string(value)
        if url_result is not None:
            return url_result

        # For large strings, scan for sensitive keywords
        if len(value) > 100:  # Only scan larger strings to avoid false positives
            return self._scan_and_redact_sensitive_patterns(value)

        # Return as-is if no patterns detected
        return value

    def _try_redact_json_string(self, value):
        """Try to parse string as JSON and redact sensitive fields.

        Args:
            value: String value that might be JSON

        Returns:
            Redacted JSON string, or None if not valid JSON
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(value)
            # Recursively redact sensitive fields in the parsed data
            redacted = self._redact_sensitive_fields_recursive(parsed)
            # Convert back to JSON string
            return json.dumps(redacted)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Not valid JSON, return None to indicate no redaction occurred
            return None

    def _try_redact_url_string(self, value):
        """Try to parse string as URL and redact sensitive parameters.

        Args:
            value: String value that might be a URL

        Returns:
            URL with sensitive parameters redacted, or None if not a URL
        """
        # Check if string looks like a URL (contains :// and has ?)
        if '://' not in value or '?' not in value:
            return None

        try:
            # Parse URL
            parsed = urlparse(value)
            # Parse query parameters
            query_params = parse_qs(parsed.query)

            # Check if any sensitive parameters exist
            has_sensitive = any(
                param.lower() in self.SENSITIVE_FIELDS
                for param in query_params.keys()
            )

            if not has_sensitive:
                return None  # No sensitive params, return original

            # Redact sensitive parameter values
            redacted_params = {}
            for param, values in query_params.items():
                if param.lower() in self.SENSITIVE_FIELDS:
                    # Redact all values for this parameter
                    redacted_params[param] = ['***REDACTED***'] * len(values)
                else:
                    redacted_params[param] = values

            # Rebuild query string
            redacted_query = urlencode(redacted_params, doseq=True)

            # Rebuild URL with redacted query
            redacted_url = parsed._replace(query=redacted_query).geturl()
            return redacted_url

        except Exception:
            # URL parsing failed, return None
            return None

    def _scan_and_redact_sensitive_patterns(self, value):
        """Scan string for sensitive keyword patterns and redact values.

        For large strings, looks for patterns like 'password: secret123'
        and redacts the values.

        Args:
            value: Large string value to scan

        Returns:
            String with sensitive patterns redacted, or original if none found
        """
        # Build regex pattern to match common sensitive field patterns
        # Matches: password: value, password=value, password="value", etc.
        patterns = []
        for field in self.SENSITIVE_FIELDS:
            # Pattern for: field: value or field=value (case-insensitive)
            pattern = rf'{field}["\']?\s*[:=]\s*["\']?([^"\'\s\}]+)["\']?'
            patterns.append(pattern)

        if not patterns:
            return value

        # Combine all patterns with OR
        combined_pattern = re.compile('|'.join(patterns), re.IGNORECASE)

        # Function to replace matched values with redaction
        def replace_match(match):
            # Return the field name with redacted value
            return match.group(0).replace(match.group(1), '***REDACTED***')

        # Apply replacement
        result = combined_pattern.sub(replace_match, value)

        return result

    def _redact_value(self, value):
        """Redact a single sensitive value.

        Args:
            value: The value to redact

        Returns:
            Redacted string representation
        """
        # Fix for Issue #1724: Full redaction for all sensitive values
        # Partial hash exposure can be a security vulnerability in high-security contexts
        # All sensitive values are now fully redacted regardless of length or type
        return '***REDACTED***'

    def _truncate_large_values(self, log_data):
        """Truncate string values that exceed MAX_LOG_SIZE.

        This method recursively processes all values in log_data and truncates
        string values that exceed MAX_LOG_SIZE, appending a '...[truncated]' suffix.

        Args:
            log_data: Dictionary of log fields

        Returns:
            Dictionary with large string values truncated
        """
        truncated = {}
        for key, value in log_data.items():
            if isinstance(value, str):
                # Truncate string if it exceeds MAX_LOG_SIZE
                if len(value) > self.MAX_LOG_SIZE:
                    suffix = '...[truncated]'
                    # Truncate the string and add suffix
                    truncated[key] = value[:self.MAX_LOG_SIZE - len(suffix)] + suffix
                else:
                    truncated[key] = value
            elif isinstance(value, dict):
                # Recursively truncate nested dictionaries
                truncated[key] = self._truncate_large_values(value)
            elif isinstance(value, list):
                # Process lists - truncate strings in the list
                truncated[key] = []
                for item in value:
                    if isinstance(item, str) and len(item) > self.MAX_LOG_SIZE:
                        suffix = '...[truncated]'
                        truncated[key].append(item[:self.MAX_LOG_SIZE - len(suffix)] + suffix)
                    elif isinstance(item, dict):
                        truncated[key].append(self._truncate_large_values(item))
                    else:
                        truncated[key].append(item)
            else:
                # Keep non-string, non-dict, non-list values as-is
                truncated[key] = value
        return truncated

    def _make_serializable(self, log_data):
        """Convert non-serializable values to serializable strings.

        This method recursively processes all values in log_data and converts
        non-serializable objects (like custom classes, lambdas, etc.) to their
        string representation, making them JSON-safe.

        Args:
            log_data: Dictionary of log fields

        Returns:
            Dictionary with all values converted to JSON-serializable types
        """
        serializable = {}
        for key, value in log_data.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                serializable[key] = self._make_serializable(value)
            elif isinstance(value, list):
                # Process lists - convert non-serializable items
                serializable[key] = []
                for item in value:
                    if isinstance(item, dict):
                        serializable[key].append(self._make_serializable(item))
                    elif self._is_serializable(item):
                        serializable[key].append(item)
                    else:
                        # Convert non-serializable item to string
                        serializable[key].append(str(item))
            elif self._is_serializable(value):
                # Keep serializable values as-is
                serializable[key] = value
            else:
                # Convert non-serializable value to string
                serializable[key] = str(value)
        return serializable

    def _is_serializable(self, value):
        """Check if a value is JSON-serializable.

        Args:
            value: Any Python value

        Returns:
            True if the value can be serialized to JSON, False otherwise
        """
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False


# Fix for Issue #1638: Storage metrics collection hook
# This allows observability tools (like Prometheus/Datadog) to track storage
# performance without parsing logs.


class StorageMetrics(Protocol):
    """Protocol for storage metrics collection.

    This protocol defines the interface for metrics collectors that can track
    storage performance metrics such as I/O operation latency, lock contention,
    and retry counts. Implementations can integrate with observability tools
    like Prometheus, Datadog, or custom monitoring systems.

    Fix for Issue #1638: Provides a hook for metrics collection that works
    with or without external dependencies like prometheus_client.
    """

    def record_io_operation(
        self,
        operation_type: str,
        duration: float,
        retries: int = 0,
        success: bool = True,
        error_type: str | None = None,
        operation_id: str | None = None
    ) -> None:
        """Record an I/O operation metric.

        Args:
            operation_type: Type of operation (e.g., 'read', 'write', 'flush')
            duration: Operation duration in seconds
            retries: Number of retry attempts
            success: Whether the operation succeeded
            error_type: Type of error if operation failed (e.g., 'EIO', 'TIMEOUT')
            operation_id: Optional unique ID for traceability with logs/traces (Issue #1642)
        """
        ...

    def record_lock_contention(self, wait_time: float) -> None:
        """Record a lock contention event.

        Args:
            wait_time: Time spent waiting for lock in seconds
        """
        ...

    def record_lock_acquired(self, acquire_time: float) -> None:
        """Record a successful lock acquisition.

        Args:
            acquire_time: Time taken to acquire lock in seconds
        """
        ...


class NoOpStorageMetrics:
    """No-op implementation of StorageMetrics for when metrics are not needed.

    This implementation provides all the required methods but does nothing,
    allowing code to use metrics without incurring overhead when not needed.

    Fix for Issue #1638: Provides a fallback when prometheus_client is not
    available or when metrics collection is not desired.
    """

    def record_io_operation(
        self,
        operation_type: str,
        duration: float,
        retries: int = 0,
        success: bool = True,
        error_type: str | None = None,
        operation_id: str | None = None
    ) -> None:
        """No-op implementation."""
        pass

    def record_lock_contention(self, wait_time: float) -> None:
        """No-op implementation."""
        pass

    def record_lock_acquired(self, acquire_time: float) -> None:
        """No-op implementation."""
        pass


# Try to import prometheus_client for Prometheus integration
# If not available, we'll use NoOpStorageMetrics as the default
try:
    from prometheus_client import Counter, Histogram, Gauge

    class PrometheusStorageMetrics:
        """Prometheus metrics implementation for storage operations.

        This implementation integrates with prometheus_client to expose
        metrics in Prometheus format for scraping by Prometheus server or
        other compatible monitoring systems.

        Fix for Issue #1638: Provides Prometheus integration when available.
        """

        def __init__(
            self,
            namespace: str = "flywheel",
            subsystem: str = "storage"
        ):
            """Initialize Prometheus metrics with default labels.

            Args:
                namespace: Metric namespace (default: "flywheel")
                subsystem: Metric subsystem (default: "storage")
            """
            self._namespace = namespace
            self._subsystem = subsystem

            # I/O operation counter
            self._io_operations_total = Counter(
                f"{namespace}_{subsystem}_io_operations_total",
                "Total number of I/O operations",
                [f"{namespace}_operation", f"{namespace}_success"]
            )

            # I/O operation duration histogram
            self._io_operation_duration_seconds = Histogram(
                f"{namespace}_{subsystem}_io_operation_duration_seconds",
                "I/O operation duration in seconds",
                [f"{namespace}_operation"]
            )

            # I/O operation retries histogram
            self._io_operation_retries = Histogram(
                f"{namespace}_{subsystem}_io_operation_retries",
                "Number of retries for I/O operations",
                [f"{namespace}_operation"]
            )

            # Lock contention counter
            self._lock_contentions_total = Counter(
                f"{namespace}_{subsystem}_lock_contentions_total",
                "Total number of lock contentions"
            )

            # Lock contention duration histogram
            self._lock_contention_duration_seconds = Histogram(
                f"{namespace}_{subsystem}_lock_contention_duration_seconds",
                "Lock contention duration in seconds"
            )

            # Lock acquisition duration histogram
            self._lock_acquisition_duration_seconds = Histogram(
                f"{namespace}_{subsystem}_lock_acquisition_duration_seconds",
                "Lock acquisition duration in seconds"
            )

        def record_io_operation(
            self,
            operation_type: str,
            duration: float,
            retries: int = 0,
            success: bool = True,
            error_type: str | None = None,
            operation_id: str | None = None
        ) -> None:
            """Record an I/O operation metric.

            Args:
                operation_type: Type of operation (e.g., 'read', 'write', 'flush')
                duration: Operation duration in seconds
                retries: Number of retry attempts
                success: Whether the operation succeeded
                error_type: Type of error if operation failed (not used in labels)
                operation_id: Optional unique ID for traceability with logs/traces (Issue #1642)
            """
            # Record operation counter
            self._io_operations_total.labels(
                **{f"{self._namespace}_operation": operation_type,
                   f"{self._namespace}_success": str(success).lower()}
            ).inc()

            # Record operation duration
            self._io_operation_duration_seconds.labels(
                **{f"{self._namespace}_operation": operation_type}
            ).observe(duration)

            # Record retries if any
            if retries > 0:
                self._io_operation_retries.labels(
                    **{f"{self._namespace}_operation": operation_type}
                ).observe(retries)

        def record_lock_contention(self, wait_time: float) -> None:
            """Record a lock contention event.

            Args:
                wait_time: Time spent waiting for lock in seconds
            """
            self._lock_contentions_total.inc()
            self._lock_contention_duration_seconds.observe(wait_time)

        def record_lock_acquired(self, acquire_time: float) -> None:
            """Record a successful lock acquisition.

            Args:
                acquire_time: Time taken to acquire lock in seconds
            """
            self._lock_acquisition_duration_seconds.observe(acquire_time)

    HAS_PROMETHEUS = True
except ImportError:
    # prometheus_client not available, will use NoOpStorageMetrics
    HAS_PROMETHEUS = False
    PrometheusStorageMetrics = None  # type: ignore


def get_storage_metrics() -> StorageMetrics:
    """Get a storage metrics instance based on available dependencies.

    Returns PrometheusStorageMetrics if prometheus_client is available,
    otherwise returns NoOpStorageMetrics.

    Fix for Issue #1638: Provides automatic fallback when prometheus_client
    is not available.

    Returns:
        StorageMetrics instance (either PrometheusStorageMetrics or NoOpStorageMetrics)
    """
    if HAS_PROMETHEUS and PrometheusStorageMetrics is not None:
        return PrometheusStorageMetrics()
    else:
        return NoOpStorageMetrics()


# Fix for Issue #1572: Check DEBUG_STORAGE environment variable to enable debug logging
# This allows developers and operators to monitor storage performance and tune parameters
# Fix for Issue #1603: Add JSON handler for structured logging when DEBUG_STORAGE is enabled
# Fix for Issue #1637: Replace StreamHandler with RotatingFileHandler for log rotation
if os.environ.get('DEBUG_STORAGE'):
    logger.setLevel(logging.DEBUG)
    logger.debug("DEBUG_STORAGE enabled: storage logger set to DEBUG level")

    # Import RotatingFileHandler for log rotation
    from logging.handlers import RotatingFileHandler

    # Check if logger already has a JSON rotating handler (avoid duplicates)
    has_json_handler = any(
        isinstance(h, RotatingFileHandler) and isinstance(h.formatter, JSONFormatter)
        for h in logger.handlers
    )

    if not has_json_handler:
        # Add JSON handler with log rotation for structured logging
        # Configure rotation to prevent disk space exhaustion
        log_file = os.path.join(os.getcwd(), 'flywheel_storage.log')
        json_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,  # Keep up to 5 backup files
        )
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(logging.INFO)  # Log INFO and above
        logger.addHandler(json_handler)
        logger.debug(f"DEBUG_STORAGE: JSON structured logging with rotation enabled: {log_file}")


class StorageTimeoutError(TimeoutError):
    """Exception raised when I/O operation or lock acquisition times out.

    This exception is raised when an I/O operation or lock acquisition takes
    longer than the configured timeout to complete. It is distinct from regular
    IOError to allow for different handling strategies.

    IMPORTANT: When this exception is raised due to a lock timeout (e.g., in
    _AsyncCompatibleLock.__enter__), the lock is NOT held by the caller. Callers
    should not assume they hold the lock after catching this exception.

    Fix for Issue #1043: Configurable timeout for I/O retries.
    Fix for Issue #1481: Documents that lock is NOT held after timeout.
    Fix for Issue #1508: Added optional context parameters (timeout, operation, caller)
    for better debugging and error handling.
    Fix for Issue #1553: Added suggested_action attribute with context-aware
    recommendations for different timeout types.
    """

    def __init__(self, message: str = "", timeout: float | None = None,
                 operation: str | None = None, caller: str | None = None,
                 suggested_action: str | None = None):
        """Initialize StorageTimeoutError with optional context parameters.

        Args:
            message: The error message
            timeout: The timeout duration in seconds
            operation: The operation that timed out (e.g., 'load_cache', 'save_data')
            caller: The function or method that triggered the timeout
            suggested_action: Optional custom suggestion for fixing the error
        """
        self.timeout = timeout
        self.operation = operation
        self.caller = caller

        # Determine suggested action based on operation type
        if suggested_action is not None:
            self.suggested_action = suggested_action
        elif operation is not None:
            operation_lower = operation.lower()
            if "lock" in operation_lower:
                self.suggested_action = "Retry the operation after a short delay"
            elif any(io_op in operation_lower for io_op in ["load", "save", "read", "write", "cache"]):
                self.suggested_action = "Check disk space and retry the operation"
            else:
                self.suggested_action = ""
        else:
            self.suggested_action = ""

        # Build enhanced error message with context
        parts = []
        if message:
            parts.append(message)

        if timeout is not None:
            parts.append(f"timeout={timeout}s")

        if operation is not None:
            parts.append(f"operation={operation}")

        if caller is not None:
            parts.append(f"caller={caller}")

        if self.suggested_action:
            parts.append(f"suggested_action={self.suggested_action}")

        # Combine original message with context
        if len(parts) > 1 or (len(parts) == 1 and parts[0] != message):
            full_message = " | ".join(parts)
        else:
            full_message = message

        super().__init__(full_message)


class _AsyncCompatibleLock:
    """A lock wrapper that supports both sync and async context managers.

    This wrapper allows the same lock to be used with both 'with' and 'async with'
    statements, solving the issue where threading.Lock doesn't support async
    context managers and asyncio.Lock doesn't support sync context managers.

    The implementation uses a unified threading.Lock for both synchronous and
    asynchronous contexts, ensuring true mutual exclusion between sync and async
    operations. Async contexts use an event for efficient waiting without blocking
    the event loop.

    Fix for Issue #1097: Provides unified lock interface for IOMetrics.
    Fix for Issue #1166: Uses single lock with thread-safe synchronization
    to ensure mutual exclusion between sync and async contexts.
    Fix for Issue #1290: Uses threading.Lock for sync contexts to prevent
    deadlock risks from event loop reuse and ensure true cross-thread mutual
    exclusion.
    Fix for Issue #1316: Uses threading.Lock + asyncio.Event for async contexts
    to prevent event loop blocking and thread pool exhaustion.
    Fix for Issue #1326: Uses separate state flags (_sync_locked and _async_locked)
    to prevent race conditions where acquiring one lock overwrites the state of
    the other.
    Fix for Issue #1381: Uses unified threading.Lock for both sync and async
    contexts to ensure true mutual exclusion, replacing the previous approach
    of using separate threading.RLock and asyncio.Lock which were independent.
    Fix for Issue #1406: Uses timeout in __enter__ to prevent potential deadlock
    when lock is contested. The lock acquisition is time-bound (10 seconds) to
    avoid freezing the thread indefinitely.
    Fix for Issue #1402: Raises StorageTimeoutError instead of TimeoutError for
    consistency with async contexts.
    Fix for Issue #1533: Implements configurable fuzzy lock timeout mechanism
    with timeout_range parameter and custom backoff strategies to prevent
    thundering herd effects during high contention.
    Fix for Issue #1538: Implements lock statistics tracking for performance
    monitoring and contention analysis.
    Fix for Issue #1582: Adds structured logging context (lock_wait_time, attempts)
    to lock acquisition when DEBUG_STORAGE is enabled for diagnosing contention.
    Fix for Issue #1587: Emits structured JSON logs with event='lock_wait' when
    DEBUG_STORAGE is active for monitoring tools (Datadog, ELK) to visualize bottlenecks.
    Fix for Issue #1603: Implements JSONFormatter class and adds JSON handler to logger
    when DEBUG_STORAGE is enabled, emitting machine-readable JSON logs with distinct
    fields (duration, caller, event, acquired, etc.) for structured logging tools.
    Fix for Issue #1609: Uses weak references for atexit handlers to prevent
    memory leaks when lock instances are garbage collected.
    """

    # Default timeout for sync lock acquisition (Issue #1406)
    # 10 seconds provides a reasonable balance between handling high contention
    # and detecting deadlocks. This matches the timeout from Issue #1291.
    _DEFAULT_LOCK_TIMEOUT = 10.0

    # Fix for Issue #1609: Class-level tracking of live lock instances using weak refs
    # This allows garbage collection while still providing atexit cleanup
    _live_locks = weakref.WeakSet()
    _atexit_handler_registered = False
    _registry_lock = threading.Lock()

    def __init__(self, lock_timeout: float | None = None,
                 timeout_range: tuple[float, float] | None = None,
                 backoff_strategy: callable | None = None,
                 adaptive_timeout: bool = False):
        """Initialize with unified lock for sync and async contexts.

        Args:
            lock_timeout: Timeout in seconds for sync lock acquisition (Issue #1406).
                         If None, uses the default timeout (10.0 seconds).
            timeout_range: Tuple of (min_timeout, max_timeout) for fuzzy timeout (Issue #1533).
                          If specified, timeout will be randomly selected within this range
                          for each lock acquisition attempt to prevent thundering herd effects.
                          If None, uses lock_timeout or default timeout.
            backoff_strategy: Custom function for retry backoff (Issue #1533).
                            Function should accept attempt number and return delay in seconds.
                            If None, uses default exponential backoff.
            adaptive_timeout: Whether to enable adaptive timeout mechanism (Issue #1533).
                            When True, timeout adjusts based on contention history.
                            (Reserved for future implementation)

        Raises:
            ValueError: If timeout_range has min > max, or if any timeout value is negative.
        """
        # Fix for Issue #1599: lock_timeout takes precedence over timeout_range
        # When explicitly provided, lock_timeout should be respected
        if lock_timeout is not None:
            # Validate explicit lock_timeout
            if lock_timeout < 0:
                raise ValueError(
                    f"lock_timeout must be non-negative, got {lock_timeout}"
                )
            self._timeout_range = None
            self._lock_timeout = lock_timeout
        elif timeout_range is not None:
            # Fix for Issue #1533: Validate timeout_range parameters
            min_timeout, max_timeout = timeout_range
            if min_timeout < 0 or max_timeout < 0:
                raise ValueError(
                    f"timeout_range values must be non-negative, got ({min_timeout}, {max_timeout})"
                )
            if min_timeout > max_timeout:
                raise ValueError(
                    f"timeout_range min must be <= max, got ({min_timeout}, {max_timeout})"
                )
            self._timeout_range = timeout_range
            # When using timeout_range, use the midpoint as base timeout
            self._lock_timeout = (min_timeout + max_timeout) / 2
        else:
            self._timeout_range = None
            self._lock_timeout = self._DEFAULT_LOCK_TIMEOUT

        # Fix for Issue #1533: Store backoff strategy
        self._backoff_strategy = backoff_strategy

        # Fix for Issue #1533: Store adaptive timeout flag (for future use)
        self._adaptive_timeout = adaptive_timeout

        # Fix for Issue #1381: Use a single threading.Lock for both sync and async
        # contexts to ensure true mutual exclusion.
        # This prevents the bug where threading.Lock and asyncio.Lock were
        # independent and could be held simultaneously.
        # Fix for Issue #1394: Replaces RLock with Lock to prevent deadlock in
        # async contexts. When using RLock with asyncio.to_thread, if a sync thread
        # holds the RLock and waits for an async event that requires the same lock
        # to be released, a deadlock occurs. Using non-reentrant Lock avoids this.
        # Note: This removes reentrancy support from Issue #1298, but prevents
        # async deadlocks which are more critical.
        self._lock = threading.Lock()
        # Fix for Issue #1381: Per-event-loop asyncio.Event objects for efficient
        # async waiting. These events are set when the lock is released, allowing
        # async coroutines to wait without blocking the event loop.
        # Fix for Issue #1545: _async_events is a regular dict protected by
        # _async_event_init_lock. All accesses to _async_events (including get,
        # set, pop, and iteration) must be guarded by this lock to ensure thread
        # safety during concurrent access across multiple threads.
        self._async_events = {}
        self._async_event_init_lock = threading.Lock()  # Protects ALL _async_events access
        # Fix for Issue #1541: Track cleanup callbacks for automatic event cleanup
        # when event loops are closed to prevent memory leaks
        self._async_event_cleanups = {}

        # Fix for Issue #1538: Initialize lock statistics tracking
        # Use threading.Lock for thread-safe access to statistics
        self._stats_lock = threading.Lock()
        self._acquire_count = 0  # Total number of lock acquisitions
        self._contention_count = 0  # Number of times lock was contended (wait time > 0)
        self._total_wait_time = 0.0  # Total time spent waiting for lock (seconds)
        # Fix for Issue #1612: Track maximum wait time for monitoring systems
        self._max_wait = 0.0  # Maximum time spent waiting for lock (seconds)

        # Fix for Issue #1548: Initialize periodic stats flushing
        # Flush stats every N acquisitions to prevent overflow in long-running processes
        self._flush_threshold = 10000  # Flush stats after every 10,000 acquisitions
        self._last_flush_count = 0  # Track the acquire count at last flush

        # Fix for Issue #1609: Add this instance to the class-level WeakSet
        # and register a single class-level atexit handler (if not already registered)
        # This prevents memory leaks from accumulating atexit handlers while still
        # providing cleanup on exit
        with self.__class__._registry_lock:
            self.__class__._live_locks.add(self)
            if not self.__class__._atexit_handler_registered:
                atexit.register(self.__class__._class_atexit_handler)
                self.__class__._atexit_handler_registered = True

    def _check_lock_at_exit(self):
        """Check this lock instance's state at application exit.

        This method checks if the lock is still held when the application
        is exiting. If the lock is held, it logs a warning and attempts to safely
        release the lock to prevent hangs in other threads during shutdown.

        Fix for Issue #1588: Adds atexit handler to release lock on exit.
        Fix for Issue #1609: Renamed to _check_lock_at_exit to allow for
        class-level atexit handler that iterates over all live locks.
        """
        # Try to check if lock is held using non-blocking acquire
        # If lock is held, we need to handle it
        try:
            # Try to acquire the lock with timeout=0 (non-blocking)
            acquired = self._lock.acquire(blocking=False)
            if acquired:
                # Lock was not held, so we just release it and return
                self._lock.release()
            else:
                # Lock is held by another thread
                # Log a warning and attempt to signal waiting async tasks
                logger = logging.getLogger("flywheel.storage")
                logger.warning(
                    "Application exiting while _AsyncCompatibleLock is still held. "
                    "This may cause hangs or inconsistent state. "
                    "Attempting to signal waiting tasks..."
                )
                # Signal all waiting async events
                with self._async_event_init_lock:
                    for event in list(self._async_events.values()):
                        if not event.is_set():
                            event.set()
        except RuntimeError:
            # Lock operations may fail during shutdown
            # This is acceptable as the process is terminating anyway
            pass
        except Exception as e:
            # Log any unexpected exceptions but don't raise during atexit
            logger = logging.getLogger("flywheel.storage")
            logger.warning(
                f"Unexpected error in _AsyncCompatibleLock atexit handler: {e}"
            )

    @classmethod
    def _class_atexit_handler(cls):
        """Class-level atexit handler that checks all live lock instances.

        This handler is registered only once (when the first lock instance is created)
        and iterates over all live lock instances (tracked via WeakSet) to check
        their state at exit.

        Fix for Issue #1609: Uses single class-level handler instead of per-instance
        handlers to prevent memory leaks. The WeakSet automatically removes garbage
        collected instances, so we only check locks that are still alive.
        """
        # Iterate over all live locks and check their state
        # We create a list to avoid "WeakSet changed size during iteration" errors
        for lock in list(cls._live_locks):
            try:
                lock._check_lock_at_exit()
            except Exception as e:
                # Log but continue checking other locks
                logger = logging.getLogger("flywheel.storage")
                logger.warning(
                    f"Error checking lock state during atexit: {e}"
                )

    def _get_async_event(self):
        """Get or create the asyncio.Event for the current event loop.

        This lazy initialization ensures we only create asyncio.Event when
        needed, avoiding RuntimeError in purely synchronous contexts.

        Fix for Issue #1381: Each event loop gets its own Event object for
        efficient waiting without blocking the event loop.
        Fix for Issue #1380: Always acquires the lock to prevent race condition
        where GC could clean up the event between get() and return.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop - raise a clear error
            raise RuntimeError(
                "_AsyncCompatibleLock._get_async_event must be called from "
                "an async context with a running event loop"
            )

        # Fix for Issue #1526: Create Event inside the lock to ensure atomic initialization
        # with correct state based on current lock state. This prevents race condition
        # where Event is created without knowledge of lock state, making the subsequent
        # check-and-set fragile.
        # Fix for Issue #1476: Double-check inside lock prevents race where
        # multiple threads create different events.
        # Fix for Issue #1480: Only one thread's event gets registered; others
        # are discarded to prevent event state overwriting.
        # Fix for Issue #1535: Always hold lock during entire check-and-return
        # sequence to prevent TOCTOU race condition where GC could clean up
        # the event between get() and return, or multiple threads could
        # create and overwrite events.

        with self._async_event_init_lock:
            # Check with lock (prevents race condition)
            # Fix for Issue #1535: Must hold lock during get() to prevent
            # GC from cleaning up the event between get() and return
            existing_event = self._async_events.get(current_loop)
            if existing_event is not None:
                # Another thread already created an event, use it instead
                # Fix for Issue #1535: Return while still holding lock to
                # ensure the reference remains valid
                return existing_event

            # Fix for Issue #1401: Always create Event unset, then set it if lock
            # is available. This eliminates race condition where lock state changes
            # between check and event creation. By checking AFTER event creation,
            # we ensure the event state reflects the current reality at return time.
            # Replaces previous logic (Issue #1446, #1475, #1526) that checked
            # lock.locked() before creating the event.
            new_event = asyncio.Event()
            # Set the event if lock is currently available
            # This check happens AFTER event creation, minimizing the window
            # for state changes. Even if state changes after this, the
            # waiting logic in __aenter__ will handle it correctly.
            if not self._lock.locked():
                new_event.set()

            # Register our event
            self._async_events[current_loop] = new_event

            # Fix for Issue #1541: Register cleanup callback to automatically
            # remove the event from _async_events when the loop is closed/garbage
            # collected. This prevents memory leaks in long-running programs.
            def cleanup_event(loop_ref):
                """Cleanup callback to remove event when loop is garbage collected."""
                with self._async_event_init_lock:
                    self._async_events.pop(loop_ref, None)
                    self._async_event_cleanups.pop(loop_ref, None)

            # Use weakref.finalize to register cleanup callback
            # The callback will be triggered when the event loop is garbage collected
            cleanup = weakref.finalize(current_loop, cleanup_event, current_loop)
            self._async_event_cleanups[current_loop] = cleanup

            # Fix for Issue #1535: Return while still holding lock to ensure
            # the reference remains valid and prevent race conditions
            return new_event

    def __enter__(self):
        """Support synchronous context manager protocol.

        Uses threading.Lock directly for simple, reliable cross-thread
        synchronization and ensures mutual exclusion with async contexts.

        Fix for Issue #1290: Uses threading.Lock to prevent
        deadlock risks from event loop reuse and ensure true
        cross-thread mutual exclusion.
        Fix for Issue #1344: Uses try-finally to ensure atomic state management
        and prevent race conditions between lock acquisition and state update.
        Fix for Issue #1381: Uses unified threading.Lock for both sync and async
        to ensure true mutual exclusion.
        Fix for Issue #1394: Uses non-reentrant Lock instead of RLock to prevent
        deadlock in async contexts where a sync thread holding the lock waits for
        an async event.
        Fix for Issue #1406: Uses timeout in acquire() to prevent potential deadlock
        when lock is contested. The lock acquisition is time-bound to avoid freezing
        the thread indefinitely.
        Fix for Issue #1402: Raises StorageTimeoutError instead of TimeoutError for
        consistency with async contexts.
        Fix for Issue #1481: Documents that when StorageTimeoutError is raised due
        to timeout, the lock is NOT held by the caller. This prevents confusion where
        callers might mistakenly believe they hold the lock after catching the exception.
        Fix for Issue #1498: Implements exponential backoff for lock acquisition retries
        to improve throughput under high contention.
        Fix for Issue #1533: Implements fuzzy timeout mechanism with configurable range
        and custom backoff strategies to prevent thundering herd effects.
        """
        import random
        import time

        # Fix for Issue #1538: Track wait time for statistics
        acquire_start_time = time.time()
        had_contention = False

        # Fix for Issue #1498: Implement exponential backoff for retries
        # This improves throughput under high contention by retrying with
        # increasing delays instead of failing immediately on the first timeout.
        MAX_RETRIES = 3
        BASE_DELAY = 0.0  # Base delay in seconds
        MAX_DELAY = 0.1   # Maximum delay for first retry

        for attempt in range(MAX_RETRIES):
            # Fix for Issue #1533: Use fuzzy timeout if timeout_range is specified
            # This prevents thundering herd effects by randomizing timeout within range
            if self._timeout_range is not None:
                min_timeout, max_timeout = self._timeout_range
                timeout_for_attempt = random.uniform(min_timeout, max_timeout)
            else:
                timeout_for_attempt = self._lock_timeout

            # Fix for Issue #1540: Validate timeout is positive to prevent race condition
            # where acquire() could be called with invalid timeout and cause indefinite blocking.
            # This defensive check ensures we never call acquire(timeout <= 0) which could
            # behave like acquire(blocking=True) and block indefinitely.
            assert timeout_for_attempt > 0, (
                f"Lock timeout must be positive, got {timeout_for_attempt}. "
                "This could cause indefinite blocking."
            )

            # Acquire the lock with timeout
            # Fix for Issue #1406: Use acquire(timeout=X) instead of acquire() to
            # prevent indefinite blocking. If the lock cannot be acquired within
            # the timeout period, raise a StorageTimeoutError to prevent deadlock.
            # Fix for Issue #1402: Raise StorageTimeoutError instead of TimeoutError
            # for consistency with async contexts.
            # Fix for Issue #1450: Simplified to just acquire and return self.
            # The try-except wrapping `return self` was problematic because:
            # 1. `return self` cannot raise an exception under normal circumstances
            # 2. If an exception somehow occurred, releasing the lock here would
            #    cause a double release when __exit__ is called, triggering RuntimeError
            # Fix for Issue #1465: Added defensive try-finally to ensure the lock is
            # released if an exception occurs between acquire() and return self.
            # This prevents lock leaks in the extremely rare case where an exception
            # could occur after the lock is acquired but before __enter__ returns.
            # Fix for Issue #1481: CRITICAL: When acquire(timeout=X) returns False (timeout),
            # the lock is NOT held. We raise StorageTimeoutError to signal this, and callers
            # MUST NOT assume they hold the lock after catching this exception.
            # Fix for Issue #1540: CRITICAL: ALWAYS use timeout parameter in acquire() to prevent
            # indefinite blocking. Never call acquire() without timeout=... in the retry loop.
            acquired = self._lock.acquire(timeout=timeout_for_attempt)
            if acquired:
                # Lock acquired successfully
                # Fix for Issue #1538: Record statistics
                wait_time = time.time() - acquire_start_time
                with self._stats_lock:
                    self._acquire_count += 1
                    if wait_time > 0:
                        self._contention_count += 1
                        self._total_wait_time += wait_time
                        # Fix for Issue #1612: Update maximum wait time
                        if wait_time > self._max_wait:
                            self._max_wait = wait_time

                    # Fix for Issue #1548: Check if we should flush stats periodically
                    # This prevents integer overflow in long-running processes
                    if self._acquire_count - self._last_flush_count >= self._flush_threshold:
                        # Capture stats for logging
                        stats_to_log = {
                            'acquire_count': self._acquire_count,
                            'contention_count': self._contention_count,
                            'total_wait_time': self._total_wait_time
                        }

                # Flush stats outside the lock to avoid holding it during I/O
                if self._acquire_count - self._last_flush_count >= self._flush_threshold:
                    # Log the stats with structured data for monitoring
                    logger.info(
                        "Flushing lock statistics (periodic)",
                        extra={
                            'component': 'lock',
                            'op': 'flush_stats',
                            'stats_flushed': stats_to_log
                        }
                    )

                    # Reset counters
                    with self._stats_lock:
                        self._acquire_count = 0
                        self._contention_count = 0
                        self._total_wait_time = 0.0
                        self._max_wait = 0.0
                        self._last_flush_count = 0

                # Fix for Issue #1502: Log with structured data for monitoring
                # Fix for Issue #1582: Add structured logging context with wait_time and attempts
                logger.debug(
                    "Lock acquired successfully",
                    extra={
                        'component': 'storage',
                        'op': 'lock_acquire',
                        'lock_wait_time': wait_time,
                        'attempts': attempt + 1
                    }
                )

                # Fix for Issue #1587: Emit structured JSON log when DEBUG_STORAGE is active
                # This provides machine-readable logs for monitoring tools (Datadog, ELK)
                # to visualize bottlenecks and diagnose contention issues post-mortem
                # Fix for Issue #1603: Add duration and caller fields for better compatibility
                if os.environ.get('DEBUG_STORAGE'):
                    logger.info(
                        "Lock contention event",
                        extra={
                            'event': 'lock_wait',
                            'wait_time': wait_time,
                            'duration': wait_time,  # Alias for compatibility
                            'acquired': True,
                            'thread': threading.current_thread().name,
                            'caller': threading.current_thread().name,  # Alias for compatibility
                            'attempts': attempt + 1,
                            'lock_timeout': self._lock_timeout
                        }
                    )
                # Fix for Issue #1531: Use try-finally to ensure lock is released
                # if an exception occurs between acquire() and return self.
                # While return self normally cannot raise, this defensive pattern
                # ensures lock cleanup in edge cases (e.g., signal handlers, async
                # edge cases, or future code modifications).
                # The lock will be normally released by __exit__ when the context exits,
                # but this ensures cleanup even if __exit__ is never reached.
                try:
                    return self
                except BaseException:
                    # Exception occurred after acquiring lock but before returning.
                    # Release the lock to prevent deadlock/leak.
                    self._lock.release()
                    raise

            # Lock acquisition timed out - implement backoff retry
            # Fix for Issue #1498: Instead of failing immediately, retry with
            # exponential backoff to reduce contention and improve throughput.
            # Fix for Issue #1533: Use custom backoff strategy if provided
            # Fix for Issue #1572: Add structured logging for contention monitoring
            if attempt < MAX_RETRIES - 1:
                if self._backoff_strategy is not None:
                    # Use custom backoff strategy
                    delay = self._backoff_strategy(attempt)
                else:
                    # Default exponential backoff
                    # Each retry uses a longer maximum delay: 0.1s, 0.2s, 0.4s
                    delay = random.uniform(BASE_DELAY, MAX_DELAY * (2 ** attempt))

                # Fix for Issue #1572: Log retry attempt with structured data
                # This allows monitoring of lock contention and retry behavior
                logger.debug(
                    f"Lock acquisition attempt {attempt + 1}/{MAX_RETRIES} timed out, "
                    f"retrying after backoff delay",
                    extra={
                        'component': 'lock',
                        'op': 'acquire_retry',
                        'attempt': attempt + 1,
                        'max_retries': MAX_RETRIES,
                        'timeout': timeout_for_attempt,
                        'backoff_delay': delay
                    }
                )

                time.sleep(delay)

        # All retries exhausted - lock is NOT held by current thread
        # Calculate total wait time
        total_wait_time = time.time() - acquire_start_time

        # Fix for Issue #1587: Emit structured JSON log when DEBUG_STORAGE is active
        # Log the failed acquisition attempt for monitoring and analysis
        # Fix for Issue #1603: Add duration and caller fields for better compatibility
        if os.environ.get('DEBUG_STORAGE'):
            logger.info(
                "Lock contention event - failed to acquire",
                extra={
                    'event': 'lock_wait',
                    'wait_time': total_wait_time,
                    'duration': total_wait_time,  # Alias for compatibility
                    'acquired': False,
                    'thread': threading.current_thread().name,
                    'caller': threading.current_thread().name,  # Alias for compatibility
                    'attempts': MAX_RETRIES,
                    'lock_timeout': self._lock_timeout
                }
            )

        timeout_msg = (
            f"{timeout_for_attempt:.2f}" if self._timeout_range is not None
            else f"{self._lock_timeout}"
        )
        raise StorageTimeoutError(
            f"Could not acquire lock within {timeout_msg} seconds "
            f"after {MAX_RETRIES} attempts. "
            "This may indicate a deadlock or very high contention. "
            "IMPORTANT: The lock is NOT held after this exception."
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock when exiting sync context.

        Simply releases the threading.Lock and wakes up any waiting async tasks.

        Fix for Issue #1181: Only releases lock if it was acquired, preventing
        RuntimeError when __exit__ is called without successful __enter__.
        Fix for Issue #1290: Uses threading.Lock for simple, reliable cleanup.
        Fix for Issue #1381: Signals all waiting async events that lock is available.
        Fix for Issue #1394: Uses non-reentrant Lock to prevent deadlock in async
        contexts where a sync thread holding the lock waits for an async event.
        Fix for Issue #1410: Removes _is_owned() check (RLock-specific) since
        threading.Lock does not support reentrancy or have _is_owned() method.
        Fix for Issue #1416: Signals events while holding lock to prevent race
        condition where another thread acquires lock and resets event before
        signaling completes.
        Fix for Issue #1431: Acquires _async_event_init_lock before signaling events
        to prevent race condition where another thread modifies _async_events during
        iteration.
        Fix for Issue #1481: Safe to call even when lock was not acquired (e.g., after
        StorageTimeoutError from __enter__). The method catches RuntimeError from
        release() to handle the case where __enter__ timed out and the lock was
        never acquired.
        """
        # For threading.Lock (non-reentrant), we need defensive handling.
        # Fix for Issue #1181: Only releases lock if it was acquired, preventing
        # RuntimeError when __exit__ is called without successful __enter__.
        # Fix for Issue #1450: Simplified __enter__ to just acquire and return self,
        # removing the problematic try-except that could cause double release.
        # Fix for Issue #1465: Added defensive exception handling in __exit__ to prevent
        # lock leaks in edge cases where __enter__ might fail after acquiring the lock.
        # While threading.Lock.release() raises RuntimeError if the lock isn't held,
        # we catch this to handle edge cases gracefully.
        # Fix for Issue #1381: Signal all async events that the lock is available
        # This wakes up any async tasks waiting on the lock
        # Fix for Issue #1391: Create snapshot to avoid RuntimeError during iteration
        # Fix for Issue #1416: Signal events BEFORE releasing lock to prevent
        # race condition where another thread acquires lock and clears event
        # Fix for Issue #1431: Acquire _async_event_init_lock before iterating to
        # prevent race condition where another thread modifies _async_events
        with self._async_event_init_lock:
            for event in list(self._async_events.values()):
                if not event.is_set():
                    event.set()
        try:
            self._lock.release()
        except RuntimeError:
            # Lock is not held by the current thread
            # This can happen if __exit__ is called without a successful __enter__
            # (e.g., if __enter__ raised StorageTimeoutError after timeout)
            # Fix for Issue #1481: This is expected behavior after timeout - the lock
            # was never acquired, so we silently handle the release attempt.
            pass
        return False

    async def __aenter__(self):
        """Support asynchronous context manager protocol.

        Uses threading.Lock with asyncio.Event for async contexts to ensure
        true mutual exclusion with sync contexts while preventing event loop blocking.

        Fix for Issue #1316: Uses threading.Lock + asyncio.Event instead of
        asyncio.Lock to ensure mutual exclusion with sync contexts.
        Fix for Issue #1360: Uses try-except to ensure atomic state management.
        If an exception occurs after acquire() but before __aenter__ returns,
        we need to ensure the lock is released to prevent deadlock.
        Fix for Issue #1381: Uses unified threading.Lock for both sync and async
        to ensure true mutual exclusion. Uses asyncio.Event for efficient async waiting.
        Fix for Issue #1385: Checks lock availability immediately after wait() to
        prevent missed wake-ups. If lock is released between acquire() failure and
        the next wait(), re-checking prevents indefinite blocking.
        Fix for Issue #1394: Uses non-reentrant Lock instead of RLock to prevent
        deadlock when sync thread holding lock waits for async event.
        Fix for Issue #1538: Track lock acquisition statistics.
        Fix for Issue #1498: Implements exponential backoff for lock acquisition retries
        to improve throughput under high contention.
        Fix for Issue #1573: Implements fuzzy timeout mechanism with configurable range
        and custom backoff strategies in async contexts to prevent thundering herd effects.
        """
        import random
        import time

        # Fix for Issue #1538: Track wait time for statistics
        acquire_start_time = time.time()

        # Fix for Issue #1381: Get the event for this event loop
        async_event = self._get_async_event()

        # Fix for Issue #1498: Implement exponential backoff for retries
        # This improves throughput under high contention by retrying with
        # increasing delays instead of waiting indefinitely.
        MAX_RETRIES = 3
        BASE_DELAY = 0.0  # Base delay in seconds
        MAX_DELAY = 0.1   # Maximum delay for first retry

        for attempt in range(MAX_RETRIES):
            # Fix for Issue #1573: Calculate timeout for this attempt
            # Use fuzzy timeout if timeout_range is specified
            if self._timeout_range is not None:
                min_timeout, max_timeout = self._timeout_range
                timeout_for_attempt = random.uniform(min_timeout, max_timeout)
            else:
                timeout_for_attempt = self._lock_timeout

            # Try to acquire the lock with timeout
            # Instead of waiting indefinitely, we use asyncio.wait_for with timeout
            try:
                # Wait for the event to be set (indicating lock is available)
                # with timeout to prevent indefinite blocking
                await asyncio.wait_for(async_event.wait(), timeout=timeout_for_attempt)

                # Event is set, try to acquire the lock with non-blocking attempt
                acquired = self._lock.acquire(blocking=False)
                if acquired:
                    # Lock acquired successfully
                    # Fix for Issue #1538: Record statistics
                    wait_time = time.time() - acquire_start_time
                    with self._stats_lock:
                        self._acquire_count += 1
                        if wait_time > 0:
                            self._contention_count += 1
                            self._total_wait_time += wait_time
                            # Fix for Issue #1612: Update maximum wait time
                            if wait_time > self._max_wait:
                                self._max_wait = wait_time

                        # Fix for Issue #1548: Check if we should flush stats periodically
                        # This prevents integer overflow in long-running processes
                        if self._acquire_count - self._last_flush_count >= self._flush_threshold:
                            # Capture stats for logging
                            stats_to_log = {
                                'acquire_count': self._acquire_count,
                                'contention_count': self._contention_count,
                                'total_wait_time': self._total_wait_time
                            }

                    # Flush stats outside the lock to avoid holding it during I/O
                    if self._acquire_count - self._last_flush_count >= self._flush_threshold:
                        # Log the stats with structured data for monitoring
                        logger.info(
                            "Flushing lock statistics (periodic)",
                            extra={
                                'component': 'lock',
                                'op': 'flush_stats',
                                'stats_flushed': stats_to_log
                            }
                        )

                        # Reset counters
                        with self._stats_lock:
                            self._acquire_count = 0
                            self._contention_count = 0
                            self._total_wait_time = 0.0
                            self._max_wait = 0.0
                            self._last_flush_count = 0

                    # Fix for Issue #1582: Add structured logging context with wait_time and attempts
                    logger.debug(
                        "Async lock acquired successfully",
                        extra={
                            'component': 'storage',
                            'op': 'async_lock_acquire',
                            'lock_wait_time': wait_time,
                            'attempts': attempt + 1
                        }
                    )

                    # Fix for Issue #1587: Emit structured JSON log when DEBUG_STORAGE is active
                    # This provides machine-readable logs for monitoring tools (Datadog, ELK)
                    # to visualize bottlenecks and diagnose contention issues post-mortem
                    # Fix for Issue #1603: Add duration and caller fields for better compatibility
                    if os.environ.get('DEBUG_STORAGE'):
                        logger.info(
                            "Lock contention event",
                            extra={
                                'event': 'lock_wait',
                                'wait_time': wait_time,
                                'duration': wait_time,  # Alias for compatibility
                                'acquired': True,
                                'thread': threading.current_thread().name,
                                'caller': threading.current_thread().name,  # Alias for compatibility
                                'attempts': attempt + 1,
                                'lock_timeout': self._lock_timeout,
                                'context': 'async'
                            }
                        )

                    try:
                        # Clear the event so other async tasks know the lock is taken
                        async_event.clear()
                        return self
                    except BaseException:
                        # If any exception occurs before we return, release the lock
                        # and set the event again to maintain consistent state
                        self._lock.release()
                        async_event.set()
                        raise
                else:
                    # Lock is held by another thread/sync context
                    # Check if the lock is still held before waiting again
                    if not self._lock.locked():
                        # Lock became available, set event to wake up immediately
                        async_event.set()
                    # Continue to next iteration to retry

            except asyncio.TimeoutError:
                # Timeout waiting for event - implement backoff retry
                # Fix for Issue #1498: Instead of failing immediately, retry with
                # exponential backoff to reduce contention and improve throughput.
                # Fix for Issue #1573: Use custom backoff strategy if provided
                # Fix for Issue #1572: Add structured logging for contention monitoring
                if attempt < MAX_RETRIES - 1:
                    if self._backoff_strategy is not None:
                        # Use custom backoff strategy
                        delay = self._backoff_strategy(attempt)
                    else:
                        # Default exponential backoff
                        # Each retry uses a longer maximum delay: 0.1s, 0.2s, 0.4s
                        delay = random.uniform(BASE_DELAY, MAX_DELAY * (2 ** attempt))

                    # Fix for Issue #1572: Log retry attempt with structured data
                    # This allows monitoring of lock contention and retry behavior
                    logger.debug(
                        f"Async lock acquisition attempt {attempt + 1}/{MAX_RETRIES} timed out, "
                        f"retrying after backoff delay",
                        extra={
                            'component': 'lock',
                            'op': 'async_acquire_retry',
                            'attempt': attempt + 1,
                            'max_retries': MAX_RETRIES,
                            'timeout': timeout_for_attempt,
                            'backoff_delay': delay
                        }
                    )

                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted - raise StorageTimeoutError
                    # Calculate total wait time
                    total_wait_time = time.time() - acquire_start_time

                    # Fix for Issue #1587: Emit structured JSON log when DEBUG_STORAGE is active
                    # Log the failed acquisition attempt for monitoring and analysis
                    # Fix for Issue #1603: Add duration and caller fields for better compatibility
                    if os.environ.get('DEBUG_STORAGE'):
                        logger.info(
                            "Lock contention event - failed to acquire",
                            extra={
                                'event': 'lock_wait',
                                'wait_time': total_wait_time,
                                'duration': total_wait_time,  # Alias for compatibility
                                'acquired': False,
                                'thread': threading.current_thread().name,
                                'caller': threading.current_thread().name,  # Alias for compatibility
                                'attempts': MAX_RETRIES,
                                'lock_timeout': self._lock_timeout,
                                'context': 'async'
                            }
                        )

                    timeout_msg = (
                        f"{timeout_for_attempt:.2f}" if self._timeout_range is not None
                        else f"{self._lock_timeout}"
                    )
                    raise StorageTimeoutError(
                        f"Could not acquire lock within {timeout_msg} seconds "
                        f"after {MAX_RETRIES} attempts. "
                        "This may indicate a deadlock or very high contention. "
                        "IMPORTANT: The lock is NOT held after this exception."
                    )

        # Should not reach here, but if we do, raise timeout error
        raise StorageTimeoutError(
            f"Could not acquire lock after {MAX_RETRIES} attempts. "
            "IMPORTANT: The lock is NOT held after this exception."
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock when exiting async context.

        Releases the threading.Lock and signals other waiting tasks.

        Fix for Issue #1181: Only releases lock if it was acquired, preventing
        RuntimeError when __aexit__ is called without successful __aenter__.
        Fix for Issue #1316: Uses threading.Lock for async context cleanup.
        Fix for Issue #1381: Uses unified threading.Lock and signals waiting tasks.
        Fix for Issue #1394: Uses non-reentrant Lock to prevent deadlock in async
        contexts where a sync thread holding the lock waits for an async event.
        Fix for Issue #1410: Removes _is_owned() check (RLock-specific) since
        threading.Lock does not support reentrancy or have _is_owned() method.
        Fix for Issue #1416: Signals events while holding lock to prevent race
        condition where another thread acquires lock and resets event before
        signaling completes.
        Fix for Issue #1436: Acquires _async_event_init_lock before signaling events
        to prevent race condition where another thread modifies _async_events during
        iteration.
        """
        # For threading.Lock (non-reentrant), we release unconditionally.
        # This is safe because __aexit__ is only called after __aenter__ succeeds,
        # which means we hold the lock. The try-except in __aenter__ ensures
        # the lock is released if __aenter__ fails before returning.
        # Fix for Issue #1381: Signal all waiting async events that the lock is available
        # This wakes up any other async tasks waiting on the lock
        # Fix for Issue #1391: Create snapshot to avoid RuntimeError during iteration
        # Fix for Issue #1416: Signal events BEFORE releasing lock to prevent
        # race condition where another thread acquires lock and clears event
        # Fix for Issue #1436: Acquire _async_event_init_lock before iterating to
        # prevent race condition where another thread modifies _async_events
        with self._async_event_init_lock:
            for event in list(self._async_events.values()):
                if not event.is_set():
                    event.set()
        self._lock.release()
        return False

    def timeout(self, new_timeout: float):
        """Context manager to temporarily override the lock timeout.

        This allows for flexible timeout handling in different contexts.
        Some quick reads need short timeouts, while long writes need longer ones.

        Args:
            new_timeout: The new timeout value in seconds to use within the context.

        Returns:
            A context manager that temporarily overrides the lock timeout.

        Example:
            >>> lock = _AsyncCompatibleLock(lock_timeout=10.0)
            >>> with lock.timeout(new_timeout=5.0):
            ...     # Lock timeout is 5.0 seconds within this block
            ...     with lock:
            ...         # Critical section
            ...         pass
            >>> # Lock timeout is restored to 10.0 seconds here

        Fix for Issue #1463: Implements timeout override context manager.
        """
        class _TimeoutOverride:
            """Internal context manager for timeout override."""

            def __init__(self, lock, original_timeout, new_timeout):
                self._lock = lock
                self._original_timeout = original_timeout
                self._new_timeout = new_timeout

            def __enter__(self):
                """Override the lock timeout."""
                self._lock._lock_timeout = self._new_timeout
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                """Restore the original lock timeout."""
                self._lock._lock_timeout = self._original_timeout
                return False

        return _TimeoutOverride(self, self._lock_timeout, new_timeout)

    def cleanup_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Explicitly clean up the asyncio.Event for a specific event loop.

        This method allows for explicit cleanup of Event objects when an event loop
        is closed or no longer needed. While WeakKeyDictionary will automatically
        handle garbage collection, explicit cleanup is more predictable and beneficial
        for resource management in long-running applications or resource-constrained
        environments (e.g., embedded Python).

        Args:
            loop: The event loop whose Event should be removed.

        Example:
            >>> lock = _AsyncCompatibleLock()
            >>> loop = asyncio.get_running_loop()
            >>> async with lock:
            ...     # Use the lock
            ...     pass
            >>> # When the loop is being closed
            >>> lock.cleanup_loop(loop)

        Fix for Issue #1493: Implements explicit cleanup for event loop resources.
        Fix for Issue #1541: Also cleans up the automatic cleanup callback to prevent
        keeping unnecessary references.
        """
        # Use the same lock that protects _async_events modifications
        # to prevent race conditions with _get_async_event()
        with self._async_event_init_lock:
            # Use pop() with default to safely handle case where loop isn't in dict
            # This is thread-safe and won't raise KeyError
            self._async_events.pop(loop, None)
            # Fix for Issue #1541: Clean up the weakref.finalize callback
            self._async_event_cleanups.pop(loop, None)

    def get_stats(self) -> dict:
        """Get lock statistics for monitoring and performance tuning.

        Returns a dictionary containing:
        - acquire_count: Total number of successful lock acquisitions
        - contention_count: Number of acquisitions that had to wait (> 0 seconds)
        - total_wait_time: Total time spent waiting for the lock (seconds)
        - average_wait_time: Average wait time per acquisition (seconds)
        - contention_rate: Ratio of contentions to acquisitions (0.0 to 1.0)

        These statistics help identify lock contention issues and optimize
        performance by understanding how often threads/tasks compete for the lock.

        Returns:
            dict: Statistics dictionary with keys 'acquire_count', 'contention_count',
                  'total_wait_time', 'average_wait_time', and 'contention_rate'.

        Example:
            >>> lock = _AsyncCompatibleLock()
            >>> with lock:
            ...     pass
            >>> stats = lock.get_stats()
            >>> print(f"Acquired {stats['acquire_count']} times")
            >>> print(f"Contention {stats['contention_count']} times")
            >>> print(f"Total wait: {stats['total_wait_time']:.3f}s")
            >>> print(f"Avg wait: {stats['average_wait_time']:.3f}s")
            >>> print(f"Contention rate: {stats['contention_rate']:.1%}")

        Fix for Issue #1538: Implements lock statistics tracking.
        Fix for Issue #1552: Adds average_wait_time and contention_rate.
        """
        with self._stats_lock:
            average_wait_time = (
                self._total_wait_time / self._acquire_count
                if self._acquire_count > 0
                else 0.0
            )
            contention_rate = (
                self._contention_count / self._acquire_count
                if self._acquire_count > 0
                else 0.0
            )
            return {
                'acquire_count': self._acquire_count,
                'contention_count': self._contention_count,
                'total_wait_time': self._total_wait_time,
                'average_wait_time': average_wait_time,
                'contention_rate': contention_rate,
            }

    def get_lock_stats(self) -> dict:
        """Get simplified lock statistics for monitoring systems.

        Returns a dictionary containing:
        - total_waits: Number of times lock acquisition had to wait (contention_count)
        - total_wait_time: Total time spent waiting for the lock (seconds)
        - max_wait: Maximum time spent waiting for the lock (seconds)

        This method provides a simplified interface for monitoring systems to poll
        lock contention metrics programmatically without parsing logs. Unlike get_stats(),
        which provides detailed analysis metrics, this method focuses on the essential
        metrics needed for dashboards and alerting.

        The returned metrics allow monitoring systems to:
        - Track lock contention over time
        - Alert on high wait times
        - Build dashboards showing lock performance
        - Correlate lock contention with other system metrics

        Returns:
            dict: Statistics dictionary with keys 'total_waits', 'total_wait_time',
                  and 'max_wait'. Returns a copy to prevent external modification.

        Example:
            >>> lock = _AsyncCompatibleLock()
            >>> with lock:
            ...     pass
            >>> stats = lock.get_lock_stats()
            >>> print(f"Waits: {stats['total_waits']}")
            >>> print(f"Total wait: {stats['total_wait_time']:.3f}s")
            >>> print(f"Max wait: {stats['max_wait']:.3f}s")

        Fix for Issue #1612: Adds metrics export for lock contention to enable
        programmatic access for monitoring systems without parsing logs.
        """
        with self._stats_lock:
            # Return a copy to prevent external modification of internal state
            return {
                'total_waits': self._contention_count,
                'total_wait_time': self._total_wait_time,
                'max_wait': self._max_wait,
            }

    def reset_stats(self) -> None:
        """Reset lock statistics to zero.

        This is useful for periodic monitoring or testing scenarios where
        you want to measure statistics for a specific time window.

        Example:
            >>> lock = _AsyncCompatibleLock()
            >>> # Run some operations...
            >>> with lock:
            ...     pass
            >>> # Reset for next measurement period
            >>> lock.reset_stats()

        Fix for Issue #1538: Implements statistics reset functionality.
        Fix for Issue #1612: Also resets max_wait.
        """
        with self._stats_lock:
            self._acquire_count = 0
            self._contention_count = 0
            self._total_wait_time = 0.0
            self._max_wait = 0.0

    def flush_stats(self) -> None:
        """Flush statistics by logging current metrics and resetting counters.

        This method is useful for long-running processes to prevent integer
        overflow and enable time-series analysis (e.g., 'locks per second').
        It logs the current statistics and resets the counters to zero.

        Example:
            >>> lock = _AsyncCompatibleLock()
            >>> # Run many operations...
            >>> # Flush stats periodically
            >>> lock.flush_stats()

        Fix for Issue #1548: Implements periodic stats flushing for long-running processes.
        Fix for Issue #1612: Also flushes and resets max_wait.
        """
        with self._stats_lock:
            # Capture current stats before resetting
            current_acquire_count = self._acquire_count
            current_contention_count = self._contention_count
            current_total_wait_time = self._total_wait_time
            current_max_wait = self._max_wait

            # Log the stats with structured data for monitoring
            logger.info(
                "Flushing lock statistics",
                extra={
                    'component': 'lock',
                    'op': 'flush_stats',
                    'stats_flushed': {
                        'acquire_count': current_acquire_count,
                        'contention_count': current_contention_count,
                        'total_wait_time': current_total_wait_time,
                        'max_wait': current_max_wait
                    }
                }
            )

            # Reset counters
            self._acquire_count = 0
            self._contention_count = 0
            self._total_wait_time = 0.0
            self._max_wait = 0.0
            self._last_flush_count = 0

    def log_stats(self, message: str = "Lock statistics") -> None:
        """Log lock statistics for monitoring and diagnostics.

        This method outputs the current lock statistics to the logger,
        which is useful for monitoring lock contention in production systems
        or debugging performance issues during development.

        Args:
            message: Optional custom message to prefix the log output.

        Example:
            >>> lock = _AsyncCompatibleLock()
            >>> # Use the lock...
            >>> with lock:
            ...     pass
            >>> # Log statistics
            >>> lock.log_stats()
            >>> lock.log_stats(message="Custom prefix")

        Fix for Issue #1552: Implements automatic lock statistics reporting.
        """
        stats = self.get_stats()
        logger.info(
            message,
            extra={
                'component': 'lock',
                'op': 'log_stats',
                'lock_stats': {
                    'acquire_count': stats['acquire_count'],
                    'contention_count': stats['contention_count'],
                    'total_wait_time': stats['total_wait_time'],
                    'average_wait_time': stats['average_wait_time'],
                    'contention_rate': stats['contention_rate'],
                }
            }
        )


class _TransactionContext:
    """Context manager for storage transactions with rollback support.

    This class provides transactional semantics for storage operations.
    It saves the state before entering the context and rolls back if
    an exception occurs.

    Fix for Issue #1453: Implements transaction context manager.
    """

    def __init__(self, storage):
        """Initialize the transaction context.

        Args:
            storage: The FileStorage instance to manage transactions for.
        """
        self._storage = storage
        self._saved_todos = None
        self._saved_next_id = None
        self._saved_cache = None

    def __enter__(self):
        """Enter the transaction context.

        Acquires the storage lock and saves the current state for rollback.
        """
        self._storage._lock.acquire()
        # Save current state for rollback
        self._saved_todos = list(self._storage._todos)
        self._saved_next_id = self._storage._next_id
        self._saved_cache = dict(self._storage._cache) if self._storage._cache_enabled else None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the transaction context.

        If an exception occurred, rolls back to the saved state.
        Otherwise, commits the changes.
        Always releases the lock.

        Args:
            exc_type: The type of exception raised, if any.
            exc_val: The exception instance raised, if any.
            exc_tb: The traceback object, if any.

        Returns:
            bool: False to propagate exceptions.
        """
        try:
            if exc_type is not None:
                # Exception occurred, rollback to saved state
                self._storage._todos = self._saved_todos
                self._storage._next_id = self._saved_next_id
                if self._storage._cache_enabled and self._saved_cache is not None:
                    self._storage._cache = self._saved_cache
                    self._storage._cache_dirty = False
            # If no exception, changes are already applied
        finally:
            # Always release the lock
            self._storage._lock.release()
        # Propagate exceptions
        return False


class _AsyncContextError(RuntimeError):
    """Exception raised when sync method is called from async context.

    This is a specific exception type to distinguish from other RuntimeError
    exceptions that might be raised by asyncio.

    Fix for Issue #1144: Uses a unique exception type instead of relying on
    fragile string matching to differentiate between our custom error and
    asyncio's RuntimeError.
    """
    pass


class IOMetrics:
    """Metrics tracker for I/O operations (Issue #1053).

    This class tracks performance metrics for I/O operations including:
    - Operation duration
    - Retry count
    - Error types
    - Success/failure rates

    Metrics can be logged via the FW_STORAGE_METRICS_LOG environment variable.

    Fix for Issue #1061: Operations list uses a circular buffer to prevent
    unbounded memory growth in long-running processes.
    """

    # Maximum number of operations to keep in memory (circular buffer size)
    MAX_OPERATIONS = 1000

    def __init__(self):
        """Initialize an empty metrics tracker with circular buffer.

        Fix for Issue #1065: Use deque with maxlen for O(1) circular buffer
        performance instead of list with O(N) pop(0).
        Fix for Issue #1080: Use asyncio.Lock for async context safety.
        Fix for Issue #1091: Use threading.Lock for sync/async context safety.
        Fix for Issue #1097: Use custom lock wrapper that supports both
        sync and async context managers.
        Fix for Issue #1109: Use threading.Lock for sync methods to work in async contexts.
        Fix for Issue #1116: Use _AsyncCompatibleLock for async-safe record_operation.
        Fix for Issue #1124: Use pure asyncio.Lock to prevent event loop blocking
        in async contexts. IOMetrics now uses async-only locking mechanism.
        Fix for Issue #1135: Use threading.Lock for sync methods to prevent
        RuntimeError when called from threads with running event loop.
        Fix for Issue #1139: Lazy-initialize asyncio.Lock to prevent RuntimeError
        in sync contexts. Only create when async methods are called.
        Fix for Issue #1150: Use per-event-loop locks to handle multi-threaded
        environments where different threads have different event loops.
        Fix for Issue #1310: Separate locks for initialization (_init_lock) and
        sync operations (_sync_operation_lock) to maintain consistency with
        documented async-only locking design while preserving thread safety
        for sync contexts.
        Fix for Issue #1321: Track event loop objects and automatically clean
        up locks for closed event loops to prevent memory leaks.
        """
        self.operations = deque(maxlen=self.MAX_OPERATIONS)
        self._locks = {}  # Dictionary mapping event loop IDs to their locks
        # Fix for Issue #1310: Renamed from _sync_lock to clarify its purpose.
        # This lock ONLY protects lazy initialization of per-event-loop locks
        # in _get_async_lock(). It is NOT used directly in public methods.
        self._init_lock = threading.Lock()
        # Dictionary mapping event loop IDs to their creation events (Issue #1305)
        self._lock_creation_events = {}
        # Fix for Issue #1310: Separate lock for sync-only record_operation.
        # This ensures thread safety while maintaining the documented async-only
        # locking design for async methods.
        self._sync_operation_lock = threading.Lock()
        # Fix for Issue #1321: Track event loop objects to detect when they're closed
        # and clean up stale locks to prevent memory leaks.
        self._event_loops = {}  # Dictionary mapping event loop IDs to loop objects

    def _get_async_lock(self):
        """Get or create the asyncio.Lock for the current event loop.

        Fix for Issue #1139: Lazy-initialize asyncio.Lock to prevent RuntimeError
        in sync contexts. The lock is only created when async methods are called.
        Fix for Issue #1145: Use threading.Lock to protect lazy initialization
        against race conditions in multi-threaded environments.
        Fix for Issue #1150: Use per-event-loop locks to handle multi-threaded
        environments where different threads have different event loops.
        Each event loop gets its own lock to avoid RuntimeError when using
        a lock from a different event loop.
        Fix for Issue #1154: Move check inside lock to prevent race condition
        where multiple threads could create multiple locks or return None.
        Fix for Issue #1161: Avoid creating asyncio.Lock while holding threading.Lock
        to prevent deadlock when current thread is not the event loop's thread.
        Use call_soon_threadsafe to schedule lock creation on event loop thread.
        Fix for Issue #1160: Use id(current_loop) instead of current_loop object
        as dictionary key to avoid circular reference and memory leak.
        Fix for Issue #1296: Remove initial unsynchronized check to prevent race
        condition where multiple threads pass the check before entering synchronized
        section. All checks must be synchronized to ensure atomicity.
        Fix for Issue #1305: Eliminate re-entrant lock acquisition in callback
        to prevent deadlock. Use a 'creating' flag to track in-progress creation
        without re-acquiring _sync_lock in the event loop thread callback.
        Fix for Issue #1310: Use _init_lock instead of _sync_lock to clarify
        that this lock is only for initialization, not for public operations.
        Fix for Issue #1320: Resolve conflict between Issue #1161 and #1296 by using
        double-checked locking (Check-Lock-Check) pattern. The first check outside
        the lock provides a fast path for already-created locks. The second check
        inside the lock ensures atomicity for creation. This avoids creating
        asyncio.Lock while holding threading.Lock while maintaining thread safety.
        Fix for Issue #1321: Automatically clean up locks for closed event loops
        by calling _cleanup_stale_locks() before lock creation/check.
        Fix for Issue #1330: Ensure all operations on shared state (_locks, _event_loops,
        _lock_creation_events) are atomic by using a single critical section protected
        by _init_lock. This prevents race conditions where lock objects could be
        overwritten or inconsistent state could be observed between dictionaries.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop - this shouldn't happen in async context
            # but handle it gracefully
            raise RuntimeError(
                "IOMetrics._get_async_lock must be called from an async context "
                "with a running event loop"
            )

        # Use id(current_loop) as key to avoid circular reference (Issue #1160)
        current_loop_id = id(current_loop)

        # Fix for Issue #1330: Use a single critical section to prevent race conditions.
        # All operations on _locks, _event_loops, and _lock_creation_events must be
        # atomic to prevent lock objects from being overwritten or inconsistent state.
        with self._init_lock:
            # Fix for Issue #1321: Clean up stale locks before checking/creating
            # This prevents memory leaks from closed event loops.
            # Fix for Issue #1330: Now protected by _init_lock for atomicity.
            self._cleanup_stale_locks()

            # Check if lock already exists for this event loop
            if current_loop_id in self._locks:
                existing_lock = self._locks[current_loop_id]
                if existing_lock is not None:
                    # Fix for Issue #1321: Update the event loop reference
                    # to ensure we can detect if it's closed later
                    # Fix for Issue #1330: This write is now protected by _init_lock
                    self._event_loops[current_loop_id] = current_loop
                    return existing_lock
                # If sentinel, another thread is creating it - fall through to wait

            # At this point, lock doesn't exist or is being created
            # Get or create the shared event for this lock creation
            if current_loop_id not in self._lock_creation_events:
                # We're the first thread - need to create the lock
                # Mark it as being created with sentinel value
                self._locks[current_loop_id] = None  # Sentinel: "creating"
                # Create a shared event for all threads waiting for this lock
                self._lock_creation_events[current_loop_id] = threading.Event()
                is_creator = True
            else:
                # Another thread is already creating it - we'll just wait
                is_creator = False

            # Get the shared event
            lock_created = self._lock_creation_events[current_loop_id]

        # Only the creator thread schedules the lock creation
        if is_creator:
            creation_error = [None]

            def create_lock_on_loop_thread():
                """Create asyncio.Lock on the event loop's thread.

                Fix for Issue #1305: This callback no longer re-acquires _sync_lock,
                preventing potential deadlock when the calling thread is waiting
                for lock creation while holding other resources.
                Fix for Issue #1310: _init_lock is only held during callback setup,
                not during this callback execution.
                Fix for Issue #1321: Store event loop reference to detect closure.
                """
                try:
                    # Create the new asyncio.Lock (we're on the event loop thread)
                    new_lock = asyncio.Lock()

                    # Update the dictionary entry from sentinel to actual lock
                    self._locks[current_loop_id] = new_lock

                    # Fix for Issue #1321: Store event loop reference for cleanup
                    self._event_loops[current_loop_id] = current_loop

                    # Clean up the event
                    if current_loop_id in self._lock_creation_events:
                        del self._lock_creation_events[current_loop_id]

                except Exception as e:
                    creation_error[0] = e
                    # Clear the sentinel on error so retry is possible
                    if current_loop_id in self._locks and self._locks[current_loop_id] is None:
                        del self._locks[current_loop_id]
                    # Clean up the event on error too
                    if current_loop_id in self._lock_creation_events:
                        del self._lock_creation_events[current_loop_id]
                finally:
                    lock_created.set()

            # Schedule lock creation on the event loop thread
            current_loop.call_soon_threadsafe(create_lock_on_loop_thread)

            # Wait for the lock to be created
            lock_created.wait(timeout=1.0)

            if creation_error[0] is not None:
                raise creation_error[0]
        else:
            # We're not the creator - just wait for creation to complete
            lock_created.wait(timeout=1.0)

        # Get the created lock
        # Fix for Issue #1305: Check for successful creation
        result_lock = self._locks.get(current_loop_id)
        if result_lock is None:
            raise RuntimeError("Failed to create asyncio.Lock - lock not found after creation")

        return result_lock

    def _cleanup_stale_locks(self):
        """Clean up locks for closed event loops to prevent memory leaks.

        Fix for Issue #1321: This method removes entries from _locks and
        _lock_creation_events for event loops that are no longer running.
        This prevents unbounded memory growth when event loops are created
        and destroyed over time.

        The method is called automatically before creating new locks to
        ensure stale entries are cleaned up proactively.
        """
        with self._init_lock:
            # Collect IDs of closed event loops
            stale_loop_ids = []
            for loop_id, loop in self._event_loops.items():
                try:
                    # Check if the event loop is still running
                    if not loop.is_running():
                        stale_loop_ids.append(loop_id)
                except (RuntimeError, ReferenceError):
                    # Event loop is closed or invalid
                    stale_loop_ids.append(loop_id)

            # Clean up stale entries
            for loop_id in stale_loop_ids:
                # Remove from _locks
                if loop_id in self._locks:
                    del self._locks[loop_id]
                # Remove from _event_loops
                if loop_id in self._event_loops:
                    del self._event_loops[loop_id]
                # Remove from _lock_creation_events (shouldn't be there, but clean up anyway)
                if loop_id in self._lock_creation_events:
                    del self._lock_creation_events[loop_id]

    async def record_operation_async(self, operation_type: str, duration: float,
                                     retries: int, success: bool, error_type: str = None,
                                     operation_id: str = None):
        """Record a single I/O operation (async version).

        This async version should be called from async contexts to avoid
        potential deadlocks with threading.Lock.

        Args:
            operation_type: Type of operation (read/write/flush/etc.)
            duration: Operation duration in seconds
            retries: Number of retry attempts
            success: Whether the operation succeeded
            error_type: Type of error if operation failed (e.g., 'ENOENT')
            operation_id: Optional unique ID for traceability with logs/traces (Issue #1642)

        Fix for Issue #1116: Added async version using _AsyncCompatibleLock
        to prevent deadlocks in async contexts.
        Fix for Issue #1642: Added operation_id parameter for traceability.
        """
        operation = {
            'operation_type': operation_type,
            'duration': duration,
            'retries': retries,
            'success': success,
            'error_type': error_type,
            'operation_id': operation_id
        }

        async with self._get_async_lock():
            # deque with maxlen automatically discards oldest when full (O(1))
            self.operations.append(operation)

    def record_operation(self, operation_type: str, duration: float,
                         retries: int, success: bool, error_type: str = None,
                         operation_id: str = None):
        """Record a single I/O operation.

        Args:
            operation_type: Type of operation (read/write/flush/etc.)
            duration: Operation duration in seconds
            retries: Number of retry attempts
            success: Whether the operation succeeded
            error_type: Type of error if operation failed (e.g., 'ENOENT')
            operation_id: Optional unique ID for traceability with logs/traces (Issue #1642)

        Fix for Issue #1061: Implements circular buffer by removing oldest
        operation when buffer is full.
        Fix for Issue #1065: Uses deque with maxlen for O(1) performance.
        Fix for Issue #1066: Thread-safe operations using lock.
        Fix for Issue #1080: Uses asyncio.Lock for async context safety.
        Fix for Issue #1091: Use threading.Lock for sync/async context safety.
        Fix for Issue #1097: Use custom lock wrapper for both sync and async safety.
        Fix for Issue #1106: Changed to sync method since it's a simple dict append.
        Fix for Issue #1109: Uses threading.Lock to work correctly in async contexts.
        Fix for Issue #1116: Provides async-safe version. Use record_operation_async
        in async contexts to avoid potential deadlocks.
        Fix for Issue #1121: Added async context detection to provide clear error
        message when called from async context.
        Fix for Issue #1124: Uses asyncio.Lock in sync contexts via asyncio.run()
        to ensure pure async locking mechanism without threading.Lock.
        Fix for Issue #1130: Fixed exception handling to properly detect running
        event loop without catching the wrong RuntimeError.
        Fix for Issue #1135: Use threading.Lock instead of asyncio.run() to
        prevent RuntimeError when called from threads with running event loop.
        Fix for Issue #1144: Uses custom _AsyncContextError exception instead of
        fragile string matching to distinguish between our custom error and
        asyncio's RuntimeError.
        Fix for Issue #1642: Added operation_id parameter for traceability.
        """
        # Fix for Issue #1121: Detect if we're in an async context and provide
        # a clear error message directing users to use record_operation_async
        # Fix for Issue #1130: Properly detect running loop without catching
        # the wrong RuntimeError exception
        # Fix for Issue #1144: Use custom exception type instead of string matching
        try:
            loop = asyncio.get_running_loop()
            # If we get here, there's a running event loop
            raise _AsyncContextError(
                "Cannot call synchronous record_operation() from an async context. "
                "Use await record_operation_async() instead. "
                "This prevents potential deadlocks when an event loop is running."
            )
        except _AsyncContextError:
            # Re-raise our custom error
            raise
        except RuntimeError:
            # Any RuntimeError from asyncio.get_running_loop() (e.g., "no running
            # event loop", "no current event loop", etc.) means there's no running
            # loop, which is the expected case - we can proceed with sync version
            # Fix for Issue #1144: Don't rely on string matching, just catch all
            # RuntimeError from asyncio since they all indicate no running loop
            pass

        operation = {
            'operation_type': operation_type,
            'duration': duration,
            'retries': retries,
            'success': success,
            'error_type': error_type,
            'operation_id': operation_id
        }

        # Fix for Issue #1135: Use threading.Lock instead of asyncio.run()
        # to prevent RuntimeError when called from threads with running event loop
        # Fix for Issue #1310: Use _sync_operation_lock instead of _sync_lock
        # to maintain separation between initialization and operation locking
        with self._sync_operation_lock:
            # deque with maxlen automatically discards oldest when full (O(1))
            self.operations.append(operation)

    def total_operation_count(self) -> int:
        """Get total number of operations recorded.

        Fix for Issue #1101: This sync version creates a new event loop
        to access the async version, ensuring lock safety.

        Fix for Issue #1131: Handle case where called from within a running
        event loop (e.g., Jupyter Notebook, async web frameworks).
        """
        async def _get_count():
            async with self._get_async_lock():
                return len(self.operations)

        # Try to get the current running event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're here, there's a running loop, use create_task
            import concurrent.futures
            import threading

            # Run in a new thread to avoid blocking the current loop
            result = [None]
            exception = [None]

            def run_in_new_loop():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result[0] = new_loop.run_until_complete(_get_count())
                    finally:
                        new_loop.close()
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()

            if exception[0] is not None:
                raise exception[0]

            return result[0]

        except RuntimeError:
            # No running loop, use asyncio.run normally
            return asyncio.run(_get_count())

    async def total_operation_count_async(self) -> int:
        """Get total number of operations recorded (async version).

        Fix for Issue #1101: Async version that properly uses locks
        to ensure thread-safe access to self.operations.
        """
        async with self._get_async_lock():
            return len(self.operations)

    def total_duration(self) -> float:
        """Get total duration of all operations in seconds.

        Fix for Issue #1101: This sync version creates a new event loop
        to access the async version, ensuring lock safety.
        """
        # For sync contexts, use asyncio.run to access the async version
        async def _get_duration():
            async with self._get_async_lock():
                return sum(op['duration'] for op in self.operations)

        return asyncio.run(_get_duration())

    async def total_duration_async(self) -> float:
        """Get total duration of all operations in seconds (async version).

        Fix for Issue #1101: Async version that properly uses locks
        to ensure thread-safe access to self.operations.
        """
        async with self._get_async_lock():
            return sum(op['duration'] for op in self.operations)

    def log_summary(self):
        """Log a summary of metrics if FW_STORAGE_METRICS_LOG is enabled.

        This method checks the FW_STORAGE_METRICS_LOG environment variable
        and logs the metrics summary if it's set to '1'.

        Fix for Issue #1076: Uses lock to ensure thread-safe access to
        self.operations during metrics calculation, preventing race conditions.
        Fix for Issue #1080: Uses asyncio.Lock for async context safety.
        Fix for Issue #1091: Use threading.Lock for sync/async context safety.
        Fix for Issue #1097: Use custom lock wrapper for both sync and async safety.
        Fix for Issue #1115: Changed to sync method using threading.Lock to avoid deadlock.
        Fix for Issue #1124: Uses asyncio.Lock via asyncio.run() to ensure pure
        async locking mechanism without threading.Lock.
        Fix for Issue #1100: Release lock before I/O operations (logging) to prevent deadlock.
        """
        if os.environ.get('FW_STORAGE_METRICS_LOG') != '1':
            return

        # Fix for Issue #1124: Use asyncio.run() to acquire asyncio.Lock in sync context
        async def _log_with_lock():
            # Fix for Issue #1100: Calculate metrics inside lock, then release before logging
            async with self._get_async_lock():
                if not self.operations:
                    # Release lock before logging
                    has_operations = False
                else:
                    has_operations = True
                    total_ops = len(self.operations)
                    total_dur = sum(op['duration'] for op in self.operations)
                    total_retries = sum(op['retries'] for op in self.operations)
                    successful_ops = sum(1 for op in self.operations if op['success'])
                    failed_ops = total_ops - successful_ops

                    # Group by operation type
                    by_type = {}
                    for op in self.operations:
                        op_type = op['operation_type']
                        if op_type not in by_type:
                            by_type[op_type] = {'count': 0, 'duration': 0, 'retries': 0}
                        by_type[op_type]['count'] += 1
                        by_type[op_type]['duration'] += op['duration']
                        by_type[op_type]['retries'] += op['retries']

            # Lock is now released - perform I/O operations outside the lock
            if not has_operations:
                logger.info("I/O Metrics: No operations recorded")
                return

            # Log the summary after releasing the lock to prevent deadlock
            logger.info(
                f"I/O Metrics Summary: "
                f"{total_ops} operations, "
                f"{successful_ops} successful, "
                f"{failed_ops} failed, "
                f"{total_retries} retries, "
                f"total duration: {total_dur:.3f}s"
            )

            for op_type, stats in sorted(by_type.items()):
                avg_duration = stats['duration'] / stats['count'] if stats['count'] > 0 else 0
                logger.info(
                    f"  {op_type}: {stats['count']} ops, "
                    f"avg duration: {avg_duration:.3f}s, "
                    f"total retries: {stats['retries']}"
                )

        asyncio.run(_log_with_lock())

    def track_operation(self, operation_type: str, retries: int = 0):
        """Async context manager for tracking I/O operations (Issue #1063).

        Simplifies tracking by automatically recording start time and duration.
        Handles exceptions and marks operations as failed when they occur.

        Args:
            operation_type: Type of operation (read/write/flush/etc.)
            retries: Number of retry attempts (default: 0)

        Returns:
            An async context manager that tracks the operation

        Example:
            >>> metrics = IOMetrics()
            >>> async with metrics.track_operation("read"):
            ...     data = await file.read()

        This is equivalent to the more verbose:
            >>> start_time = time.time()
            >>> try:
            ...     data = await file.read()
            ...     success = True
            ...     error_type = None
            ... except Exception as e:
            ...     success = False
            ...     error_type = type(e).__name()
            ...     raise
            >>> finally:
            ...     duration = time.time() - start_time
            ...     metrics.record_operation("read", duration, 0, success, error_type)
        """
        return _IOMetricsContextManager(self, operation_type, retries)

    def export_to_dict(self) -> dict:
        """Export metrics to a dictionary for serialization (Issue #1068).

        This method converts the metrics data into a dictionary format that
        can be easily serialized to JSON or other formats for persistence
        or external monitoring tools.

        Fix for Issue #1087: Now an async method that uses async with
        self._lock to avoid RuntimeError when using asyncio.Lock.
        Fix for Issue #1097: Uses custom lock wrapper that supports both
        sync and async context managers.
        Fix for Issue #1115: Changed to sync method using threading.Lock to avoid deadlock.
        Fix for Issue #1124: Uses asyncio.Lock via asyncio.run() to ensure pure
        async locking mechanism without threading.Lock.

        Returns:
            A dictionary containing:
            - operations: List of all recorded operations
            - total_operation_count: Total number of operations
            - total_duration: Total duration of all operations in seconds
            - successful_operations: Number of successful operations
            - failed_operations: Number of failed operations
            - total_retries: Total number of retry attempts

        Example:
            >>> metrics = IOMetrics()
            >>> metrics.record_operation('read', 0.5, 0, True)
            >>> data = metrics.export_to_dict()
            >>> json.dumps(data)  # Can be serialized to JSON
        """
        # Fix for Issue #1124: Use asyncio.run() to acquire asyncio.Lock in sync context
        async def _export_with_lock():
            async with self._get_async_lock():
                operations_list = list(self.operations)
                successful_ops = sum(1 for op in operations_list if op['success'])
                failed_ops = len(operations_list) - successful_ops
                total_retries = sum(op['retries'] for op in operations_list)
                total_dur = self.total_duration()
            return {
                'operations': operations_list,
                'total_operation_count': len(operations_list),
                'total_duration': total_dur,
                'successful_operations': successful_ops,
                'failed_operations': failed_ops,
                'total_retries': total_retries
            }

        return asyncio.run(_export_with_lock())

    async def save_to_file(self, path: str | Path):
        """Save metrics to a JSON file (Issue #1068).

        This method serializes the metrics data and saves it to a file
        in JSON format. The file can be used for persistence or integration
        with external monitoring tools like Prometheus/Grafana.

        Fix for Issue #1075: Now an async method that uses asyncio.to_thread
        to avoid blocking the event loop during file I/O.

        Args:
            path: Path to the file where metrics will be saved

        Raises:
            IOError: If the file cannot be written
            TypeError: If path is not a string or Path object

        Example:
            >>> metrics = IOMetrics()
            >>> metrics.record_operation('read', 0.5, 0, True)
            >>> await metrics.save_to_file('/tmp/metrics.json')
        """
        if not isinstance(path, (str, Path)):
            raise TypeError(f"path must be str or Path, not {type(path).__name__}")

        data = self.export_to_dict()

        # Use asyncio.to_thread to run blocking I/O in a separate thread
        # This prevents blocking the event loop during file write operations
        await asyncio.to_thread(self._write_to_file_sync, path, data)

    def _write_to_file_sync(self, path: str | Path, data: dict):
        """Synchronous helper method to write data to file.

        This method is intended to be run in a separate thread via
        asyncio.to_thread to avoid blocking the event loop.

        Uses atomic write pattern (Issue #1509):
        1. Write to temporary file
        2. Sync to disk (flush)
        3. Atomically rename to target path

        This prevents data loss if the process crashes during write.

        Args:
            path: Path to the file where metrics will be saved
            data: Dictionary data to write as JSON
        """
        path = Path(path)

        # Create temporary file in the same directory as the target
        # This ensures the rename operation is atomic (same filesystem)
        temp_path = path.with_suffix(path.suffix + '.tmp')

        try:
            # Write data to temporary file
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
                # Ensure data is written to disk before renaming
                f.flush()
                os.fsync(f.fileno())

            # Atomically rename temporary file to target path
            # This is atomic on POSIX systems and ensures either
            # the old file or new file exists, never a partial state
            temp_path.replace(path)

        except Exception:
            # Clean up temporary file if something goes wrong
            if temp_path.exists():
                temp_path.unlink()
            raise

    def reset(self):
        """Clear all recorded metrics (Issue #1078).

        This method clears the operations deque, allowing for fresh metrics
        tracking between test runs or batch operations without restarting
        the application. Uses the existing _lock for thread safety.

        Example:
            >>> metrics = IOMetrics()
            >>> metrics.record_operation('read', 0.5, 0, True)
            >>> metrics.total_operation_count()
            1
            >>> metrics.reset()
            >>> metrics.total_operation_count()
            0

        Thread Safety:
            This method is thread-safe and uses the same lock as other methods
            to prevent race conditions during concurrent access.
            Fix for Issue #1080: Uses asyncio.Lock for async context safety.
            Fix for Issue #1115: Changed to sync method using threading.Lock to avoid deadlock.
            Fix for Issue #1124: Uses asyncio.Lock via asyncio.run() to ensure pure
            async locking mechanism without threading.Lock.
        """
        # Fix for Issue #1124: Use asyncio.run() to acquire asyncio.Lock in sync context
        async def _clear_with_lock():
            async with self._get_async_lock():
                self.operations.clear()

        asyncio.run(_clear_with_lock())

    def record_io_operation(
        self,
        operation_type: str,
        duration: float,
        retries: int = 0,
        success: bool = True,
        error_type: str | None = None,
        operation_id: str | None = None
    ) -> None:
        """Record an I/O operation metric (StorageMetrics protocol).

        This method implements the StorageMetrics protocol for integration
        with observability tools like Prometheus and Datadog.

        Fix for Issue #1638: Implements StorageMetrics.record_io_operation
        to allow external metrics collection.
        Fix for Issue #1642: Added operation_id parameter for traceability.

        Args:
            operation_type: Type of operation (e.g., 'read', 'write', 'flush')
            duration: Operation duration in seconds
            retries: Number of retry attempts
            success: Whether the operation succeeded
            error_type: Type of error if operation failed
            operation_id: Optional unique ID for traceability with logs/traces
        """
        # Delegate to existing record_operation method
        # This maintains compatibility with existing IOMetrics functionality
        # while implementing the StorageMetrics protocol
        self.record_operation(
            operation_type=operation_type,
            duration=duration,
            retries=retries,
            success=success,
            error_type=error_type,
            operation_id=operation_id
        )

    def record_lock_contention(self, wait_time: float) -> None:
        """Record a lock contention event (StorageMetrics protocol).

        This method implements the StorageMetrics protocol for tracking
        lock contention events.

        Fix for Issue #1638: Implements StorageMetrics.record_lock_contention.

        Args:
            wait_time: Time spent waiting for lock in seconds
        """
        # Record as a special operation type for tracking
        # This integrates with existing IOMetrics infrastructure
        self.record_operation(
            operation_type='lock_contention',
            duration=wait_time,
            retries=0,
            success=True
        )

    def record_lock_acquired(self, acquire_time: float) -> None:
        """Record a successful lock acquisition (StorageMetrics protocol).

        This method implements the StorageMetrics protocol for tracking
        lock acquisition performance.

        Fix for Issue #1638: Implements StorageMetrics.record_lock_acquired.

        Args:
            acquire_time: Time taken to acquire lock in seconds
        """
        # Record as a special operation type for tracking
        self.record_operation(
            operation_type='lock_acquired',
            duration=acquire_time,
            retries=0,
            success=True
        )


class _IOMetricsContextManager:
    """Async context manager for tracking I/O operations (Issue #1063)."""

    def __init__(self, metrics: IOMetrics, operation_type: str, retries: int = 0):
        """Initialize the context manager.

        Args:
            metrics: The IOMetrics instance to record to
            operation_type: Type of operation being tracked
            retries: Number of retry attempts
        """
        self.metrics = metrics
        self.operation_type = operation_type
        self.retries = retries
        self.start_time = None
        self.success = True
        self.error_type = None

    async def __aenter__(self):
        """Enter the context and record start time."""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and record the operation."""
        duration = time.time() - self.start_time

        # Determine success and error type
        if exc_type is not None:
            self.success = False
            self.error_type = exc_type.__name__

        # Record the operation using async version to avoid deadlock (issue #1116)
        await self.metrics.record_operation_async(
            self.operation_type,
            duration,
            self.retries,
            self.success,
            self.error_type
        )

        # Don't suppress exceptions
        return False


# Retry I/O operations on transient errors with exponential backoff (Issue #1038, #1043, #1042, #1048, #1053)
# This function is always available regardless of whether aiofiles is installed (Issue #1064)
async def _retry_io_operation(
    operation: Callable,
    *args,
    max_attempts: int = 3,
    initial_backoff: float = 0.1,
    timeout: float | None = 30.0,
    path: str | None = None,
    operation_type: str | None = None,
    metrics: IOMetrics = None,
    log_level: str | None = None,
    **kwargs
):
    """Retry I/O operations on transient errors with exponential backoff.

    This helper function retries I/O operations that may fail due to transient
    errors like network filesystem glitches (errno.EIO, errno.EAGAIN).

    Args:
        operation: The I/O operation to retry (callable)
        *args: Positional arguments to pass to the operation
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_backoff: Initial backoff time in seconds (default: 0.1)
        timeout: Maximum time in seconds for each operation attempt (default: 30.0).
                 Set to None to disable timeout. Fix for Issue #1043.
        path: File path for structured logging context (Issue #1042).
        operation_type: Operation type (read/write/flush/etc.) for logging context (Issue #1042).
        metrics: IOMetrics instance to track performance metrics (Issue #1053).
        log_level: Log level for retry operations ('DEBUG', 'INFO', 'WARNING', 'ERROR').
                   If None, checks FW_LOG_LEVEL environment variable (Issue #1072).
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        The result of the operation

    Raises:
        IOError: If all retry attempts fail
        StorageTimeoutError: If an operation times out (Issue #1043)

    Transient errors that trigger retry:
    - errno.EIO: I/O error (common on network mounts)
    - errno.EAGAIN: Resource temporarily unavailable
    - errno.EBUSY: Device or resource busy

    Permanent errors that don't trigger retry:
    - errno.ENOENT: No such file or directory
    - errno.EACCES: Permission denied
    - errno.EISDIR: Is a directory
    And other non-transient errors

    Fix for Issue #1038: Automatic retry logic for transient I/O errors.
    Fix for Issue #1043: Configurable timeout for I/O operations.
    Fix for Issue #1042: Structured logging context with path and operation type.
    Fix for Issue #1048: Bypass mode for testing/debugging (FW_STORAGE_BYPASS_RETRY env var).
    Fix for Issue #1053: I/O operation metrics tracking via IOMetrics class.
    Fix for Issue #1064: Function is always available, not just when aiofiles is missing.
    Fix for Issue #1072: Configurable log levels for I/O retries (FW_LOG_LEVEL env var).
    """
    # Create logger adapter with structured context (Issue #1042)
    # LoggerAdapter automatically adds extra dict to all log records
    extra_context = {}
    if path is not None:
        extra_context['path'] = str(path)
    if operation_type is not None:
        extra_context['operation'] = operation_type

    # Create a logger adapter to add context to all log messages
    if extra_context:
        class ContextualLoggerAdapter(logging.LoggerAdapter):
            """Logger adapter that adds extra context as record attributes."""
            def process(self, msg, kwargs):
                # Add extra context to kwargs, which adds them to the LogRecord
                if 'extra' not in kwargs:
                    kwargs['extra'] = {}
                kwargs['extra'].update(self.extra)
                return msg, kwargs

        retry_logger = ContextualLoggerAdapter(logger, extra_context)
    else:
        retry_logger = logger

    # Determine log level for retry operations (Issue #1072)
    # Check parameter first, then environment variable, default to WARNING
    if log_level is None:
        log_level = os.environ.get('FW_LOG_LEVEL', 'WARNING').upper()

    # Create sampler for high-frequency debug logs (Issue #1773)
    # Get sampling rate from environment variable, default to 10% (0.1)
    # Set to 1.0 to log all messages, 0.0 to disable debug retry logging
    debug_sample_rate = float(os.environ.get('FW_DEBUG_SAMPLE_RATE', '0.1'))
    retry_debug_sampler = sample_debug_log(rate_limit=debug_sample_rate)

    # Import traceback here for stack trace logging in DEBUG mode
    import traceback

    # Check for bypass mode (Issue #1048)
    # When enabled, skip retry logic and timeout for debugging/testing
    if os.environ.get('FW_STORAGE_BYPASS_RETRY') == '1':
        retry_logger.warning(
            "I/O bypass mode enabled via FW_STORAGE_BYPASS_RETRY=1. "
            "Retry logic and timeout are disabled. Use only for debugging/testing."
        )
        # Execute operation directly without retry or timeout
        start_time = time.time()
        try:
            # Issue #1056: Handle both sync and async operations correctly
            # Check if operation is a coroutine function
            if inspect.iscoroutinefunction(operation):
                # Async function: await directly
                result = await operation(*args, **kwargs)
            else:
                # Sync function: run in thread pool to avoid blocking
                result = await asyncio.to_thread(operation, *args, **kwargs)
            # Record metrics if provided
            if metrics:
                duration = time.time() - start_time
                metrics.record_operation(
                    operation_type or 'unknown',
                    duration,
                    retries=0,
                    success=True
                )
                # Fix for Issue #1638: Also call StorageMetrics protocol method
                # if the metrics object implements it
                if hasattr(metrics, 'record_io_operation'):
                    metrics.record_io_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=0,
                        success=True
                    )
            return result
        except Exception as e:
            # Record failed metrics
            if metrics:
                duration = time.time() - start_time
                error_type = None
                if isinstance(e, IOError) and hasattr(e, 'errno'):
                    error_type = errno.errorcode.get(e.errno, str(e.errno))
                metrics.record_operation(
                    operation_type or 'unknown',
                    duration,
                    retries=0,
                    success=False,
                    error_type=error_type
                )
                # Fix for Issue #1638: Also call StorageMetrics protocol method
                # if the metrics object implements it
                if hasattr(metrics, 'record_io_operation'):
                    metrics.record_io_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=0,
                        success=False,
                        error_type=error_type
                    )
            raise

    # Track start time and retry count for metrics (Issue #1053)
    start_time = time.time()
    actual_retries = 0
    last_error = None

    for attempt in range(max_attempts):
        try:
            # Run the operation in a thread pool to avoid blocking
            # Wrap with timeout if specified (Issue #1043)
            # Issue #1056: Handle both sync and async operations correctly
            if timeout is not None:
                if inspect.iscoroutinefunction(operation):
                    # Async function: await with timeout
                    result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=timeout
                    )
                else:
                    # Sync function: run in thread pool with timeout
                    result = await asyncio.wait_for(
                        asyncio.to_thread(operation, *args, **kwargs),
                        timeout=timeout
                    )
                # Record successful metrics
                if metrics:
                    duration = time.time() - start_time
                    metrics.record_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=actual_retries,
                        success=True
                    )
                    # Fix for Issue #1638: Also call StorageMetrics protocol method
                    if hasattr(metrics, 'record_io_operation'):
                        metrics.record_io_operation(
                            operation_type or 'unknown',
                            duration,
                            retries=actual_retries,
                            success=True
                        )
                return result
            else:
                # Issue #1056: Handle both sync and async operations correctly
                if inspect.iscoroutinefunction(operation):
                    # Async function: await directly
                    result = await operation(*args, **kwargs)
                else:
                    # Sync function: run in thread pool to avoid blocking
                    result = await asyncio.to_thread(operation, *args, **kwargs)
                # Record successful metrics
                if metrics:
                    duration = time.time() - start_time
                    metrics.record_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=actual_retries,
                        success=True
                    )
                    # Fix for Issue #1638: Also call StorageMetrics protocol method
                    if hasattr(metrics, 'record_io_operation'):
                        metrics.record_io_operation(
                            operation_type or 'unknown',
                            duration,
                            retries=actual_retries,
                            success=True
                        )
                return result
        except asyncio.TimeoutError:
            # Convert asyncio.TimeoutError to StorageTimeoutError (Issue #1043, #1045)
            # Record timeout metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_operation(
                    operation_type or 'unknown',
                    duration,
                    retries=actual_retries,
                    success=False,
                    error_type='TIMEOUT'
                )
                # Fix for Issue #1638: Also call StorageMetrics protocol method
                if hasattr(metrics, 'record_io_operation'):
                    metrics.record_io_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=actual_retries,
                        success=False,
                        error_type='TIMEOUT'
                    )
            raise StorageTimeoutError(
                f"I/O operation timed out after {timeout}s"
            )
        except IOError as e:
            last_error = e
            # Check if this is a transient error that should be retried
            transient_errors = (
                errno.EIO,      # I/O error (common on network mounts)
                errno.EAGAIN,   # Resource temporarily unavailable
                errno.EBUSY,    # Device or resource busy
            )

            if e.errno not in transient_errors:
                # Permanent error, record metrics and raise without retry
                if metrics:
                    duration = time.time() - start_time
                    error_type = errno.errorcode.get(e.errno, str(e.errno))
                    metrics.record_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=actual_retries,
                        success=False,
                        error_type=error_type
                    )
                    # Fix for Issue #1638: Also call StorageMetrics protocol method
                    if hasattr(metrics, 'record_io_operation'):
                        metrics.record_io_operation(
                            operation_type or 'unknown',
                            duration,
                            retries=actual_retries,
                            success=False,
                            error_type=error_type
                        )
                raise

            if attempt < max_attempts - 1:
                # Calculate exponential backoff
                backoff = initial_backoff * (2 ** attempt)
                actual_retries += 1

                # Log retry with details based on configured log level (Issue #1072)
                if log_level == 'DEBUG':
                    # In DEBUG mode, include stack trace and detailed backoff information
                    # Apply sampling to reduce log volume in tight loops (Issue #1773)
                    stack_trace = ''.join(traceback.format_stack())
                    retry_debug_sampler(
                        retry_logger,
                        f"Transient I/O error (errno={e.errno}), "
                        f"retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{max_attempts})\n"
                        f"Stack trace:\n{stack_trace}"
                    )
                elif log_level == 'INFO':
                    # In INFO mode, log retry with moderate detail
                    retry_logger.info(
                        f"Transient I/O error (errno={e.errno}), "
                        f"retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
                # For WARNING or ERROR level, don't log individual retry attempts

                await asyncio.sleep(backoff)
            else:
                # Last attempt failed, record metrics and raise the error
                if metrics:
                    duration = time.time() - start_time
                    error_type = errno.errorcode.get(e.errno, str(e.errno))
                    metrics.record_operation(
                        operation_type or 'unknown',
                        duration,
                        retries=actual_retries,
                        success=False,
                        error_type=error_type
                    )
                    # Fix for Issue #1638: Also call StorageMetrics protocol method
                    if hasattr(metrics, 'record_io_operation'):
                        metrics.record_io_operation(
                            operation_type or 'unknown',
                            duration,
                            retries=actual_retries,
                            success=False,
                            error_type=error_type
                        )
                retry_logger.warning(
                    f"I/O operation failed after {max_attempts} attempts: {e}"
                )
                raise

    # This should never be reached, but just in case
    if last_error:
        # Record failed metrics as a fallback
        if metrics:
            duration = time.time() - start_time
            error_type = None
            if isinstance(last_error, IOError) and hasattr(last_error, 'errno'):
                error_type = errno.errorcode.get(last_error.errno, str(last_error.errno))
            metrics.record_operation(
                operation_type or 'unknown',
                duration,
                retries=actual_retries,
                success=False,
                error_type=error_type
            )
            # Fix for Issue #1638: Also call StorageMetrics protocol method
            if hasattr(metrics, 'record_io_operation'):
                metrics.record_io_operation(
                    operation_type or 'unknown',
                    duration,
                    retries=actual_retries,
                    success=False,
                    error_type=error_type
                )
        raise last_error


# Fallback async file operations for when aiofiles is not available (Issue #1032)
# This ensures aiofiles is ALWAYS available, eliminating need for HAS_AIOFILES checks (Issue #1613)
if not HAS_AIOFILES:
    class _AsyncFileContextManager:
        """Async context manager for file operations without aiofiles."""

        def __init__(self, path: str, mode: str):
            self.path = path
            self.mode = mode
            self._file = None
            # Determine if this is binary mode (Issue #1036)
            self._is_binary = 'b' in mode

        async def __aenter__(self):
            # Use asyncio.to_thread to run blocking I/O in a thread pool
            # with retry logic for transient errors (Issue #1038)
            self._file = await _retry_io_operation(open, self.path, self.mode,
                                                   path=self.path, operation_type='open')
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._file:
                # Close operation typically doesn't need retry,
                # but we use to_thread for non-blocking behavior
                await asyncio.to_thread(self._file.close)

        async def read(self) -> str | bytes:
            """Read file content asynchronously with retry logic.

            Returns str in text mode, bytes in binary mode (Issue #1036).

            Retries on transient I/O errors (Issue #1038).
            """
            if self._file is None:
                raise ValueError("File not opened")
            return await _retry_io_operation(self._file.read,
                                              path=self.path, operation_type='read')

        async def write(self, data: str | bytes) -> int:
            """Write data to file asynchronously with retry logic.

            Accepts str in text mode, bytes in binary mode (Issue #1036).

            Retries on transient I/O errors (Issue #1038).
            """
            if self._file is None:
                raise ValueError("File not opened")
            return await _retry_io_operation(self._file.write, data,
                                              path=self.path, operation_type='write')

        async def flush(self):
            """Flush file buffers asynchronously with retry logic.

            Retries on transient I/O errors (Issue #1038).
            """
            if self._file is None:
                raise ValueError("File not opened")
            return await _retry_io_operation(self._file.flush,
                                              path=self.path, operation_type='flush')

        def fileno(self) -> int:
            """Get file descriptor number."""
            if self._file is None:
                raise ValueError("File not opened")
            return self._file.fileno()

    class _AiofilesFallback:
        """Fallback module for aiofiles using asyncio.to_thread.

        This provides a drop-in replacement for aiofiles that uses Python's
        built-in asyncio.to_thread to run file I/O operations in a thread pool.
        This ensures aiofiles is ALWAYS available, eliminating the need for
        HAS_AIOFILES checks throughout the codebase (Issue #1613).
        """

        @staticmethod
        def open(path: str, mode: str = 'rb') -> '_AsyncFileContextManager':
            """Open a file asynchronously.

            Defaults to binary mode 'rb' to match aiofiles behavior (Issue #1036).
            """
            return _AsyncFileContextManager(path, mode)

    # Replace aiofiles with our fallback implementation
    # This ensures aiofiles is NEVER None, eliminating need for HAS_AIOFILES checks (Issue #1613)
    # Type annotation ensures this satisfies the _AiofilesProtocol (Issue #1565)
    aiofiles: _AiofilesProtocol = _AiofilesFallback()

if TYPE_CHECKING:
    from collections.abc import Mapping


# Storage latency metrics support (Issue #1003)
# Provides telemetry for critical I/O operations to help identify
# slow I/O operations or lock contention.

# Cache statsd configuration at module level to avoid repeated
# environment variable lookups (Issue #1013)
_statsd_host = os.environ.get('FW_STATSD_HOST')
_statsd_port = os.environ.get('FW_STATSD_PORT', '8125')


@functools.lru_cache(maxsize=1)
def get_statsd_client():
    """Get the statsd client for metrics emission.

    Returns:
        The statsd client if available, None otherwise.

    Note:
        Environment variables are checked at module import time (Issue #1013)
        to avoid repeated lookups during high-frequency I/O operations.
        The client instance is cached using functools.lru_cache (Issue #1028)
        which provides thread-safe initialization without explicit locks.

        Using lru_cache eliminates the need for manual double-checked locking
        and provides better performance in high-concurrency scenarios.
    """
    # Try to import statsd
    try:
        import statsd

        # Use module-level cached environment variables (Issue #1013)
        if _statsd_host:
            # Create statsd client
            client = statsd.StatsClient(
                host=_statsd_host,
                port=int(_statsd_port),
                prefix='flywheel.storage'
            )
            logger.debug(
                f"Statsd client initialized: {_statsd_host}:{_statsd_port}"
            )
            return client
        else:
            # No statsd configuration
            return None
    except ImportError:
        # statsd not available
        return None


def _extract_context(args: tuple, kwargs: dict, func: Callable) -> str:
    """Extract context information from function arguments.

    Inspects function arguments for 'path' or 'id' parameters to provide
    context-aware logging (Issue #1007).

    Args:
        args: Positional arguments passed to the decorated function.
        kwargs: Keyword arguments passed to the decorated function.
        func: The decorated function (used to inspect parameter names).

    Returns:
        A string context if found (e.g., "on /tmp/file.json" or "on 12345"),
        or empty string if no context is available.
    """
    # Check kwargs first (keyword arguments take precedence)
    if 'path' in kwargs:
        path_value = kwargs['path']
        # Convert Path object to string if needed
        if isinstance(path_value, Path):
            path_value = str(path_value)
        return f" on {path_value}"
    elif 'id' in kwargs:
        return f" on {kwargs['id']}"

    # Check positional arguments by inspecting function signature
    try:
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Map positional args to parameter names
        for i, arg_value in enumerate(args):
            if i < len(param_names):
                param_name = param_names[i]
                # Skip 'self' and 'cls' parameters (Issue #1018)
                if param_name in ('self', 'cls'):
                    continue
                if param_name == 'path':
                    # Convert Path object to string if needed
                    if isinstance(arg_value, Path):
                        arg_value = str(arg_value)
                    return f" on {arg_value}"
                elif param_name == 'id':
                    return f" on {arg_value}"
    except (ValueError, TypeError):
        # If signature inspection fails, just return empty context
        pass

    return ""


def _get_slow_operation_threshold() -> int:
    """Get the slow operation threshold from environment variable.

    Returns:
        The threshold in milliseconds. Default is 1000ms.
        Returns -1 if warnings are disabled (negative threshold).
        Returns 1000 if the environment variable is invalid.
    """
    import os
    threshold_str = os.environ.get('FW_STORAGE_SLOW_LOG_THRESHOLD', '1000')
    try:
        threshold = int(threshold_str)
        return threshold
    except (ValueError, TypeError):
        # If invalid, use default
        return 1000


def _record_metrics(operation_name: str, elapsed_ms: float, context: str) -> None:
    """Record metrics and logs for a storage operation.

    This helper function sends timing metrics to statsd (if available),
    logs debug information, and checks for slow operations.

    Args:
        operation_name: The name of the operation (e.g., 'load', 'save').
        elapsed_ms: The elapsed time in milliseconds.
        context: The context string (e.g., '[/tmp/todos.json]' or '[id:123]').

    Refactored as part of Issue #1022 to reduce code duplication between
    sync and async wrappers.
    """
    # Emit metric to statsd if available
    client = get_statsd_client()
    if client is not None:
        metric_name = f"{operation_name}.latency"
        client.timing(metric_name, elapsed_ms)

        # Also emit histogram if supported
        if hasattr(client, 'histogram'):
            client.histogram(f"{operation_name}.latency.dist", elapsed_ms)

    # Log timing for debugging
    # Extract context (path/id) for better debugging (Issue #1007)
    logger.debug(
        f"{operation_name}{context} completed in {elapsed_ms:.3f}ms"
    )

    # Check if operation exceeded slow threshold (Issue #1023)
    threshold = _get_slow_operation_threshold()
    if threshold >= 0 and elapsed_ms > threshold:
        logger.warning(
            f"{operation_name}{context} exceeded slow threshold: "
            f"{elapsed_ms:.3f}ms > {threshold}ms"
        )


def measure_latency(operation_name: str):
    """Decorator to measure and log execution time for I/O operations.

    This decorator measures the execution time of the decorated function
    and emits metrics to statsd if available. It works with both synchronous
    and asynchronous functions.

    Context-Aware Logging (Issue #1007):
        The decorator inspects function arguments for 'path' or 'id' parameters
        and includes them in log messages for easier debugging. For example:
        - "save on /tmp/todos.json completed in 5.234ms"
        - "load on 12345 completed in 2.456ms"

    Slow Operation Warning (Issue #1023):
        The decorator checks if operation execution time exceeds a configurable threshold
        and logs a warning if it does. The threshold can be configured via the
        FW_STORAGE_SLOW_LOG_THRESHOLD environment variable (in milliseconds).
        Default threshold is 1000ms (1 second). Set to -1 to disable warnings.

    Args:
        operation_name: The name of the operation being measured (e.g., 'load', 'save').

    Returns:
        The decorated function with latency measurement.

    Example:
        @measure_latency("load")
        def _load(self):
            # Load operation
            pass

        @measure_latency("save")
        async def _save(self):
            # Save operation
            pass

    Note:
        - Metrics are emitted to statsd if configured via FW_STATSD_HOST
        - Timing is measured in milliseconds
        - If statsd is not available, the operation proceeds normally
        - Supports both sync and async functions
        - Includes context (path/id) in log messages when available
        - Slow operations (exceeding threshold) trigger warning logs
    """
    def decorator(func: Callable) -> Callable:
        is_coroutine = inspect.iscoroutinefunction(func)

        if is_coroutine:
            # Async version
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                context = _extract_context(args, kwargs, func)
                try:
                    result = await func(*args, **kwargs)
                    # Calculate elapsed time in milliseconds
                    elapsed_ms = (time.time() - start_time) * 1000

                    # Record metrics and logs (Issue #1022)
                    _record_metrics(operation_name, elapsed_ms, context)

                    return result
                except Exception as e:
                    # Add context to exception for better debugging (Issue #1012)
                    # Use add_note for Python 3.11+ to preserve exception chain (Issue #1016)
                    if context and not str(e).count(context) > 0:
                        # Add context using add_note if available (Python 3.11+)
                        # This preserves the original exception and stack trace
                        if hasattr(e, 'add_note'):
                            e.add_note(f"Context: {context}")
                        else:
                            # For older Python versions, modify args directly
                            # This is less ideal but preserves the exception instance
                            if e.args:
                                # Append context to the first argument
                                e.args = (f"{e}{context}",)
                            else:
                                # If no args, set it with context
                                e.args = (f"Error{context}",)
                    raise

            return async_wrapper
        else:
            # Sync version
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                context = _extract_context(args, kwargs, func)
                try:
                    result = func(*args, **kwargs)
                    # Calculate elapsed time in milliseconds
                    elapsed_ms = (time.time() - start_time) * 1000

                    # Record metrics and logs (Issue #1022)
                    _record_metrics(operation_name, elapsed_ms, context)

                    return result
                except Exception as e:
                    # Add context to exception for better debugging (Issue #1012)
                    # Use add_note for Python 3.11+ to preserve exception chain (Issue #1016)
                    if context and not str(e).count(context) > 0:
                        # Add context using add_note if available (Python 3.11+)
                        # This preserves the original exception and stack trace
                        if hasattr(e, 'add_note'):
                            e.add_note(f"Context: {context}")
                        else:
                            # For older Python versions, modify args directly
                            # This is less ideal but preserves the exception instance
                            if e.args:
                                # Append context to the first argument
                                e.args = (f"{e}{context}",)
                            else:
                                # If no args, set it with context
                                e.args = (f"Error{context}",)
                    raise

            return sync_wrapper

    return decorator

# Platform-specific file locking (Issue #268, #411, #451)
# IMPORTANT: Windows file locking implementation
# - Windows uses win32file.LockFileEx which provides MANDATORY LOCKING
# - Mandatory locks enforce mutual exclusion and prevent concurrent access
# - All processes are blocked from writing while the lock is held
# - Unix systems use fcntl.flock which provides strong synchronization
#
# Security fix for Issue #429: Windows modules are now imported at module level
# to prevent race conditions in multi-threaded environments. Module-level imports
# ensure thread-safe initialization and eliminate TOCTOU vulnerabilities between
# __init__ checks and actual module usage.
#
# On Windows, all pywin32 modules are imported at module level. If pywin32 is not
# installed, the import will fail immediately with a clear ImportError, preventing
# runtime crashes later. This is preferred over lazy imports for thread safety.
#
# Security fix for Issue #674, #696: pywin32 is preferred on Windows.
# The module will attempt to import pywin32 for optimal file locking behavior.
# If pywin32 is not available, the module will fall back to a slower but
# safe pure Python file lock implementation to maintain portability.
if os.name == 'nt':  # Windows
    # Thread-safe module-level imports for Windows security (Issue #429, #674)
    # These imports happen once when the module is loaded, ensuring all threads
    # see consistent module availability and preventing race conditions.
    #
    # Security fix for Issue #535: Declare module variables at global scope
    # before try/except to ensure they are accessible everywhere in the module.
    # This prevents NameError if the variables are accessed before import completes.
    #
    # Fix for Issue #696: Allow graceful fallback when pywin32 is not available
    # instead of raising ImportError. This maintains code portability while still
    # preferring pywin32 for optimal performance on Windows.
    win32security = None
    win32con = None
    win32api = None
    win32file = None
    pywintypes = None

    try:
        import win32security
        import win32con
        import win32api
        import win32file
        import pywintypes
    except ImportError:
        # Issue #846: Use file-based lock instead of msvcrt.locking to prevent deadlock risk
        # When pywin32 is not available, use a file-based lock mechanism (.lock file)
        # which provides automatic cleanup when processes terminate, preventing deadlocks
        # that could occur with msvcrt.locking (which only releases locks on file handle close).
        win32security = None
        win32con = None
        win32api = None
        win32file = None
        pywintypes = None

        # Issue #696: Fall back to degraded mode instead of raising ImportError.
        # On Windows, pywin32 is preferred for optimal file locking, but the module
        # will use a fallback lock mechanism (file-based .lock files) to maintain safety.
        # Users are encouraged to install pywin32 for best performance and safety:
        #   pip install pywin32
        #
        # Issue #846, #874: Using file-based lock (.lock file) instead of msvcrt.locking.
        # This prevents deadlock risk and includes enhanced stale lock detection:
        # - Lock files contain PID and timestamp for robust stale lock detection
        # - PID checking allows immediate cleanup when the owning process dies
        # - Time-based fallback (configurable via FW_LOCK_STALE_SECONDS, default 5 min) handles edge cases
        # - atexit handler ensures cleanup on normal program termination
        # Note: Lock files may not be cleaned up on abnormal termination (segfaults),
        # but the PID-based detection allows new processes to recover quickly.
        #
        # Issue #894: CONFIRMED - FileStorage ENFORCES file-based lock in degraded mode.
        # The _acquire_file_lock() method (line 1174+) explicitly checks _is_degraded_mode()
        # and uses .lock files when pywin32 is not available. There is NO msvcrt.locking usage
        # anywhere in the codebase, eliminating deadlock risks mentioned in Issue #894.
        import warnings
        warnings.warn(
            "pywin32 is not installed. Using fallback file locking (.lock files). "
            "For optimal performance and safety on Windows, install pywin32: "
            "pip install pywin32",
            UserWarning,
            stacklevel=2
        )
else:  # Unix-like systems
    # Security fix for Issue #679, #791: Handle missing fcntl gracefully
    # On some Unix-like systems (e.g., Cygwin, restricted environments),
    # fcntl may not be available. We handle this gracefully to allow
    # degraded mode operation, similar to Windows pywin32 handling.
    #
    # Fix for Issue #791: Allow graceful fallback when fcntl is not available
    # instead of raising ImportError. This maintains code portability while still
    # preferring fcntl for optimal performance on Unix systems.
    fcntl = None

    try:
        import fcntl
    except ImportError:
        # Issue #791: Fall back to degraded mode instead of raising ImportError.
        # Issue #884: Update warning to reflect that fallback locking is used.
        # On Unix, fcntl is preferred for optimal file locking, but the module
        # will use a file-based fallback locking mechanism to maintain safety.
        import warnings
        warnings.warn(
            "fcntl is not available. Using fallback file-based locking (.lock files). "
            "This provides safety but may have reduced performance compared to fcntl. "
            "For optimal performance on Unix-like systems, ensure fcntl is available. "
            "If you are on Cygwin, consider using native Windows or a full Unix environment.",
            UserWarning,
            stacklevel=2
        )


def _is_degraded_mode() -> bool:
    """Check if running in degraded mode without optimal file locking.

    Returns True if running on:
    - Windows without pywin32 (uses file-based .lock file fallback)
    - Unix-like systems without fcntl (uses lock file fallback)

    Fix for Issue #696: Allow degraded mode for portability instead of
    raising ImportError. This allows the code to run on Windows without
    pywin32 or on Unix without fcntl, but with fallback locking.

    Fix for Issue #791: Allow degraded mode on Unix systems without fcntl
    for portability, similar to Windows pywin32 handling.

    Fix for Issue #846: Windows degraded mode uses file-based .lock files
    instead of msvcrt.locking to prevent deadlock risk. Lock files include
    stale lock detection.

    Fix for Issue #874: Enhanced lock file cleanup with PID-based detection.
    Lock files contain PID and timestamp. New processes check if the owning
    process is still alive using os.kill(pid, 0), allowing immediate cleanup
    of stale locks when the owner dies. Also added atexit handler cleanup.

    Fix for Issue #829: Unix degraded mode uses lock file fallback instead of
    completely disabling file locking, preventing data corruption in concurrent

    Fix for Issue #894: CONFIRMED - FileStorage ENFORCES file-based lock in
    degraded mode. When _is_degraded_mode() returns True, the _acquire_file_lock()
    method (line 1174+) strictly uses .lock files. NO msvcrt.locking is used,
    eliminating deadlock risks. FileStorage.check() validates degraded mode safety.
    access scenarios.

    Returns:
        bool: True if in degraded mode (Windows without pywin32,
              or Unix without fcntl), False otherwise.
    """
    if os.name == 'nt':
        # On Windows, check if pywin32 modules are available
        return win32file is None
    else:
        # On Unix-like systems, check if fcntl is available
        return fcntl is None


# Fix for Issue #897: Implement generic retry mechanism for transient failures
# File I/O and network operations can fail transiently (e.g., 'Permission denied',
# 'Lock timeout'). This retry mechanism makes the application more resilient against
# temporary glitches without crashing.
import functools
import inspect


# Issue #923: Configurable stale lock timeout via environment variable
# The default stale lock timeout is 300 seconds (5 minutes)
# Users can customize this via FW_LOCK_STALE_SECONDS environment variable
# This is useful for long CI/CD jobs or batch processes that may need
# to hold locks longer than the default threshold
_STALE_LOCK_TIMEOUT_DEFAULT = 300  # 5 minutes in seconds


def _get_stale_lock_timeout() -> int:
    """Get the stale lock timeout from environment variable or default.

    Reads the FW_LOCK_STALE_SECONDS environment variable and validates it.
    If the variable is not set, invalid, or <= 0, returns the default timeout.

    Returns:
        The stale lock timeout in seconds (default: 300).

    Example:
        # Set custom timeout of 10 minutes
        export FW_LOCK_STALE_SECONDS=600
    """
    env_value = os.environ.get('FW_LOCK_STALE_SECONDS', '')
    if not env_value:
        return _STALE_LOCK_TIMEOUT_DEFAULT

    try:
        timeout = int(env_value)
        if timeout <= 0:
            logger.warning(
                f"Invalid FW_LOCK_STALE_SECONDS value: {env_value} "
                f"(must be positive, using default: {_STALE_LOCK_TIMEOUT_DEFAULT})"
            )
            return _STALE_LOCK_TIMEOUT_DEFAULT
        return timeout
    except ValueError:
        logger.warning(
            f"Invalid FW_LOCK_STALE_SECONDS value: {env_value} "
            f"(not a valid integer, using default: {_STALE_LOCK_TIMEOUT_DEFAULT})"
        )
        return _STALE_LOCK_TIMEOUT_DEFAULT


# Module-level constant for easy access in tests
# This is computed once at module load time
STALE_LOCK_TIMEOUT = _get_stale_lock_timeout()


# Reference to module-level logger for use in retry decorator (Issue #937)
_module_logger = logger


def retry_transient_errors(
    max_attempts: int = 3,
    initial_backoff: float = 0.1,
    exponential_base: float = 2.0,
    logger: logging.Logger | None = None,
):
    """Decorator that retries a function on transient I/O errors.

    This decorator catches specific transient exceptions (like IOError with
    EAGAIN, EACCES) and retries with exponential backoff before failing.
    Works with both synchronous and asynchronous functions.

    Transient errors that trigger retry:
    - errno.EAGAIN: Resource temporarily unavailable
    - errno.EACCES: Permission denied (may be transient on some systems)
    - IOError with these error codes

    Permanent errors that do NOT trigger retry (fail immediately):
    - errno.ENOSPC: No space left on device
    - errno.ENOENT: No such file or directory
    - Other permanent I/O errors

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_backoff: Initial backoff time in seconds (default: 0.1)
        exponential_base: Base for exponential backoff (default: 2.0)
        logger: Optional logger instance for logging retry attempts.
                If not provided, uses the default module logger (Issue #937).

    Returns:
        The decorated function with retry logic

    Example:
        @retry_transient_errors(max_attempts=3)
        def save_data():
            # Save operations that may fail transiently
            pass

        @retry_transient_errors(max_attempts=3, logger=custom_logger)
        def save_data_with_custom_logger():
            # Save operations with custom logger
            pass

        @retry_transient_errors(max_attempts=3)
        async def save_data_async():
            # Async save operations that may fail transiently
            pass

    Fix for Issue #897: Generic retry mechanism for transient failures.
    Fix for Issue #937: Add context to retry mechanism with custom logger.
    """
    def decorator(func):
        # Use custom logger if provided, otherwise use module-level logger
        _logger = logger if logger is not None else _module_logger
        is_coroutine = inspect.iscoroutinefunction(func)

        if is_coroutine:
            # Async version
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                attempt = 0
                backoff = initial_backoff

                while attempt < max_attempts:
                    try:
                        return await func(*args, **kwargs)
                    except IOError as e:
                        attempt += 1

                        # Check if this is a transient error
                        # Only retry on specific transient error codes
                        transient_errors = (
                            errno.EAGAIN,  # Resource temporarily unavailable
                            errno.EACCES,  # Permission denied (may be transient)
                            errno.EBUSY,   # Device or resource busy
                            errno.EWOULDBLOCK,  # Operation would block
                        )

                        # Check if error has an errno attribute
                        error_code = getattr(e, 'errno', None)

                        # If it's a permanent error, fail immediately
                        if error_code in (
                            errno.ENOSPC,  # No space left on device
                            errno.ENOENT,  # No such file or directory
                            errno.ENOTDIR,  # Not a directory
                        ):
                            # Permanent error - don't retry
                            _logger.debug(
                                f"Permanent I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If it's not a recognized transient error, don't retry
                        if error_code not in transient_errors:
                            _logger.debug(
                                f"Non-transient I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If we've exhausted all attempts, raise the last error
                        if attempt >= max_attempts:
                            _logger.warning(
                                f"Max retry attempts ({max_attempts}) exhausted for "
                                f"{func.__name__}: {e}"
                            )
                            raise

                        # Retry with exponential backoff with structured logging (Issue #922)
                        _logger.debug(
                            f"Transient error in {func.__name__} (attempt {attempt}/{max_attempts}): "
                            f"{e}. Retrying in {backoff:.2f}s...",
                            extra={
                                'structured': True,
                                'event': 'retry_attempt',
                                'function': func.__name__,
                                'attempt': attempt,
                                'max_attempts': max_attempts,
                                'backoff_seconds': backoff,
                                'error_code': error_code,
                                'error_name': errno.errorcode.get(error_code, 'UNKNOWN'),
                                'error_message': str(e)
                            }
                        )
                        await asyncio.sleep(backoff)
                        backoff *= exponential_base

                # Should not reach here, but just in case
                raise RuntimeError("Unexpected state in retry logic")

            return async_wrapper
        else:
            # Sync version
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                attempt = 0
                backoff = initial_backoff

                while attempt < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except IOError as e:
                        attempt += 1

                        # Check if this is a transient error
                        # Only retry on specific transient error codes
                        transient_errors = (
                            errno.EAGAIN,  # Resource temporarily unavailable
                            errno.EACCES,  # Permission denied (may be transient)
                            errno.EBUSY,   # Device or resource busy
                            errno.EWOULDBLOCK,  # Operation would block
                        )

                        # Check if error has an errno attribute
                        error_code = getattr(e, 'errno', None)

                        # If it's a permanent error, fail immediately
                        if error_code in (
                            errno.ENOSPC,  # No space left on device
                            errno.ENOENT,  # No such file or directory
                            errno.ENOTDIR,  # Not a directory
                        ):
                            # Permanent error - don't retry
                            _logger.debug(
                                f"Permanent I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If it's not a recognized transient error, don't retry
                        if error_code not in transient_errors:
                            _logger.debug(
                                f"Non-transient I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If we've exhausted all attempts, raise the last error
                        if attempt >= max_attempts:
                            _logger.warning(
                                f"Max retry attempts ({max_attempts}) exhausted for "
                                f"{func.__name__}: {e}"
                            )
                            raise

                        # Retry with exponential backoff with structured logging (Issue #922)
                        _logger.debug(
                            f"Transient error in {func.__name__} (attempt {attempt}/{max_attempts}): "
                            f"{e}. Retrying in {backoff:.2f}s...",
                            extra={
                                'structured': True,
                                'event': 'retry_attempt',
                                'function': func.__name__,
                                'attempt': attempt,
                                'max_attempts': max_attempts,
                                'backoff_seconds': backoff,
                                'error_code': error_code,
                                'error_name': errno.errorcode.get(error_code, 'UNKNOWN'),
                                'error_message': str(e)
                            }
                        )
                        time.sleep(backoff)
                        backoff *= exponential_base

                # Should not reach here, but just in case
                raise RuntimeError("Unexpected state in retry logic")

            return sync_wrapper

    return decorator


def retry_io(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
):
    """Decorator that retries I/O operations on transient errors with exponential backoff.

    This decorator is specifically designed for I/O operations and retries on
    common transient filesystem errors (EIO, ENOSPC, EAGAIN, EBUSY) with exponential
    backoff. Unlike retry_transient_errors, this treats ENOSPC as a transient error
    since network filesystems may temporarily report no space.

    Transient errors that trigger retry:
    - errno.EIO: I/O error (common on network mounts)
    - errno.ENOSPC: No space left on device (may be transient on network mounts)
    - errno.EAGAIN: Resource temporarily unavailable
    - errno.EBUSY: Device or resource busy

    Permanent errors that do NOT trigger retry (fail immediately):
    - errno.ENOENT: No such file or directory
    - errno.ENOTDIR: Not a directory
    - Other permanent I/O errors

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Base backoff time in seconds for exponential backoff (default: 0.5)
                        Backoff sequence: backoff_factor, backoff_factor*2, backoff_factor*4, ...

    Returns:
        The decorated function with retry logic

    Example:
        @retry_io(max_retries=3, backoff_factor=0.5)
        def save_data():
            # Save operations that may fail transiently
            pass

        @retry_io(max_retries=5, backoff_factor=1.0)
        async def save_data_async():
            # Async save operations with more retries
            pass

    Fix for Issue #948: Configurable retry mechanism for transient I/O errors.
    """
    def decorator(func):
        is_coroutine = inspect.iscoroutinefunction(func)

        if is_coroutine:
            # Async version
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                attempt = 0
                backoff = backoff_factor

                while attempt < max_retries:
                    try:
                        return await func(*args, **kwargs)
                    except OSError as e:
                        attempt += 1

                        # Check if error has an errno attribute
                        error_code = getattr(e, 'errno', None)

                        # Transient errors that should trigger retry
                        transient_errors = (
                            errno.EIO,      # I/O error (common on network mounts)
                            errno.ENOSPC,   # No space left (may be transient)
                            errno.EAGAIN,   # Resource temporarily unavailable
                            errno.EBUSY,    # Device or resource busy
                        )

                        # Permanent errors that should fail immediately
                        permanent_errors = (
                            errno.ENOENT,   # No such file or directory
                            errno.ENOTDIR,  # Not a directory
                        )

                        # If it's a permanent error, fail immediately
                        if error_code in permanent_errors:
                            _module_logger.debug(
                                f"Permanent I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If it's not a recognized transient error, don't retry
                        if error_code not in transient_errors:
                            _module_logger.debug(
                                f"Non-transient I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If we've exhausted all attempts, raise the last error
                        if attempt >= max_retries:
                            _module_logger.warning(
                                f"Max retry attempts ({max_retries}) exhausted for "
                                f"{func.__name__}: {e}"
                            )
                            raise

                        # Retry with exponential backoff
                        _module_logger.debug(
                            f"Transient I/O error in {func.__name__} (attempt {attempt}/{max_retries}): "
                            f"{e}. Retrying in {backoff:.2f}s..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2  # Exponential backoff

                # Should not reach here, but just in case
                raise RuntimeError("Unexpected state in retry logic")

            return async_wrapper
        else:
            # Sync version
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                attempt = 0
                backoff = backoff_factor

                while attempt < max_retries:
                    try:
                        return func(*args, **kwargs)
                    except OSError as e:
                        attempt += 1

                        # Check if error has an errno attribute
                        error_code = getattr(e, 'errno', None)

                        # Transient errors that should trigger retry
                        transient_errors = (
                            errno.EIO,      # I/O error (common on network mounts)
                            errno.ENOSPC,   # No space left (may be transient)
                            errno.EAGAIN,   # Resource temporarily unavailable
                            errno.EBUSY,    # Device or resource busy
                        )

                        # Permanent errors that should fail immediately
                        permanent_errors = (
                            errno.ENOENT,   # No such file or directory
                            errno.ENOTDIR,  # Not a directory
                        )

                        # If it's a permanent error, fail immediately
                        if error_code in permanent_errors:
                            _module_logger.debug(
                                f"Permanent I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If it's not a recognized transient error, don't retry
                        if error_code not in transient_errors:
                            _module_logger.debug(
                                f"Non-transient I/O error in {func.__name__}: {e}"
                            )
                            raise

                        # If we've exhausted all attempts, raise the last error
                        if attempt >= max_retries:
                            _module_logger.warning(
                                f"Max retry attempts ({max_retries}) exhausted for "
                                f"{func.__name__}: {e}"
                            )
                            raise

                        # Retry with exponential backoff
                        _module_logger.debug(
                            f"Transient I/O error in {func.__name__} (attempt {attempt}/{max_retries}): "
                            f"{e}. Retrying in {backoff:.2f}s..."
                        )
                        time.sleep(backoff)
                        backoff *= 2  # Exponential backoff

                # Should not reach here, but just in case
                raise RuntimeError("Unexpected state in retry logic")

            return sync_wrapper

    return decorator


class AbstractStorage(abc.ABC):
    """Abstract base class for todo storage backends.

    This class defines the interface that all storage implementations must follow.
    It allows the application to support different storage mechanisms (file-based,
    SQLite, Redis, etc.) without modifying the core logic.
    """

    @abc.abstractmethod
    def add(self, todo: Todo, dry_run: bool = False) -> Todo:
        """Add a new todo to storage.

        Args:
            todo: The Todo object to add.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1503).

        Returns:
            The added Todo with any generated fields (like ID) populated.
        """
        pass

    @abc.abstractmethod
    def list(self, status: str | None = None) -> list[Todo]:
        """List all todos, optionally filtered by status.

        Args:
            status: Optional status filter ('pending', 'completed', etc.).

        Returns:
            List of Todo objects.
        """
        pass

    @abc.abstractmethod
    def get(self, todo_id: int) -> Todo | None:
        """Get a todo by ID.

        Args:
            todo_id: The ID of the todo to retrieve.

        Returns:
            The Todo object if found, None otherwise.
        """
        pass

    @abc.abstractmethod
    def update(self, todo: Todo, dry_run: bool = False) -> Todo | None:
        """Update an existing todo.

        Args:
            todo: The Todo object with updated fields.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1503).

        Returns:
            The updated Todo if found, None otherwise.
        """
        pass

    @abc.abstractmethod
    def delete(self, todo_id: int, dry_run: bool = False) -> bool:
        """Delete a todo by ID.

        Args:
            todo_id: The ID of the todo to delete.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1503).

        Returns:
            True if deleted, False if not found.
        """
        pass

    # Async methods (Issue #702)
    @abc.abstractmethod
    async def async_add(self, todo: Todo) -> Todo:
        """Asynchronously add a new todo to storage.

        Args:
            todo: The Todo object to add.

        Returns:
            The added Todo with any generated fields (like ID) populated.
        """
        pass

    @abc.abstractmethod
    async def async_list(self, status: str | None = None) -> list[Todo]:
        """Asynchronously list all todos, optionally filtered by status.

        Args:
            status: Optional status filter ('pending', 'completed', etc.).

        Returns:
            List of Todo objects.
        """
        pass

    @abc.abstractmethod
    async def async_get(self, todo_id: int) -> Todo | None:
        """Asynchronously get a todo by ID.

        Args:
            todo_id: The ID of the todo to retrieve.

        Returns:
            The Todo object if found, None otherwise.
        """
        pass

    @abc.abstractmethod
    async def async_update(self, todo: Todo) -> Todo | None:
        """Asynchronously update an existing todo.

        Args:
            todo: The Todo object with updated fields.

        Returns:
            The updated Todo if found, None otherwise.
        """
        pass

    @abc.abstractmethod
    async def async_delete(self, todo_id: int) -> bool:
        """Asynchronously delete a todo by ID.

        Args:
            todo_id: The ID of the todo to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abc.abstractmethod
    def get_next_id(self) -> int:
        """Get the next available todo ID.

        Returns:
            The next ID to use for a new todo.
        """
        pass

    @abc.abstractmethod
    def add_batch(self, todos: list[Todo]) -> list[Todo]:
        """Add multiple todos in a single batch operation.

        This is more efficient than calling add() multiple times as it
        reduces disk I/O operations.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        pass

    @abc.abstractmethod
    def update_batch(self, todos: list[Todo]) -> list[Todo]:
        """Update multiple todos in a single batch operation.

        This is more efficient than calling update() multiple times as it
        reduces disk I/O operations.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        pass

    @abc.abstractmethod
    async def async_add_batch(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously add multiple todos in a single batch operation.

        This is the async version of add_batch. It provides the same benefits
        of reduced disk I/O operations but in a non-blocking manner.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        pass

    @abc.abstractmethod
    async def async_update_batch(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously update multiple todos in a single batch operation.

        This is the async version of update_batch. It provides the same benefits
        of reduced disk I/O operations but in a non-blocking manner.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        pass

    @abc.abstractmethod
    def delete_batch(self, todo_ids: list[int]) -> list[bool]:
        """Delete multiple todos in a single batch operation.

        This is more efficient than calling delete() multiple times as it
        reduces disk I/O operations.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        pass

    def bulk_add(self, todos: list[Todo]) -> list[Todo]:
        """Add multiple todos in a single bulk operation.

        This is an alias for add_batch() for consistency with bulk naming.
        See add_batch() for full documentation.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        return self.add_batch(todos)

    def bulk_delete(self, todo_ids: list[int]) -> int:
        """Delete multiple todos in a single bulk operation.

        This is a convenience wrapper around delete_batch() that returns
        the count of deleted todos instead of a list of boolean results.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            The number of todos that were successfully deleted.
        """
        results = self.delete_batch(todo_ids)
        return sum(1 for r in results if r)

    def bulk_update(self, todos: list[Todo]) -> int:
        """Update multiple todos in a single bulk operation.

        This is a convenience wrapper around update_batch() that returns
        the count of updated todos instead of a list of updated Todo objects.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            The number of todos that were successfully updated.
        """
        updated = self.update_batch(todos)
        return len(updated)

    @abc.abstractmethod
    async def async_delete_batch(self, todo_ids: list[int]) -> list[bool]:
        """Asynchronously delete multiple todos in a single batch operation.

        This is the async version of delete_batch. It provides the same benefits
        of reduced disk I/O operations but in a non-blocking manner.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        pass

    # Bulk operation aliases (Issue #858)
    @abc.abstractmethod
    def add_many(self, todos: list[Todo]) -> list[Todo]:
        """Add multiple todos (alias for add_batch).

        This is a convenience alias for add_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        pass

    @abc.abstractmethod
    def update_many(self, todos: list[Todo]) -> list[Todo]:
        """Update multiple todos (alias for update_batch).

        This is a convenience alias for update_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        pass

    @abc.abstractmethod
    def delete_many(self, todo_ids: list[int]) -> list[bool]:
        """Delete multiple todos (alias for delete_batch).

        This is a convenience alias for delete_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        pass

    @abc.abstractmethod
    async def async_add_many(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously add multiple todos (alias for async_add_batch).

        This is a convenience alias for async_add_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        pass

    @abc.abstractmethod
    async def async_update_many(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously update multiple todos (alias for async_update_batch).

        This is a convenience alias for async_update_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        pass

    @abc.abstractmethod
    async def async_delete_many(self, todo_ids: list[int]) -> list[bool]:
        """Asynchronously delete multiple todos (alias for async_delete_batch).

        This is a convenience alias for async_delete_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        pass

    async def async_bulk_update(self, todos: list[Todo]) -> int:
        """Asynchronously update multiple todos in a single bulk operation.

        This is a convenience wrapper around async_update_batch() that returns
        the count of updated todos instead of a list of updated Todo objects.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            The number of todos that were successfully updated.
        """
        updated = await self.async_update_batch(todos)
        return len(updated)

    @abc.abstractmethod
    def health_check(self) -> bool:
        """Check if storage backend is healthy and functional.

        This method performs a diagnostic check to verify that the storage
        backend is working properly. It should test file locks, permissions,
        and basic read/write operations.

        Returns:
            True if the storage is healthy, False otherwise.

        Example:
            >>> storage = FileStorage()
            >>> if storage.health_check():
            ...     print("Storage is healthy")
        """
        pass

    @abc.abstractmethod
    def stats(self) -> dict:
        """Get storage statistics and metrics.

        This method returns statistics about the current state of the storage,
        including counts of todos by status and the last modification timestamp.

        Returns:
            A dictionary with the following keys:
            - total: Total number of todos (int)
            - pending: Number of pending todos (int, includes TODO and IN_PROGRESS)
            - completed: Number of completed todos (int, only DONE status)
            - last_modified: Last modification timestamp (int, float, str, or None)

        Example:
            >>> storage = FileStorage()
            >>> stats = storage.stats()
            >>> print(f"Total: {stats['total']}, Completed: {stats['completed']}")
        """
        pass

    def __enter__(self):
        """Enter the context manager.

        This method enables storage implementations to be used as context managers,
        ensuring locks are properly acquired and resources are managed during
        batch operations.

        Returns:
            The storage instance itself.

        Example:
            >>> with storage:
            ...     storage.add(Todo(title="Task"))
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager.

        This method releases resources, handles cleanup, and manages any exceptions
        that occurred within the context. Resources are always cleaned up even if
        an exception occurs.

        Args:
            exc_type: The type of exception raised, if any.
            exc_val: The exception instance raised, if any.
            exc_tb: The traceback object, if any.

        Returns:
            bool: False to indicate exceptions should propagate.

        Example:
            >>> with storage:
            ...     storage.add(Todo(title="Task"))
        """
        # Default implementation - can be overridden by subclasses
        # to perform specific cleanup (e.g., releasing locks, closing files)
        return False

    def __len__(self) -> int:
        """Return the number of todos in storage.

        This allows the storage backend to be used with the built-in len() function,
        making it behave like a standard Python collection.

        Returns:
            The total number of todos in storage.

        Example:
            >>> storage = FileStorage()
            >>> storage.add(Todo(title="Task"))
            >>> len(storage)
            1
        """
        return len(self.list())

    def __iter__(self):
        """Iterate over all todos in storage.

        This allows the storage backend to be used in for loops and other
        iteration contexts, making it behave like a standard Python collection.

        Yields:
            Todo objects from the storage.

        Example:
            >>> storage = FileStorage()
            >>> storage.add(Todo(title="Task 1"))
            >>> storage.add(Todo(title="Task 2"))
            >>> for todo in storage:
            ...     print(todo.title)
        """
        return iter(self.list())


class FileStorage(AbstractStorage):
    """File-based todo storage implementation."""

    def __init__(self, path: str = "~/.flywheel/todos.json", compression: bool = False, backup_count: int = 0, enable_cache: bool = False, lock_timeout: float | None = None, lock_retry_interval: float = 0.1, dry_run: bool = False, metrics: StorageMetrics | None = None):
        """Initialize FileStorage.

        Args:
            path: Path to the storage file.
            compression: Whether to use gzip compression (Issue #652).
                        When True, .gz extension is automatically added to the path.
            backup_count: Number of backup versions to keep (Issue #693).
                          If 0, no backups are created. If > 0, backups are rotated
                          (e.g., .bak, .bak.1, .bak.2, etc.).
            enable_cache: Whether to enable memory cache (Issue #703).
                         When True, get and list operations use cached data,
                         reducing disk I/O and improving performance.
            lock_timeout: File lock acquisition timeout in seconds (Issue #777, #952).
                         If None, reads from FW_LOCK_TIMEOUT_SECONDS environment variable
                         (default 30.0 seconds). If the lock cannot be acquired within
                         this time, a RuntimeError is raised.
            lock_retry_interval: Time in seconds to wait between lock retry attempts (Issue #777).
                                Default is 0.1 seconds (100ms).
            dry_run: Whether to enable dry run mode (Issue #987).
                     When True, skips actual file writes and lock acquisitions,
                     but logs what would have happened. Useful for verifying storage
                     integrity or checking for stale locks without modifying files.
            metrics: Storage metrics instance for observability (Issue #1638).
                    If None, creates a NoOpStorageMetrics instance.

        Raises:
            ValueError: If lock_timeout or lock_retry_interval is not positive.
            RuntimeError: If FLYWHEEL_STRICT_MODE is enabled and optimal file locking
                         is not available (fcntl on Unix, pywin32 on Windows) (Issue #854).
        """
        # Determine lock timeout value (Issue #952)
        # Priority: explicit parameter > environment variable > default
        default_timeout = 30.0
        if lock_timeout is None:
            # Read from environment variable if not explicitly provided
            env_timeout = os.environ.get('FW_LOCK_TIMEOUT_SECONDS')
            if env_timeout is not None:
                try:
                    lock_timeout = float(env_timeout)
                except ValueError:
                    raise ValueError(
                        f"FW_LOCK_TIMEOUT_SECONDS must be a valid number, got '{env_timeout}'"
                    )
            else:
                lock_timeout = default_timeout

        # Validate lock_timeout (Issue #777)
        if lock_timeout <= 0:
            raise ValueError(f"lock_timeout must be positive, got {lock_timeout}")

        # Validate lock_retry_interval (Issue #777)
        if lock_retry_interval <= 0:
            raise ValueError(f"lock_retry_interval must be positive, got {lock_retry_interval}")

        # Security fix for Issue #854: Strict mode prevents degraded operation
        # When FLYWHEEL_STRICT_MODE=1 is set, raise an error if optimal
        # file locking is not available (fcntl on Unix, pywin32 on Windows).
        # This prevents data corruption risks in concurrent scenarios.
        strict_mode = os.environ.get('FLYWHEEL_STRICT_MODE', '0').strip() in ('1', 'true', 'yes', 'on')
        if strict_mode and _is_degraded_mode():
            if os.name == 'nt':
                raise RuntimeError(
                    "FLYWHEEL_STRICT_MODE is enabled but pywin32 is not available. "
                    "For optimal file locking on Windows, install pywin32: pip install pywin32. "
                    "Without pywin32, the system uses degraded mode which may cause data "
                    "corruption when multiple instances run concurrently."
                )
            else:
                raise RuntimeError(
                    "FLYWHEEL_STRICT_MODE is enabled but fcntl is not available. "
                    "For optimal file locking on Unix-like systems, ensure fcntl is available. "
                    "Without fcntl, the system uses degraded mode which may cause data "
                    "corruption when multiple instances run concurrently. "
                    "If you are on Cygwin, consider using native Windows or a full Unix environment."
                )

        self.compression = compression
        self.backup_count = backup_count
        self.dry_run = dry_run  # Issue #987: Dry run mode for safe diagnostics
        # Add .gz extension if compression is enabled and path doesn't already have it
        path_obj = Path(path).expanduser()
        if compression and not str(path_obj).endswith('.gz'):
            path_obj = path_obj.with_suffix(path_obj.suffix + '.gz')
        self.path = path_obj

        # Issue #987: In dry run mode, skip directory creation and lock cleanup
        if not dry_run:
            # Security fix for Issue #429: Module-level imports ensure thread safety.
            # Windows modules (win32security, win32con, win32api, win32file, pywintypes)
            # are now imported at module level, preventing race conditions in multi-threaded
            # environments. The ImportError is raised immediately if pywin32 is missing,
            # so no need to check again here.

            # Security fix for Issue #486: Create and secure parent directories atomically.
            # This eliminates the race condition window between the previous separate calls
            # to _create_and_secure_directories and _secure_all_parent_directories.
            #
            # The _secure_all_parent_directories method now handles both creation and securing
            # in a single atomic operation, ensuring there's no window where directories
            # can be created with insecure permissions.
            #
            # This approach:
            # 1. Creates directories that don't exist with secure permissions from the start
            # 2. Secures all parent directories (even those created by other processes)
            # 3. Handles race conditions where multiple processes create directories concurrently
            # 4. Uses retry logic with exponential backoff to handle TOCTOU issues
            #
            # On Unix: Creates directories with mode=0o700 using restricted umask (Issue #474, #479)
            # On Windows: Creates directories with atomic ACLs using win32file.CreateDirectory (Issue #400)
            self._secure_all_parent_directories(self.path.parent)

            # Cleanup stale lock files on startup (Issue #938)
            # This ensures a clean state for long-running services or after crashes
            self._cleanup_stale_locks(self.path.parent)

        self._todos: list[Todo] = []
        self._next_id: int = 1  # Track next available ID for O(1) generation
        # Thread lock for synchronous operations (Issue #582, #661)
        # IMPORTANT: Uses non-reentrant Lock instead of RLock (Issue #1394)
        # This prevents deadlock in async contexts when using asyncio.to_thread.
        # The FileStorage implementation is designed to avoid reentrancy:
        # - No method holds the lock while calling another method that needs the lock
        # - All methods acquire the lock only for the minimum necessary time
        # - Methods release the lock before calling I/O operations
        # If you add new methods, ensure they follow this pattern to avoid deadlock.
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()  # Async lock for asynchronous operations (Issue #666)
        self._lock_range: int = 0  # File lock range cache (Issue #361)
        self._lock_file_path: str | None = None  # Track lock file path for cleanup (Issue #846)
        self._dirty: bool = False  # Track if data has been modified (Issue #203)
        # Memory cache for improved get/list performance (Issue #703, #718)
        # When enabled, get and list operations return cached data without disk I/O
        # Write-through cache: writes update both cache and disk immediately
        self._cache_enabled = enable_cache
        self._cache: dict[int, Todo] = {}  # Cache dictionary for O(1) lookups by ID
        self._cache_dirty = False  # Track if cache needs invalidation
        self._cache_mtime: float | None = None  # Track file modification time for cache invalidation
        # LRU cache for metadata reads to reduce I/O on network filesystems (Issue #1073)
        # Stores recently loaded file contents with limited size to prevent memory bloat
        self._metadata_cache: dict[str, tuple[list, int, float]] = {}  # path -> (todos, next_id, mtime)
        self._metadata_cache_maxsize = 128  # Maximum number of entries in LRU cache
        self._metadata_cache_lock = threading.Lock()  # Thread-safe cache access
        # File lock timeout to prevent indefinite hangs (Issue #396, #777)
        # Use the provided timeout parameter (default 30.0 seconds)
        self._lock_timeout: float = lock_timeout
        # Retry interval for non-blocking lock attempts (Issue #396, #777)
        # Use the provided retry interval parameter (default 0.1 seconds)
        self._lock_retry_interval: float = lock_retry_interval
        # Storage metrics for observability (Issue #1638)
        # Use provided metrics instance or create NoOpStorageMetrics as fallback
        self.metrics = metrics if metrics is not None else NoOpStorageMetrics()
        # Auto-save interval for periodic saves during operations (Issue #547)
        # 60 seconds provides a good balance between data durability and performance
        self.AUTO_SAVE_INTERVAL: float = 60.0
        # Track last save time for auto-save functionality (Issue #547)
        self.last_saved_time: float = time.time()
        # Minimum save interval to batch rapid small writes (Issue #563)
        # Only save to disk if this much time has passed since the last save,
        # even if _cleanup is called. This reduces I/O for applications making
        # rapid small changes.
        self.MIN_SAVE_INTERVAL: float = 5.0
        # Compaction threshold for automatic file rewriting on delete (Issue #683)
        # When the ratio of deleted items to total items exceeds this threshold,
        # the file will be rewritten to remove deleted items and prevent bloat.
        # 20% (0.2) provides a good balance between performance and storage efficiency.
        self.COMPACTION_THRESHOLD: float = 0.2
        # Gracefully handle load failures to allow object instantiation (Issue #456)
        # If the file is corrupted or malformed, log the error and start with empty state
        # Track initialization success to control cleanup registration (Issue #596)
        # This prevents calling cleanup on partially initialized objects
        # Use synchronous loading to avoid asyncio.run() in __init__ (Issue #641)
        init_success = False
        try:
            self._load_sync()
            init_success = True
        except (
            json.JSONDecodeError,  # JSON parsing errors
            ValueError,  # Invalid data values
        ) as e:
            # Catch specific exceptions during load to prevent data loss (Issue #570)
            # We do NOT catch broad Exception to avoid masking system-level errors
            # like SystemExit or KeyboardInterrupt.
            # NOTE: _load() converts these exceptions to RuntimeError with backup info.
            # If we reach here, it means _load() didn't convert them properly,
            # which should not happen. Log and handle gracefully (Issue #556).
            logger.warning(
                f"Failed to load todos from {self.path}: {e}. "
                f"Starting with empty state."
            )
            # Reset to empty state (already initialized above)
            self._todos = []
            self._next_id = 1
            self._dirty = False
            # Mark as success since we handled the error gracefully
            init_success = True
        except FileNotFoundError:
            # File doesn't exist - normal case for first run (Issue #601)
            # No warning needed, just start with empty state
            # Reset to empty state (already initialized above)
            self._todos = []
            self._next_id = 1
            self._dirty = False
            # Mark as success since this is normal for first run
            init_success = True
        except OSError as e:
            # Other OSErrors (PermissionError, IOError, etc.) should log warning (Issue #601)
            logger.warning(
                f"Failed to load todos from {self.path}: {e}. "
                f"Starting with empty state."
            )
            # Reset to empty state (already initialized above)
            self._todos = []
            self._next_id = 1
            self._dirty = False
            # Mark as success since we handled the error gracefully
            init_success = True
        except RuntimeError as e:
            # RuntimeError from _load() may or may not have successful backup (Issue #580)
            # Check error message to determine if backup was created
            error_msg = str(e)
            if "Backup saved to" in error_msg or "Backup created at" in error_msg:
                # Backup was created successfully, we can recover gracefully
                logger.warning(
                    f"Data integrity issue in {self.path}: {e}. "
                    f"Starting with empty state."
                )
                # Reset to empty state (already initialized above)
                self._todos = []
                self._next_id = 1
                self._dirty = False
                # Mark as success since backup exists and we handled the error
                init_success = True
            else:
                # Critical failure without successful backup (Issue #580)
                # This could mean:
                # 1. Original RuntimeError from _load() (e.g., format validation failure)
                # 2. Backup creation failed
                # In either case, init_success should remain False
                logger.error(
                    f"Critical initialization failure for {self.path}: {e}. "
                    f"Object not properly initialized."
                )
                # init_success remains False, atexit will not be registered
                # Re-raise to inform the caller of the failure
                raise
        finally:
            # Register cleanup handler to save dirty data on exit (Issue #203)
            # IMPORTANT: Only register if initialization succeeded (Issue #525)
            # This prevents calling cleanup on partially initialized objects
            if init_success:
                atexit.register(self._cleanup)

                # Start auto-save background thread (Issue #592)
                # This thread periodically checks if data has been modified (_dirty flag)
                # and automatically saves to disk to prevent data loss if the program crashes
                self._auto_save_stop_event = threading.Event()
                self._auto_save_thread = threading.Thread(
                    target=self._auto_save_worker,
                    daemon=True,
                    name="FileStorage-auto-save"
                )
                self._auto_save_thread.start()

    @classmethod
    async def create(cls, path: str = "~/.flywheel/todos.json", compression: bool = False, backup_count: int = 0, enable_cache: bool = False, lock_timeout: float = 30.0, lock_retry_interval: float = 0.1, dry_run: bool = False) -> "FileStorage":
        """Asynchronously create a FileStorage instance without blocking the event loop.

        This is an async factory method that creates a FileStorage instance and runs
        the synchronous file I/O in a thread pool executor to avoid blocking the event loop (Issue #646).

        The regular __init__ method performs synchronous file I/O which can block the event loop
        when called from async code. This method uses asyncio.to_thread() to run the file I/O
        in a separate thread, allowing other async tasks to run concurrently.

        Args:
            path: The path to the storage file. Defaults to ~/.flywheel/todos.json.
            compression: Whether to use gzip compression (Issue #652).
            backup_count: Number of backup versions to keep (Issue #693).
            enable_cache: Whether to enable memory cache (Issue #703).
            lock_timeout: File lock acquisition timeout in seconds (Issue #777).
                         Default is 30.0 seconds.
            lock_retry_interval: Time in seconds to wait between lock retry attempts (Issue #777).
                                Default is 0.1 seconds.
            dry_run: Whether to enable dry run mode (Issue #987).
                     When True, skips actual file writes and lock acquisitions.

        Returns:
            A fully initialized FileStorage instance with data loaded from disk.

        Raises:
            RuntimeError: If a critical initialization failure occurs and no backup was created.
            ValueError: If lock_timeout or lock_retry_interval is not positive.

        Example:
            >>> # In async context
            >>> storage = await FileStorage.create()
            >>> # Or with custom path
            >>> storage = await FileStorage.create(path="/custom/path/todos.json")
        """
        # Validate lock_timeout (Issue #777)
        if lock_timeout <= 0:
            raise ValueError(f"lock_timeout must be positive, got {lock_timeout}")

        # Validate lock_retry_interval (Issue #777)
        if lock_retry_interval <= 0:
            raise ValueError(f"lock_retry_interval must be positive, got {lock_retry_interval}")

        # Create instance with minimal initialization
        # We need to bypass __init__ to avoid blocking, so we use __new__ and manually initialize
        instance = cls.__new__(cls)
        instance.compression = compression
        instance.backup_count = backup_count
        instance.dry_run = dry_run  # Issue #987: Dry run mode
        # Add .gz extension if compression is enabled and path doesn't already have it
        path_obj = Path(path).expanduser()
        if compression and not str(path_obj).endswith('.gz'):
            path_obj = path_obj.with_suffix(path_obj.suffix + '.gz')
        instance.path = path_obj

        # Issue #987: Skip directory initialization in dry run mode
        if not dry_run:
            # Initialize all instance attributes (same as __init__)
            instance._secure_all_parent_directories(instance.path.parent)
        instance._todos = []
        instance._next_id = 1
        instance._lock = threading.Lock()
        instance._lock_range = 0
        instance._dirty = False
        # Memory cache for improved get/list performance (Issue #703, #718)
        instance._cache_enabled = enable_cache
        instance._cache: dict[int, Todo] = {}
        instance._cache_dirty = False
        instance._cache_mtime = None
        instance._lock_timeout = lock_timeout
        instance._lock_retry_interval = lock_retry_interval
        instance.AUTO_SAVE_INTERVAL = 60.0
        instance.last_saved_time = time.time()
        instance.MIN_SAVE_INTERVAL = 5.0
        instance.COMPACTION_THRESHOLD = 0.2

        # Gracefully handle load failures to allow object instantiation (Issue #456)
        # Load data asynchronously using aiofiles to avoid blocking event loop (Issue #646, #747)
        init_success = False
        try:
            await instance._load_async()
            init_success = True
        except (
            json.JSONDecodeError,  # JSON parsing errors
            ValueError,  # Invalid data values
        ) as e:
            # Catch specific exceptions during load to prevent data loss (Issue #570)
            logger.warning(
                f"Failed to load todos from {instance.path}: {e}. "
                f"Starting with empty state."
            )
            # Reset to empty state (already initialized above)
            instance._todos = []
            instance._next_id = 1
            instance._dirty = False
            # Mark as success since we handled the error gracefully
            init_success = True
        except FileNotFoundError:
            # File doesn't exist - normal case for first run (Issue #601)
            # No warning needed, just start with empty state
            # Reset to empty state (already initialized above)
            instance._todos = []
            instance._next_id = 1
            instance._dirty = False
            # Mark as success since this is normal for first run
            init_success = True
        except OSError as e:
            # Other OSErrors (PermissionError, IOError, etc.) should log warning (Issue #601)
            logger.warning(
                f"Failed to load todos from {instance.path}: {e}. "
                f"Starting with empty state."
            )
            # Reset to empty state (already initialized above)
            instance._todos = []
            instance._next_id = 1
            instance._dirty = False
            # Mark as success since we handled the error gracefully
            init_success = True
        except RuntimeError as e:
            # RuntimeError from _load_sync may or may not have successful backup (Issue #580)
            # Check error message to determine if backup was created
            error_msg = str(e)
            if "Backup saved to" in error_msg or "Backup created at" in error_msg:
                # Backup was created successfully, we can recover gracefully
                logger.warning(
                    f"Data integrity issue in {instance.path}: {e}. "
                    f"Starting with empty state."
                )
                # Reset to empty state (already initialized above)
                instance._todos = []
                instance._next_id = 1
                instance._dirty = False
                # Mark as success since backup exists and we handled the error
                init_success = True
            else:
                # Critical failure without successful backup (Issue #580)
                # This could mean:
                # 1. Original RuntimeError from _load_sync (e.g., format validation failure)
                # 2. Backup creation failed
                # In either case, init_success should remain False
                logger.error(
                    f"Critical initialization failure for {instance.path}: {e}. "
                    f"Object not properly initialized."
                )
                # init_success remains False, atexit will not be registered
                # Re-raise to inform the caller of the failure
                raise

        # Register cleanup handler and start auto-save thread only if initialization succeeded (Issue #525)
        if init_success:
            # Register cleanup handler to save dirty data on exit (Issue #203)
            atexit.register(instance._cleanup)

            # Start auto-save background thread (Issue #592)
            instance._auto_save_stop_event = threading.Event()
            instance._auto_save_thread = threading.Thread(
                target=instance._auto_save_worker,
                daemon=True,
                name="FileStorage-auto-save"
            )
            instance._auto_save_thread.start()

        return instance

    def _get_file_lock_range_from_handle(self, file_handle) -> tuple:
        """Get the Windows file lock range for mandatory locking.

        This method returns lock range parameters for Windows mandatory file
        locking using win32file.LockFileEx. On Windows, a fixed very large
        lock range is used to prevent deadlocks when the file size changes
        between lock acquisition and release (Issue #375, #426, #451).

        Args:
            file_handle: The open file handle (unused, kept for API compatibility).

        Returns:
            On Windows: A tuple of (low, high) representing the LENGTH to lock in bytes.
                The actual lock region starts from offset 0 (file beginning) and extends
                for (low + high << 32) bytes. Returns (0, 1) for exactly 4GB.
            On Unix: A placeholder value (ignored by fcntl.flock).

        Note:
            PYWIN32 API SEMANTICS (Issue #496):
            The pywin32 LockFileEx wrapper uses these parameters:
                LockFileEx(hFile, dwFlags, dwReserved,
                          NumberOfBytesToLockLow, NumberOfBytesToLockHigh,
                          overlapped)

            - The 4th and 5th parameters (returned by this method) specify the LENGTH
              to lock, NOT the offset. The offset is specified via the overlapped
              structure, which defaults to 0 (file start).
            - Therefore, (0, 1) means: lock 4GB bytes starting from file beginning
              (offset 0) to offset 4GB.

            - On Windows, uses win32file.LockFileEx for MANDATORY locking (Issue #451)
            - Mandatory locks enforce mutual exclusion on all systems
            - Returns (0, 1) representing exactly 4GB (0x100000000 bytes) of lock LENGTH
            - This approach prevents the issue where file grows between lock
              acquisition and release
            - On Unix, fcntl.flock doesn't use lock ranges, so value is ignored
        """
        if os.name == 'nt':  # Windows
            # Security fix for Issue #375, #426, and #451: Use a fixed very large
            # lock range with win32file.LockFileEx for mandatory locking
            #
            # Mandatory locking (Issue #451):
            # - Uses win32file.LockFileEx instead of msvcrt.locking
            # - Enforces mutual exclusion on ALL processes, not just cooperative ones
            # - Prevents malicious or unaware processes from writing concurrently
            # - Provides data integrity guarantees that advisory locks cannot
            #
            # PYWIN32 API SEMANTICS (Issue #496):
            # The pywin32 LockFileEx wrapper has signature:
            #   LockFileEx(hFile, dwFlags, dwReserved, NumberOfBytesToLockLow,
            #              NumberOfBytesToLockHigh, overlapped)
            #
            # - The 4th and 5th parameters specify the LENGTH to lock (not offset)
            # - The offset is specified via the overlapped structure (defaults to 0)
            # - We use a default OVERLAPPED() which locks from offset 0 (file start)
            #
            # Therefore, (0, 1) means: lock 4GB bytes starting from file beginning
            # - Length = 0 + (1 << 32) = 0x100000000 = 4294967296 bytes = exactly 4GB
            # - Offset = 0 (from default OVERLAPPED structure)
            #
            # Security fix for Issue #465: Starting from offset 0 instead of 0xFFFFFFFF
            # prevents lock failures on files smaller than 4GB. The previous approach
            # attempted to lock from beyond EOF, causing ERROR_LOCK_VIOLATION (error 33).
            # Security fix for Issue #469: Corrected from (0, 0xFFFFFFFF) to (0xFFFFFFFF, 0)
            # to accurately represent 4GB. The old value (0, 0xFFFFFFFF) would lock
            # ~16 Exabytes, which did not match the documented behavior.
            # Security fix for Issue #480: Corrected from (0xFFFFFFFF, 0) to (0, 1) to
            # represent exactly 4GB (0x100000000 bytes). The old value (0xFFFFFFFF, 0)
            # represented 4GB-1 (0xFFFFFFFF bytes), which is not exactly 4GB as documented.
            # Security fix for Issue #496: Clarified that (0, 1) specifies LENGTH, not offset.
            # The offset is 0 (file start) from the default OVERLAPPED structure.
            return (0, 1)
        else:
            # On Unix, fcntl.flock doesn't use lock ranges
            # Return a placeholder value (will be ignored)
            return 0

    @measure_latency("acquire_file_lock")
    def _acquire_file_lock(self, file_handle) -> None:
        """Acquire an exclusive file lock for multi-process safety (Issue #268, #451).

        Args:
            file_handle: The file handle to lock.

        Raises:
            IOError: If the lock cannot be acquired.
            RuntimeError: If lock acquisition times out (Issue #396).

        Note:
            PLATFORM DIFFERENCES (Issue #411, #451):

            Windows (win32file.LockFileEx):
            - Uses MANDATORY LOCKING - enforces mutual exclusion on ALL processes
            - Blocks ALL processes from writing, including malicious or unaware ones
            - Provides strong data integrity guarantees
            - Uses LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK flags
            - Non-blocking mode with retry to prevent hangs (Issue #396)

            Unix-like systems (fcntl.flock):
            - Provides strong synchronization guarantees
            - Uses non-blocking mode (LOCK_EX | LOCK_NB) with retry

            For Windows, a fixed 4GB lock LENGTH (0, 1) is used to prevent
            deadlocks when the file size changes between lock acquisition and
            release (Issue #375, #426, #451, #465, #469, #480, #496).

            IMPORTANT (Issue #496): The values (0, 1) represent LENGTH, not offset.
            The pywin32 LockFileEx wrapper specifies lock length via parameters and
            offset via the overlapped structure (which defaults to 0). Therefore,
            (0, 1) locks 4GB bytes starting from file offset 0 (file beginning).

            All file operations are serialized by self._lock (RLock), ensuring
            that acquire and release are always properly paired (Issue #366).

            Timeout mechanism (Issue #396):
            - Windows: Uses LOCKFILE_FAIL_IMMEDIATELY with retry loop and timeout
            - Unix: Uses LOCK_EX | LOCK_NB with retry loop and timeout

            Degraded mode (Issue #846, #874):
            - Windows without pywin32: Uses file-based .lock files
            - Unix without fcntl: Uses file-based .lock files
            - Lock files contain PID and timestamp for stale detection
            - PID checking allows immediate cleanup when owner process dies
            - Time-based fallback (configurable via FW_LOCK_STALE_SECONDS, default 5 min) handles edge cases
            - atexit handler ensures cleanup on normal termination

            IMPORTANT (Issue #894): CONFIRMED - Degraded mode ENFORCES file-based locking.
            When _is_degraded_mode() returns True, this method STRICTLY uses .lock files.
            There is NO code path that uses msvcrt.locking or skips locking entirely.
            This eliminates deadlock and data corruption risks mentioned in Issue #894.

            Dry run mode (Issue #987):
            - When dry_run is True, skips actual lock acquisition
            - Logs what would have happened without modifying any files
            - Useful for diagnostics and checking for stale locks safely
        """
        # Issue #987: Skip lock acquisition in dry run mode
        if self.dry_run:
            logger.info(
                f"Dry run mode: Would acquire file lock for {file_handle.name}",
                extra={
                    'structured': True,
                    'event': 'dry_run_lock_skipped',
                    'file_path': file_handle.name
                }
            )
            return
        if os.name == 'nt':  # Windows
            # Portability fix for Issue #671: Check if running in degraded mode
            if _is_degraded_mode():
                # Issue #846: pywin32 is not available - use file-based lock (.lock file)
                # instead of msvcrt.locking to prevent deadlock risk
                #
                # Issue #894: CONFIRMED - This code path is MANDATORY when degraded mode is active.
                # There is NO fallback to msvcrt.locking or skipping locks. File-based locking
                # is enforced here, preventing the deadlock risks described in Issue #894.
                #
                # Issue #899: SAFETY CHECK - Ensure win32file is None in degraded mode.
                # This defensive check prevents accidental use of win32file when it should be None,
                # eliminating any potential for deadlock or data corruption in degraded mode.
                assert win32file is None, (
                    "CRITICAL: In degraded mode, win32file must be None. "
                    "This ensures file-based locking is used instead of win32file.LockFileEx."
                )

                # Issue #919: SAFETY CHECK - Ensure ALL win32 modules are None in degraded mode.
                # This defensive check prevents accidental use of any win32 module when it should be None,
                # eliminating any potential for deadlock or data corruption in degraded mode.
                # These checks ensure that degraded mode cannot accidentally use pywin32 APIs,
                # which would be unsafe and could cause deadlocks or crashes.
                assert win32security is None, (
                    "CRITICAL: In degraded mode, win32security must be None. "
                    "This ensures file-based locking is used and prevents accidental use "
                    "of Windows security APIs that could cause deadlocks."
                )
                assert win32con is None, (
                    "CRITICAL: In degraded mode, win32con must be None. "
                    "This ensures file-based locking is used and prevents accidental use "
                    "of Windows constants that could cause deadlocks."
                )
                assert win32api is None, (
                    "CRITICAL: In degraded mode, win32api must be None. "
                    "This ensures file-based locking is used and prevents accidental use "
                    "of Windows APIs that could cause deadlocks."
                )
                assert pywintypes is None, (
                    "CRITICAL: In degraded mode, pywintypes must be None. "
                    "This ensures file-based locking is used and prevents accidental use "
                    "of pywin32 types that could cause deadlocks."
                )

                logger.info(
                    "Using fallback file locking (.lock files) in degraded mode. "
                    "For optimal performance, install pywin32.",
                    extra={
                        'structured': True,
                        'event': 'lock_mode_info',
                        'mode': 'degraded',
                        'lock_type': 'file_based',
                        'reason': 'pywin32_not_available'
                    }
                )

                # Use file-based lock mechanism with automatic stale lock cleanup
                # This prevents deadlocks that could occur with msvcrt.locking
                lock_file_path = file_handle.name + ".lock"

                start_time = time.time()
                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= self._lock_timeout:
                        raise RuntimeError(
                            f"File lock acquisition timed out after {elapsed:.1f}s "
                            f"(timeout: {self._lock_timeout}s) using file-based lock. "
                            f"File: {file_handle.name}"
                        )

                    try:
                        # Try to create lock file exclusively (atomic operation)
                        # Issue #886: This 'x' mode provides atomicity - only one process
                        # can succeed even if multiple detected and removed a stale lock
                        # This will fail if the file already exists
                        with open(lock_file_path, 'x') as lock_file:
                            # Write lock metadata for debugging and stale lock detection
                            lock_file.write(f"pid={os.getpid()}\n")
                            lock_file.write(f"locked_at={time.time()}\n")

                        # Lock acquired successfully - track for cleanup and log with structured data (Issue #922)
                        self._lock_range = "filelock"
                        self._lock_file_path = lock_file_path
                        logger.debug(
                            f"File-based lock acquired: {lock_file_path}",
                            extra={
                                'structured': True,
                                'event': 'lock_acquired',
                                'lock_type': 'file_based',
                                'lock_file_path': lock_file_path,
                                'acquisition_time_seconds': elapsed,
                                'lock_wait_ms': elapsed * 1000,  # Issue #1618: Performance metric
                                'pid': os.getpid()
                            }
                        )
                        return

                    except FileExistsError:
                        # Lock file already exists - check if it's stale
                        try:
                            with open(lock_file_path, 'r') as lock_file:
                                content = lock_file.read()
                                locked_at = None
                                locked_pid = None
                                for line in content.split('\n'):
                                    if line.startswith('locked_at='):
                                        locked_at = float(line.split('=')[1])
                                    elif line.startswith('pid='):
                                        locked_pid = int(line.split('=')[1])

                                # Issue #874: Enhanced stale lock detection with PID checking
                                # Check if the process that created the lock is still alive
                                is_stale = False
                                stale_reason = ""

                                # Method 1: Check if PID exists (most reliable)
                                if locked_pid is not None:
                                    try:
                                        # Send signal 0 to check if process exists
                                        # This doesn't actually send a signal, just checks existence
                                        os.kill(locked_pid, 0)
                                        # Process exists, check if it's old enough to be stale
                                        stale_threshold = STALE_LOCK_TIMEOUT
                                        if locked_at and (time.time() - locked_at) > stale_threshold:
                                            is_stale = True
                                            stale_reason = f"old lock (age: {time.time() - locked_at:.1f}s)"
                                    except OSError:
                                        # Process doesn't exist - lock is stale
                                        is_stale = True
                                        stale_reason = f"process {locked_pid} not found"
                                elif locked_at is not None:
                                    # Fallback: If no PID info, use time-based detection
                                    stale_threshold = STALE_LOCK_TIMEOUT
                                    if (time.time() - locked_at) > stale_threshold:
                                        is_stale = True
                                        stale_reason = f"old lock without PID (age: {time.time() - locked_at:.1f}s)"

                                if is_stale:
                                    logger.warning(
                                        f"Found stale lock file ({stale_reason}), "
                                        f"removing and retrying: {lock_file_path}",
                                        extra={
                                            'structured': True,
                                            'event': 'stale_lock_detected',
                                            'lock_type': 'file_based',
                                            'file_path': lock_file_path,
                                            'reason': stale_reason,
                                            'stale_pid': locked_pid,
                                            'stale_age_seconds': time.time() - locked_at if locked_at else None
                                        }
                                    )
                                    # Issue #886: Fix TOCTOU race condition in stale lock removal
                                    # Use atomic unlink-and-retry pattern to prevent race condition
                                    # where multiple processes detect stale lock simultaneously.
                                    # The atomic open(..., 'x') at the top of the loop ensures
                                    # only one process will acquire the lock after removal.
                                    try:
                                        os.unlink(lock_file_path)
                                    except FileNotFoundError:
                                        # Another process already removed the stale lock
                                        logger.debug(f"Stale lock already removed by another process: {lock_file_path}")
                                    except OSError as e:
                                        logger.warning(f"Failed to remove stale lock: {e}")
                                    # Immediately retry to acquire lock (no sleep needed)
                                    # The atomic open(..., 'x') will ensure mutual exclusion
                                    continue

                        except (OSError, ValueError, IndexError) as e:
                            # Lock file exists but is corrupted or unreadable
                            logger.warning(f"Unreadable lock file found, removing: {e}")
                            # Issue #886: Handle corrupted lock files with proper error handling
                            try:
                                os.unlink(lock_file_path)
                            except FileNotFoundError:
                                # Another process already removed the corrupted lock
                                logger.debug(f"Corrupted lock already removed: {lock_file_path}")
                            except OSError as unlink_err:
                                logger.warning(f"Failed to remove corrupted lock: {unlink_err}")
                            # Immediately retry to acquire lock
                            continue

                        # Lock is held by another active process - log with structured data (Issue #922)
                        logger.debug(
                            f"File is locked by another process, waiting... "
                            f"(elapsed: {elapsed:.1f}s)",
                            extra={
                                'structured': True,
                                'event': 'lock_retry',
                                'lock_type': 'file_based',
                                'file_path': file_handle.name,
                                'elapsed_seconds': elapsed,
                                'retry_interval': self._lock_retry_interval,
                                'lock_timeout': self._lock_timeout
                            }
                        )
                        time.sleep(self._lock_retry_interval)
                    except OSError as e:
                        # Other OS error - retry
                        logger.warning(f"Failed to create lock file: {e}, retrying...")
                        time.sleep(self._lock_retry_interval)

            # Windows locking: win32file.LockFileEx for MANDATORY locking (Issue #451)
            # SECURITY: Mandatory locks enforce mutual exclusion on ALL processes
            # - Prevents malicious or unaware processes from writing concurrently
            # - Provides data integrity guarantees that advisory locks cannot
            # - Uses win32file.LockFileEx instead of file-based .lock files
            #
            # Security fix for Issue #429: Windows modules are imported at module level,
            # ensuring thread-safe initialization. No need to import here.

            try:
                # Get the Windows file handle from Python file object
                win_handle = win32file._get_osfhandle(file_handle.fileno())

                # Get the lock range (fixed large value for mandatory locking)
                lock_range_low, lock_range_high = self._get_file_lock_range_from_handle(file_handle)

                # Cache the lock range for use in _release_file_lock (Issue #351)
                # This ensures we use the same range for unlock
                self._lock_range = (lock_range_low, lock_range_high)

                # CRITICAL: Flush buffers before locking (Issue #390)
                # Python file objects have buffers that must be flushed before
                # locking to ensure data is synchronized to disk
                file_handle.flush()

                # Create overlapped structure for async operation
                overlapped = pywintypes.OVERLAPPED()

                # Timeout mechanism for lock acquisition (Issue #396)
                # Use LOCKFILE_FAIL_IMMEDIATELY with retry loop
                start_time = time.time()
                last_error = None

                # Lock flags: LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK
                lock_flags = win32con.LOCKFILE_FAIL_IMMEDIATELY | win32con.LOCKFILE_EXCLUSIVE_LOCK

                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= self._lock_timeout:
                        # Timeout exceeded - raise error with details
                        raise RuntimeError(
                            f"File lock acquisition timed out after {elapsed:.1f}s "
                            f"(timeout: {self._lock_timeout}s). "
                            f"This may indicate a competing process died while holding "
                            f"the lock or a deadlock condition. File: {file_handle.name}"
                        )

                    try:
                        # Try non-blocking mandatory lock (Issue #451)
                        # win32file.LockFileEx provides MANDATORY locking on Windows
                        # This blocks ALL processes from writing, not just cooperative ones
                        #
                        # PYWIN32 API (Issue #496):
                        # LockFileEx(hFile, dwFlags, dwReserved,
                        #            NumberOfBytesToLockLow, NumberOfBytesToLockHigh,
                        #            overlapped)
                        # - lock_range_low/high: LENGTH to lock (not offset)
                        # - overlapped: specifies offset (defaults to 0 = file start)
                        # - Therefore: locks from file start for 4GB bytes
                        win32file.LockFileEx(
                            win_handle,
                            lock_flags,
                            0,  # Reserved
                            lock_range_low,  # NumberOfBytesToLockLow (LENGTH, not offset)
                            lock_range_high,  # NumberOfBytesToLockHigh (LENGTH, not offset)
                            overlapped  # Specifies offset (defaults to 0)
                        )
                        # Lock acquired successfully - log with structured data (Issue #922)
                        elapsed = time.time() - start_time
                        logger.debug(
                            f"File lock acquired successfully for {file_handle.name}",
                            extra={
                                'structured': True,
                                'event': 'lock_acquired',
                                'lock_type': 'windows_win32',
                                'file_path': file_handle.name,
                                'acquisition_time_seconds': elapsed,
                                'lock_wait_ms': elapsed * 1000,  # Issue #1618: Performance metric
                                'lock_range_low': lock_range_low,
                                'lock_range_high': lock_range_high
                            }
                        )
                        break
                    except pywintypes.error as e:
                        # Lock is held by another process
                        # Error code 33: ERROR_LOCK_VIOLATION
                        # Error code 167: ERROR_LOCK_FAILED
                        if e.winerror in (33, 167):
                            # Save error for potential reporting
                            last_error = e
                            # Log retry attempt with structured data (Issue #922)
                            elapsed = time.time() - start_time
                            logger.debug(
                                f"Windows lock held by another process, retrying... "
                                f"(elapsed: {elapsed:.1f}s, error: {e.winerror})",
                                extra={
                                    'structured': True,
                                    'event': 'lock_retry',
                                    'lock_type': 'windows_win32',
                                    'file_path': file_handle.name,
                                    'elapsed_seconds': elapsed,
                                    'retry_interval': self._lock_retry_interval,
                                    'winerror_code': e.winerror,
                                    'lock_timeout': self._lock_timeout
                                }
                            )
                            # Wait before retrying
                            time.sleep(self._lock_retry_interval)
                            # Continue retry loop
                        else:
                            # Unexpected error - raise immediately
                            logger.error(f"Failed to acquire Windows mandatory lock: {e}")
                            raise

            except (pywintypes.error, RuntimeError) as e:
                if isinstance(e, RuntimeError):
                    # Re-raise timeout errors as-is
                    logger.error(f"Failed to acquire Windows mandatory lock: {e}")
                    raise
                else:
                    logger.error(f"Failed to acquire Windows mandatory lock: {e}")
                    raise
        else:  # Unix-like systems
            # Portability fix for Issue #791: Check if running in degraded mode
            if _is_degraded_mode():
                # Issue #829: fcntl is not available - use file-based lock fallback
                # instead of completely disabling file locking
                logger.info(
                    "Using fallback file locking (lock file) in degraded mode. "
                    "For optimal performance, ensure fcntl is available.",
                    extra={
                        'structured': True,
                        'event': 'lock_mode_info',
                        'mode': 'degraded',
                        'lock_type': 'file_based_fallback',
                        'reason': 'fcntl_not_available'
                    }
                )

                try:
                    # Implement file-based lock using atomic mkdir operation
                    # This is a common pattern for file locking on Unix without fcntl
                    lock_dir = Path(str(file_handle.name) + ".lock")
                    lock_pid_file = lock_dir / "pid"

                    # Timeout mechanism for lock acquisition
                    start_time = time.time()

                    while True:
                        elapsed = time.time() - start_time
                        if elapsed >= self._lock_timeout:
                            raise RuntimeError(
                                f"File lock acquisition timed out after {elapsed:.1f}s "
                                f"(timeout: {self._lock_timeout}s) using lock file fallback. "
                                f"File: {file_handle.name}"
                            )

                        try:
                            # Try to create lock directory (atomic operation)
                            lock_dir.mkdir(exist_ok=False)

                            # Successfully created lock directory - we have the lock
                            # Write our PID to the lock file for debugging
                            lock_pid_file.write_text(str(os.getpid()))

                            # Store lock directory path for later release
                            self._lock_range = str(lock_dir)

                            logger.debug(
                                f"Lock file fallback acquired for {file_handle.name}",
                                extra={
                                    'structured': True,
                                    'event': 'lock_acquired',
                                    'lock_type': 'file_based',
                                    'file_path': file_handle.name,
                                    'lock_dir': str(lock_dir),
                                    'mode': 'degraded',
                                    'acquisition_time_seconds': elapsed
                                }
                            )
                            return  # Lock acquired successfully

                        except FileExistsError:
                            # Lock directory already exists - check if it's stale
                            try:
                                # Read PID from lock file
                                pid_str = lock_pid_file.read_text().strip()
                                pid = int(pid_str)

                                # Check if process with this PID is still running
                                try:
                                    # Send signal 0 to check if process exists
                                    os.kill(pid, 0)
                                    # Process is still running - lock is active
                                except OSError:
                                    # Process is not running - stale lock
                                    logger.warning(
                                        f"Removing stale lock file from PID {pid}",
                                        extra={
                                            'structured': True,
                                            'event': 'stale_lock_detected',
                                            'lock_type': 'file_based',
                                            'file_path': str(lock_dir),
                                            'stale_pid': pid,
                                            'reason': f'process_{pid}_not_found'
                                        }
                                    )
                                    # Remove the stale lock directory
                                    lock_pid_file.unlink(missing_ok=True)
                                    lock_dir.rmdir()
                                    # Continue to retry acquiring the lock
                            except (ValueError, FileNotFoundError, OSError) as e:
                                # Lock file is corrupted or unreadable
                                # Wait and retry to avoid race conditions
                                pass

                            # Wait before retrying
                            time.sleep(self._lock_retry_interval)

                except (RuntimeError, OSError) as e:
                    if isinstance(e, RuntimeError):
                        # Re-raise timeout errors as-is
                        logger.error(f"Failed to acquire fallback file lock: {e}")
                        raise
                    else:
                        logger.error(f"Failed to acquire fallback file lock: {e}")
                        raise

            # Unix locking: fcntl.flock (Issue #411)
            # Provides strong synchronization guarantees
            # LOCK_EX = exclusive lock
            # LOCK_NB = non-blocking mode
            # Use retry loop with timeout for consistency with Windows (Issue #396)
            try:
                # Cache a placeholder lock range for consistency (Issue #351)
                # On Unix, this isn't used by fcntl.flock but we cache it
                # to maintain consistent API behavior across platforms
                self._lock_range = 0

                # Timeout mechanism for lock acquisition (Issue #396)
                # Use non-blocking mode with retry loop for consistency with Windows
                start_time = time.time()
                last_error = None

                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= self._lock_timeout:
                        # Timeout exceeded - raise error with details
                        raise RuntimeError(
                            f"File lock acquisition timed out after {elapsed:.1f}s "
                            f"(timeout: {self._lock_timeout}s). "
                            f"This may indicate a competing process died while holding "
                            f"the lock or a deadlock condition. File: {file_handle.name}"
                        )

                    try:
                        # Try non-blocking lock (LOCK_EX | LOCK_NB)
                        # This returns immediately with IOError if lock is held
                        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        # Lock acquired successfully - log with structured data (Issue #922)
                        elapsed = time.time() - start_time
                        logger.debug(
                            f"File lock acquired successfully for {file_handle.name}",
                            extra={
                                'structured': True,
                                'event': 'lock_acquired',
                                'lock_type': 'unix_fcntl',
                                'file_path': file_handle.name,
                                'acquisition_time_seconds': elapsed,
                                'lock_wait_ms': elapsed * 1000  # Issue #1618: Performance metric
                            }
                        )
                        break
                    except IOError as e:
                        # Lock is held by another process - log retry with structured data (Issue #922)
                        # Save error for potential reporting
                        last_error = e
                        elapsed = time.time() - start_time
                        error_code = getattr(e, 'errno', None)
                        logger.debug(
                            f"Unix lock held by another process, retrying... "
                            f"(elapsed: {elapsed:.1f}s, errno: {error_code})",
                            extra={
                                'structured': True,
                                'event': 'lock_retry',
                                'lock_type': 'unix_fcntl',
                                'file_path': file_handle.name,
                                'elapsed_seconds': elapsed,
                                'retry_interval': self._lock_retry_interval,
                                'error_code': error_code,
                                'error_name': errno.errorcode.get(error_code, 'UNKNOWN') if error_code else None,
                                'lock_timeout': self._lock_timeout
                            }
                        )
                        # Wait before retrying
                        time.sleep(self._lock_retry_interval)
                        # Continue retry loop

            except (IOError, RuntimeError) as e:
                if isinstance(e, RuntimeError):
                    # Re-raise timeout errors as-is
                    logger.error(f"Failed to acquire Unix file lock: {e}")
                    raise
                else:
                    logger.error(f"Failed to acquire Unix file lock: {e}")
                    raise

    def _release_file_lock(self, file_handle) -> None:
        """Release a file lock for multi-process safety (Issue #268, #451).

        Args:
            file_handle: The file handle to unlock.

        Raises:
            IOError: If the lock cannot be released.

        Note:
            PLATFORM DIFFERENCES (Issue #411, #451):

            Windows (win32file.UnlockFile):
            - Mandatory lock release - enforces mutual exclusion
            - Must match exact lock length used during acquisition
            - Uses cached length to prevent deadlocks

            Unix-like systems (fcntl.flock):
            - Provides strong release guarantees
            - Simple unlock without range matching

            For Windows, the lock length matches the fixed 4GB LENGTH
            (0, 1) used during acquisition to avoid errors.
            Uses the cached lock length from _acquire_file_lock (Issue #351, #465, #469, #480, #496).

            IMPORTANT (Issue #496): The cached values (0, 1) represent LENGTH, not offset.
            The pywin32 UnlockFile wrapper takes the length to unlock as parameters.
            The offset is implied from the overlapped structure used during LockFileEx.
            Therefore, (0, 1) unlocks 4GB bytes starting from file offset 0 (file beginning).

            With the fixed length approach (Issue #375, #426, #451), file size
            changes between lock and unlock no longer cause deadlocks or unlock
            failures, as the locked region is always large enough.

            The lock length cache is thread-safe because all file operations are
            serialized by self._lock (RLock), ensuring proper acquire/release
            pairing (Issue #366).

            Error handling is consistent with _acquire_file_lock - exceptions
            are re-raised to ensure lock release failures are not silently
            ignored (Issue #376).
        """
        if os.name == 'nt':  # Windows
            # Portability fix for Issue #671: Check if running in degraded mode
            if _is_degraded_mode():
                # Issue #846: Release file-based lock
                if hasattr(self, '_lock_range') and self._lock_range == "filelock":
                    lock_file_path = file_handle.name + ".lock"
                    try:
                        # Remove the lock file to release the lock
                        os.unlink(lock_file_path)
                        logger.debug(
                            f"File-based lock released: {lock_file_path}",
                            extra={
                                'structured': True,
                                'event': 'lock_released',
                                'lock_type': 'file_based',
                                'file_path': lock_file_path,
                                'mode': 'degraded'
                            }
                        )
                        # Clear the tracked lock file path
                        self._lock_file_path = None
                        return
                    except FileNotFoundError:
                        # Lock file doesn't exist - already cleaned up
                        logger.debug(f"Lock file already removed: {lock_file_path}")
                        # Clear the tracked lock file path
                        self._lock_file_path = None
                        return
                    except Exception as e:
                        logger.error(f"Failed to release file-based lock: {e}")
                        raise
                else:
                    # No lock was acquired
                    return

            # Windows unlocking: win32file.UnlockFile (Issue #451)
            # Mandatory lock release for strong synchronization
            # Unlock range must match lock range exactly (Issue #271)
            # Use the cached lock range from _acquire_file_lock (Issue #351)
            #
            # Security fix for Issue #429: Windows modules are imported at module level,
            # ensuring thread-safe initialization. No need to import here.

            try:
                # Get the Windows file handle from Python file object
                win_handle = win32file._get_osfhandle(file_handle.fileno())

                # Use the cached lock range from acquire to ensure consistency (Issue #351)
                # Validate lock range before using it (Issue #366)
                # Security fix (Issue #374): Raise exception instead of insecure fallback
                lock_range = self._lock_range
                if not isinstance(lock_range, tuple) or len(lock_range) != 2:
                    # Invalid lock range - this should never happen if acquire was called
                    # Security fix (Issue #374): Raise instead of falling back
                    raise RuntimeError(
                        f"Invalid lock range {lock_range} in _release_file_lock. "
                        f"This indicates acquire/release are not properly paired (Issue #366). "
                        f"Refusing to use insecure partial lock fallback."
                    )

                lock_range_low, lock_range_high = lock_range

                # Unlock the file using win32file.UnlockFile (Issue #451)
                # This releases the mandatory lock acquired by LockFileEx
                #
                # PYWIN32 API (Issue #496):
                # UnlockFile(hFile, NumberOfBytesToUnlockLow, NumberOfBytesToUnlockHigh)
                # - The parameters specify the LENGTH to unlock (must match lock length)
                # - The offset is specified via the overlapped structure used during LockFileEx
                # - Therefore: unlocks 4GB bytes starting from file start (offset 0)
                win32file.UnlockFile(
                    win_handle,
                    lock_range_low,  # NumberOfBytesToUnlockLow (LENGTH, must match lock)
                    lock_range_high  # NumberOfBytesToUnlockHigh (LENGTH, must match lock)
                )
                logger.debug(
                    f"File lock released successfully for {file_handle.name}",
                    extra={
                        'structured': True,
                        'event': 'lock_released',
                        'lock_type': 'windows_win32',
                        'file_path': file_handle.name,
                        'lock_range_low': lock_range_low,
                        'lock_range_high': lock_range_high
                    }
                )
            except (pywintypes.error, RuntimeError) as e:
                if isinstance(e, RuntimeError):
                    logger.error(f"Failed to release Windows mandatory lock: {e}")
                    raise
                else:
                    logger.error(f"Failed to release Windows mandatory lock: {e}")
                    raise
        else:  # Unix-like systems
            # Portability fix for Issue #791: Check if running in degraded mode
            if _is_degraded_mode():
                # Issue #829: Release file-based lock fallback
                if hasattr(self, '_lock_range') and isinstance(self._lock_range, str):
                    try:
                        lock_dir = Path(self._lock_range)
                        lock_pid_file = lock_dir / "pid"

                        # Remove the PID file
                        lock_pid_file.unlink(missing_ok=True)

                        # Remove the lock directory
                        lock_dir.rmdir()

                        logger.debug(
                            f"Lock file fallback released for {file_handle.name}",
                            extra={
                                'structured': True,
                                'event': 'lock_released',
                                'lock_type': 'file_based',
                                'file_path': file_handle.name,
                                'lock_dir': str(lock_dir),
                                'mode': 'degraded'
                            }
                        )
                        return
                    except Exception as e:
                        logger.error(f"Failed to release lock file fallback: {e}")
                        raise
                else:
                    # No lock was acquired
                    return

            # Unix unlocking
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                logger.debug(
                    f"File lock released successfully for {file_handle.name}",
                    extra={
                        'structured': True,
                        'event': 'lock_released',
                        'lock_type': 'unix_fcntl',
                        'file_path': file_handle.name
                    }
                )
            except IOError as e:
                logger.error(f"Failed to release Unix file lock: {e}")
                raise

    def _file_lock(self, file_handle):
        """Context manager for automatic file lock acquisition and release (Issue #943).

        This context manager eliminates error-prone manual try/finally blocks by
        automatically acquiring the lock on entry and releasing it on exit, even
        when exceptions occur.

        Args:
            file_handle: The file handle to lock.

        Yields:
            The file_handle for use within the context.

        Raises:
            IOError: If the lock cannot be acquired or released.
            RuntimeError: If lock acquisition times out.

        Example:
            >>> with open(self.path, 'r+b') as f:
            ...     with self._file_lock(f):
            ...         # File operations here are protected by lock
            ...         data = f.read()

        Note:
            This context manager ensures locks are always released, even when
            exceptions occur, preventing deadlocks that can happen with manual
            lock handling.
        """
        self._acquire_file_lock(file_handle)
        try:
            yield file_handle
        finally:
            self._release_file_lock(file_handle)

    def _secure_directory(self, directory: Path) -> None:
        """Set restrictive permissions on the storage directory.

        This method attempts to set restrictive permissions on the storage
        directory to protect sensitive data. The approach varies by platform:

        - Unix-like systems: Uses chmod(0o700) to set owner-only access.
          Raises RuntimeError if chmod fails.
        - Windows: Uses win32security to set restrictive ACLs.
          Raises RuntimeError if ACL setup fails.

        Args:
            directory: The directory path to secure.

        Raises:
            RuntimeError: If directory permissions cannot be set securely.

        Note:
            This method will raise an exception and prevent execution if
            secure directory permissions cannot be established. This ensures
            the application does not run with unprotected sensitive data (Issue #304).

            On Windows, pywin32 availability is verified in __init__ (Issue #414).
            This ensures early, clear error messages instead of runtime crashes.

            Security fix for Issue #514: In degraded mode without pywin32, directory
            security is skipped with a warning. This is UNSAFE for production use.
        """
        if os.name != 'nt':  # Unix-like systems
            try:
                directory.chmod(0o700)
            except OSError as e:
                # Raise error instead of warning for security (Issue #304)
                raise RuntimeError(
                    f"Failed to set directory permissions on {directory}: {e}. "
                    f"Cannot continue without secure directory permissions."
                ) from e
        else:  # Windows
            # Portability fix for Issue #671: Check if running in degraded mode
            if _is_degraded_mode():
                # pywin32 is not available - log warning and skip directory security
                logger.warning(
                    f"Directory security is disabled in degraded mode (pywin32 not installed). "
                    f"Directory '{directory}' may have insecure permissions. "
                    f"This is UNSAFE for production use."
                )
                return  # Skip directory security in degraded mode

            # Security fix for Issue #429: Windows modules are imported at module level,
            # ensuring thread-safe initialization. Modules are available immediately
            # when this code runs, preventing race conditions.

            # Attempt to use Windows ACLs for security (Issue #226)
            win32_success = False
            try:
                # Get the current user's SID using Windows API (Issue #229)
                # Use GetUserNameEx to get the primary domain instead of relying
                # on environment variables which can be manipulated or missing
                # Initialize domain to ensure it's always defined (Issue #234)
                domain = None

                # Security fix (Issue #329): Do NOT fall back to environment variables
                # when GetUserName fails. Environment variables can be manipulated by
                # the process or parent process, which is a security risk when setting ACLs.
                try:
                    user = win32api.GetUserName()
                except Exception as e:
                    # GetUserName failed - raise error immediately without fallback
                    raise RuntimeError(
                        "Cannot set Windows security: win32api.GetUserName() failed. "
                        "Unable to securely determine username. "
                        f"Install pywin32: pip install pywin32. Error: {e}"
                    ) from e

                # Validate user - do NOT use environment variable fallback (Issue #329)
                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                    # GetUserName returned invalid value - raise error
                    raise RuntimeError(
                        "Cannot set Windows security: win32api.GetUserName() returned invalid value. "
                        "Unable to securely determine username. "
                        "Install pywin32: pip install pywin32"
                    )

                # Fix Issue #251: Extract pure username if GetUserName returns
                # 'COMPUTERNAME\\username' or 'DOMAIN\\username' format
                # This can happen in non-domain environments and causes
                # LookupAccountName to fail
                if '\\' in user:
                    # Extract the part after the last backslash
                    parts = user.rsplit('\\', 1)
                    if len(parts) == 2:
                        user = parts[1]

                try:
                    # Try to get the fully qualified domain name
                    name = win32api.GetUserNameEx(win32con.NameFullyQualifiedDN)
                    # Validate that name is a string before parsing (Issue #349)
                    if not isinstance(name, str):
                        raise TypeError(
                            f"GetUserNameEx returned non-string value: {type(name).__name__}"
                        )
                    # Extract domain from the qualified DN
                    # Format: CN=user,OU=users,DC=domain,DC=com
                    parts = name.split(',')
                    # Build domain from all DC= parts (execute once, not in loop)
                    # Validate that split results have expected format (Issue #349)
                    dc_parts = []
                    for p in parts:
                        p = p.strip()
                        if p.startswith('DC='):
                            split_parts = p.split('=', 1)
                            if len(split_parts) >= 2:
                                dc_parts.append(split_parts[1])
                            else:
                                # Malformed DN - raise error instead of silently continuing (Issue #349)
                                raise ValueError(
                                    f"Malformed domain component in DN: '{p}'. "
                                    f"Expected format 'DC=value', got '{p}'"
                                )
                    if dc_parts:
                        domain = '.'.join(dc_parts)
                    else:
                        # Fallback to local computer if no domain found
                        domain = win32api.GetComputerName()
                except (TypeError, ValueError) as e:
                    # Parsing failed due to invalid format - raise error (Issue #349)
                    # These exceptions indicate GetUserNameEx returned invalid data
                    # We should NOT silently fall back to GetComputerName in this case
                    # as it could lead to insecure configuration
                    raise RuntimeError(
                        f"Cannot set Windows security: GetUserNameEx returned invalid data. "
                        f"Unable to parse domain information. Error: {e}. "
                        f"Install pywin32: pip install pywin32"
                    ) from e
                except Exception:
                    # GetUserNameEx failed (not a parsing error) - fallback to GetComputerName
                    # This is expected in non-domain environments
                    # Security fix (Issue #329): Do NOT fall back to environment variables
                    try:
                        domain = win32api.GetComputerName()
                    except Exception as e:
                        # GetComputerName also failed - raise error
                        raise RuntimeError(
                            "Cannot set Windows security: Unable to determine domain. "
                            f"win32api.GetComputerName() failed. "
                            f"Install pywin32: pip install pywin32. Error: {e}"
                        ) from e

                # Validate domain - ensure it's defined before LookupAccountName (Issue #234)
                # Security fix (Issue #329): Do NOT fall back to environment variables
                if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                    raise RuntimeError(
                        "Cannot set Windows security: Unable to determine domain. "
                        "Domain is None or empty after Windows API calls. "
                        "Install pywin32: pip install pywin32"
                    )

                # Validate user before calling LookupAccountName (Issue #240)
                # Ensure user is initialized and non-empty to prevent passing invalid values
                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                    raise ValueError(
                        f"Invalid user name '{user}': Cannot set Windows security. "
                        f"GetUserName() returned invalid value."
                    )

                # Security fix (Issue #329): Do NOT fall back to environment variables
                # when LookupAccountName fails. Environment variables can be manipulated.
                try:
                    sid, _, _ = win32security.LookupAccountName(domain, user)
                except Exception as e:
                    # LookupAccountName failed - raise error without fallback
                    raise RuntimeError(
                        f"Failed to set Windows ACLs: Unable to lookup account '{user}' in domain '{domain}'. "
                        f"Install pywin32: pip install pywin32. Error: {e}"
                    ) from e

                # Create a security descriptor with owner-only access
                security_descriptor = win32security.SECURITY_DESCRIPTOR()
                security_descriptor.SetSecurityDescriptorOwner(sid, False)

                # Create a DACL (Discretionary Access Control List)
                # Use minimal permissions instead of FILE_ALL_ACCESS (Issue #239)
                # Following the principle of least privilege (Issue #249)
                # Do NOT use FILE_GENERIC_READ | FILE_GENERIC_WRITE as they include DELETE
                # Use explicit minimal permissions
                # Remove FILE_READ_EA and FILE_WRITE_EA (Issue #254)
                # Add DELETE permission to allow file management (Issue #274)
                # This prevents disk space leaks from old/temporary files
                dacl = win32security.ACL()
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    win32con.FILE_LIST_DIRECTORY |
                    win32con.FILE_ADD_FILE |
                    win32con.FILE_READ_ATTRIBUTES |
                    win32con.FILE_WRITE_ATTRIBUTES |
                    win32con.DELETE |
                    win32con.SYNCHRONIZE,
                    sid
                )

                security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)

                # Fix Issue #244: Set SACL (System Access Control List) for auditing
                # SACL enables security auditing for access attempts on the directory
                # Create an empty SACL (no audit policies by default)
                # Administrators can configure audit policies using Windows Security Audit
                sacl = win32security.ACL()
                security_descriptor.SetSecurityDescriptorSacl(0, sacl, 0)

                # Fix Issue #256: Explicitly set DACL protection to prevent inheritance
                # This ensures PROTECTED_DACL_SECURITY_INFORMATION flag takes effect
                security_descriptor.SetSecurityDescriptorControl(
                    win32security.SE_DACL_PROTECTED, 1
                )

                # Apply the security descriptor to the directory
                # Include OWNER_SECURITY_INFORMATION to ensure owner info is applied (Issue #264)
                # Include SACL_SECURITY_INFORMATION to ensure SACL is applied (Issue #277)
                security_info = (
                    win32security.DACL_SECURITY_INFORMATION |
                    win32security.PROTECTED_DACL_SECURITY_INFORMATION |
                    win32security.OWNER_SECURITY_INFORMATION |
                    win32security.SACL_SECURITY_INFORMATION
                )
                win32security.SetFileSecurity(
                    str(directory),
                    security_info,
                    security_descriptor
                )
                logger.debug(f"Applied restrictive ACLs to {directory}")
                win32_success = True

            except Exception as e:
                # Failed to set ACLs - raise error for security (Issue #304)
                # Note: ImportError for missing pywin32 is now caught at module import time (Issue #324)
                raise RuntimeError(
                    f"Failed to set Windows ACLs on {directory}: {e}. "
                    f"Cannot continue without secure directory permissions. "
                    f"Install pywin32: pip install pywin32"
                ) from e

    def _create_and_secure_directories(self, target_directory: Path) -> None:
        """Create and secure directories atomically to prevent race condition (Issue #395).

        This method creates directories one by one from the root towards the target,
        securing each directory immediately after creation. This eliminates the
        security window that exists when using mkdir(parents=True) followed by
        _secure_directory, where a crash could leave directories with insecure
        inherited ACLs on Windows.

        Args:
            target_directory: The target directory to create and secure.

        Raises:
            RuntimeError: If any directory cannot be created or secured.

        Note:
            This is a security fix for Issue #395 and Issue #400. On Windows, we use
            win32file.CreateDirectory() with a security descriptor to create directories
            atomically with the correct ACLs, eliminating the time window entirely.

            On Unix, we use mkdir() followed by chmod() which is still atomic enough
            for practical purposes (the time window is microseconds).

            Race condition fix (Issue #409): Implements retry mechanism with exponential
            backoff to handle TOCTOU (Time-of-Check-Time-of-Use) race conditions where
            multiple threads/processes attempt to create the same directory simultaneously.

            Security fix for Issue #481: When FileExistsError is caught (indicating
            another process created the directory), ALWAYS verify and fix permissions
            by calling _secure_directory, rather than checking permissions first and
            conditionally fixing them. This ensures we never assume the other process
            created the directory securely. The verification is critical because we
            cannot trust that another process created the directory with correct permissions.

            The algorithm:
            1. Build list of directories from root to target
            2. For each directory that doesn't exist:
               a. On Windows: Create with win32file.CreateDirectory() + security descriptor
               b. On Unix: Create with mkdir() and immediately chmod()
            3. If creation fails with FileExistsError, ALWAYS verify and secure directory
            4. Use exponential backoff for retries (max 5 attempts, ~500ms total)
        """
        # Build list of directories from outermost to innermost
        # Start from the target and walk up to find what needs to be created
        directories_to_create = []
        current = target_directory

        # Walk up from target to root, collecting non-existent directories
        while current != current.parent:  # Stop at filesystem root
            if not current.exists():
                directories_to_create.append(current)
            current = current.parent

        # Reverse to create from outermost to innermost
        directories_to_create.reverse()

        # Create and secure each directory with retry mechanism (Issue #409)
        import time
        max_retries = 5
        base_delay = 0.01  # 10ms starting delay

        for directory in directories_to_create:
            # Retry loop with exponential backoff for race condition handling
            success = False
            last_error = None

            for attempt in range(max_retries):
                try:
                    if os.name == 'nt':  # Windows - use atomic directory creation (Issue #400)
                        if not directory.exists():
                            # Portability fix for Issue #671: Check if running in degraded mode
                            if _is_degraded_mode():
                                # pywin32 is not available - fall back to basic directory creation
                                logger.warning(
                                    f"Creating directory '{directory}' without security in degraded mode "
                                    f"(pywin32 not installed). This is UNSAFE for production use."
                                )
                                directory.mkdir(mode=0o700, exist_ok=True)
                            else:
                                # Security fix for Issue #429: Windows modules are imported at module level,
                                # ensuring thread-safe initialization. Modules are available immediately.

                                # Security fix for Issue #400: Use CreateDirectory with security descriptor
                                # to eliminate the time window between directory creation and ACL application.
                                # This is truly atomic - the directory is created with the correct ACLs
                                # from the very moment it exists.
                                #
                                # First, prepare the security descriptor
                                # Get the current user's SID
                                user = win32api.GetUserName()

                                # Fix Issue #251: Extract pure username if GetUserName returns
                                # 'COMPUTERNAME\\username' or 'DOMAIN\\username' format
                                if '\\' in user:
                                    parts = user.rsplit('\\', 1)
                                    if len(parts) == 2:
                                        user = parts[1]

                                # Get domain
                                try:
                                    name = win32api.GetUserNameEx(win32con.NameFullyQualifiedDN)
                                    if not isinstance(name, str):
                                        raise TypeError(
                                            f"GetUserNameEx returned non-string value: {type(name).__name__}"
                                        )
                                    # Extract domain from the qualified DN
                                    parts = name.split(',')
                                    dc_parts = []
                                    for p in parts:
                                        p = p.strip()
                                        if p.startswith('DC='):
                                            split_parts = p.split('=', 1)
                                            if len(split_parts) >= 2:
                                                dc_parts.append(split_parts[1])
                                    if dc_parts:
                                        domain = '.'.join(dc_parts)
                                    else:
                                        domain = win32api.GetComputerName()
                                except (TypeError, ValueError):
                                    raise RuntimeError(
                                        f"Cannot set Windows security: GetUserNameEx returned invalid data. "
                                        f"Install pywin32: pip install pywin32"
                                    )
                                except Exception:
                                    domain = win32api.GetComputerName()

                                # Validate domain
                                if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                                    raise RuntimeError(
                                        "Cannot set Windows security: Unable to determine domain. "
                                        "Install pywin32: pip install pywin32"
                                    )

                                # Validate user
                                if not user or not isinstance(user, str) or len(user.strip()) == 0:
                                    raise ValueError(
                                        f"Invalid user name '{user}': Cannot set Windows security."
                                    )

                                # Lookup account SID
                                try:
                                    sid, _, _ = win32security.LookupAccountName(domain, user)
                                except Exception as e:
                                    raise RuntimeError(
                                        f"Failed to set Windows ACLs: Unable to lookup account '{user}'. "
                                        f"Install pywin32: pip install pywin32. Error: {e}"
                                    ) from e

                                # Create security descriptor with owner-only access
                                security_descriptor = win32security.SECURITY_DESCRIPTOR()
                                security_descriptor.SetSecurityDescriptorOwner(sid, False)

                                # Create DACL with minimal permissions (Issue #239, #249, #254, #274)
                                dacl = win32security.ACL()
                                dacl.AddAccessAllowedAce(
                                    win32security.ACL_REVISION,
                                    win32con.FILE_LIST_DIRECTORY |
                                    win32con.FILE_ADD_FILE |
                                    win32con.FILE_READ_ATTRIBUTES |
                                    win32con.FILE_WRITE_ATTRIBUTES |
                                    win32con.DELETE |
                                    win32con.SYNCHRONIZE,
                                    sid
                                )

                                security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)

                                # Create SACL for auditing (Issue #244)
                                sacl = win32security.ACL()
                                security_descriptor.SetSecurityDescriptorSacl(0, sacl, 0)

                                # Set DACL protection to prevent inheritance (Issue #256)
                                security_descriptor.SetSecurityDescriptorControl(
                                    win32security.SE_DACL_PROTECTED, 1
                                )

                                # Create directory atomically with security descriptor (Issue #400)
                                # win32file.CreateDirectory creates the directory with the specified
                                # security attributes atomically - there's no time window where
                                # the directory exists with insecure permissions.
                                win32file.CreateDirectory(
                                    str(directory),
                                    security_descriptor
                                )

                    else:  # Unix-like systems
                        # On Unix, create the directory and immediately secure it
                        # The time window is extremely small (microseconds) and acceptable
                        # for practical purposes
                        #
                        # Security fix for Issue #419: Do NOT use exist_ok=True
                        # If we use exist_ok=True, the FileExistsError handling below
                        # won't be triggered, and we won't properly handle the race
                        # condition where the directory is created by another process.
                        # Instead, let FileExistsError be raised and handle it in the
                        # exception handler below.
                        #
                        # Security fix for Issue #439: Use mode=0o700 to create directory
                        # with restrictive permissions from the start. This ensures that
                        # even if _secure_directory fails (e.g., due to race condition
                        # or error), the directory has secure permissions and is not left
                        # with umask-dependent insecure permissions.
                        #
                        # Security fix for Issue #474 and #479: Temporarily restrict umask
                        # to 0o077 during directory creation to prevent umask from making the
                        # directory more permissive than intended. This eliminates the
                        # TOCTOU security window where mkdir(mode=0o700) could create a
                        # directory with 0o755 permissions if umask is 0o022. The umask
                        # restriction ensures atomic creation with secure permissions.
                        old_umask = os.umask(0o077)  # Restrictive umask for mkdir
                        try:
                            directory.mkdir(mode=0o700)  # Create with secure permissions
                        finally:
                            os.umask(old_umask)  # Restore original umask
                        self._secure_directory(directory)  # Ensure consistency

                    # If we get here, creation succeeded
                    success = True
                    break

                except FileExistsError:
                    # Race condition fix (Issue #409): Directory was created by another thread/process
                    # between our check and creation attempt.
                    #
                    # Security fix for Issue #424: Always verify and secure the directory,
                    # regardless of platform. This prevents TOCTOU vulnerabilities where
                    # another process could create the directory with insecure permissions.
                    #
                    # Security fix for Issue #481: ALWAYS call _secure_directory to verify
                    # and fix permissions, rather than checking first. This ensures we don't
                    # assume the other process created the directory securely. The verification
                    # is critical because we cannot trust that another process (especially a
                    # malicious or compromised one) created the directory with correct permissions.
                    # By always securing, we guarantee the directory meets our security requirements.
                    if directory.exists():
                        try:
                            # Security fix for Issue #481: Always verify permissions after catching
                            # FileExistsError, regardless of platform. Do NOT check permissions first
                            # and conditionally call _secure_directory - this could leave a window
                            # where we proceed with insecure permissions. Instead, ALWAYS secure to
                            # ensure correctness, even if it's slightly less efficient.
                            #
                            # This is safe because _secure_directory is idempotent and efficient.
                            # On Unix: chmod(0o700) is a fast syscall even if permissions are correct.
                            # On Windows: ACL reapplication is necessary because verification is complex.
                            #
                            # The tradeoff: A few extra microseconds of syscall time for guaranteed
                            # security. This is acceptable because directory creation is a rare operation
                            # (only happens during initialization), not a hot path.
                            self._secure_directory(directory)

                            # Directory exists and is now secure
                            # Consider this a success (another process created it for us)
                            success = True
                            logger.debug(
                                f"Directory {directory} already exists (created by competing process). "
                                f"Verified and secured directory to ensure correct permissions (Issue #481)."
                            )
                            break
                        except Exception as verify_error:
                            # Failed to verify security - save error and retry
                            last_error = verify_error
                            logger.debug(
                                f"Attempt {attempt + 1}/{max_retries}: Directory {directory} "
                                f"exists but verification failed: {verify_error}. Retrying..."
                            )
                    else:
                        # Directory doesn't exist but we got FileExistsError
                        # This is unusual - save error and retry
                        last_error = e
                        logger.debug(
                            f"Attempt {attempt + 1}/{max_retries}: Got FileExistsError but "
                            f"{directory} doesn't exist. Retrying..."
                        )

                    # Exponential backoff before retry
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)

                except Exception as e:
                    # Non-retryable error - save and break out of retry loop
                    last_error = e
                    break

            # After all retries, check if we succeeded
            if not success:
                # If we fail to create or secure a directory after all retries,
                # raise an error to prevent running with insecure directories
                raise RuntimeError(
                    f"Failed to create and secure directory {directory} after {max_retries} attempts. "
                    f"Last error: {last_error}. "
                    f"Cannot continue without secure directory permissions."
                ) from last_error

    def _acquire_directory_lock(self, directory: Path) -> None:
        """Acquire a lock file for directory creation to prevent TOCTOU race conditions.

        This method creates a lock file in the parent directory to ensure atomic
        directory creation. The lock prevents multiple processes from creating the
        same directory concurrently, which could lead to permission issues.

        This is a security fix for Issue #521 to address TOCTOU race conditions
        in directory creation.

        Args:
            directory: The directory for which to acquire a lock.

        Raises:
            RuntimeError: If the lock cannot be acquired after multiple attempts.
            OSError: If the lock file cannot be created.
        """
        # Use the parent directory for the lock file location
        # If parent doesn't exist, we need to handle that
        parent_dir = directory.parent

        # Create a lock file path
        # Use a hash of the directory path to avoid filesystem issues
        dir_hash = hashlib.sha256(str(directory).encode()).hexdigest()[:16]
        lock_path = parent_dir / f".flywheel_lock_{dir_hash}.lock"

        # Try to acquire the lock with retries
        max_retries = 10
        base_delay = 0.005  # 5ms starting delay

        for attempt in range(max_retries):
            try:
                # Try to create the lock file exclusively (atomic operation)
                # This uses O_CREAT | O_EXCL flags which are atomic
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)

                # Lock acquired successfully
                try:
                    # Write our PID to the lock file for debugging
                    os.write(fd, str(os.getpid()).encode())
                finally:
                    os.close(fd)

                # Lock acquired - store the lock path for cleanup
                if not hasattr(self, '_directory_locks'):
                    self._directory_locks = []
                self._directory_locks.append(lock_path)

                return

            except FileExistsError:
                # Lock file exists - check if it's stale (from a crashed process)
                try:
                    # Try to read the lock file
                    with open(lock_path, 'r') as f:
                        pid_str = f.read().strip()

                    # Check if the process is still running
                    try:
                        pid = int(pid_str)
                        # Try to send signal 0 to check if process exists
                        os.kill(pid, 0)
                        # Process is still running - lock is valid
                        # Wait and retry
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            time.sleep(delay)
                            continue
                        else:
                            raise RuntimeError(
                                f"Could not acquire directory lock for {directory} "
                                f"after {max_retries} attempts. Lock file: {lock_path}"
                            )
                    except (OSError, ValueError, ProcessLookupError):
                        # Process is not running - stale lock file
                        # Remove it and retry
                        try:
                            os.remove(lock_path)
                            # Continue to next iteration to try acquiring again
                            continue
                        except OSError:
                            # Someone else removed it or we can't remove it
                            # Just retry
                            if attempt < max_retries - 1:
                                delay = base_delay * (2 ** attempt)
                                time.sleep(delay)
                                continue
                            else:
                                raise RuntimeError(
                                    f"Could not acquire directory lock for {directory} "
                                    f"after {max_retries} attempts"
                                )

                except (OSError, IOError) as e:
                    # Can't read lock file - treat as locked and retry
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        raise RuntimeError(
                            f"Could not acquire directory lock for {directory}: {e}"
                        ) from e

            except OSError as e:
                # Other error creating lock file
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(
                        f"Failed to create lock file for {directory}: {e}"
                    ) from e

        # Should not reach here
        raise RuntimeError(
            f"Failed to acquire directory lock for {directory} after {max_retries} attempts"
        )

    def _release_directory_lock(self, directory: Path) -> None:
        """Release a directory lock file.

        This method removes the lock file created by _acquire_directory_lock.

        Args:
            directory: The directory for which to release the lock.
        """
        # Calculate the lock path the same way as in _acquire_directory_lock
        parent_dir = directory.parent
        dir_hash = hashlib.sha256(str(directory).encode()).hexdigest()[:16]
        lock_path = parent_dir / f".flywheel_lock_{dir_hash}.lock"

        # Remove the lock file if it exists
        try:
            if lock_path.exists():
                os.remove(lock_path)

            # Remove from our tracking list
            if hasattr(self, '_directory_locks') and lock_path in self._directory_locks:
                self._directory_locks.remove(lock_path)

        except OSError:
            # Lock file might have been removed by another process
            # This is not a critical error
            pass

    @classmethod
    def cleanup_stale_locks(cls, directory: Path) -> None:
        """Clean up stale lock files in the specified directory (Issue #958).

        This is a public classmethod that allows users to manually clean up
        stale lock files on startup, without needing to instantiate FileStorage.
        This is useful for maintaining a clean workspace, especially after
        process crashes or for long-running services.

        Args:
            directory: The directory to scan for stale lock files.

        Example:
            >>> from pathlib import Path
            >>> from flywheel.storage import FileStorage
            >>> FileStorage.cleanup_stale_locks(Path("/path/to/todos"))

        Note:
            This method scans for .lock files in the specified directory,
            reads the PID from each lock file, checks if the process is still
            alive using os.kill(pid, 0), and removes the file if the process
            is dead.

            The method handles:
            - Lock files with dead PIDs (removed)
            - Lock files with active PIDs (preserved)
            - Corrupted lock files (removed)
            - Files that don't exist (ignored)

            Enhancement for Issue #958: Public API for manual lock cleanup.
        """
        # Create a temporary instance to reuse the existing implementation
        # We need to call the private method, but since we're in a classmethod,
        # we can't access self. We'll replicate the logic here.
        try:
            # Scan for .lock files in the directory
            for lock_file in directory.glob("*.lock"):
                try:
                    # Read lock file content
                    with open(lock_file, 'r') as f:
                        content = f.read()

                    # Extract PID and timestamp
                    locked_pid = None
                    locked_at = None
                    for line in content.split('\n'):
                        if line.startswith('pid='):
                            try:
                                locked_pid = int(line.split('=')[1])
                            except (ValueError, IndexError):
                                pass
                        elif line.startswith('locked_at='):
                            try:
                                locked_at = float(line.split('=')[1])
                            except (ValueError, IndexError):
                                pass

                    # Check if the lock is stale
                    is_stale = False
                    stale_reason = ""

                    # Method 1: Check if PID exists (most reliable)
                    if locked_pid is not None:
                        try:
                            # Send signal 0 to check if process exists
                            # This doesn't actually send a signal, just checks existence
                            os.kill(locked_pid, 0)
                            # Process exists, lock is not stale
                            stale_reason = ""
                        except OSError:
                            # Process doesn't exist - lock is stale
                            is_stale = True
                            stale_reason = f"process {locked_pid} not found"
                    else:
                        # No PID info - consider it stale (corrupted or old format)
                        is_stale = True
                        stale_reason = "no PID information"

                    # Remove stale lock files
                    if is_stale:
                        logger.warning(
                            f"Found stale lock file ({stale_reason}), "
                            f"removing: {lock_file}",
                            extra={
                                'structured': True,
                                'event': 'stale_lock_cleanup',
                                'lock_type': 'file_based',
                                'file_path': str(lock_file),
                                'reason': stale_reason,
                                'stale_pid': locked_pid
                            }
                        )
                        try:
                            os.unlink(lock_file)
                            logger.debug(f"Stale lock file removed: {lock_file}")
                        except FileNotFoundError:
                            # Another process already removed the stale lock
                            logger.debug(f"Stale lock already removed by another process: {lock_file}")
                        except OSError as e:
                            logger.warning(f"Failed to remove stale lock: {e}")

                except (OSError, ValueError, IndexError) as e:
                    # Lock file is corrupted or unreadable - remove it
                    logger.warning(
                        f"Corrupted or unreadable lock file found, removing: {lock_file} - {e}"
                    )
                    try:
                        os.unlink(lock_file)
                        logger.debug(f"Corrupted lock file removed: {lock_file}")
                    except FileNotFoundError:
                        # Another process already removed the corrupted lock
                        logger.debug(f"Corrupted lock already removed: {lock_file}")
                    except OSError as unlink_err:
                        logger.warning(f"Failed to remove corrupted lock: {unlink_err}")

        except OSError as e:
            # Failed to scan directory - not critical, log and continue
            logger.warning(f"Failed to scan directory for stale locks: {e}")

    def _cleanup_stale_locks(self, directory: Path) -> None:
        """Clean up stale lock files in the specified directory (Issue #938).

        Scans for .lock files in the directory, reads the PID from each lock file,
        checks if the process is still alive using os.kill(pid, 0), and removes
        the file if the process is dead. This ensures a clean state for long-running
        services or after crashes.

        Args:
            directory: The directory to scan for stale lock files.

        Note:
            This is a security fix for Issue #938. While Issue #874 mentions PID-based
            stale lock detection, it relies on a new process checking an old one.
            Implementing a 'cleanup on startup' routine ensures a clean state for
            long-running services or after crashes.

            The method handles:
            - Lock files with dead PIDs (removed)
            - Lock files with active PIDs (preserved)
            - Corrupted lock files (removed)
            - Files that don't exist (ignored)
        """
        try:
            # Scan for .lock files in the directory
            for lock_file in directory.glob("*.lock"):
                try:
                    # Read lock file content
                    with open(lock_file, 'r') as f:
                        content = f.read()

                    # Extract PID and timestamp
                    locked_pid = None
                    locked_at = None
                    for line in content.split('\n'):
                        if line.startswith('pid='):
                            try:
                                locked_pid = int(line.split('=')[1])
                            except (ValueError, IndexError):
                                pass
                        elif line.startswith('locked_at='):
                            try:
                                locked_at = float(line.split('=')[1])
                            except (ValueError, IndexError):
                                pass

                    # Check if the lock is stale
                    is_stale = False
                    stale_reason = ""

                    # Method 1: Check if PID exists (most reliable)
                    if locked_pid is not None:
                        try:
                            # Send signal 0 to check if process exists
                            # This doesn't actually send a signal, just checks existence
                            os.kill(locked_pid, 0)
                            # Process exists, lock is not stale
                            stale_reason = ""
                        except OSError:
                            # Process doesn't exist - lock is stale
                            is_stale = True
                            stale_reason = f"process {locked_pid} not found"
                    else:
                        # No PID info - consider it stale (corrupted or old format)
                        is_stale = True
                        stale_reason = "no PID information"

                    # Remove stale lock files
                    if is_stale:
                        logger.warning(
                            f"Found stale lock file ({stale_reason}), "
                            f"removing: {lock_file}",
                            extra={
                                'structured': True,
                                'event': 'stale_lock_cleanup',
                                'lock_type': 'file_based',
                                'file_path': str(lock_file),
                                'reason': stale_reason,
                                'stale_pid': locked_pid
                            }
                        )
                        try:
                            os.unlink(lock_file)
                            logger.debug(f"Stale lock file removed: {lock_file}")
                        except FileNotFoundError:
                            # Another process already removed the stale lock
                            logger.debug(f"Stale lock already removed by another process: {lock_file}")
                        except OSError as e:
                            logger.warning(f"Failed to remove stale lock: {e}")

                except (OSError, ValueError, IndexError) as e:
                    # Lock file is corrupted or unreadable - remove it
                    logger.warning(
                        f"Corrupted or unreadable lock file found, removing: {lock_file} - {e}"
                    )
                    try:
                        os.unlink(lock_file)
                        logger.debug(f"Corrupted lock file removed: {lock_file}")
                    except FileNotFoundError:
                        # Another process already removed the corrupted lock
                        logger.debug(f"Corrupted lock already removed: {lock_file}")
                    except OSError as unlink_err:
                        logger.warning(f"Failed to remove corrupted lock: {unlink_err}")

        except OSError as e:
            # Failed to scan directory - not critical, log and continue
            logger.warning(f"Failed to scan directory for stale locks: {e}")

    def _secure_all_parent_directories(self, directory: Path) -> None:
        """Secure all parent directories with restrictive permissions.

        This method secures not just the final directory, but all parent
        directories that may have been created by mkdir(parents=True).
        This is critical on Windows where mkdir's mode parameter is ignored
        and parent directories may inherit insecure default permissions.

        The method walks up the directory tree from the target directory
        to the root (or until it finds a directory that's already secured),
        applying _secure_directory to each one.

        Args:
            directory: The target directory whose parents should be secured.

        Raises:
            RuntimeError: If any directory cannot be created or secured.

        Note:
            This is a security fix for Issue #369, #441, and #476. This method is now
            called on ALL platforms (Windows and Unix) to ensure parent directories
            are secured even if they were created by other processes.

            Security fix for Issue #476: This method now handles TOCTOU (Time-of-Check-
            Time-of-Use) race conditions where directories might be created by other
            processes with insecure permissions. The implementation tries to secure
            each directory and handles the case where it doesn't exist gracefully,
            rather than checking existence first. This ensures that if a directory
            is created by another process at any point, it will be secured.

            Security fix for Issue #486: This method now CREATES directories if they
            don't exist, eliminating the race condition window between
            _create_and_secure_directories and _secure_all_parent_directories. By
            combining creation and securing in a single method, we ensure atomicity
            and eliminate the security window where directories could be created with
            insecure permissions.

            Security fix for Issue #521: This method now uses dedicated lock files
            to prevent TOCTOU race conditions in directory creation. The lock files
            ensure that the check-exist-create sequence is atomic, eliminating the
            window where multiple processes could race to create the same directory.

            Security fix for Issue #561: This method now uses os.makedirs() with
            controlled umask on Unix systems, which is simpler and more atomic than
            the previous lock-based approach. os.makedirs with exist_ok=True handles
            the race condition where multiple processes try to create the same directory
            - one will succeed and others will see that it already exists.

            On Windows: Uses win32file.CreateDirectory with security descriptors for
            atomic directory creation with proper ACLs. Parent directories may inherit
            default permissions which are then secured by _secure_directory.

            On Unix: Uses os.makedirs() with umask=0o077 to ensure directories are
            created with mode 0o700 atomically. This is simpler than the previous
            lock-based approach and leverages the atomicity guarantees of os.makedirs.
        """
        # Get all parent directories from root to target
        # We want to secure them in order: from outermost to innermost
        # This ensures that if we need to create any intermediate structure,
        # we do it from the outside in
        parents_to_secure = []

        # Start from the target directory and walk up
        current = directory
        while current != current.parent:  # Stop at filesystem root
            parents_to_secure.append(current)
            current = current.parent

        # Security fix for Issue #561: Use os.makedirs for atomic directory creation
        # On Unix: Use os.makedirs with controlled umask (0o077) to ensure directories
        # are created with mode 0o700. This is simpler and more atomic than the previous
        # lock-based approach.
        # On Windows: Use the existing loop-based approach with win32file.CreateDirectory
        # for atomic directory creation with proper ACLs.
        if os.name != 'nt':  # Unix-like systems
            # Security fix for Issue #561: Use os.makedirs with controlled umask
            # This is simpler and more atomic than the lock-based approach.
            # os.makedirs with exist_ok=True handles race conditions where multiple
            # processes try to create the same directory.
            #
            # Security fix for Issue #576: Added retry logic and explicit error handling
            # to provide even more robust protection against TOCTOU race conditions
            # during concurrent directory creation. This ensures that even in extreme
            # race conditions (e.g., filesystem delays, NFS), the operation succeeds.
            import time

            max_retries = 3
            base_delay = 0.01  # 10ms starting delay
            last_error = None

            for attempt in range(max_retries):
                try:
                    old_umask = os.umask(0o077)
                    try:
                        # Create all parent directories with secure permissions in one call
                        # exist_ok=True handles the EEXIST error from concurrent creation
                        os.makedirs(directory, mode=0o700, exist_ok=True)
                    finally:
                        os.umask(old_umask)
                    # Success - break out of retry loop
                    break
                except FileExistsError:
                    # Even with exist_ok=True, rare edge cases can raise FileExistsError
                    # (e.g., race between exist_ok=True check and actual makedirs syscall)
                    # If the directory now exists, consider it a success
                    if directory.exists() and directory.is_dir():
                        logger.debug(
                            f"Directory {directory} already exists (concurrent creation detected). "
                            f"This is expected behavior and is handled correctly."
                        )
                        break
                    # If directory doesn't exist yet, retry
                    last_error = f"FileExistsError but directory not found: {directory}"
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.debug(
                            f"Retry {attempt + 1}/{max_retries} after {delay:.3f}s: {last_error}"
                        )
                        time.sleep(delay)
                except OSError as e:
                    # Handle other OS-level errors (e.g., EEXIST on some systems)
                    # errno 17 is EEXIST on Unix systems
                    if e.errno == 17 or hasattr(e, 'winerror') and e.winerror == 183:
                        # Directory already exists - verify and continue
                        if directory.exists() and directory.is_dir():
                            logger.debug(
                                f"Directory {directory} already exists (OSError EEXIST). "
                                f"This is expected behavior and is handled correctly."
                            )
                            break
                    # For other errors, retry or raise
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.debug(
                            f"Retry {attempt + 1}/{max_retries} after {delay:.3f}s: {last_error}"
                        )
                        time.sleep(delay)
                    else:
                        # Final attempt failed - raise the original error
                        raise RuntimeError(
                            f"Failed to create directory {directory} after {max_retries} attempts: {last_error}"
                        ) from e

            # Security fix for Issue #481: Secure all parent directories even if they
            # were created by other processes with insecure permissions.
            for parent_dir in parents_to_secure:
                if parent_dir.exists():
                    try:
                        self._secure_directory(parent_dir)
                    except PermissionError as e:
                        # Security fix for Issue #434: Handle PermissionError gracefully
                        logger.warning(
                            f"Cannot set secure permissions on {parent_dir}: {e}. "
                            f"This directory may be owned by another user or have restrictive "
                            f"permissions. The application will continue, but this directory "
                            f"may have less restrictive permissions than desired."
                        )
        else:  # Windows - use atomic directory creation with ACLs
            # Security fix for Issue #486: Create and secure each parent directory atomically
            # This eliminates the race condition window between the separate
            # _create_and_secure_directories call and _secure_all_parent_directories call.
            # By combining creation and securing in a single loop, we ensure that directories
            # are created and secured in one atomic operation.
            for parent_dir in parents_to_secure:
                # Security fix for Issue #521: Acquire lock before checking/creating directory
                # This prevents TOCTOU race conditions where multiple processes could
                # race between the exists() check and mkdir() call.
                lock_acquired = False
                try:
                    self._acquire_directory_lock(parent_dir)
                    lock_acquired = True
                except RuntimeError as lock_error:
                    # If we can't acquire the lock, it means another process is creating
                    # this directory. Wait a bit and check if it gets created.
                    logger.debug(f"Could not acquire lock for {parent_dir}: {lock_error}")
                    if parent_dir.exists():
                        # Directory was created by another process, just secure it
                        try:
                            self._secure_directory(parent_dir)
                            continue
                        except Exception as secure_error:
                            logger.warning(f"Failed to secure directory {parent_dir}: {secure_error}")
                            continue
                    else:
                        # Directory doesn't exist and we can't create it
                        logger.warning(f"Cannot create {parent_dir}: lock acquisition failed")
                        continue

                # Retry loop for handling race conditions (Issue #409, #486)
                import time
                max_retries = 5
                base_delay = 0.01  # 10ms starting delay
                success = False
                last_error = None

                try:
                    for attempt in range(max_retries):
                        try:
                            # Security fix for Issue #521: With lock held, check and create directory
                            # The lock ensures this sequence is atomic - no other process can
                            # create the directory between the check and creation.
                            if not parent_dir.exists():
                                # Portability fix for Issue #671: Check if running in degraded mode
                                if _is_degraded_mode():
                                    # pywin32 is not available - fall back to basic directory creation
                                    logger.warning(
                                        f"Creating parent directory '{parent_dir}' without security "
                                        f"in degraded mode (pywin32 not installed). "
                                        f"This is UNSAFE for production use."
                                    )
                                    parent_dir.mkdir(mode=0o700, exist_ok=True)
                                else:
                                    # Windows - use atomic directory creation (Issue #400)
                                    # Security fix for Issue #429: Windows modules are imported at module level,
                                    # ensuring thread-safe initialization. Modules are available immediately.

                                    # Use CreateDirectory with security descriptor (Issue #400)
                                    user = win32api.GetUserName()

                                    # Fix Issue #251: Extract pure username
                                    if '\\' in user:
                                        parts = user.rsplit('\\', 1)
                                        if len(parts) == 2:
                                            user = parts[1]

                                    # Get domain
                                    try:
                                        name = win32api.GetUserNameEx(win32con.NameFullyQualifiedDN)
                                        if not isinstance(name, str):
                                            raise TypeError(
                                                f"GetUserNameEx returned non-string value: {type(name).__name__}"
                                            )
                                        parts = name.split(',')
                                        dc_parts = []
                                        for p in parts:
                                            p = p.strip()
                                            if p.startswith('DC='):
                                                split_parts = p.split('=', 1)
                                                if len(split_parts) >= 2:
                                                    dc_parts.append(split_parts[1])
                                        if dc_parts:
                                            domain = '.'.join(dc_parts)
                                        else:
                                            domain = win32api.GetComputerName()
                                    except (TypeError, ValueError):
                                        raise RuntimeError(
                                            f"Cannot set Windows security: GetUserNameEx returned invalid data. "
                                            f"Install pywin32: pip install pywin32"
                                        )
                                    except Exception:
                                        domain = win32api.GetComputerName()

                                    # Validate domain
                                    if domain is None or (isinstance(domain, str) and len(domain.strip()) == 0):
                                        raise RuntimeError(
                                            "Cannot set Windows security: Unable to determine domain. "
                                            "Install pywin32: pip install pywin32"
                                        )

                                    # Validate user
                                    if not user or not isinstance(user, str) or len(user.strip()) == 0:
                                        raise ValueError(
                                            f"Invalid user name '{user}': Cannot set Windows security."
                                        )

                                    # Lookup account SID
                                    try:
                                        sid, _, _ = win32security.LookupAccountName(domain, user)
                                    except Exception as e:
                                        raise RuntimeError(
                                            f"Failed to set Windows ACLs: Unable to lookup account '{user}'. "
                                            f"Install pywin32: pip install pywin32. Error: {e}"
                                        ) from e

                                    # Create security descriptor
                                    security_descriptor = win32security.SECURITY_DESCRIPTOR()
                                    security_descriptor.SetSecurityDescriptorOwner(sid, False)

                                    # Create DACL with minimal permissions
                                    dacl = win32security.ACL()
                                    dacl.AddAccessAllowedAce(
                                        win32security.ACL_REVISION,
                                        win32con.FILE_LIST_DIRECTORY |
                                        win32con.FILE_ADD_FILE |
                                        win32con.FILE_READ_ATTRIBUTES |
                                        win32con.FILE_WRITE_ATTRIBUTES |
                                        win32con.DELETE |
                                        win32con.SYNCHRONIZE,
                                        sid
                                    )

                                    security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)

                                    # Create SACL for auditing
                                    sacl = win32security.ACL()
                                    security_descriptor.SetSecurityDescriptorSacl(0, sacl, 0)

                                    # Set DACL protection
                                    security_descriptor.SetSecurityDescriptorControl(
                                        win32security.SE_DACL_PROTECTED, 1
                                    )

                                    # Create directory atomically with security descriptor
                                    win32file.CreateDirectory(
                                        str(parent_dir),
                                        security_descriptor
                                    )

                            # Always secure the directory (Issue #481, #486)
                            # Even if we just created it, call _secure_directory to ensure consistency
                            # This is safe because _secure_directory is idempotent
                            self._secure_directory(parent_dir)

                            # Success - break out of retry loop
                            success = True
                            break

                        except FileExistsError:
                            # Security fix for Issue #481: Directory was created by another process
                            # Always verify and secure it, don't just assume it's secure
                            if parent_dir.exists():
                                try:
                                    self._secure_directory(parent_dir)
                                    success = True
                                    break
                                except Exception as verify_error:
                                    last_error = verify_error
                                    if attempt < max_retries - 1:
                                        delay = base_delay * (2 ** attempt)
                                        time.sleep(delay)
                            else:
                                # Directory doesn't exist but we got FileExistsError
                                last_error = Exception("Got FileExistsError but directory doesn't exist")
                                if attempt < max_retries - 1:
                                    delay = base_delay * (2 ** attempt)
                                    time.sleep(delay)

                        except PermissionError as e:
                            # Security fix for Issue #434: Handle PermissionError gracefully
                            # when parent directories are owned by another user or have restrictive
                            # permissions preventing ACL/chmod modification. Log a warning and
                            # continue rather than crashing the application.
                            logger.warning(
                                f"Cannot set secure permissions on {parent_dir}: {e}. "
                                f"This directory may be owned by another user or have restrictive "
                                f"permissions. The application will continue, but this directory "
                                f"may have less restrictive permissions than desired."
                            )
                            # Mark as success to continue with other directories
                            # The immediate application directory will still be secured separately
                            success = True
                            break

                        except Exception as e:
                            # Non-retryable error
                            last_error = e
                            break

                # After all retries, check if we succeeded
                if not success:
                    # Security fix for Issue #434: Check if the error is permission-related
                    # If so, log a warning and continue instead of crashing
                    error_is_permission_related = (
                        isinstance(last_error, PermissionError) or
                        (isinstance(last_error, RuntimeError) and
                         ("Permission denied" in str(last_error) or
                          "Cannot continue without secure directory permissions" in str(last_error)))
                    )

                    if error_is_permission_related:
                        # Log a warning and continue
                        logger.warning(
                            f"Cannot secure directory {parent_dir}: {last_error}. "
                            f"This may be due to insufficient permissions. The application will "
                            f"continue, but this directory may have less restrictive permissions."
                        )
                        # Continue to next directory instead of raising
                        continue
                    else:
                        # For other errors, still raise to prevent running with insecure state
                        raise RuntimeError(
                            f"Failed to create and secure directory {parent_dir} after {max_retries} attempts. "
                            f"Last error: {last_error}. "
                            f"Cannot continue without secure directory permissions."
                        ) from last_error

                except BaseException:
                    # Re-raise any exceptions
                    raise
                finally:
                    # Security fix for Issue #521: Always release the lock, even if an error occurred
                    if lock_acquired:
                        self._release_directory_lock(parent_dir)

    def _create_backup(self, error_message: str) -> str:
        """Create a backup of the todo file.

        Args:
            error_message: Description of the error that triggered the backup.

        Returns:
            Path to the backup file.

        Raises:
            RuntimeError: If backup creation fails.
        """
        import shutil

        # Use .bak extension for backup files (Issue #632)
        backup_path = str(self.path) + ".bak"
        try:
            shutil.copy2(self.path, backup_path)
            logger.error(f"{error_message}. Backup created at {backup_path}")
        except Exception as backup_error:
            logger.error(f"Failed to create backup: {backup_error}")
            raise RuntimeError(f"{error_message}. Failed to create backup") from backup_error
        return backup_path

    def _auto_save_worker(self) -> None:
        """Background thread worker for auto-save functionality (Issue #592).

        This method runs in a daemon thread and periodically checks if the data
        has been modified (_dirty flag). If dirty and enough time has passed since
        the last save, it triggers a save operation to prevent data loss.

        The thread sleeps for 1 second between checks to balance responsiveness
        with CPU usage. The check interval is independent of AUTO_SAVE_INTERVAL.
        """
        while not self._auto_save_stop_event.is_set():
            try:
                # Check if auto-save should be triggered
                self._check_auto_save()
            except Exception as e:
                # Log error but continue running to prevent thread crash
                logger.error(f"Auto-save worker error: {e}")

            # Sleep for 1 second before next check
            # This provides responsive checking without excessive CPU usage
            self._auto_save_stop_event.wait(1.0)

    def _check_auto_save(self) -> None:
        """Check if auto-save should be triggered based on time interval (Issue #547).

        This method checks if the time elapsed since the last save exceeds
        the AUTO_SAVE_INTERVAL. If so, it triggers a background save operation.
        The save operation uses the existing thread-safe _save() method with RLock.
        """
        current_time = time.time()
        if current_time - self.last_saved_time > self.AUTO_SAVE_INTERVAL:
            if self._dirty:
                try:
                    self._save()
                    self.last_saved_time = current_time
                    logger.debug("Auto-save triggered after interval")
                except Exception as e:
                    logger.error(f"Auto-save failed: {e}")

    def _cleanup(self) -> None:
        """Cleanup handler called on program exit.

        Ensures any pending changes are saved before the program exits.
        This prevents data loss when the program terminates unexpectedly.

        Uses MIN_SAVE_INTERVAL to batch rapid small writes (Issue #563).
        Only saves if enough time has passed since the last save.

        If the storage has been explicitly closed via close(), this method
        does nothing (Issue #688).

        Issue #874: Also cleans up lock files in degraded mode to prevent
        stale locks from blocking future processes.
        """
        # Skip cleanup if already closed (Issue #688)
        if hasattr(self, '_closed') and self._closed:
            return

        if self._dirty:
            current_time = time.time()
            time_since_last_save = current_time - self.last_saved_time

            # Only save if enough time has passed since the last save
            # This batches rapid small writes to reduce I/O
            if time_since_last_save >= self.MIN_SAVE_INTERVAL:
                try:
                    self._save()
                    self.last_saved_time = current_time
                    logger.info("Saved pending changes on exit")
                except Exception as e:
                    logger.error(f"Failed to save pending changes on exit: {e}")
            else:
                logger.debug(
                    f"Skipping save: only {time_since_last_save:.2f}s "
                    f"since last save (threshold: {self.MIN_SAVE_INTERVAL}s)"
                )

        # Issue #874: Clean up lock file in degraded mode
        # This ensures locks are released even on abnormal termination
        # when __del__ might not be called or close() was not invoked
        if (hasattr(self, '_lock_file_path') and
            self._lock_file_path is not None and
            os.path.exists(self._lock_file_path)):
            try:
                os.unlink(self._lock_file_path)
                logger.info(f"Cleaned up lock file on exit: {self._lock_file_path}")
                self._lock_file_path = None
            except OSError as e:
                logger.warning(f"Failed to clean up lock file on exit: {e}")

    def _rotate_backups(self) -> None:
        """Rotate backup files to keep last N versions (Issue #693).

        Backup rotation scheme:
        - todos.json.bak (most recent backup)
        - todos.json.bak.1 (second most recent)
        - todos.json.bak.2 (third most recent)
        - ...
        - todos.json.bak.N (oldest backup within backup_count)

        If backup_count is 3, we keep:
        - .bak (most recent)
        - .bak.1 (second most recent)
        - .bak.2 (third most recent)

        Older backups (.bak.3, .bak.4, etc.) are removed.
        """
        import shutil

        # First, delete the oldest backup if it exists
        oldest_backup = self.path.parent / f"{self.path.name}.bak.{self.backup_count - 1}"
        if oldest_backup.exists():
            try:
                oldest_backup.unlink()
            except OSError:
                # Ignore errors when removing old backup
                pass

        # Rotate existing backups: .bak.N-1 -> .bak.N
        for i in range(self.backup_count - 1, 0, -1):
            old_backup = self.path.parent / f"{self.path.name}.bak.{i - 1}" if i > 1 else self.path.parent / f"{self.path.name}.bak"
            new_backup = self.path.parent / f"{self.path.name}.bak.{i}"

            if old_backup.exists():
                try:
                    # Use atomic write pattern (Issue #1515):
                    # 1. Write to temporary file
                    # 2. Sync to disk (flush)
                    # 3. Atomically rename to target path
                    # This prevents data loss if the process crashes during write
                    temp_backup = new_backup.with_suffix(new_backup.suffix + '.tmp')

                    # Copy to temporary file first
                    shutil.copy2(old_backup, temp_backup)

                    # Atomically replace the target file
                    temp_backup.replace(new_backup)
                except OSError:
                    # Ignore errors during backup rotation
                    pass

        # Create new backup from current file
        backup_path = self.path.parent / f"{self.path.name}.bak"
        try:
            # Use atomic write pattern (Issue #1515):
            # 1. Write to temporary file
            # 2. Sync to disk (flush)
            # 3. Atomically rename to target path
            # This prevents data loss if the process crashes during write
            temp_backup = backup_path.with_suffix(backup_path.suffix + '.tmp')

            # Copy to temporary file first
            shutil.copy2(self.path, temp_backup)

            # Atomically replace the target file
            temp_backup.replace(backup_path)
        except OSError:
            # Ignore errors when creating backup
            pass

    async def _rotate_backups_async(self) -> None:
        """Rotate backup files asynchronously using aiofiles (Issue #747).

        Backup rotation scheme:
        - todos.json.bak (most recent backup)
        - todos.json.bak.1 (second most recent)
        - todos.json.bak.2 (third most recent)
        - ...
        - todos.json.bak.N (oldest backup within backup_count)

        If backup_count is 3, we keep:
        - .bak (most recent)
        - .bak.1 (second most recent)
        - .bak.2 (third most recent)

        Older backups (.bak.3, .bak.4, etc.) are removed.

        This async version uses aiofiles for non-blocking I/O operations,
        ensuring the event loop is not blocked during backup rotation.
        """
        import shutil

        # First, delete the oldest backup if it exists
        oldest_backup = self.path.parent / f"{self.path.name}.bak.{self.backup_count - 1}"
        if oldest_backup.exists():
            try:
                oldest_backup.unlink()
            except OSError:
                # Ignore errors when removing old backup
                pass

        # Rotate existing backups: .bak.N-1 -> .bak.N
        for i in range(self.backup_count - 1, 0, -1):
            old_backup = self.path.parent / f"{self.path.name}.bak.{i - 1}" if i > 1 else self.path.parent / f"{self.path.name}.bak"
            new_backup = self.path.parent / f"{self.path.name}.bak.{i}"

            if old_backup.exists():
                try:
                    # Use atomic write pattern (Issue #1515):
                    # 1. Write to temporary file
                    # 2. Sync to disk (flush)
                    # 3. Atomically rename to target path
                    # This prevents data loss if the process crashes during write
                    temp_backup = new_backup.with_suffix(new_backup.suffix + '.tmp')

                    # Use async file copy for non-blocking I/O
                    async with aiofiles.open(old_backup, 'rb') as src_file:
                        data = await src_file.read()

                    # Write to temporary file
                    async with aiofiles.open(temp_backup, 'wb') as dst_file:
                        await dst_file.write(data)
                        await dst_file.flush()
                        os.fsync(dst_file.fileno())

                    # Atomically replace the target file
                    temp_backup.replace(new_backup)

                    # Copy metadata (modification time, etc.)
                    shutil.copystat(old_backup, new_backup)
                except OSError:
                    # Ignore errors during backup rotation
                    pass

        # Create new backup from current file
        backup_path = self.path.parent / f"{self.path.name}.bak"
        try:
            # Use atomic write pattern (Issue #1515):
            # 1. Write to temporary file
            # 2. Sync to disk (flush)
            # 3. Atomically rename to target path
            # This prevents data loss if the process crashes during write
            temp_backup = backup_path.with_suffix(backup_path.suffix + '.tmp')

            # Use async file copy for non-blocking I/O
            async with aiofiles.open(self.path, 'rb') as src_file:
                data = await src_file.read()

            # Write to temporary file
            async with aiofiles.open(temp_backup, 'wb') as dst_file:
                await dst_file.write(data)
                await dst_file.flush()
                os.fsync(dst_file.fileno())

            # Atomically replace the target file
            temp_backup.replace(backup_path)

            # Copy metadata (modification time, etc.)
            shutil.copystat(self.path, backup_path)
        except OSError:
            # Ignore errors when creating backup
            pass

    def _calculate_checksum(self, todos: list) -> str:
        """Calculate SHA256 checksum of todos data (Issue #223).

        Args:
            todos: List of todo objects to calculate checksum for.

        Returns:
            Hexadecimal string representation of SHA256 hash.
        """
        # Serialize todos to JSON for hashing
        todos_json = json.dumps([t.to_dict() for t in todos], sort_keys=True)
        return hashlib.sha256(todos_json.encode('utf-8')).hexdigest()

    def _validate_storage_schema(self, data: dict | list) -> None:
        """Validate the storage data schema for security (Issue #7).

        This method performs strict schema validation to prevent:
        - Injection attacks via malformed data structures
        - Type confusion vulnerabilities
        - Unexpected nested structures

        Args:
            data: The raw parsed JSON data (dict or list)

        Raises:
            RuntimeError: If the data structure is invalid or potentially malicious.
        """
        # Validate top-level structure
        if isinstance(data, dict):
            # New format with metadata
            # Check for unexpected keys that could indicate tampering
            expected_keys = {"todos", "next_id", "metadata"}
            actual_keys = set(data.keys())
            # Warn about unexpected keys but don't fail (forward compatibility)
            unexpected = actual_keys - expected_keys
            if unexpected:
                logger.warning(f"Unexpected keys in storage file: {unexpected}")

            # Validate 'metadata' field if present (Issue #223)
            if "metadata" in data:
                if not isinstance(data["metadata"], dict):
                    raise RuntimeError(
                        f"Invalid schema: 'metadata' must be a dict, got {type(data['metadata']).__name__}"
                    )
                # Checksum is optional but must be a string if present
                if "checksum" in data["metadata"] and not isinstance(data["metadata"]["checksum"], str):
                    raise RuntimeError(
                        f"Invalid schema: 'metadata.checksum' must be a string"
                    )

            # Validate 'todos' field
            if "todos" in data:
                if not isinstance(data["todos"], list):
                    raise RuntimeError(
                        f"Invalid schema: 'todos' must be a list, got {type(data['todos']).__name__}"
                    )

            # Validate 'next_id' field
            if "next_id" in data:
                if not isinstance(data["next_id"], int):
                    raise RuntimeError(
                        f"Invalid schema: 'next_id' must be an int, got {type(data['next_id']).__name__}"
                    )
                if data["next_id"] < 1:
                    raise RuntimeError(f"Invalid schema: 'next_id' must be >= 1, got {data['next_id']}")

        elif isinstance(data, list):
            # Old format - list of todos
            # No additional validation needed, individual todos will be validated
            pass
        else:
            # Invalid top-level type
            raise RuntimeError(
                f"Invalid schema: expected dict or list at top level, got {type(data).__name__}"
            )

    def _validate_and_repair_todos(self, todos: list[Todo]) -> list[Todo]:
        """Validate and repair todos by detecting and fixing data integrity issues.

        This method implements data validation and repair mechanism (Issue #632):
        - Detects and removes duplicate IDs (keeps first occurrence)
        - Validates field types
        - Logs warnings for any repairs made

        Args:
            todos: List of Todo objects to validate and repair.

        Returns:
            A repaired list of todos with duplicates removed and only valid items.
        """
        if not todos:
            return []

        # Track seen IDs to detect duplicates
        seen_ids = set()
        repaired_todos = []
        duplicates_removed = 0

        for todo in todos:
            # Validate ID is an integer (basic type check)
            if not isinstance(todo.id, int):
                logger.warning(f"Skipping todo with invalid ID type: {type(todo.id).__name__}")
                continue

            # Check for duplicate IDs
            if todo.id in seen_ids:
                duplicates_removed += 1
                logger.warning(
                    f"Duplicate ID detected: {todo.id}. "
                    f"Keeping first occurrence, removing: '{todo.title}'"
                )
                continue

            # Validate basic field types
            if not isinstance(todo.title, str):
                logger.warning(
                    f"Skipping todo {todo.id} with invalid title type: "
                    f"{type(todo.title).__name__}"
                )
                continue

            if not isinstance(todo.status, str):
                logger.warning(
                    f"Skipping todo {todo.id} with invalid status type: "
                    f"{type(todo.status).__name__}"
                )
                continue

            # Todo is valid, add it to the repaired list
            seen_ids.add(todo.id)
            repaired_todos.append(todo)

        if duplicates_removed > 0:
            logger.info(
                f"Data repair completed: Removed {duplicates_removed} duplicate(s). "
                f"Retained {len(repaired_todos)} unique todo(s)."
            )

        return repaired_todos

    @retry_transient_errors(max_attempts=3, initial_backoff=0.1)
    @measure_latency("load")
    async def _load(self) -> None:
        """Load todos from file asynchronously.

        File read and state update are performed atomically within the lock
        to prevent race conditions where the file could change between
        reading and updating internal state.

        Uses aiofiles for non-blocking async I/O (Issue #582).
        """
        import time
        start_time = time.time()
        logger.debug(f"Loading todos from {self.path}")

        # Acquire lock first to ensure atomicity of read + state update
        async with self._async_lock:
            logger.debug("Acquiring async lock for load operation")
            if not self.path.exists():
                logger.debug(f"File {self.path} does not exist, initializing empty storage")
                self._todos = []
                self._next_id = 1
                self._dirty = False  # Reset dirty flag (Issue #203)
                return

            try:
                # Read file and parse JSON atomically using json.load()
                # This prevents TOCTOU issues by keeping the file handle open
                # during parsing, instead of separating read_text() and json.loads()
                # Acquire file lock for multi-process safety (Issue #268)

                # Use compression setting from initialization (Issue #652)
                is_compressed = self.compression

                # Read file as bytes first to verify integrity hash (Issue #588)
                # This allows us to detect file truncation or corruption
                # Use aiofiles for async non-blocking I/O (Issue #582)
                logger.debug(f"Reading file {self.path}")
                async with aiofiles.open(self.path, 'rb') as f:
                    logger.debug("Acquiring file lock for read operation")
                    self._acquire_file_lock(f)
                    try:
                        file_bytes = await f.read()
                        bytes_read = len(file_bytes)  # Track bytes for performance logging (Issue #758)
                    finally:
                        self._release_file_lock(f)

                # Extract and verify integrity hash from end of file (Issue #588)
                # Format: \n##INTEGRITY:<hash>##\n
                file_str = file_bytes.decode('utf-8')
                integrity_marker = '##INTEGRITY:'
                marker_start = file_str.rfind(integrity_marker)

                if marker_start != -1:
                    # Found integrity marker - extract and verify hash
                    marker_end = file_str.find('##', marker_start + len(integrity_marker))
                    if marker_end != -1:
                        stored_hash = file_str[marker_start + len(integrity_marker):marker_end]

                        # Calculate hash of the data before the integrity marker
                        # Find the newline before the marker
                        data_end = file_str.rfind('\n', 0, marker_start)
                        if data_end == -1:
                            data_end = 0  # No newline found, use entire content before marker

                        actual_data = file_bytes[:data_end] if data_end > 0 else file_bytes[:marker_start-1]
                        calculated_hash = hashlib.sha256(actual_data).hexdigest()

                        if calculated_hash != stored_hash:
                            # Hash mismatch - data corruption detected
                            backup_path = self._create_backup(
                                f"Integrity hash mismatch in {self.path}: "
                                f"expected {stored_hash}, got {calculated_hash}"
                            )
                            raise RuntimeError(
                                f"Data integrity verification failed. Hash mismatch. "
                                f"Backup saved to {backup_path}"
                            )

                        # Remove integrity marker from data for JSON parsing
                        file_str = file_str[:data_end] if data_end > 0 else file_str[:marker_start-1]
                        file_bytes = file_str.encode('utf-8')

                # Decompress if needed
                if is_compressed:
                    file_bytes = gzip.decompress(file_bytes)

                raw_data = json.loads(file_bytes.decode('utf-8'))

                # Validate schema before deserializing (Issue #7)
                # This prevents injection attacks and malformed data from causing crashes
                self._validate_storage_schema(raw_data)

                # Handle both new format (dict with metadata) and old format (list)
                # Schema validation already performed above (Issue #7)
                if isinstance(raw_data, dict):
                    # New format with metadata
                    todos_data = raw_data.get("todos", [])

                    # Verify data integrity using checksum (Issue #223)
                    metadata = raw_data.get("metadata", {})
                    stored_checksum = metadata.get("checksum")

                    if stored_checksum:
                        # Calculate checksum of loaded todos
                        calculated_checksum = None
                        try:
                            # Temporarily deserialize todos for checksum calculation
                            temp_todos = []
                            for item in todos_data:
                                try:
                                    temp_todos.append(Todo.from_dict(item))
                                except (ValueError, TypeError, KeyError):
                                    pass
                            calculated_checksum = self._calculate_checksum(temp_todos)

                            if calculated_checksum != stored_checksum:
                                # Checksum mismatch - data corruption detected
                                backup_path = self._create_backup(
                                    f"Checksum mismatch in {self.path}: "
                                    f"expected {stored_checksum}, got {calculated_checksum}"
                                )
                                raise RuntimeError(
                                    f"Data integrity check failed. Checksum mismatch. "
                                    f"Backup saved to {backup_path}"
                                )
                        except Exception as e:
                            if isinstance(e, RuntimeError):
                                raise
                            # If checksum calculation fails, log warning but continue
                            logger.warning(f"Failed to verify checksum: {e}")

                    # Use direct access after validation to ensure type safety (Issue #219)
                    # _validate_storage_schema already confirmed next_id is an int if it exists
                    next_id = raw_data["next_id"] if "next_id" in raw_data else 1
                elif isinstance(raw_data, list):
                    # Old format - backward compatibility
                    todos_data = raw_data
                    # Calculate next_id from existing todos, safely handling invalid items
                    valid_ids = []
                    for item in raw_data:
                        if isinstance(item, dict):
                            try:
                                todo = Todo.from_dict(item)
                                valid_ids.append(todo.id)
                            except (ValueError, TypeError, KeyError):
                                # Skip invalid items when calculating next_id
                                pass
                    next_id = max(set(valid_ids), default=0) + 1

                # Deserialize todo items inside the lock
                todos = []
                for i, item in enumerate(todos_data):
                    try:
                        todo = Todo.from_dict(item)
                        todos.append(todo)
                    except (ValueError, TypeError, KeyError) as e:
                        # Skip invalid todo items but continue loading valid ones
                        logger.warning(f"Skipping invalid todo at index {i}: {e}")

                # Validate and repair todos (Issue #632)
                # This checks for duplicate IDs, invalid field types, and attempts auto-repair
                todos = self._validate_and_repair_todos(todos)

                # Update internal state
                self._todos = todos
                self._next_id = next_id
                # Reset dirty flag after successful load (Issue #203)
                self._dirty = False

                # Log successful load completion
                elapsed = time.time() - start_time
                logger.debug(
                    f"Load completed in {elapsed:.3f}s ({len(todos)} todos loaded, {bytes_read} bytes read)",
                    extra={'duration_ms': elapsed * 1000, 'operation': 'load', 'bytes_read': bytes_read}
                )
            except json.JSONDecodeError as e:
                # Create backup before raising exception to prevent data loss
                backup_path = self._create_backup(f"Invalid JSON in {self.path}")
                # Include detailed error context: line number, column, and position
                # This helps users locate and fix JSON syntax errors manually (Issue #548)
                raise RuntimeError(
                    f"Invalid JSON in {self.path}: {e.msg} at line {e.lineno}, column {e.colno}. "
                    f"Backup saved to {backup_path}"
                ) from e
            except RuntimeError as e:
                # Re-raise RuntimeError without creating backup
                # This handles format validation errors that should not trigger backup
                raise
            except Exception as e:
                # Create backup before raising exception to prevent data loss
                backup_path = self._create_backup(f"Failed to load todos from {self.path}")
                raise RuntimeError(f"Failed to load todos. Backup saved to {backup_path}") from e

    def _load_sync(self) -> None:
        """Load todos from file synchronously.

        This is a synchronous version of _load() for use in __init__.
        It uses standard file I/O instead of async I/O to avoid issues
        with asyncio.run() being called from __init__ (Issue #641).

        File read and state update are performed atomically to prevent
        race conditions where the file could change between reading and
        updating internal state.

        Implements LRU cache for metadata reads to reduce I/O on network
        filesystems (Issue #1073). Cache uses file modification time to
        detect changes and automatically invalidate stale entries.
        """
        import time
        start_time = time.time()
        logger.debug(f"Loading todos from {self.path} (synchronously)")

        if not self.path.exists():
            self._todos = []
            self._next_id = 1
            self._dirty = False  # Reset dirty flag (Issue #203)
            return

        # Check LRU cache first (Issue #1073)
        cache_key = str(self.path)
        current_mtime = self.path.stat().st_mtime

        with self._metadata_cache_lock:
            if cache_key in self._metadata_cache:
                cached_todos, cached_next_id, cached_mtime = self._metadata_cache[cache_key]
                # Use cached data if file hasn't been modified
                if cached_mtime == current_mtime:
                    self._todos = cached_todos
                    self._next_id = cached_next_id
                    self._dirty = False
                    elapsed = time.time() - start_time
                    logger.debug(
                        f"Load completed in {elapsed:.3f}s (cached, {len(cached_todos)} todos)",
                        extra={'duration_ms': elapsed * 1000, 'operation': 'load_cached', 'todos_count': len(cached_todos)}
                    )
                    return

        try:
            # Read file and parse JSON atomically using json.load()
            # This prevents TOCTOU issues by keeping the file handle open
            # during parsing, instead of separating read_text() and json.loads()
            # Acquire file lock for multi-process safety (Issue #268)

            # Use compression setting from initialization (Issue #652)
            is_compressed = self.compression

            # Read file as bytes first to verify integrity hash (Issue #588)
            # This allows us to detect file truncation or corruption
            # Use standard file I/O for synchronous loading
            with open(self.path, 'rb') as f:
                self._acquire_file_lock(f)
                try:
                    file_bytes = f.read()
                    bytes_read = len(file_bytes)  # Track bytes for performance logging (Issue #758)
                finally:
                    self._release_file_lock(f)

            # Extract and verify integrity hash from end of file (Issue #588)
            # Format: \n##INTEGRITY:<hash>##\n
            file_str = file_bytes.decode('utf-8')
            integrity_marker = '##INTEGRITY:'
            marker_start = file_str.rfind(integrity_marker)

            if marker_start != -1:
                # Found integrity marker - extract and verify hash
                marker_end = file_str.find('##', marker_start + len(integrity_marker))
                if marker_end != -1:
                    stored_hash = file_str[marker_start + len(integrity_marker):marker_end]

                    # Calculate hash of the data before the integrity marker
                    # Find the newline before the marker
                    data_end = file_str.rfind('\n', 0, marker_start)
                    if data_end == -1:
                        data_end = 0  # No newline found, use entire content before marker

                    actual_data = file_bytes[:data_end] if data_end > 0 else file_bytes[:marker_start-1]
                    calculated_hash = hashlib.sha256(actual_data).hexdigest()

                    if calculated_hash != stored_hash:
                        # Hash mismatch - data corruption detected
                        backup_path = self._create_backup(
                            f"Integrity hash mismatch in {self.path}: "
                            f"expected {stored_hash}, got {calculated_hash}"
                        )
                        raise RuntimeError(
                            f"Data integrity verification failed. Hash mismatch. "
                            f"Backup saved to {backup_path}"
                        )

                    # Remove integrity marker from data for JSON parsing
                    file_str = file_str[:data_end] if data_end > 0 else file_str[:marker_start-1]
                    file_bytes = file_str.encode('utf-8')

            # Decompress if needed
            if is_compressed:
                file_bytes = gzip.decompress(file_bytes)

            raw_data = json.loads(file_bytes.decode('utf-8'))

            # Validate schema before deserializing (Issue #7)
            # This prevents injection attacks and malformed data from causing crashes
            self._validate_storage_schema(raw_data)

            # Handle both new format (dict with metadata) and old format (list)
            # Schema validation already performed above (Issue #7)
            if isinstance(raw_data, dict):
                # New format with metadata
                todos_data = raw_data.get("todos", [])

                # Verify data integrity using checksum (Issue #223)
                metadata = raw_data.get("metadata", {})
                stored_checksum = metadata.get("checksum")

                if stored_checksum:
                    # Calculate checksum of loaded todos
                    calculated_checksum = None
                    try:
                        # Temporarily deserialize todos for checksum calculation
                        temp_todos = []
                        for item in todos_data:
                            try:
                                temp_todos.append(Todo.from_dict(item))
                            except (ValueError, TypeError, KeyError):
                                pass
                        calculated_checksum = self._calculate_checksum(temp_todos)

                        if calculated_checksum != stored_checksum:
                            # Checksum mismatch - data corruption detected
                            backup_path = self._create_backup(
                                f"Checksum mismatch in {self.path}: "
                                f"expected {stored_checksum}, got {calculated_checksum}"
                            )
                            raise RuntimeError(
                                f"Data integrity check failed. Checksum mismatch. "
                                f"Backup saved to {backup_path}"
                            )
                    except Exception as e:
                        if isinstance(e, RuntimeError):
                            raise
                        # If checksum calculation fails, log warning but continue
                        logger.warning(f"Failed to verify checksum: {e}")

                # Use direct access after validation to ensure type safety (Issue #219)
                # _validate_storage_schema already confirmed next_id is an int if it exists
                next_id = raw_data["next_id"] if "next_id" in raw_data else 1
            elif isinstance(raw_data, list):
                # Old format - backward compatibility
                todos_data = raw_data
                # Calculate next_id from existing todos, safely handling invalid items
                valid_ids = []
                for item in raw_data:
                    if isinstance(item, dict):
                        try:
                            todo = Todo.from_dict(item)
                            valid_ids.append(todo.id)
                        except (ValueError, TypeError, KeyError):
                            # Skip invalid items when calculating next_id
                            pass
                next_id = max(set(valid_ids), default=0) + 1

            # Deserialize todo items
            todos = []
            for i, item in enumerate(todos_data):
                try:
                    todo = Todo.from_dict(item)
                    todos.append(todo)
                except (ValueError, TypeError, KeyError) as e:
                    # Skip invalid todo items but continue loading valid ones
                    logger.warning(f"Skipping invalid todo at index {i}: {e}")

            # Validate and repair todos (Issue #632)
            # This checks for duplicate IDs, invalid field types, and attempts auto-repair
            todos = self._validate_and_repair_todos(todos)

            # Update internal state
            self._todos = todos
            self._next_id = next_id
            # Reset dirty flag after successful load (Issue #203)
            self._dirty = False

            # Initialize cache from loaded data if cache is enabled (Issue #742)
            # This ensures cache is available immediately after load, rather than
            # waiting for the first access to rebuild it
            if self._cache_enabled:
                self._update_cache_from_todos()

            # Update LRU cache with loaded data (Issue #1073)
            with self._metadata_cache_lock:
                # Implement LRU eviction if cache is full
                if len(self._metadata_cache) >= self._metadata_cache_maxsize:
                    # Remove oldest entry (first item in dict)
                    oldest_key = next(iter(self._metadata_cache))
                    del self._metadata_cache[oldest_key]

                # Store in cache with current modification time
                self._metadata_cache[cache_key] = (todos, next_id, current_mtime)

            # Log successful load completion
            elapsed = time.time() - start_time
            logger.debug(
                f"Load completed in {elapsed:.3f}s ({len(todos)} todos loaded, {bytes_read} bytes read)",
                extra={'duration_ms': elapsed * 1000, 'operation': 'load_sync', 'bytes_read': bytes_read}
            )
        except json.JSONDecodeError as e:
            # Create backup before raising exception to prevent data loss
            backup_path = self._create_backup(f"Invalid JSON in {self.path}")
            # Include detailed error context: line number, column, and position
            # This helps users locate and fix JSON syntax errors manually (Issue #548)
            raise RuntimeError(
                f"Invalid JSON in {self.path}: {e.msg} at line {e.lineno}, column {e.colno}. "
                f"Backup saved to {backup_path}"
            ) from e
        except RuntimeError as e:
            # Re-raise RuntimeError without creating backup
            # This handles format validation errors that should not trigger backup
            raise
        except Exception as e:
            # Create backup before raising exception to prevent data loss
            backup_path = self._create_backup(f"Failed to load todos from {self.path}")
            raise RuntimeError(f"Failed to load todos. Backup saved to {backup_path}") from e

    async def _load_async(self) -> None:
        """Load todos from file asynchronously using aiofiles (Issue #747).

        This is an async version of _load_sync() that uses aiofiles for non-blocking I/O.
        It provides true async file loading without blocking the event loop.

        File read and state update are performed atomically to prevent
        race conditions where the file could change between reading and
        updating internal state.
        """
        import time
        start_time = time.time()
        # Fix for Issue #1502: Use structured logging for monitoring
        logger.debug(
            f"Loading todos from {self.path} (asynchronously)",
            extra={'component': 'storage', 'op': 'load_async'}
        )

        if not self.path.exists():
            self._todos = []
            self._next_id = 1
            self._dirty = False  # Reset dirty flag (Issue #203)
            return

        try:
            # Use compression setting from initialization (Issue #652)
            is_compressed = self.compression

            # Read file asynchronously using aiofiles (Issue #747)
            # This prevents blocking the event loop during file I/O
            async with aiofiles.open(self.path, 'rb') as f:
                # Acquire file lock for multi-process safety (Issue #268)
                self._acquire_file_lock(f)
                try:
                    file_bytes = await f.read()
                    bytes_read = len(file_bytes)  # Track bytes for performance logging (Issue #758)
                finally:
                    self._release_file_lock(f)

            # Extract and verify integrity hash from end of file (Issue #588)
            # Format: \n##INTEGRITY:<hash>##\n
            file_str = file_bytes.decode('utf-8')
            integrity_marker = '##INTEGRITY:'
            marker_start = file_str.rfind(integrity_marker)

            if marker_start != -1:
                # Found integrity marker - extract and verify hash
                marker_end = file_str.find('##', marker_start + len(integrity_marker))
                if marker_end != -1:
                    stored_hash = file_str[marker_start + len(integrity_marker):marker_end]

                    # Calculate hash of the data before the integrity marker
                    # Find the newline before the marker
                    data_end = file_str.rfind('\n', 0, marker_start)
                    if data_end == -1:
                        data_end = 0  # No newline found, use entire content before marker

                    actual_data = file_bytes[:data_end] if data_end > 0 else file_bytes[:marker_start-1]
                    calculated_hash = hashlib.sha256(actual_data).hexdigest()

                    if calculated_hash != stored_hash:
                        # Hash mismatch - data corruption detected
                        backup_path = self._create_backup(
                            f"Integrity hash mismatch in {self.path}: "
                            f"expected {stored_hash}, got {calculated_hash}"
                        )
                        raise RuntimeError(
                            f"Data integrity verification failed. Hash mismatch. "
                            f"Backup saved to {backup_path}"
                        )

                    # Remove integrity marker from data for JSON parsing
                    file_str = file_str[:data_end] if data_end > 0 else file_str[:marker_start-1]
                    file_bytes = file_str.encode('utf-8')

            # Decompress if needed
            if is_compressed:
                file_bytes = gzip.decompress(file_bytes)

            raw_data = json.loads(file_bytes.decode('utf-8'))

            # Validate schema before deserializing (Issue #7)
            # This prevents injection attacks and malformed data from causing crashes
            self._validate_storage_schema(raw_data)

            # Handle both new format (dict with metadata) and old format (list)
            # Schema validation already performed above (Issue #7)
            if isinstance(raw_data, dict):
                # New format with metadata
                todos_data = raw_data.get("todos", [])

                # Verify data integrity using checksum (Issue #223)
                metadata = raw_data.get("metadata", {})
                stored_checksum = metadata.get("checksum")

                if stored_checksum:
                    # Calculate checksum of loaded todos
                    calculated_checksum = None
                    try:
                        # Temporarily deserialize todos for checksum calculation
                        temp_todos = []
                        for item in todos_data:
                            try:
                                temp_todos.append(Todo.from_dict(item))
                            except (ValueError, TypeError, KeyError):
                                pass
                        calculated_checksum = self._calculate_checksum(temp_todos)

                        if calculated_checksum != stored_checksum:
                            # Checksum mismatch - data corruption detected
                            backup_path = self._create_backup(
                                f"Checksum mismatch in {self.path}: "
                                f"expected {stored_checksum}, got {calculated_checksum}"
                            )
                            raise RuntimeError(
                                f"Data integrity check failed. Checksum mismatch. "
                                f"Backup saved to {backup_path}"
                            )
                    except Exception as e:
                        if isinstance(e, RuntimeError):
                            raise
                        # If checksum calculation fails, log warning but continue
                        logger.warning(f"Failed to verify checksum: {e}")

                # Use direct access after validation to ensure type safety (Issue #219)
                # _validate_storage_schema already confirmed next_id is an int if it exists
                next_id = raw_data["next_id"] if "next_id" in raw_data else 1
            elif isinstance(raw_data, list):
                # Old format - backward compatibility
                todos_data = raw_data
                # Calculate next_id from existing todos, safely handling invalid items
                valid_ids = []
                for item in raw_data:
                    if isinstance(item, dict):
                        try:
                            todo = Todo.from_dict(item)
                            valid_ids.append(todo.id)
                        except (ValueError, TypeError, KeyError):
                            # Skip invalid items when calculating next_id
                            pass
                next_id = max(set(valid_ids), default=0) + 1

            # Deserialize todo items inside the lock
            todos = []
            for i, item in enumerate(todos_data):
                try:
                    todo = Todo.from_dict(item)
                    todos.append(todo)
                except (ValueError, TypeError, KeyError) as e:
                    # Skip invalid todo items but continue loading valid ones
                    logger.warning(f"Skipping invalid todo at index {i}: {e}")

            # Validate and repair todos (Issue #632)
            # This checks for duplicate IDs, invalid field types, and attempts auto-repair
            todos = self._validate_and_repair_todos(todos)

            # Update internal state
            self._todos = todos
            self._next_id = next_id
            # Reset dirty flag after successful load (Issue #203)
            self._dirty = False

            # Initialize cache from loaded data if cache is enabled (Issue #742)
            # This ensures cache is available immediately after load, rather than
            # waiting for the first access to rebuild it
            if self._cache_enabled:
                self._update_cache_from_todos()

            # Log successful load completion
            elapsed = time.time() - start_time
            logger.debug(
                f"Load completed in {elapsed:.3f}s ({len(todos)} todos loaded, {bytes_read} bytes read)",
                extra={'duration_ms': elapsed * 1000, 'operation': 'load_sync', 'bytes_read': bytes_read}
            )
        except json.JSONDecodeError as e:
            # Create backup before raising exception to prevent data loss
            backup_path = self._create_backup(f"Invalid JSON in {self.path}")
            # Include detailed error context: line number, column, and position
            # This helps users locate and fix JSON syntax errors manually (Issue #548)
            raise RuntimeError(
                f"Invalid JSON in {self.path}: {e.msg} at line {e.lineno}, column {e.colno}. "
                f"Backup saved to {backup_path}"
            ) from e
        except RuntimeError as e:
            # Re-raise RuntimeError without creating backup
            # This handles format validation errors that should not trigger backup
            raise
        except Exception as e:
            # Create backup before raising exception to prevent data loss
            backup_path = self._create_backup(f"Failed to load todos from {self.path}")
            raise RuntimeError(f"Failed to load todos. Backup saved to {backup_path}") from e

    @retry_transient_errors(max_attempts=3, initial_backoff=0.1)
    @measure_latency("save")
    async def _save(self) -> None:
        """Save todos to file using atomic write asynchronously.

        Uses Copy-on-Write pattern: captures data under lock, releases lock,
        then performs I/O. This minimizes lock contention and prevents blocking
        other operations during file I/O (Issue #582).

        Atomic write implementation (Issue #732):
        Prevents data loss if the application crashes or power fails during write:
        - Writes to temp file (todos.json.{random}.tmp)
        - Calls flush() and fsync() to ensure data is written to disk
        - Uses os.replace() for atomic replacement (POSIX and Windows)
        - This ensures the old file remains intact until the new one is fully ready

        Note on file truncation (Issue #370):
        This implementation uses tempfile.mkstemp() + os.replace() which
        naturally prevents data corruption from size reduction:
        - mkstemp creates a new empty file (no old data remnants possible)
        - os.replace atomically replaces the target file
        This is superior to manual truncation as it's atomic and safer.

        Dry run mode (Issue #987):
        When dry_run is True, skips actual file writes but logs what would have happened.
        """
        import tempfile
        import copy
        import time

        # Issue #987: Skip file writes in dry run mode
        if self.dry_run:
            logger.info(
                f"Dry run mode: Would save {len(self._todos)} todos to {self.path}",
                extra={
                    'structured': True,
                    'event': 'dry_run_save_skipped',
                    'file_path': str(self.path),
                    'todo_count': len(self._todos)
                }
            )
            # Mark as saved to prevent dirty flag from persisting
            self._dirty = False
            return

        start_time = time.time()
        logger.debug(f"Saving {len(self._todos)} todos to {self.path}")

        # Phase 1: Capture data under lock (minimal critical section)
        async with self._async_lock:
            # Deep copy todos to ensure we have a consistent snapshot
            todos_copy = copy.deepcopy(self._todos)
            next_id_copy = self._next_id

        # Phase 2: Serialize and perform I/O OUTSIDE the lock
        # Save with metadata for efficient ID generation and data integrity (Issue #223)
        # Calculate checksum of todos data
        checksum = self._calculate_checksum(todos_copy)
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy,
            "metadata": {
                "checksum": checksum
            }
        }, indent=2)

        # Use compression setting from initialization (Issue #652)
        is_compressed = self.compression

        # Encode data to bytes
        data_bytes = data.encode('utf-8')

        # Compress data if compression is enabled
        if is_compressed:
            data_bytes = gzip.compress(data_bytes, compresslevel=6)

        # Add SHA256 hash at the end for data integrity verification (Issue #588)
        # This helps detect silent data corruption or JSON truncation
        file_hash = hashlib.sha256(data_bytes).hexdigest()
        # Use a special delimiter that won't appear in JSON
        hash_footer = f"\n##INTEGRITY:{file_hash}##\n".encode('utf-8')
        data_bytes_with_hash = data_bytes + hash_footer

        # Write to temporary file first
        # Use random temp file name for async compatibility (Issue #582)
        temp_path = self.path.parent / f"{self.path.name}.{os.urandom(8).hex()}.tmp"

        try:
            # Set strict file permissions (0o600) to prevent unauthorized access
            # This ensures security regardless of umask settings (Issue #179)
            # Apply chmod BEFORE any data is written to prevent race condition (Issue #205)
            logger.debug(f"Writing to temporary file {temp_path}")
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                # chmod failed - re-raise to prevent writing with incorrect permissions (Issue #224)
                raise

            # Write data asynchronously using aiofiles (Issue #582)
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(data_bytes_with_hash)
                await f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

                # Verify SHA256 integrity by reading back data (Issue #1037)
                # This prevents silent data corruption by ensuring what was written
                # matches what was calculated
                await f.seek(0)  # Go back to start of file
                read_back_data = await f.read()

                # Separate the hash footer from the actual data
                hash_footer_start = read_back_data.find(b'##INTEGRITY:')
                if hash_footer_start != -1:
                    hash_footer_end = read_back_data.find(b'##', hash_footer_start + len(b'##INTEGRITY:'))
                    if hash_footer_end != -1:
                        # Extract the stored hash
                        stored_hash = read_back_data[hash_footer_start + len(b'##INTEGRITY:'):hash_footer_end].decode('utf-8').strip()

                        # Calculate hash of the actual data (before footer)
                        actual_data = read_back_data[:hash_footer_start]
                        calculated_hash = hashlib.sha256(actual_data).hexdigest()

                        # Verify integrity - log critical error if mismatch detected
                        if stored_hash != calculated_hash:
                            logger.critical(
                                f"SHA256 integrity verification failed for {temp_path}: "
                                f"expected {stored_hash}, calculated {calculated_hash}. "
                                f"This indicates silent data corruption! Data may be lost.",
                                extra={
                                    'structured': True,
                                    'event': 'integrity_verification_failed',
                                    'file_path': str(temp_path),
                                    'expected_hash': stored_hash,
                                    'calculated_hash': calculated_hash
                                }
                            )
                        else:
                            logger.debug(
                                f"SHA256 integrity verification passed for {temp_path}",
                                extra={
                                    'structured': True,
                                    'event': 'integrity_verification_passed',
                                    'file_path': str(temp_path),
                                    'hash': stored_hash
                                }
                            )

            # Close is handled by the context manager

            # Create backup before replacing if backup_count > 0 (Issue #693)
            # Use async backup rotation to avoid blocking event loop (Issue #747)
            if self.backup_count > 0 and self.path.exists():
                await self._rotate_backups_async()

            # Atomically replace the original file using os.replace (Issue #227)
            # os.replace is atomic on POSIX systems and handles target file existence on Windows
            # Acquire file lock on target file before replacement for multi-process safety (Issue #268)
            # Use aiofiles for async file operations to avoid blocking event loop (Issue #747)
            if self.path.exists():
                async with aiofiles.open(self.path, 'r') as target_file:
                    self._acquire_file_lock(target_file)
                    try:
                        os.replace(temp_path, self.path)
                    finally:
                        self._release_file_lock(target_file)
            else:
                # If target doesn't exist, no need to lock
                os.replace(temp_path, self.path)

            # Invalidate LRU cache on write (Issue #1073)
            # Remove cached entry for this file since it has been modified
            cache_key = str(self.path)
            with self._metadata_cache_lock:
                if cache_key in self._metadata_cache:
                    del self._metadata_cache[cache_key]

            # Log successful save completion
            elapsed = time.time() - start_time
            bytes_written = len(data_bytes_with_hash)  # Track bytes for performance logging (Issue #758)
            logger.debug(
                f"Save completed in {elapsed:.3f}s ({bytes_written} bytes written)",
                extra={'duration_ms': elapsed * 1000, 'operation': 'save', 'bytes_written': bytes_written}
            )
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

    @retry_transient_errors(max_attempts=3, initial_backoff=0.1)
    def _save_with_todos_sync(self, todos: list[Todo]) -> None:
        """Save specified todos to file using atomic write synchronously.

        This is the synchronous version of _save_with_todos for use by
        synchronous methods like add(), update(), add_batch(), etc.

        Uses Copy-on-Write pattern: captures data under lock, releases lock,
        then performs I/O. This minimizes lock contention and prevents blocking
        other operations during file I/O (Issue #582).

        Args:
            todos: The todos list to save. This will become the new internal state.

        Note:
            This method updates self._todos ONLY after successful file write
            to maintain consistency and prevent race conditions (fixes Issue #95, #105, #121).

            File truncation (Issue #370): Uses tempfile + os.replace()
            which naturally prevents data corruption from size reduction by creating
            a new empty file and atomically replacing the target.

            Atomic write operations (Issue #732, #748): Uses "write to temp file + atomic replace"
            pattern to prevent data corruption from crashes or power failures during writes.
            - Writes to todos.json.tmp (with random suffix)
            - Calls flush() and fsync() to ensure data is written to disk
            - Uses os.replace() for atomic replacement (POSIX and Windows)
            - This ensures the old file remains intact until the new one is fully ready
        """
        import copy
        import tempfile
        import time

        start_time = time.time()
        logger.debug(f"Saving {len(todos)} todos to {self.path} (synchronously)")

        # Phase 1: Capture data under lock (minimal critical section)
        # DO NOT update internal state yet - wait until write succeeds
        with self._lock:
            # Deep copy the new todos to ensure we have a consistent snapshot
            todos_copy = copy.deepcopy(todos)
            # Calculate next_id from the todos being saved (fixes Issue #166, #170)
            # This ensures the saved next_id matches the actual max ID in the file
            if todos:
                max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
                next_id_copy = max(max_id + 1, self._next_id)
            else:
                # Preserve current next_id when todos list is empty (fixes Issue #175)
                # This prevents ID conflicts by not resetting to 1
                next_id_copy = self._next_id

        # Phase 2: Serialize and perform I/O OUTSIDE the lock
        # Save with metadata for efficient ID generation and data integrity (Issue #223)
        # Calculate checksum of todos data
        checksum = self._calculate_checksum(todos_copy)
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy,
            "metadata": {
                "checksum": checksum
            }
        }, indent=2)

        # Use compression setting from initialization (Issue #652)
        is_compressed = self.compression

        # Encode data to bytes
        data_bytes = data.encode('utf-8')

        # Compress data if compression is enabled
        if is_compressed:
            data_bytes = gzip.compress(data_bytes, compresslevel=6)

        # Add SHA256 hash at the end for data integrity verification (Issue #588)
        # This helps detect silent data corruption or JSON truncation
        file_hash = hashlib.sha256(data_bytes).hexdigest()
        # Use a special delimiter that won't appear in JSON
        hash_footer = f"\n##INTEGRITY:{file_hash}##\n".encode('utf-8')
        data_bytes_with_hash = data_bytes + hash_footer

        # Write to temporary file first (Issue #748: Transaction support)
        # Use random temp file name for atomicity
        temp_path = self.path.parent / f"{self.path.name}.{os.urandom(8).hex()}.tmp"

        try:
            # Set strict file permissions (0o600) to prevent unauthorized access
            # This ensures security regardless of umask settings (Issue #179)
            # Apply chmod BEFORE any data is written to prevent race condition (Issue #205)
            logger.debug(f"Writing to temporary file {temp_path}")
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                # chmod failed - re-raise to prevent writing with incorrect permissions (Issue #224)
                raise

            # Write data synchronously (Issue #748: uses temp file for transaction safety)
            with temp_path.open('wb') as f:
                f.write(data_bytes_with_hash)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

                # Verify SHA256 integrity by reading back data (Issue #1037)
                # This prevents silent data corruption by ensuring what was written
                # matches what was calculated
                f.seek(0)  # Go back to start of file
                read_back_data = f.read()

                # Separate the hash footer from the actual data
                hash_footer_start = read_back_data.find(b'##INTEGRITY:')
                if hash_footer_start != -1:
                    hash_footer_end = read_back_data.find(b'##', hash_footer_start + len(b'##INTEGRITY:'))
                    if hash_footer_end != -1:
                        # Extract the stored hash
                        stored_hash = read_back_data[hash_footer_start + len(b'##INTEGRITY:'):hash_footer_end].decode('utf-8').strip()

                        # Calculate hash of the actual data (before footer)
                        actual_data = read_back_data[:hash_footer_start]
                        calculated_hash = hashlib.sha256(actual_data).hexdigest()

                        # Verify integrity - log critical error if mismatch detected
                        if stored_hash != calculated_hash:
                            logger.critical(
                                f"SHA256 integrity verification failed for {temp_path}: "
                                f"expected {stored_hash}, calculated {calculated_hash}. "
                                f"This indicates silent data corruption! Data may be lost.",
                                extra={
                                    'structured': True,
                                    'event': 'integrity_verification_failed',
                                    'file_path': str(temp_path),
                                    'expected_hash': stored_hash,
                                    'calculated_hash': calculated_hash
                                }
                            )
                        else:
                            logger.debug(
                                f"SHA256 integrity verification passed for {temp_path}",
                                extra={
                                    'structured': True,
                                    'event': 'integrity_verification_passed',
                                    'file_path': str(temp_path),
                                    'hash': stored_hash
                                }
                            )

            # Create backup before replacing if backup_count > 0 (Issue #693)
            # Use async backup rotation to avoid blocking event loop (Issue #747)
            if self.backup_count > 0 and self.path.exists():
                await self._rotate_backups_async()

            # Atomically replace the original file using os.replace (Issue #227, #748)
            # os.replace is atomic on POSIX systems and handles target file existence on Windows
            # This provides transaction support: either all data is written or none (Issue #748)
            # Acquire file lock on target file before replacement for multi-process safety (Issue #268)
            if self.path.exists():
                with self.path.open('r') as target_file:
                    self._acquire_file_lock(target_file)
                    try:
                        os.replace(temp_path, self.path)
                    finally:
                        self._release_file_lock(target_file)
            else:
                # If target doesn't exist, no need to lock
                os.replace(temp_path, self.path)

            # Invalidate LRU cache on write (Issue #1073)
            # Remove cached entry for this file since it has been modified
            cache_key = str(self.path)
            with self._metadata_cache_lock:
                if cache_key in self._metadata_cache:
                    del self._metadata_cache[cache_key]

            # Phase 3: Update internal state ONLY after successful write
            # This ensures consistency between memory and disk (fixes Issue #121, #150)
            with self._lock:
                # Use the original todos parameter to update internal state (fixes Issue #150)
                # Deep copy to prevent external modifications from affecting internal state
                self._todos = copy.deepcopy(todos)
                # Recalculate _next_id to maintain consistency (fixes Issue #101)
                # If the new todos contain higher IDs than current _next_id, update it
                if todos:
                    max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
                    if max_id >= self._next_id:
                        self._next_id = max_id + 1
                # Mark as clean after successful save (Issue #203)
                self._dirty = False
                # Update last saved time for auto-save functionality (Issue #547)
                self.last_saved_time = time.time()

            # Log successful save completion
            elapsed = time.time() - start_time
            bytes_written = len(data_bytes_with_hash)  # Track bytes for performance logging (Issue #758)
            logger.debug(
                f"Save completed in {elapsed:.3f}s ({bytes_written} bytes written)",
                extra={'duration_ms': elapsed * 1000, 'operation': 'save', 'bytes_written': bytes_written}
            )
        except Exception:
            # Clean up temp file on error (Issue #748: ensure no partial writes remain)
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

    @retry_transient_errors(max_attempts=3, initial_backoff=0.1)
    async def _save_with_todos(self, todos: list[Todo]) -> None:
        """Save specified todos to file using atomic write asynchronously.

        Uses Copy-on-Write pattern: captures data under lock, releases lock,
        then performs I/O. This minimizes lock contention and prevents blocking
        other operations during file I/O (Issue #582).

        Args:
            todos: The todos list to save. This will become the new internal state.

        Note:
            This method updates self._todos ONLY after successful file write
            to maintain consistency and prevent race conditions (fixes Issue #95, #105, #121).

            File truncation (Issue #370): Uses aiofiles + os.replace()
            which naturally prevents data corruption from size reduction by creating
            a new empty file and atomically replacing the target.
        """
        import copy
        import time

        start_time = time.time()
        logger.debug(f"Saving {len(todos)} todos to {self.path} (asynchronously)")

        # Phase 1: Capture data under lock (minimal critical section)
        # DO NOT update internal state yet - wait until write succeeds
        async with self._async_lock:
            # Deep copy the new todos to ensure we have a consistent snapshot
            todos_copy = copy.deepcopy(todos)
            # Calculate next_id from the todos being saved (fixes Issue #166, #170)
            # This ensures the saved next_id matches the actual max ID in the file
            if todos:
                max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
                next_id_copy = max(max_id + 1, self._next_id)
            else:
                # Preserve current next_id when todos list is empty (fixes Issue #175)
                # This prevents ID conflicts by not resetting to 1
                next_id_copy = self._next_id

        # Phase 2: Serialize and perform I/O OUTSIDE the lock
        # Save with metadata for efficient ID generation and data integrity (Issue #223)
        # Calculate checksum of todos data
        checksum = self._calculate_checksum(todos_copy)
        data = json.dumps({
            "todos": [t.to_dict() for t in todos_copy],
            "next_id": next_id_copy,
            "metadata": {
                "checksum": checksum
            }
        }, indent=2)

        # Use compression setting from initialization (Issue #652)
        is_compressed = self.compression

        # Encode data to bytes
        data_bytes = data.encode('utf-8')

        # Compress data if compression is enabled
        if is_compressed:
            data_bytes = gzip.compress(data_bytes, compresslevel=6)

        # Add SHA256 hash at the end for data integrity verification (Issue #588)
        # This helps detect silent data corruption or JSON truncation
        file_hash = hashlib.sha256(data_bytes).hexdigest()
        # Use a special delimiter that won't appear in JSON
        hash_footer = f"\n##INTEGRITY:{file_hash}##\n".encode('utf-8')
        data_bytes_with_hash = data_bytes + hash_footer

        # Write to temporary file first
        # Use random temp file name for async compatibility (Issue #582)
        temp_path = self.path.parent / f"{self.path.name}.{os.urandom(8).hex()}.tmp"

        try:
            # Set strict file permissions (0o600) to prevent unauthorized access
            # This ensures security regardless of umask settings (Issue #179)
            # Apply chmod BEFORE any data is written to prevent race condition (Issue #205)
            logger.debug(f"Writing to temporary file {temp_path}")
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                # chmod failed - re-raise to prevent writing with incorrect permissions (Issue #224)
                raise

            # Write data asynchronously using aiofiles (Issue #582)
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(data_bytes_with_hash)
                await f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

                # Verify SHA256 integrity by reading back data (Issue #1037)
                # This prevents silent data corruption by ensuring what was written
                # matches what was calculated
                await f.seek(0)  # Go back to start of file
                read_back_data = await f.read()

                # Separate the hash footer from the actual data
                hash_footer_start = read_back_data.find(b'##INTEGRITY:')
                if hash_footer_start != -1:
                    hash_footer_end = read_back_data.find(b'##', hash_footer_start + len(b'##INTEGRITY:'))
                    if hash_footer_end != -1:
                        # Extract the stored hash
                        stored_hash = read_back_data[hash_footer_start + len(b'##INTEGRITY:'):hash_footer_end].decode('utf-8').strip()

                        # Calculate hash of the actual data (before footer)
                        actual_data = read_back_data[:hash_footer_start]
                        calculated_hash = hashlib.sha256(actual_data).hexdigest()

                        # Verify integrity - log critical error if mismatch detected
                        if stored_hash != calculated_hash:
                            logger.critical(
                                f"SHA256 integrity verification failed for {temp_path}: "
                                f"expected {stored_hash}, calculated {calculated_hash}. "
                                f"This indicates silent data corruption! Data may be lost.",
                                extra={
                                    'structured': True,
                                    'event': 'integrity_verification_failed',
                                    'file_path': str(temp_path),
                                    'expected_hash': stored_hash,
                                    'calculated_hash': calculated_hash
                                }
                            )
                        else:
                            logger.debug(
                                f"SHA256 integrity verification passed for {temp_path}",
                                extra={
                                    'structured': True,
                                    'event': 'integrity_verification_passed',
                                    'file_path': str(temp_path),
                                    'hash': stored_hash
                                }
                            )

            # Close is handled by the context manager

            # Create backup before replacing if backup_count > 0 (Issue #693)
            # Use async backup rotation to avoid blocking event loop (Issue #747)
            if self.backup_count > 0 and self.path.exists():
                await self._rotate_backups_async()

            # Atomically replace the original file using os.replace (Issue #227)
            # os.replace is atomic on POSIX systems and handles target file existence on Windows
            # Acquire file lock on target file before replacement for multi-process safety (Issue #268)
            # Use aiofiles for async file operations to avoid blocking event loop (Issue #747)
            if self.path.exists():
                async with aiofiles.open(self.path, 'r') as target_file:
                    self._acquire_file_lock(target_file)
                    try:
                        os.replace(temp_path, self.path)
                    finally:
                        self._release_file_lock(target_file)
            else:
                # If target doesn't exist, no need to lock
                os.replace(temp_path, self.path)

            # Invalidate LRU cache on write (Issue #1073)
            # Remove cached entry for this file since it has been modified
            cache_key = str(self.path)
            with self._metadata_cache_lock:
                if cache_key in self._metadata_cache:
                    del self._metadata_cache[cache_key]

            # Phase 3: Update internal state ONLY after successful write
            # This ensures consistency between memory and disk (fixes Issue #121, #150)
            with self._lock:
                # Use the original todos parameter to update internal state (fixes Issue #150)
                # Deep copy to prevent external modifications from affecting internal state
                import copy
                self._todos = copy.deepcopy(todos)
                # Recalculate _next_id to maintain consistency (fixes Issue #101)
                # If the new todos contain higher IDs than current _next_id, update it
                if todos:
                    max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
                    if max_id >= self._next_id:
                        self._next_id = max_id + 1
                # Mark as clean after successful save (Issue #203)
                self._dirty = False
                # Update last saved time for auto-save functionality (Issue #547)
                self.last_saved_time = time.time()

            # Log successful save completion
            elapsed = time.time() - start_time
            bytes_written = len(data_bytes_with_hash)  # Track bytes for performance logging (Issue #758)
            logger.debug(
                f"Save completed in {elapsed:.3f}s ({bytes_written} bytes written)",
                extra={'duration_ms': elapsed * 1000, 'operation': 'save', 'bytes_written': bytes_written}
            )
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

    def add(self, todo: Todo, dry_run: bool = False) -> Todo:
        """Add a new todo with atomic ID generation.

        Args:
            todo: The Todo object to add.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1503).

        Raises:
            ValueError: If a todo with the same ID already exists.
        """
        with self._lock:
            # Dry run mode: log the intended action and return success without writing to disk (Issue #1503)
            if dry_run:
                logger.info(f"[DRY RUN] Would add todo: {todo}")
                # Return a todo with generated ID for consistency, without modifying storage
                if todo.id is None:
                    todo = Todo(id=self._next_id, title=todo.title, status=todo.status)
                return todo

            # Capture the ID from the todo atomically to prevent race conditions
            # Even if another thread modifies todo.id after this check, we use the captured value
            todo_id = todo.id

            # Check for duplicate ID FIRST, before any other logic
            # This prevents race conditions when todo.id is set externally
            if todo_id is not None:
                # Direct iteration to avoid reentrant lock acquisition
                # (self.get() would acquire the lock again while we already hold it)
                for existing_todo in self._todos:
                    if existing_todo.id == todo_id:
                        # Todo with this ID already exists - raise an error
                        # The caller should use update() instead for existing todos
                        raise ValueError(f"Todo with ID {todo_id} already exists. Use update() instead.")

            # If todo doesn't have an ID, generate one atomically
            # Inline the ID generation logic to ensure atomicity with insertion
            if todo_id is None:
                # Use _next_id for O(1) ID generation instead of max() which is O(N)
                # Capture the ID but DON'T increment self._next_id yet
                # The increment will happen in _save_with_todos after successful write
                # This prevents state inconsistency if save fails (fixes Issue #9)
                todo_id = self._next_id
                # Create a new todo with the generated ID
                todo = Todo(id=todo_id, title=todo.title, status=todo.status)
            # Note: For external IDs, _next_id will be updated in _save_with_todos
            # to maintain consistency (fixes Issue #9)

            # Create a copy of todos list with the new todo
            new_todos = self._todos + [todo]
            # Mark as dirty since we're modifying the data (Issue #203)
            self._dirty = True
            # Mark cache as dirty when data changes (Issue #703)
            if self._cache_enabled:
                self._cache_dirty = True
            # Save and update internal state atomically
            # _save_with_todos_sync will update self._todos and self._next_id
            # only after successful write (fixes Issue #9)
            self._save_with_todos_sync(new_todos)
            # Update cache immediately after successful write (write-through cache, Issue #718)
            if self._cache_enabled and todo.id is not None:
                self._cache[todo.id] = todo
                self._cache_dirty = False
            # Check if auto-save should be triggered (Issue #547)
            self._check_auto_save()
            return todo

    def list(self, status: str | None = None) -> list[Todo]:
        """List all todos."""
        with self._lock:
            # Rebuild cache from _todos if cache is dirty or not yet populated (Issue #718)
            if self._cache_enabled:
                self._update_cache_from_todos()

            if status:
                return [t for t in self._todos if t.status == status]
            return list(self._todos)  # Return a copy to prevent external modification

    def get(self, todo_id: int) -> Todo | None:
        """Get a todo by ID."""
        with self._lock:
            # Rebuild cache from _todos if cache is dirty or not yet populated (Issue #718)
            if self._cache_enabled:
                self._update_cache_from_todos()
                # Use cache for O(1) lookup
                result = self._cache.get(todo_id)
                if result is not None:
                    logger.debug(f"Cache HIT for todo_id={todo_id}")
                else:
                    logger.debug(f"Cache MISS for todo_id={todo_id}")
                return result

            # Fallback to linear search when cache is disabled
            for todo in self._todos:
                if todo.id == todo_id:
                    return todo
            return None

    def update(self, todo: Todo, dry_run: bool = False) -> Todo | None:
        """Update a todo.

        Args:
            todo: The Todo object with updated fields.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1503).
        """
        with self._lock:
            # Dry run mode: log the intended action and return success without writing to disk (Issue #1503)
            if dry_run:
                logger.info(f"[DRY RUN] Would update todo: {todo}")
                # Return the todo to simulate success, without modifying storage
                return todo

            for i, t in enumerate(self._todos):
                if t.id == todo.id:
                    # Create a copy of todos list with the updated todo
                    new_todos = self._todos.copy()
                    new_todos[i] = todo
                    # Mark as dirty since we're modifying the data (Issue #203)
                    self._dirty = True
                    # Mark cache as dirty when data changes (Issue #703)
                    if self._cache_enabled:
                        self._cache_dirty = True
                    # Save and update internal state atomically
                    self._save_with_todos_sync(new_todos)
                    # Update cache immediately after successful write (write-through cache, Issue #718)
                    if self._cache_enabled and todo.id is not None:
                        self._cache[todo.id] = todo
                        self._cache_dirty = False
                    # Check if auto-save should be triggered (Issue #547)
                    self._check_auto_save()
                    return todo
            return None

    def delete(self, todo_id: int, dry_run: bool = False) -> bool:
        """Delete a todo.

        Args:
            todo_id: The ID of the todo to delete.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1503). Can also be enabled globally
                    via DRY_RUN_STORAGE=1 environment variable (Issue #1628).
        """
        # Check environment variable for global dry_run mode (Issue #1628)
        env_dry_run = os.environ.get('DRY_RUN_STORAGE', '0').strip() in ('1', 'true', 'yes', 'on')
        effective_dry_run = dry_run or env_dry_run

        with self._lock:
            # Dry run mode: log the intended action and return success without writing to disk (Issue #1503, #1628)
            if effective_dry_run:
                logger.info(f"[DRY RUN] Would delete todo with id: {todo_id}")
                # Return True to simulate successful deletion, without modifying storage
                return True

            for i, t in enumerate(self._todos):
                if t.id == todo_id:
                    # Create a copy of todos list without the deleted todo
                    new_todos = self._todos[:i] + self._todos[i+1:]
                    # Mark as dirty since we're modifying the data (Issue #203)
                    self._dirty = True
                    # Mark cache as dirty when data changes (Issue #703)
                    if self._cache_enabled:
                        self._cache_dirty = True
                    # Save and update internal state atomically
                    self._save_with_todos_sync(new_todos)
                    # Update cache immediately after successful write (write-through cache, Issue #718)
                    if self._cache_enabled:
                        self._cache.pop(todo_id, None)
                        self._cache_dirty = False

                    # Check if automatic file compaction should be triggered (Issue #683)
                    # Calculate the ratio of deleted items to total items
                    total_count = len(self._todos) + 1  # +1 because we just deleted one
                    deleted_count = 1  # Count of items deleted in this operation
                    deleted_ratio = deleted_count / total_count if total_count > 0 else 0

                    # If deleted ratio exceeds threshold, trigger background save for compaction
                    if deleted_ratio > self.COMPACTION_THRESHOLD:
                        # Trigger auto-save to rewrite file without deleted items
                        self._check_auto_save()

                    return True
            return False

    def get_next_id(self) -> int:
        """Get next available ID."""
        with self._lock:
            return self._next_id

    def add_batch(self, todos: list[Todo]) -> list[Todo]:
        """Add multiple todos in a single batch operation.

        This is more efficient than calling add() multiple times as it
        reduces disk I/O operations by only triggering auto-save once
        after all todos are added.

        Transactional behavior (Issue #763): This operation is atomic.
        If the save fails, no todos are added and next_id is not modified.
        Either all todos are committed, or none are.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        if not todos:
            return []

        with self._lock:
            # Capture current state for validation
            max_id = self._next_id
            existing_ids = {t.id for t in self._todos}

            # First pass: validate no duplicate IDs and track max ID
            for todo in todos:
                todo_id = todo.id

                # Check for duplicate ID
                if todo_id is not None:
                    if todo_id in existing_ids:
                        raise ValueError(
                            f"Todo with ID {todo_id} already exists. Use update() instead."
                        )
                    # Track max ID for _next_id update (Issue #763)
                    if todo_id >= max_id:
                        max_id = todo_id + 1

            # Second pass: generate IDs for todos without them
            # IMPORTANT: Don't modify self._next_id yet (Issue #763)
            # Only calculate what IDs should be used. _save_with_todos_sync
            # will update self._next_id after successful save.
            new_todos_list = []
            next_id_candidate = self._next_id
            for todo in todos:
                if todo.id is None:
                    # Calculate ID but don't increment self._next_id yet
                    todo_id = next_id_candidate
                    next_id_candidate += 1
                    new_todo = Todo(id=todo_id, title=todo.title, status=todo.status)
                    new_todos_list.append(new_todo)
                else:
                    new_todos_list.append(todo)

            # Combine existing and new todos
            combined_todos = self._todos + new_todos_list

            # Mark as dirty and save once for all todos
            self._dirty = True
            # Mark cache as dirty when data changes (Issue #703)
            if self._cache_enabled:
                self._cache_dirty = True

            # Transactional save (Issue #763): _save_with_todos_sync will:
            # 1. Write to temp file
            # 2. Atomic replace
            # 3. Update self._todos and self._next_id ONLY on success
            # If save fails, self._next_id remains unchanged
            self._save_with_todos_sync(combined_todos)

            # Check auto-save once after all additions
            self._check_auto_save()

            return new_todos_list

    def update_batch(self, todos: list[Todo]) -> list[Todo]:
        """Update multiple todos in a single batch operation.

        This is more efficient than calling update() multiple times as it
        reduces disk I/O operations by only triggering auto-save once
        after all todos are updated.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        if not todos:
            return []

        with self._lock:
            updated_todos = []
            new_todos = self._todos.copy()
            todo_indices = {}  # Map todo_id to index in new_todos

            # Build index of existing todos
            for i, todo in enumerate(new_todos):
                todo_indices[todo.id] = i

            # Update todos that exist
            for todo in todos:
                if todo.id in todo_indices:
                    idx = todo_indices[todo.id]
                    new_todos[idx] = todo
                    updated_todos.append(todo)

            # Only save if we actually updated something
            if updated_todos:
                self._dirty = True
                # Mark cache as dirty when data changes (Issue #703)
                if self._cache_enabled:
                    self._cache_dirty = True
                self._save_with_todos_sync(new_todos)
                self._check_auto_save()

            return updated_todos

    def delete_batch(self, todo_ids: list[int], dry_run: bool = False) -> list[bool]:
        """Delete multiple todos in a single batch operation.

        This is more efficient than calling delete() multiple times as it
        reduces disk I/O operations by only triggering auto-save once
        after all todos are deleted.

        Transactional behavior (Issue #763): This operation is atomic.
        If the save fails, no todos are deleted.

        Args:
            todo_ids: List of todo IDs to delete.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1628). Can also be enabled globally
                    via DRY_RUN_STORAGE=1 environment variable.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        if not todo_ids:
            return []

        # Check environment variable for global dry_run mode (Issue #1628)
        env_dry_run = os.environ.get('DRY_RUN_STORAGE', '0').strip() in ('1', 'true', 'yes', 'on')
        effective_dry_run = dry_run or env_dry_run

        with self._lock:
            # Track which IDs were found and deleted
            results = []
            ids_to_delete = set()
            indices_to_delete = []

            # Find indices of todos to delete
            for i, todo in enumerate(self._todos):
                if todo.id in todo_ids:
                    ids_to_delete.add(todo.id)
                    indices_to_delete.append(i)

            # Create result list in the same order as input
            for todo_id in todo_ids:
                results.append(todo_id in ids_to_delete)

            # Dry run mode: log the intended action and return success without writing to disk (Issue #1628)
            if effective_dry_run:
                logger.info(f"[DRY RUN] Would delete todos with ids: {list(ids_to_delete)}")
                # Return results to simulate successful deletion, without modifying storage
                return results

            # Only save if we actually found something to delete
            if indices_to_delete:
                # Create new list without deleted todos
                # Sort indices in descending order to delete from end to start
                indices_to_delete.sort(reverse=True)
                new_todos = self._todos.copy()
                for idx in indices_to_delete:
                    del new_todos[idx]

                # Mark as dirty and save once for all deletions
                self._dirty = True
                # Mark cache as dirty when data changes (Issue #703)
                if self._cache_enabled:
                    self._cache_dirty = True
                self._save_with_todos_sync(new_todos)

                # Update cache immediately after successful write (write-through cache, Issue #718)
                if self._cache_enabled:
                    for todo_id in ids_to_delete:
                        self._cache.pop(todo_id, None)
                    self._cache_dirty = False

                # Check if auto-save should be triggered (Issue #547)
                self._check_auto_save()

            return results

    def bulk_add(self, todos: list[Todo]) -> list[Todo]:
        """Add multiple todos in a single bulk operation.

        This is an alias for add_batch() for consistency with bulk naming.
        See add_batch() for full documentation.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        return self.add_batch(todos)

    def bulk_delete(self, todo_ids: list[int]) -> int:
        """Delete multiple todos in a single bulk operation.

        This is a convenience wrapper around delete_batch() that returns
        the count of deleted todos instead of a list of boolean results.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            The number of todos that were successfully deleted.
        """
        results = self.delete_batch(todo_ids)
        return sum(1 for r in results if r)

    # Async public methods (Issue #702)
    async def async_add(self, todo: Todo) -> Todo:
        """Asynchronously add a new todo with atomic ID generation.

        This is the async version of add(). Uses asyncio.Lock instead of
        threading.Lock and async I/O operations for better performance
        in async contexts.

        Args:
            todo: The Todo object to add.

        Returns:
            The added Todo with generated ID.

        Raises:
            ValueError: If a todo with the same ID already exists.
        """
        async with self._async_lock:
            # Capture the ID from the todo atomically to prevent race conditions
            todo_id = todo.id

            # Check for duplicate ID FIRST, before any other logic
            if todo_id is not None:
                # Direct iteration to avoid reentrant lock acquisition
                for existing_todo in self._todos:
                    if existing_todo.id == todo_id:
                        raise ValueError(
                            f"Todo with ID {todo_id} already exists. Use update() instead."
                        )

            # Generate ID if not provided
            if todo_id is None:
                todo_id = self._next_id
                todo = Todo(id=todo_id, title=todo.title, status=todo.status)

            # Create a copy of todos list with the new todo
            new_todos = self._todos + [todo]
            # Mark as dirty since we're modifying the data (Issue #203)
            self._dirty = True
            # Mark cache as dirty when data changes (Issue #703)
            if self._cache_enabled:
                self._cache_dirty = True

            # Save asynchronously using _save_with_todos
            await self._save_with_todos(new_todos)

            # Check if auto-save should be triggered (Issue #547)
            self._check_auto_save()
            return todo

    async def async_list(self, status: str | None = None) -> list[Todo]:
        """Asynchronously list all todos, optionally filtered by status.

        This is the async version of list(). Returns a copy to prevent
        external modification.

        Args:
            status: Optional status filter ('pending', 'completed', etc.).

        Returns:
            List of Todo objects.
        """
        async with self._async_lock:
            if status:
                return [t for t in self._todos if t.status == status]
            return list(self._todos)  # Return a copy to prevent external modification

    async def async_get(self, todo_id: int) -> Todo | None:
        """Asynchronously get a todo by ID.

        This is the async version of get().

        Args:
            todo_id: The ID of the todo to retrieve.

        Returns:
            The Todo object if found, None otherwise.
        """
        async with self._async_lock:
            for todo in self._todos:
                if todo.id == todo_id:
                    return todo
            return None

    async def async_update(self, todo: Todo) -> Todo | None:
        """Asynchronously update a todo.

        This is the async version of update().

        Args:
            todo: The Todo object with updated fields.

        Returns:
            The updated Todo if found, None otherwise.
        """
        async with self._async_lock:
            for i, t in enumerate(self._todos):
                if t.id == todo.id:
                    # Create a copy of todos list with the updated todo
                    new_todos = self._todos.copy()
                    new_todos[i] = todo
                    # Mark as dirty since we're modifying the data (Issue #203)
                    self._dirty = True
                    # Mark cache as dirty when data changes (Issue #703)
                    if self._cache_enabled:
                        self._cache_dirty = True
                    # Save asynchronously using _save_with_todos
                    await self._save_with_todos(new_todos)
                    # Check if auto-save should be triggered (Issue #547)
                    self._check_auto_save()
                    return todo
            return None

    async def async_delete(self, todo_id: int) -> bool:
        """Asynchronously delete a todo by ID.

        This is the async version of delete().

        Args:
            todo_id: The ID of the todo to delete.

        Returns:
            True if deleted, False if not found.
        """
        async with self._async_lock:
            for i, t in enumerate(self._todos):
                if t.id == todo_id:
                    # Create a copy of todos list without the deleted todo
                    new_todos = self._todos[:i] + self._todos[i+1:]
                    # Mark as dirty since we're modifying the data (Issue #203)
                    self._dirty = True
                    # Mark cache as dirty when data changes (Issue #703)
                    if self._cache_enabled:
                        self._cache_dirty = True
                    # Save asynchronously using _save_with_todos
                    await self._save_with_todos(new_todos)

                    # Check if automatic file compaction should be triggered (Issue #683)
                    # Calculate the ratio of deleted items to total items
                    total_count = len(self._todos) + 1  # +1 because we just deleted one
                    deleted_count = 1  # Count of items deleted in this operation
                    deleted_ratio = deleted_count / total_count if total_count > 0 else 0

                    # If deleted ratio exceeds threshold, trigger background save for compaction
                    if deleted_ratio > self.COMPACTION_THRESHOLD:
                        # Trigger auto-save to rewrite file without deleted items
                        self._check_auto_save()

                    return True
            return False

    async def async_add_batch(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously add multiple todos in a single batch operation.

        This is the async version of add_batch. It provides the same benefits
        of reduced disk I/O operations but in a non-blocking manner.

        Transactional behavior (Issue #763): This operation is atomic.
        If the save fails, no todos are added and next_id is not modified.
        Either all todos are committed, or none are.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        if not todos:
            return []

        async with self._async_lock:
            # Capture current state for validation
            max_id = self._next_id
            existing_ids = {t.id for t in self._todos}

            # First pass: validate no duplicate IDs and track max ID
            for todo in todos:
                todo_id = todo.id

                # Check for duplicate ID
                if todo_id is not None:
                    if todo_id in existing_ids:
                        raise ValueError(
                            f"Todo with ID {todo_id} already exists. Use update() instead."
                        )
                    # Track max ID for _next_id update (Issue #763)
                    if todo_id >= max_id:
                        max_id = todo_id + 1

            # Second pass: generate IDs for todos without them
            # IMPORTANT: Don't modify self._next_id yet (Issue #763)
            # Only calculate what IDs should be used. _save_with_todos
            # will update self._next_id after successful save.
            new_todos_list = []
            next_id_candidate = self._next_id
            for todo in todos:
                if todo.id is None:
                    # Calculate ID but don't increment self._next_id yet
                    todo_id = next_id_candidate
                    next_id_candidate += 1
                    new_todo = Todo(id=todo_id, title=todo.title, status=todo.status)
                    new_todos_list.append(new_todo)
                else:
                    new_todos_list.append(todo)

            # Combine existing and new todos
            combined_todos = self._todos + new_todos_list

            # Mark as dirty and save once for all todos
            self._dirty = True
            # Mark cache as dirty when data changes (Issue #703)
            if self._cache_enabled:
                self._cache_dirty = True

            # Transactional save (Issue #763): _save_with_todos will:
            # 1. Write to temp file
            # 2. Atomic replace
            # 3. Update self._todos and self._next_id ONLY on success
            # If save fails, self._next_id remains unchanged
            await self._save_with_todos(combined_todos)

            # Check auto-save once after all additions
            self._check_auto_save()

            return new_todos_list

    async def async_update_batch(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously update multiple todos in a single batch operation.

        This is the async version of update_batch. It provides the same benefits
        of reduced disk I/O operations but in a non-blocking manner.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        if not todos:
            return []

        async with self._async_lock:
            updated_todos = []
            new_todos = self._todos.copy()
            todo_indices = {}  # Map todo_id to index in new_todos

            # Build index of existing todos
            for i, todo in enumerate(new_todos):
                todo_indices[todo.id] = i

            # Update todos that exist
            for todo in todos:
                if todo.id in todo_indices:
                    idx = todo_indices[todo.id]
                    new_todos[idx] = todo
                    updated_todos.append(todo)

            # Only save if we actually updated something
            if updated_todos:
                self._dirty = True
                # Mark cache as dirty when data changes (Issue #703)
                if self._cache_enabled:
                    self._cache_dirty = True
                await self._save_with_todos(new_todos)
                self._check_auto_save()

            return updated_todos

    async def async_delete_batch(self, todo_ids: list[int]) -> list[bool]:
        """Asynchronously delete multiple todos in a single batch operation.

        This is the async version of delete_batch. It provides the same benefits
        of reduced disk I/O operations but in a non-blocking manner.

        Transactional behavior (Issue #763): This operation is atomic.
        If the save fails, no todos are deleted.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        if not todo_ids:
            return []

        async with self._async_lock:
            # Track which IDs were found and deleted
            results = []
            ids_to_delete = set()
            indices_to_delete = []

            # Find indices of todos to delete
            for i, todo in enumerate(self._todos):
                if todo.id in todo_ids:
                    ids_to_delete.add(todo.id)
                    indices_to_delete.append(i)

            # Create result list in the same order as input
            for todo_id in todo_ids:
                results.append(todo_id in ids_to_delete)

            # Only save if we actually found something to delete
            if indices_to_delete:
                # Create new list without deleted todos
                # Sort indices in descending order to delete from end to start
                indices_to_delete.sort(reverse=True)
                new_todos = self._todos.copy()
                for idx in indices_to_delete:
                    del new_todos[idx]

                # Mark as dirty and save once for all deletions
                self._dirty = True
                # Mark cache as dirty when data changes (Issue #703)
                if self._cache_enabled:
                    self._cache_dirty = True
                await self._save_with_todos(new_todos)

                # Update cache immediately after successful write (write-through cache, Issue #718)
                if self._cache_enabled:
                    for todo_id in ids_to_delete:
                        self._cache.pop(todo_id, None)
                    self._cache_dirty = False

                # Check if auto-save should be triggered (Issue #547)
                self._check_auto_save()

            return results

    # Bulk operation aliases (Issue #858)
    def add_many(self, todos: list[Todo]) -> list[Todo]:
        """Add multiple todos (alias for add_batch).

        This is a convenience alias for add_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        return self.add_batch(todos)

    def update_many(self, todos: list[Todo]) -> list[Todo]:
        """Update multiple todos (alias for update_batch).

        This is a convenience alias for update_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        return self.update_batch(todos)

    def delete_many(self, todo_ids: list[int], dry_run: bool = False) -> list[bool]:
        """Delete multiple todos (alias for delete_batch).

        This is a convenience alias for delete_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todo_ids: List of todo IDs to delete.
            dry_run: If True, log the intended action and return success without
                    writing to disk (Issue #1628). Can also be enabled globally
                    via DRY_RUN_STORAGE=1 environment variable.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        return self.delete_batch(todo_ids, dry_run=dry_run)

    async def async_add_many(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously add multiple todos (alias for async_add_batch).

        This is a convenience alias for async_add_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects to add.

        Returns:
            List of added Todo objects with generated IDs populated.
        """
        return await self.async_add_batch(todos)

    async def async_update_many(self, todos: list[Todo]) -> list[Todo]:
        """Asynchronously update multiple todos (alias for async_update_batch).

        This is a convenience alias for async_update_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todos: List of Todo objects with updated fields.

        Returns:
            List of successfully updated Todo objects.
        """
        return await self.async_update_batch(todos)

    async def async_delete_many(self, todo_ids: list[int]) -> list[bool]:
        """Asynchronously delete multiple todos (alias for async_delete_batch).

        This is a convenience alias for async_delete_batch() for users who prefer
        the 'many' naming convention over 'batch'.

        Args:
            todo_ids: List of todo IDs to delete.

        Returns:
            List of boolean values indicating whether each todo was deleted.
            True if deleted, False if not found.
        """
        return await self.async_delete_batch(todo_ids)

    def _update_cache_from_todos(self) -> None:
        """Update cache from _todos list (Issue #718).

        This method rebuilds the cache from the current _todos list if the cache is dirty
        or if the file has been modified externally. It's called automatically by get() and list()
        operations when cache is enabled.
        """
        # Check if file has been modified externally
        if self._cache_mtime is not None and self.path.exists():
            current_mtime = os.path.getmtime(self.path)
            if current_mtime != self._cache_mtime:
                # File was modified externally, mark cache as dirty
                logger.debug(f"Cache invalidated due to external file modification")
                self._cache_dirty = True

        # Rebuild cache if dirty or empty
        if self._cache_dirty or not self._cache:
            logger.debug(f"Rebuilding cache with {len(self._todos)} todos")
            self._cache.clear()
            for todo in self._todos:
                if todo.id is not None:
                    self._cache[todo.id] = todo
            self._cache_dirty = False
            # Update cache modification time
            if self.path.exists():
                self._cache_mtime = os.path.getmtime(self.path)
            logger.debug(f"Cache rebuilt successfully with {len(self._cache)} entries")

    def health_check(self) -> bool:
        """Check if storage backend is healthy and functional.

        This method performs a diagnostic check to verify that:
        1. The storage directory exists and is writable
        2. File locks can be acquired and released
        3. Temporary files can be created and cleaned up
        4. Sufficient disk space is available
        5. File permissions are correct
        6. JSON file integrity is valid (if file exists) (Issue #757)

        This is useful for startup diagnostics and configuration validation.

        Returns:
            True if the storage is healthy, False otherwise.

        Example:
            >>> storage = Storage()
            >>> if storage.health_check():
            ...     print("Storage is healthy")
        """
        import tempfile
        import shutil

        writable = False
        file_lock = False
        disk_space_free = 0

        # Check permissions
        try:
            parent_dir = self.path.parent
            if parent_dir.exists():
                readable = os.access(parent_dir, os.R_OK)
                writable = os.access(parent_dir, os.W_OK)
                executable = os.access(parent_dir, os.X_OK)
            else:
                # Directory doesn't exist yet, create it for checking
                parent_dir.mkdir(parents=True, exist_ok=True)
                readable = os.access(parent_dir, os.R_OK)
                writable = os.access(parent_dir, os.W_OK)
                executable = os.access(parent_dir, os.X_OK)
        except Exception:
            return False

        # Check disk space
        try:
            disk_usage = shutil.disk_usage(self.path.parent)
            disk_space_free = disk_usage.free
        except Exception:
            pass

        # Check file locking mechanism
        try:
            # Create a test temporary file in the storage directory
            fd, temp_path = tempfile.mkstemp(
                dir=self.path.parent,
                prefix=".health_check_",
                suffix=".tmp"
            )

            try:
                # Try to acquire a file lock on the temp file
                # This tests both write permissions and locking mechanism
                file_obj = os.fdopen(fd, 'r')
                self._acquire_file_lock(file_obj)

                # If we got here, we can write and lock successfully
                file_lock = True

                # Release the lock
                self._release_file_lock(file_obj)

                # Clean up the temp file
                try:
                    file_obj.close()
                except:
                    pass  # Already closed or invalid
                os.remove(temp_path)

            except Exception:
                # Lock acquisition failed - clean up
                file_lock = False
                try:
                    os.fdopen(fd, 'r').close()
                except:
                    pass
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass

        except (OSError, IOError, PermissionError):
            # Cannot create temp file - directory doesn't exist or isn't writable
            file_lock = False
            writable = False
        except Exception:
            # Any other error indicates unhealthy storage
            file_lock = False

        # Check JSON file integrity (Issue #757)
        json_integrity_ok = True
        if self.path.exists():
            try:
                # Try to load and parse the JSON file
                # Use compression setting from initialization
                is_compressed = self.compression

                # Read file as bytes
                with open(self.path, 'rb') as f:
                    file_bytes = f.read()

                # Check if file is empty
                if len(file_bytes) == 0:
                    json_integrity_ok = False
                else:
                    # Decompress if needed
                    if is_compressed:
                        import gzip
                        file_bytes = gzip.decompress(file_bytes)

                    # Parse JSON to verify integrity
                    file_str = file_bytes.decode('utf-8')

                    # Handle integrity marker if present
                    integrity_marker = '##INTEGRITY:'
                    marker_start = file_str.rfind(integrity_marker)
                    if marker_start != -1:
                        marker_end = file_str.find('##', marker_start + len(integrity_marker))
                        if marker_end != -1:
                            # Find the newline before the marker
                            data_end = file_str.rfind('\n', 0, marker_start)
                            if data_end == -1:
                                data_end = 0
                            file_str = file_str[:data_end] if data_end > 0 else file_str[:marker_start-1]

                    # Parse and validate JSON structure
                    data = json.loads(file_str)

                    # Verify it's a list (valid structure for todos)
                    if not isinstance(data, list):
                        json_integrity_ok = False

            except (json.JSONDecodeError, ValueError, TypeError, gzip.BadGzipFile, OSError):
                # JSON parsing failed or file corruption detected
                json_integrity_ok = False
            except Exception:
                # Any other error indicates unhealthy storage
                json_integrity_ok = False

        # Determine overall health
        return writable and file_lock and disk_space_free > 0 and json_integrity_ok

    def stats(self) -> dict:
        """Get storage statistics and metrics.

        This method returns statistics about the current state of the storage,
        including counts of todos by status and the last modification timestamp.

        Returns:
            A dictionary with the following keys:
            - total: Total number of todos (int)
            - pending: Number of pending todos (int, includes TODO and IN_PROGRESS)
            - completed: Number of completed todos (int, only DONE status)
            - last_modified: Last modification timestamp (Unix timestamp as float, or None)

        Example:
            >>> storage = FileStorage()
            >>> stats = storage.stats()
            >>> print(f"Total: {stats['total']}, Completed: {stats['completed']}")
        """
        from flywheel.todo import Status

        # Ensure data is loaded
        self._load()

        # Count todos by status
        total = len(self._todos)
        completed = sum(1 for todo in self._todos if todo.status == Status.DONE)
        pending = total - completed  # Everything else is pending

        # Get last modified timestamp from file
        last_modified = None
        if self.path.exists():
            try:
                last_modified = os.path.getmtime(self.path)
            except OSError:
                pass

        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "last_modified": last_modified,
        }

    def close(self) -> None:
        """Close storage and release resources.

        This method properly cleans up resources by:
        1. Saving any pending changes (if dirty)
        2. Stopping the auto-save background thread
        3. Cleaning up lock files (Issue #846)
        4. Unregistering the atexit handler

        The method is idempotent and can be called multiple times safely.
        Once closed, the storage object should not be used for further operations.

        Example:
            >>> storage = FileStorage()
            >>> storage.add(Todo(title="Task"))
            >>> storage.close()
        """
        # Idempotency check - only close once
        if hasattr(self, '_closed') and self._closed:
            return

        # Save any pending changes before closing
        # This ensures data durability even if the program crashes after close()
        if self._dirty:
            try:
                self._save()
                logger.info("Saved pending changes on close")
            except Exception as e:
                logger.error(f"Failed to save pending changes on close: {e}")

        # Stop the auto-save background thread
        if hasattr(self, '_auto_save_stop_event'):
            self._auto_save_stop_event.set()

        # Wait for the auto-save thread to finish (with timeout)
        if hasattr(self, '_auto_save_thread') and self._auto_save_thread.is_alive():
            # Give thread up to 2 seconds to finish gracefully
            self._auto_save_thread.join(timeout=2.0)
            if self._auto_save_thread.is_alive():
                logger.warning("Auto-save thread did not stop gracefully within timeout")

        # Issue #846: Clean up lock file if we're using file-based lock
        # This ensures locks are released even if the program crashes
        if (hasattr(self, '_lock_file_path') and
            self._lock_file_path is not None and
            os.path.exists(self._lock_file_path)):
            try:
                os.unlink(self._lock_file_path)
                logger.info(f"Cleaned up lock file on close: {self._lock_file_path}")
                self._lock_file_path = None
            except OSError as e:
                logger.warning(f"Failed to clean up lock file: {e}")

        # Mark as closed to prevent further operations
        self._closed = True

        # Try to unregister the atexit handler
        # Note: atexit.unregister() was added in Python 3.9
        try:
            atexit.unregister(self._cleanup)
        except AttributeError:
            # Python < 3.9 doesn't support unregister
            # The _cleanup method will check _closed flag and do nothing
            pass

    def transaction(self):
        """Create a transaction context manager for batch operations.

        This method returns a context manager that provides transactional
        semantics for batch operations. Changes are automatically committed
        if the block succeeds, or rolled back if an exception occurs.

        Returns:
            _TransactionContext: A context manager for transactional operations.

        Example:
            >>> with storage.transaction():
            ...     storage.add(Todo(title="Task 1"))
            ...     storage.update(1, Todo(title="Updated Task 1"))
            ...     storage.add(Todo(title="Task 2"))

        Note:
            The transaction acquires the storage lock and saves the current state.
            If an exception occurs, the state is rolled back. The storage is
            NOT closed after the transaction completes.

        Fix for Issue #1453: Implements transaction context manager with rollback.
        """
        return _TransactionContext(self)

    def __enter__(self):
        """Enter the context manager.

        This method enables Storage to be used as a context manager, ensuring
        locks are properly acquired and resources are managed during batch operations.

        NOTE: Uses non-reentrant Lock (Issue #1394). The lock is held for the
        duration of the context, so avoid calling other storage methods that
        attempt to acquire the same lock from within the context.

        Returns:
            Storage: The storage instance itself.

        Example:
            >>> with Storage() as storage:
            ...     storage.add(Todo(title="Task"))
        """
        # Acquire the lock to ensure thread safety
        # Note: This is a non-reentrant Lock (Issue #1394)
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager.

        This method releases resources, handles cleanup, and manages any exceptions
        that occurred within the context. Resources are always cleaned up and the
        lock is always released, even if an exception occurs (issue #587).

        As of issue #707, this method also calls close() to ensure proper lifecycle
        management, including saving dirty data, stopping the auto-save thread, and
        releasing all resources.

        Args:
            exc_type: The type of exception raised, if any.
            exc_val: The exception instance raised, if any.
            exc_tb: The traceback object, if any.

        Returns:
            bool: False to indicate exceptions should propagate.

        Example:
            >>> with Storage() as storage:
            ...     storage.add(Todo(title="Task"))
        """
        # Always release the lock, even if an exception occurred
        self._lock.release()
        # Call close() to ensure proper lifecycle management (issue #707)
        # This saves dirty data, stops auto-save thread, and releases resources
        self.close()
        # Return False to propagate any exceptions
        return False

    def __del__(self) -> None:
        """Destructor for cleanup when object is garbage collected.

        This method ensures that dirty data is saved when the FileStorage object
        is destroyed, even if the user doesn't explicitly call close() or use
        a context manager. It's registered with atexit for additional safety.

        Note: Python doesn't guarantee __del__ will be called in all circumstances
        (e.g., circular references, interpreter shutdown), so atexit registration
        is also used for cleanup (issue #615).

        Example:
            >>> storage = FileStorage()
            >>> storage.add(Todo(title="Task"))
            >>> # When storage is garbage collected, __del__ ensures data is saved
        """
        # Try to cleanup, but handle any errors gracefully
        # During interpreter shutdown, some modules may already be cleaned up
        try:
            self._cleanup()
        except (AttributeError, TypeError):
            # Ignore errors during interpreter shutdown or partial cleanup
            pass
        except Exception:
            # Log but don't raise in destructor - destructors should not raise
            # The atexit handler will handle proper cleanup
            pass

# Backward compatibility alias (issue #568)
# Storage is now an alias to FileStorage to maintain backward compatibility
Storage = FileStorage

# Global IOMetrics instance for module-level tracking (Issue #1068)
_global_io_metrics: IOMetrics | None = None


def _get_global_metrics() -> IOMetrics:
    """Get or create the global IOMetrics instance (Issue #1068).

    This function provides a singleton IOMetrics instance that can be used
    throughout the module for tracking I/O operations. It also registers
    an atexit handler to automatically dump metrics to a file if the
    FW_STORAGE_METRICS_FILE environment variable is set.

    Returns:
        The global IOMetrics instance

    Example:
        >>> metrics = _get_global_metrics()
        >>> metrics.record_operation('read', 0.5, 0, True)
        >>> # On exit, metrics will be automatically saved if FW_STORAGE_METRICS_FILE is set
    """
    global _global_io_metrics

    if _global_io_metrics is None:
        _global_io_metrics = IOMetrics()

        # Register atexit handler to dump metrics if FW_STORAGE_METRICS_FILE is set
        metrics_file = os.environ.get('FW_STORAGE_METRICS_FILE')
        if metrics_file:
            def _dump_metrics_on_exit():
                """Dump metrics to file on program exit (Issue #1068)."""
                if _global_io_metrics:
                    try:
                        _global_io_metrics.save_to_file(metrics_file)
                        logger.info(f"I/O metrics saved to {metrics_file}")
                    except Exception as e:
                        logger.error(f"Failed to save I/O metrics to {metrics_file}: {e}")

            atexit.register(_dump_metrics_on_exit)

    return _global_io_metrics
