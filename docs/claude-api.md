# GitHub Actions 调用 Claude API 技术调研报告

## 1. 概述

本文档调研如何在 GitHub Actions 中调用 Claude API，包括官方 Action、直接 API 调用、Python SDK 使用和安全最佳实践。

---

## 2. 方案一：官方 GitHub Action (推荐用于 PR/Issue 分析)

### 2.1 anthropics/claude-code-action

**仓库**: [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)

**简介**: Anthropic 官方提供的 GitHub Action，专门用于在 PR 和 Issue 中使用 Claude Code。

**发布时间**: 2025年9月29日

### 2.2 使用示例

```yaml
# .github/workflows/claude-review.yml
name: Claude Code Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Claude Code
        uses: anthropics/claude-code-action@v1
        with:
          # API 密钥 (从 GitHub Secrets 获取)
          apiKey: ${{ secrets.ANTHROPIC_API_KEY }}

          # 触发词 (可选)
          trigger: '/claude'

          # 模型选择 (可选)
          model: 'claude-sonnet-4-5-20250929'

          # 自定义系统提示 (可选)
          systemPrompt: |
            你是一个代码审查专家。请检查代码中的：
            1. 潜在的 bug
            2. 安全问题
            3. 性能优化建议
            4. 代码风格问题

          # 输出格式 (可选)
          output: 'comment'  # 或 'summary'
```

### 2.3 适用场景

| 场景 | 适用性 | 说明 |
|------|--------|------|
| PR 自动 Review | ✅ 推荐 | 官方支持，配置简单 |
| Issue 自动回复 | ✅ 推荐 | 可在 Issue 中触发 |
| 代码生成/修改 | ⚠️ 有限 | 主要用于分析，不适合大规模修改 |
| 自定义工作流 | ⚠️ 受限 | 灵活性不如直接调用 API |

---

## 3. 方案二：直接调用 Anthropic API (推荐用于自定义场景)

### 3.1 API 基础信息

**API 端点**: `https://api.anthropic.com/v1/messages`

**认证方式**: Header `x-api-key: <your-api-key>`

**Python SDK**: [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)

### 3.2 安装 SDK

```bash
pip install anthropic
```

### 3.3 基础调用示例

```python
import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, world"}
    ]
)

print(message.content)
```

### 3.4 GitHub Actions 中使用 Python SDK

```yaml
# .github/workflows/ai-fix.yml
name: AI Auto Fix

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  auto-fix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install anthropic

      - name: Run AI Fix Script
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python scripts/ai_fixer.py
```

### 3.5 完整的 Python 脚本示例

```python
# scripts/ai_fixer.py
import os
import re
from anthropic import Anthropic
from github import Github

def analyze_code(code: str, context: str) -> dict:
    """使用 Claude 分析代码"""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""
分析以下代码，找出潜在问题：

{context}

代码:
```python
{code}
```

请以 JSON 格式返回：
{{
    "issues": [
        {{
            "type": "bug|security|performance|style",
            "severity": "p0|p1|p2|p3",
            "description": "问题描述",
            "line": 行号,
            "suggestion": "修复建议"
        }}
    ]
}}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2  # 降低随机性，更稳定
    )

    # 解析 JSON 响应
    import json
    content = response.content[0].text
    return json.loads(re.search(r'\{[\s\S]*\}', content).group())

def fix_issue(issue: dict, file_path: str) -> str:
    """使用 Claude 生成修复代码"""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""
修复以下问题：

{issue['description']}

文件: {file_path}
行号: {issue['line']}

请提供修复后的完整代码。
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text

def create_github_issue(title: str, body: str, labels: list):
    """创建 GitHub Issue"""
    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))

    issue = repo.create_issue(
        title=title,
        body=body,
        labels=labels
    )

    return issue.number

def main():
    # 示例：扫描 Python 文件
    for file_path in ["src/service.py"]:
        with open(file_path) as f:
            code = f.read()

        issues = analyze_code(code, f"File: {file_path}")

        for issue in issues["issues"]:
            title = f"[{issue['type'].upper()}]: {issue['description'][:50]}"

            body = f"""

## 问题描述

{issue['description']}

## 位置

- 文件: {file_path}
- 行号: {issue['line']}

## 修复建议

{issue['suggestion']}

## 优先级

{issue['severity']}

---
*AI 生成时间: {datetime.now().isoformat()}*
"""

            create_github_issue(title, body, [issue['severity']])

if **name** == "**main**":
    main()
```

