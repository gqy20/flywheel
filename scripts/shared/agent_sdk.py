"""Claude Agent SDK wrapper for script automation."""

from __future__ import annotations

import itertools
import logging
import os
import time
from typing import Any, cast

import anyio
from claude_agent_sdk import ClaudeAgentOptions, TextBlock, query

logger = logging.getLogger(__name__)


class AgentSDKClient:
    """Small wrapper around claude-agent-sdk query API."""

    def __init__(self, model: str | None = None):
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
        if not token:
            raise ValueError("ANTHROPIC_AUTH_TOKEN environment variable is required")

        self.model = model or os.environ.get("ANTHROPIC_MODEL", "")
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
        self.token = token
        self.max_turns_default = int(os.environ.get("CLAUDE_MAX_TURNS", "25"))
        self.trace_enabled = os.environ.get("CLAUDE_SDK_TRACE", "1").lower() not in {
            "0",
            "false",
            "off",
        }
        self.log_prompt = os.environ.get("CLAUDE_SDK_LOG_PROMPT", "0").lower() in {
            "1",
            "true",
            "on",
        }
        self._request_counter = itertools.count(1)

    def _build_env(self) -> dict[str, str]:
        env: dict[str, str] = {
            # Keep user-requested variable name as source-of-truth.
            "ANTHROPIC_AUTH_TOKEN": self.token,
            # Some SDK/provider adapters read API_TOKEN; provide both.
            "ANTHROPIC_API_TOKEN": self.token,
        }
        if self.base_url:
            env["ANTHROPIC_BASE_URL"] = self.base_url
        if self.model:
            env["ANTHROPIC_MODEL"] = self.model
        return env

    async def _chat_async(
        self,
        prompt: str,
        max_turns: int,
        temperature: float,
        allowed_tools: list[str] | None,
        request_id: str,
    ) -> str:
        extra_args: dict[str, Any] = {"max-turns": str(max_turns)}
        if self.model:
            extra_args["model"] = self.model

        options = ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code"},
            setting_sources=["user", "project"],
            cwd=os.getcwd(),
            env=self._build_env(),
            extra_args=extra_args,
            permission_mode="bypassPermissions",
            allowed_tools=allowed_tools or [],
        )

        chunks: list[str] = []
        assistant_events = 0
        result_events = 0
        async for message in query(prompt=prompt, options=options):
            message_type = str(getattr(message, "type", "unknown"))
            if message_type == "assistant":
                assistant_events += 1
                msg = getattr(message, "message", None)
                if msg is None:
                    if self.trace_enabled:
                        logger.info("[%s] assistant event with empty message payload", request_id)
                    continue
                text_blocks = 0
                text_chars = 0
                for block in getattr(msg, "content", []) or []:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
                        text_blocks += 1
                        text_chars += len(block.text)
                if self.trace_enabled:
                    logger.info(
                        "[%s] assistant event=%s text_blocks=%s text_chars=%s",
                        request_id,
                        assistant_events,
                        text_blocks,
                        text_chars,
                    )
            elif message_type == "result":
                result_events += 1
                # bubble up explicit error result to caller for better diagnostics
                if getattr(message, "is_error", False):
                    result_text = getattr(message, "result", "")
                    logger.error(
                        "[%s] sdk result is_error=true event=%s detail=%s",
                        request_id,
                        result_events,
                        (str(result_text)[:400] if result_text else "empty"),
                    )
                    raise RuntimeError(result_text or "Claude Agent SDK returned error")
                if self.trace_enabled:
                    logger.info(
                        "[%s] sdk result event=%s is_error=false", request_id, result_events
                    )
            elif self.trace_enabled:
                logger.info("[%s] sdk message type=%s", request_id, message_type)

        return "".join(chunks).strip()

    def chat(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        max_turns: int | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        """Chat via Claude Agent SDK.

        max_tokens is accepted for interface compatibility.
        """
        _ = max_tokens
        _ = temperature
        turns = max_turns if max_turns is not None else self.max_turns_default
        request_id = f"req-{next(self._request_counter):04d}"
        start = time.monotonic()
        logger.info(
            "[%s] sdk chat start model=%s max_turns=%s allowed_tools=%s prompt_chars=%s",
            request_id,
            self.model or "default",
            turns,
            ",".join(allowed_tools or []) or "none",
            len(prompt),
        )
        if self.log_prompt:
            logger.debug("[%s] sdk prompt:\n%s", request_id, prompt)
        try:
            response = cast(
                str,
                anyio.run(self._chat_async, prompt, turns, temperature, allowed_tools, request_id),
            )
            elapsed = time.monotonic() - start
            logger.info(
                "[%s] sdk chat done elapsed=%.2fs response_chars=%s",
                request_id,
                elapsed,
                len(response),
            )
            return response
        except Exception:
            elapsed = time.monotonic() - start
            logger.exception("[%s] sdk chat failed elapsed=%.2fs", request_id, elapsed)
            raise
