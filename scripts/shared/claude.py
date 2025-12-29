"""Claude API client wrapper."""

import logging
import os
import time

from anthropic import Anthropic, APIError, RateLimitError

logger = logging.getLogger(__name__)

# 模型配置
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "glm-4.7")
FAST_MODEL = os.getenv("ANTHROPIC_FAST_MODEL", "glm-4.7")

# 优先级映射
PRIORITY_MAP = {
    "[Security]": 100,  # p0
    "[Bug]": 75,  # p1
    "[Perf]": 50,  # p1/p2
    "[Test]": 30,  # p2
    "[Refactor]": 20,  # p2
    "[Docs]": 10,  # p3
}

PRIORITY_LABELS = {
    (80, 1000): "p0",
    (50, 79): "p1",
    (30, 49): "p2",
    (0, 29): "p3",
}


class ClaudeClient:
    """Claude API wrapper with retry logic."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        # 支持自定义 base_url
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        if base_url:
            self.client = Anthropic(api_key=self.api_key, base_url=base_url)
        else:
            self.client = Anthropic(api_key=self.api_key)

        self.model = model
        self.max_retries = 3

    def _calculate_priority(self, title: str) -> str:
        """Calculate priority from issue title."""
        for prefix, score in PRIORITY_MAP.items():
            if prefix in title:
                for (min_score, max_score), label in PRIORITY_LABELS.items():
                    if min_score <= score <= max_score:
                        return label
        return "p2"  # default

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if we should retry the request."""
        if attempt >= self.max_retries:
            return False

        if isinstance(error, RateLimitError):
            return True

        if (
            isinstance(error, APIError)
            and hasattr(error, "status_code")
            and 500 <= error.status_code < 600
        ):
            # Retry on server errors (5xx)
            return True

        return False

    def _wait_with_backoff(self, attempt: int):
        """Exponential backoff wait."""
        wait_time = 2**attempt
        logger.warning(f"Retry attempt {attempt + 1}/{self.max_retries}, waiting {wait_time}s")
        time.sleep(wait_time)

    def chat(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        system_prompt: str | None = None,
    ) -> str:
        """Send a chat prompt to Claude.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            system_prompt: Optional system prompt

        Returns:
            Response text
        """
        for attempt in range(self.max_retries):
            try:
                messages = [{"role": "user", "content": prompt}]

                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "temperature": temperature,
                }

                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self.client.messages.create(**kwargs)

                # Log usage
                usage = response.usage
                logger.info(
                    f"Claude API call: "
                    f"{usage.input_tokens} input + {usage.output_tokens} output tokens"
                )

                return response.content[0].text

            except (RateLimitError, APIError) as e:
                if self._should_retry(e, attempt):
                    self._wait_with_backoff(attempt)
                    continue
                raise

        raise Exception("Max retries exceeded")

    def analyze_code(self, code: str, filepath: str) -> list[dict]:
        """Analyze code and return list of issues.

        Args:
            code: Code content
            filepath: File path for context

        Returns:
            List of issue dictionaries
        """
        prompt = f"""
扫描以下 Python 代码，找出潜在问题：

文件: {filepath}

```python
{code[:10000]}
```

请以 JSON 格式返回：
{{
    "issues": [
        {{
            "type": "Bug|Security|Test|Docs|Refactor|Perf",
            "severity": "p0|p1|p2|p3",
            "description": "简短描述",
            "line": 行号 (int),
            "code": "相关代码片段",
            "suggestion": "修复建议"
        }}
    ]
}}
"""

        response = self.chat(prompt, temperature=0.1)

        # Parse JSON from response
        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result.get("issues", [])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {response[:200]}")
                return []

        return []

    def generate_fix(self, issue: dict, file_content: str) -> dict:
        """Generate fix for an issue.

        Args:
            issue: Issue dictionary
            file_content: Current file content

        Returns:
            Fix dictionary with content and line numbers
        """
        prompt = f"""
修复以下问题：

{issue["description"]}

文件: {issue.get("file", "unknown")}
行号: {issue.get("line", "unknown")}

当前代码：
```python
{issue.get("code", file_content[:2000])}
```

修复建议：
{issue.get("suggestion", "N/A")}

请提供修复后的完整代码（只返回修复的部分，不要返回整个文件）。
以 JSON 格式返回：
{{
    "fixed_code": "修复后的代码",
    "start_line": 起始行号,
    "end_line": 结束行号,
    "confidence": 置信度 (0-100)
}}
"""

        response = self.chat(prompt, temperature=0.2)

        # Parse JSON
        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {response[:200]}")

        return {"fixed_code": "", "confidence": 0}

    def generate_test(self, code: str, function_name: str) -> str:
        """Generate unit test for code.

        Args:
            code: Code to test
            function_name: Function name

        Returns:
            Test code
        """
        prompt = f"""
为以下代码生成单元测试：

```python
{code}
```

函数名: {function_name}

使用 pytest，生成完整的测试类。
确保测试覆盖率（正常情况、边界情况、异常情况）。
"""

        return self.chat(prompt, temperature=0.2)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (approximately 4 chars per token)."""
        return len(text) // 4