---

## 4. 可用模型列表

| 模型名称 | 用途 | 速度 | 成本 |
|---------|------|------|------|
| `claude-opus-4-5-20251101` | 复杂任务 | 慢 | 高 |
| `claude-opus-4-5` | 复杂任务 | 慢 | 高 |
| `claude-sonnet-4-5-20250929` | **编码推荐** | 中 | 中 |
| `claude-sonnet-4-5` | **编码推荐** | 中 | 中 |
| `claude-haiku-4-5` | 快速响应 | 快 | 低 |

**推荐配置**:
- 代码分析/生成: `claude-sonnet-4-5-20250929`
- 快速扫描: `claude-haiku-4-5`
- 复杂重构: `claude-opus-4-5`

---

## 5. API 参数详解

### 5.1 核心参数

```python
client.messages.create(
    # 模型选择 (必需)
    model="claude-sonnet-4-5-20250929",

    # 最大生成 token 数 (必需)
    max_tokens=4096,

    # 消息列表 (必需)
    messages=[
        {"role": "user", "content": "提示词"}
    ],

    # 系统提示 (可选)
    system="你是一个代码分析专家",

    # 温度 (0-1，默认 1.0)
    temperature=0.2,  # 代码任务建议用低值

    # 顶层 P 采样 (0-1，与 temperature 二选一)
    top_p=0.9,

    # 停止序列 (可选)
    stop_sequences=["\n\n\n"],

    # 工具使用 (可选)
    tools=[...],

    # 思维预算 (可选，用于复杂推理)
    thinking={
        "type": "enabled",
        "budget_tokens": 1024
    }
)
```

### 5.2 流式响应

```python
with client.messages.stream(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "写一个快排"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

---

## 6. 安全最佳实践

### 6.1 API 密钥管理

**✅ 正确做法**:

```yaml
# 1. 在 GitHub 仓库设置中添加 Secret
# Settings → Secrets and variables → Actions → New repository secret
# Name: ANTHROPIC_API_KEY
# Value: sk-ant-xxx...

# 2. 在 Workflow 中引用
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**❌ 错误做法**:

```yaml
# 永远不要硬编码 API 密钥！
env:
  ANTHROPIC_API_KEY: sk-ant-xxx...  # 绝对禁止！
```

### 6.2 密钥轮换策略

```yaml
# 使用环境变量，便于轮换
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY_V2 }}  # 添加版本号
```

### 6.3 访问权限最小化

```yaml
# 只授予必要的权限
permissions:
  contents: read      # 只读代码
  issues: write       # 写 Issue
  pull-requests: write  # 写 PR
  # 不要给 admin、repo 等宽权限
```

### 6.4 速率限制

```yaml
env:
  # 设置速率限制
  MAX_REQUESTS_PER_MINUTE: "10"
  RETRY_AFTER_RATE_LIMIT: "60"
```

### 6.5 成本控制

```python
# 在脚本中设置预算
MAX_TOKENS_PER_RUN = 100000
COST_PER_TOKEN = 0.003  # USD per 1K tokens (示例)

def check_budget(tokens_used):
    cost = (tokens_used / 1000) * COST_PER_TOKEN
    if cost > MAX_DAILY_BUDGET:
        raise Exception("Budget exceeded")
```

---

## 7. 错误处理与重试

### 7.1 常见错误

| 错误类型 | HTTP 状态 | 处理方式 |
|---------|----------|----------|
| 速率限制 | 429 | 指数退避重试 |
| 无效密钥 | 401 | 检查密钥配置 |
| 令牌超限 | 400 | 减少 max_tokens |
| 服务器错误 | 500 | 重试 |

### 7.2 重试逻辑示例

