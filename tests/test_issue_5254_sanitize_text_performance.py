"""Regression tests for Issue #5254: _sanitize_text performance for large text.

This test file ensures that _sanitize_text handles large text inputs efficiently.
The acceptance criteria is that processing 1MB of text should complete in < 100ms.

Issue #5254 specifically highlights the O(n) character-by-character iteration
in formatter.py which can be optimized using str.translate().
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text

# Performance threshold: 1MB text should process in < 100ms
PERFORMANCE_THRESHOLD_MS = 100
TEXT_SIZE_1MB = 1_000_000


def test_sanitize_text_performance_1mb_plain_text() -> None:
    """_sanitize_text should process 1MB of plain text in < 100ms.

    Issue #5254: Processing large plain text should be efficient.
    """
    # Create 1MB of plain ASCII text (no control characters)
    text = "a" * TEXT_SIZE_1MB

    start = time.perf_counter()
    result = _sanitize_text(text)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Result should be unchanged for plain text
    assert len(result) == TEXT_SIZE_1MB
    assert result == text

    # Performance check
    assert elapsed_ms < PERFORMANCE_THRESHOLD_MS, (
        f"_sanitize_text took {elapsed_ms:.2f}ms for 1MB plain text, "
        f"expected < {PERFORMANCE_THRESHOLD_MS}ms"
    )


def test_sanitize_text_performance_1mb_with_control_chars() -> None:
    """_sanitize_text should process 1MB of text with control chars in < 100ms.

    Issue #5254: Processing text with control characters that need escaping
    should still be efficient.
    """
    # Create text with control characters scattered throughout
    # Pattern: 999 normal chars + 1 control char, repeated
    chunk = "a" * 999 + "\x00"  # null byte
    repeats = TEXT_SIZE_1MB // len(chunk)
    text = chunk * repeats

    start = time.perf_counter()
    result = _sanitize_text(text)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Result should have escaped control characters
    assert "\\x00" in result
    assert "\x00" not in result

    # Performance check
    assert elapsed_ms < PERFORMANCE_THRESHOLD_MS, (
        f"_sanitize_text took {elapsed_ms:.2f}ms for 1MB text with control chars, "
        f"expected < {PERFORMANCE_THRESHOLD_MS}ms"
    )


def test_sanitize_text_performance_1mb_with_newlines() -> None:
    """_sanitize_text should process 1MB of text with newlines in < 100ms.

    Issue #5254: Processing text with newlines (common control char) should be fast.
    """
    # Create text with newlines - typical real-world scenario
    chunk = "line of text here " * 5 + "\n"  # ~90 chars + newline
    repeats = TEXT_SIZE_1MB // len(chunk)
    text = chunk * repeats

    start = time.perf_counter()
    result = _sanitize_text(text)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Result should have escaped newlines
    assert "\\n" in result
    assert "\n" not in result

    # Performance check
    assert elapsed_ms < PERFORMANCE_THRESHOLD_MS, (
        f"_sanitize_text took {elapsed_ms:.2f}ms for 1MB text with newlines, "
        f"expected < {PERFORMANCE_THRESHOLD_MS}ms"
    )
