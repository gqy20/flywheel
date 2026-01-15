"""Test for Issue #1824 - JSONFormatter.format 截断逻辑验证

Issue: JSONFormatter.format 方法截断逻辑不完整，可能导致生成无效的 JSON 字符串

测试场景：
1. 验证超大 message 能够被正确截断
2. 验证超长 exception 能够被移除
3. 验证极端情况（所有字段都超长）下仍能生成有效 JSON
4. 验证最终输出始终是有效的 JSON 且不超过 MAX_JSON_SIZE
"""

import json
import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import JSONFormatter


def test_extremely_large_message():
    """测试超大 message 能被正确截断且输出有效 JSON"""
    formatter = JSONFormatter()

    # Create a log record with an extremely large message
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="x" * (2 * 1024 * 1024),  # 2MB message (much larger than MAX_JSON_SIZE)
        args=(),
        exc_info=None,
    )

    json_output = formatter.format(record)

    # Verify output is valid JSON
    parsed = json.loads(json_output)
    assert isinstance(parsed, dict)

    # Verify output size is within MAX_JSON_SIZE
    assert len(json_output) <= JSONFormatter.MAX_JSON_SIZE, \
        f"Output size {len(json_output)} exceeds MAX_JSON_SIZE {JSONFormatter.MAX_JSON_SIZE}"

    # Verify message was truncated
    assert len(parsed['message']) < len(record.msg)
    assert 'truncated' in parsed['message'] or len(parsed['message']) < JSONFormatter.MAX_JSON_SIZE

    print(f"✓ Test passed: Large message truncated correctly")
    print(f"  Input size: {len(record.msg):,} bytes")
    print(f"  Output size: {len(json_output):,} bytes")
    print(f"  Message size: {len(parsed['message']):,} bytes")


def test_extremely_large_exception():
    """测试超长 exception 能被移除且输出有效 JSON"""
    formatter = JSONFormatter()

    # Create a log record with extremely large exception info
    try:
        # Create a deep stack trace
        def recursive_error(depth):
            if depth <= 0:
                raise ValueError("Test error")
            recursive_error(depth - 1)

        recursive_error(100)  # Deep recursion to create large stack trace
    except Exception:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )

    json_output = formatter.format(record)

    # Verify output is valid JSON
    parsed = json.loads(json_output)
    assert isinstance(parsed, dict)

    # Verify output size is within MAX_JSON_SIZE
    assert len(json_output) <= JSONFormatter.MAX_JSON_SIZE, \
        f"Output size {len(json_output)} exceeds MAX_JSON_SIZE {JSONFormatter.MAX_JSON_SIZE}"

    print(f"✓ Test passed: Large exception handled correctly")
    print(f"  Output size: {len(json_output):,} bytes")


def test_extreme_case_all_fields_large():
    """测试极端情况：所有字段都超长，仍能生成有效 JSON"""
    formatter = JSONFormatter()

    # Create a record with both large message and large exception
    large_message = "x" * (800 * 1024)  # 800KB message

    try:
        def recursive_error(depth):
            if depth <= 0:
                raise ValueError("x" * 10000)  # Error with large message
            recursive_error(depth - 1)
        recursive_error(50)
    except Exception:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg=large_message,
        args=(),
        exc_info=exc_info,
    )

    # Add extra fields with large values
    record.extra_large_field = "y" * (500 * 1024)  # 500KB extra field

    json_output = formatter.format(record)

    # Verify output is valid JSON
    parsed = json.loads(json_output)
    assert isinstance(parsed, dict)

    # Verify output size is within MAX_JSON_SIZE
    assert len(json_output) <= JSONFormatter.MAX_JSON_SIZE, \
        f"Output size {len(json_output)} exceeds MAX_JSON_SIZE {JSONFormatter.MAX_JSON_SIZE}"

    print(f"✓ Test passed: Extreme case handled correctly")
    print(f"  Output size: {len(json_output):,} bytes")
    print(f"  Fields in output: {list(parsed.keys())}")


def test_json_always_valid():
    """测试所有情况下的输出都是有效的 JSON"""
    formatter = JSONFormatter()

    test_cases = [
        # Normal case
        ("Normal message", None),
        # Empty message
        ("", None),
        # Large message
        ("x" * (5 * 1024 * 1024), None),
        # Unicode
        ("🔥" * 10000, None),
        # Special characters
        ("\"{}[],\\" * 1000, None),
    ]

    for msg, exc_info in test_cases:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )

        json_output = formatter.format(record)

        # Must be valid JSON
        try:
            parsed = json.loads(json_output)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON output for message '{msg[:50]}...': {e}\nOutput: {json_output[:200]}")

        # Must be within size limit
        assert len(json_output) <= JSONFormatter.MAX_JSON_SIZE, \
            f"Output size {len(json_output)} exceeds MAX_JSON_SIZE"

    print(f"✓ Test passed: All test cases produce valid JSON")


if __name__ == "__main__":
    print("Testing Issue #1824 - JSONFormatter truncation logic\n")

    try:
        test_extremely_large_message()
        print()
        test_extremely_large_exception()
        print()
        test_extreme_case_all_fields_large()
        print()
        test_json_always_valid()
        print("\n" + "="*50)
        print("✅ All tests passed!")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