```python
import time
from anthropic import Anthropic, APIError, RateLimitError

def call_claude_with_retry(client, prompt, max_retries=3):
    """带重试的 Claude API 调用"""
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response

        except RateLimitError as e:
            wait_time = 2 ** attempt  # 指数退避: 2, 4, 8 秒
            print(f"Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)

        except APIError as e:
            if attempt == max_retries - 1:
                raise
            print(f"API error: {e}, retrying...")
            time.sleep(1)

    raise Exception("Max retries exceeded")
```

---

## 8. 监控与日志

### 8.1 使用情况追踪

```python
import logging

def log_api_usage(response):
    """记录 API 使用情况"""
    usage = response.usage

    logging.info(f"""
    Claude API Usage:
    - Input tokens: {usage.input_tokens}
    - Output tokens: {usage.output_tokens}
    - Cache creation: {usage.cache_creation_input_tokens}
    - Cache read: {usage.cache_read_input_tokens}
    - Total: {usage.input_tokens + usage.output_tokens}
    - Cost: ${calculate_cost(usage):.4f}
    """)

def calculate_cost(usage):
    """计算成本 (根据官方定价)"""
    # 示例定价，请查看最新定价
    INPUT_COST_PER_1K = 0.003
    OUTPUT_COST_PER_1K = 0.015

    input_cost = (usage.input_tokens / 1000) * INPUT_COST_PER_1K
    output_cost = (usage.output_tokens / 1000) * OUTPUT_COST_PER_1K

    return input_cost + output_cost
```

### 8.2 GitHub Actions 日志

```yaml
- name: Run AI Fix
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    echo "Starting AI fix at $(date)" >> $GITHUB_STEP_SUMMARY
    python scripts/ai_fixer.py 2>&1 | tee ai_fix.log
    echo "Completed at $(date)" >> $GITHUB_STEP_SUMMARY
```

---

## 9. 成本优化

### 9.1 使用 Prompt 缓存

```python
# 对于重复的上下文，使用缓存
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    messages=[...],
    system=[{
        "type": "text",
        "text": "你是一个代码分析专家...",
        "cache_control": {"type": "ephemeral"}  # 启用缓存
    }]
)
```

### 9.2 批处理

```python
# 批量处理，减少 API 调用次数
def batch_analyze(files: list):
    all_code = "\n\n".join([f"// File: {f}\n{read_file(f)}" for f in files])

    prompt = f"""
分析以下多个文件中的问题：

{all_code}

请按文件分组返回问题。
"""
    # 一次调用分析多个文件
    return call_claude(prompt)
```

### 9.3 模型选择策略

```python
def choose_model(task_complexity):
    """根据任务复杂度选择模型"""
    if task_complexity == "simple":
        return "claude-haiku-4-5"  # 快速便宜
    elif task_complexity == "medium":
        return "claude-sonnet-4-5-20250929"  # 平衡
    else:
        return "claude-opus-4-5"  # 最强但贵
```

---

## 10. 完整示例：Issue 生成器

```yaml
# .github/workflows/01-scan-issues.yml
name: AI Issue Scanner

on:
  schedule:
    - cron: '0 0 * * 1'  # 每周一 00:00
  workflow_dispatch:

permissions:
  contents: read
  issues: write

jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install anthropic PyGithub

      - name: Run AI Scanner
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MAX_ISSUES: "5"
        run: |
          python scripts/issue_generator/scanner.py

      - name: Summary
        run: |
          echo "### Scan Results" >> $GITHUB_STEP_SUMMARY
          echo "- Issues created: $(git log -1 --pretty=%B | grep -c 'Closes #' || echo 0)" >> $GITHUB_STEP_SUMMARY
```

