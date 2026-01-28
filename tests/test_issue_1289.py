"""Test for issue #1289 - context-based default max_length in sanitize_for_security_context."""

import pytest
from flywheel.cli import sanitize_for_security_context


def test_filename_context_default_max_length():
    """Test that filename context has a default max_length of 255."""
    # Create a string longer than 255 but shorter than 4096
    long_string = "a" * 300

    # With filename context and no explicit max_length, should truncate to 255
    result = sanitize_for_security_context(long_string, context="filename")
    assert len(result) == 255, f"Expected 255 chars for filename context, got {len(result)}"


def test_url_context_default_max_length():
    """Test that url context has a default max_length of 255."""
    # Create a string longer than 255 but shorter than 4096
    long_string = "b" * 500

    # With url context and no explicit max_length, should truncate to 255
    result = sanitize_for_security_context(long_string, context="url")
    assert len(result) == 255, f"Expected 255 chars for url context, got {len(result)}"


def test_general_context_default_max_length():
    """Test that general context still has default max_length of 4096."""
    # Create a string longer than 4096 but shorter than hard limit
    long_string = "c" * 5000

    # With general context and no explicit max_length, should truncate to 4096
    result = sanitize_for_security_context(long_string, context="general")
    assert len(result) == 4096, f"Expected 4096 chars for general context, got {len(result)}"


def test_explicit_max_length_overrides_context_default():
    """Test that explicit max_length parameter overrides context default."""
    # Create a string longer than both 255 and 1000
    long_string = "d" * 2000

    # Explicit max_length should override context default
    result = sanitize_for_security_context(long_string, context="filename", max_length=1000)
    assert len(result) == 1000, f"Expected 1000 chars with explicit max_length, got {len(result)}"


def test_shell_context_default_max_length():
    """Test that shell context has a default max_length of 255."""
    # Create a string longer than 255 but shorter than 4096
    long_string = "e" * 300

    # With shell context and no explicit max_length, should truncate to 255
    result = sanitize_for_security_context(long_string, context="shell")
    # Shell context adds quotes, so we need to check the actual content length
    # The quoted string will be 'eee...eee' with quotes
    assert len(result) <= 302, f"Expected ~302 chars (255 content + quotes) for shell context, got {len(result)}"
    # Remove the quotes to check actual content length
    unquoted = result.strip("'")
    assert len(unquoted) == 255, f"Expected 255 chars of content for shell context, got {len(unquoted)}"


def test_format_context_default_max_length():
    """Test that format context has a default max_length of 255."""
    # Create a string longer than 255 but shorter than 4096
    long_string = "f" * 300

    # With format context and no explicit max_length, should truncate to 255
    result = sanitize_for_security_context(long_string, context="format")
    assert len(result) == 255, f"Expected 255 chars for format context, got {len(result)}"
