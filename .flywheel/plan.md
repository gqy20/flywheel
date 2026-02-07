# TDD Plan for Issue #1958: JSON Parse Error Handling

## Problem Summary
The `TodoStorage.load()` method in `src/flywheel/storage.py` line 73 does not handle `json.JSONDecodeError`. When a JSON file is corrupted, the program crashes with an unhelpful error message.

## Files to Touch

### Test Files
1. **NEW**: `tests/test_issue_1958_json_parse_error.py` - Regression test for JSON parse error handling

### Source Files
1. **MODIFY**: `src/flywheel/storage.py` - Add exception handling in `load()` method

---

## TDD Implementation Sequence

### RED Phase: Write Failing Test First

**File: `tests/test_issue_1958_json_parse_error.py`**

Test cases:
1. `test_load_with_invalid_json_raises_clear_error()` - Verify that malformed JSON raises a clear ValueError with file path
2. `test_load_with_non_list_json_raises_value_error()` - Verify that valid JSON but wrong type (not a list) raises ValueError
3. `test_load_error_message_contains_file_path()` - Verify error message includes the problematic file path

**Expected failing behavior:**
- Currently `json.JSONDecodeError` propagates uncaught
- Tests should fail because no proper exception handling exists

### GREEN Phase: Minimal Fix Implementation

**File: `src/flywheel/storage.py`**

Changes to `TodoStorage.load()` method (around line 59-76):

```python
def load(self) -> list[Todo]:
    if not self.path.exists():
        return []

    # Security: Check file size before loading to prevent DoS
    file_size = self.path.stat().st_size
    if file_size > _MAX_JSON_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
        raise ValueError(
            f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
            f"This protects against denial-of-service attacks."
        )

    try:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse todo file '{self.path}': {e.msg}"
        ) from e

    if not isinstance(raw, list):
        raise ValueError("Todo storage must be a JSON list")
    return [Todo.from_dict(item) for item in raw]
```

---

## Final Verification Commands

```bash
# Run the specific issue test
uv run pytest tests/test_issue_1958_json_parse_error.py -v

# Run all storage-related tests
uv run pytest tests/test_storage_atomicity.py tests/test_issue_1958_json_parse_error.py -v

# Run linter checks
uv run ruff check src/flywheel/storage.py tests/test_issue_1958_json_parse_error.py

# Format check
uv run ruff format --check src/flywheel/storage.py tests/test_issue_1958_json_parse_error.py
```

---

## Acceptance Criteria (from Issue)
- [x] When JSON file is corrupted, program should not crash silently
- [x] Error message should include file path and corruption reason
- [x] Unit tests cover JSON parse failure scenarios