```python
# scripts/issue_generator/scanner.py
import os
import re
import json
from datetime import datetime
from anthropic import Anthropic
from github import Github

class ClaudeScanner:
    def __init__(self):
        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.github = Github(os.environ["GITHUB_TOKEN"])
        self.repo = self.github.get_repo(os.getenv("GITHUB_REPOSITORY"))

    def scan_file(self, filepath: str) -> list:
        """扫描单个文件"""
        with open(filepath) as f:
            code = f.read()

        prompt = f"""
扫描以下 Python 代码，找出潜在问题：

```python
{code[:5000]}  # 限制长度
```

返回 JSON 格式：
{{
    "issues": [
        {{
            "type": "bug|security|test|docs|refactor",
            "severity": "p0|p1|p2|p3",
            "description": "简短描述",
            "line": 行号,
            "code": "相关代码片段"
        }}
    ]
}}
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        # 解析 JSON
        content = response.content[0].text
        json_match = re.search(r'\{[\s\S]*\}', content)

        if json_match:
            return json.loads(json_match.group())["issues"]
        return []

    def create_issue(self, issue: dict, filepath: str):
        """创建 Issue"""
        title = f"[{issue['type'].upper()}]: {issue['description'][:60]}"

        body = f"""

## 问题描述

{issue['description']}

## 位置

- **文件**: `{filepath}`
- **行号**: {issue.get('line', 'N/A')}

## 代码片段

```python
{issue.get('code', 'N/A')}
```

## 修复建议

待 AI 生成

---

**AI 元数据**

- 生成时间: {datetime.now().isoformat()}
- 扫描器: Claude Sonnet 4.5
- 置信度: 中等
"""

        # 检查是否已存在类似 Issue
        existing = self.repo.get_issues(state='open')
        for e in existing:
            if issue['description'] in e.title:
                print(f"Issue already exists: {e.number}")
                return

        # 创建新 Issue
        new_issue = self.repo.create_issue(
            title=title,
            body=body,
            labels=[issue['severity']]
        )

        print(f"Created issue #{new_issue.number}: {title}")

    def run(self):
        """执行扫描"""
        max_issues = int(os.getenv("MAX_ISSUES", "5"))
        created = 0

        # 扫描 Python 文件
        for filepath in ["src", "scripts"]:
            if not os.path.exists(filepath):
                continue

            for root, dirs, files in os.walk(filepath):
                if created >= max_issues:
                    print(f"Reached max issues limit: {max_issues}")
                    return

                for file in files:
                    if not file.endswith('.py'):
                        continue

                    full_path = os.path.join(root, file)
                    issues = self.scan_file(full_path)

                    for issue in issues:
                        if created >= max_issues:
                            return

                        self.create_issue(issue, full_path)
                        created += 1

if **name** == "**main**":
    scanner = ClaudeScanner()
    scanner.run()
```

---

## 11. 参考资料

### 官方文档
- [Claude API 文档](https://platform.claude.com/docs/en/api/client-sdks)
- [Python SDK GitHub](https://github.com/anthropics/anthropic-sdk-python)
- [Messages API 参考](https://platform.claude.com/docs/en/api/python/messages/create)
- [Anthropic Academy](https://www.anthropic.com/learn/build-with-claude)

### GitHub Actions
- [官方 Action: anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)
- [GitHub Actions 安全最佳实践](https://docs.github.com/en/rest/authentication/keeping-your-api-credentials-secure)

### 社区资源
- [Claude Code + GitHub Actions 教程 (中文)](https://zhuanlan.zhihu.com/p/1888999194720702630)
- [Claude API 新手教程](https://poloapi.com/poloapi-blog/Claude-API-Beginner's-Guide)
- [API 密钥安全指南](https://blog.gitguardian.com/secrets-api-management/)

### 成本参考
- [Claude 定价页面](https://www.anthropic.com/pricing)
- [成本估算工具](https://github.com/anthropics/anthropic-sdk-python#token-counting)

---

## 12. 总结

### 方案选择

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **官方 Action** | PR/Issue 分析 | 配置简单，官方维护 | 灵活性受限 |
| **直接调用 API** | 自定义工作流 | 完全控制，功能强大 | 需要自己实现 |
| **Python SDK** | 复杂逻辑 | 类型安全，易维护 | 需要 Python 环境 |

### 推荐方案

**对于 AI 编程飞轮项目**，推荐使用 **方案二（直接调用 API + Python SDK）**，原因：
1. ✅ 需要深度定制（Issue 生成、优先级评估、自动修复）
2. ✅ 需要与 GitHub API 深度集成
3. ✅ 需要复杂的状态管理和错误处理
4. ✅ Python 脚本易于测试和调试

---

**文档版本**: v1.0
**更新时间**: 2025-12-29
**调研范围**: Anthropic Claude API + GitHub Actions 集成
