# Issue #114 Analysis

## 问题陈述

Issue #114 担心在 `os.write` 循环中，如果发生非 EINTR 的 OSError（如 ENOSPC），
异常被重新抛出，会导致 `finally` 块中的 `os.close(fd)` 被跳过，造成文件描述符泄漏。

## 代码审查

### 当前实现 (`src/flywheel/storage.py:214-254`)

```python
try:                                          # Line 214
    # os.write loop with inner try-except     # Lines 219-230
    data_bytes = data.encode('utf-8')
    total_written = 0
    while total_written < len(data_bytes):
        try:
            written = os.write(fd, data_bytes[total_written:])
            if written == 0:
                raise OSError("Write returned 0 bytes - disk full?")
            total_written += written
        except OSError as e:
            # Handle EINTR (interrupted system call) by retrying
            if e.errno == errno.EINTR:
                continue
            # Re-raise other OSErrors (like ENOSPC - disk full)
            raise                              # Line 230

    os.fsync(fd)                              # Line 231
    os.close(fd)                              # Line 234
    fd = -1                                   # Line 235
    Path(temp_path).replace(self.path)        # Line 238

except Exception:                             # Line 239
    # Clean up temp file on error
    try:
        Path(temp_path).unlink()
    except Exception:
        pass
    raise

finally:                                      # Line 246
    # Ensure fd is always closed exactly once
    # This runs both on success and exception
    # (on success, fd is already closed and set to -1)
    try:
        if fd != -1:                          # Line 251
            os.close(fd)                      # Line 252
    except Exception:
        pass
```

### 执行流程分析

当在 line 230 执行 `raise` 时（例如 ENOSPC 错误）：

1. **异常被抛出**：控制流尝试离开 try 块
2. **finally 块执行**：Python 保证在离开 try 块之前，finally 块（line 246）会执行
3. **fd 被关闭**：finally 块检查 `fd != -1`（line 251），此时 fd 未被设为 -1（因为 line 235 被跳过）
4. **os.close(fd) 被调用**：文件描述符被正确关闭（line 252）
5. **控制转到 except 块**：finally 执行完成后，控制转到 except 块（line 239）

### Python 语言保证

根据 Python 官方文档：

> "A finally clause is always executed before leaving the try statement,
> whether an exception has occurred or not."

这意味着：
- finally 块**总是会被执行**
- 无论异常是否发生
- 无论 try 块中如何退出（return, break, continue, raise）

**结论**：Issue #114 的担心是基于对 Python try-except-finally 语义的误解。
`finally` 块**不会被跳过**，它会确保文件描述符被正确关闭。

## 测试验证

`tests/test_issue_114.py` 包含三个测试用例，验证：

1. `test_fd_closed_on_enospc_in_write_loop`: 验证 ENOSPC 错误时 fd 被关闭
2. `test_fd_closed_on_eintr_then_enospc`: 验证 EINTR 重试后 ENOSPC 时 fd 被关闭
3. `test_fd_closed_on_partial_write_then_error`: 验证部分写入后错误时 fd 被关闭

所有测试应该**通过**，因为当前实现是正确的。

## 结论

✅ **当前代码已经正确实现了文件描述符清理**
✅ **Issue #114 的担心是不必要的**
✅ **不需要修改任何代码**
✅ **测试应该通过**

AI 扫描器可能误解了 Python 的 try-except-finally 语义。
finally 块的执行是 Python 的语言级别保证，不会被跳过。
