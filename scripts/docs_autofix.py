"""Automate docs maintenance with Agent SDK script workflow."""

from __future__ import annotations

import json
import logging
import os
import subprocess

from shared.agent_sdk import AgentSDKClient
from shared.utils import run_gh_command

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _build_prompt(branch_name: str, source_run_url: str, trigger_event: str) -> str:
    source_text = source_run_url if source_run_url else "N/A"
    return f"""
You are maintaining repository documentation quality.

Context:
- Trigger event: {trigger_event}
- Source docs-ci run URL: {source_text}
- Required work branch: `{branch_name}`

Goals:
1. Run docs checks:
   - `uv run python scripts/check_docs_sync.py --check`
   - `npx --yes markdownlint-cli2 --config .markdownlint-cli2.yaml`
2. If checks fail, apply focused docs-only fixes and rerun checks until green.
3. If workflow input docs are stale, run:
   - `uv run python scripts/check_docs_sync.py --generate`
4. Create branch `{branch_name}`.
5. Commit docs-only changes with conventional commit message.
6. Open exactly one PR to `master` with title prefix `[DOCS-AUTOFIX]`.
7. PR body must include:
   - Root cause summary
   - Files changed
   - Checks run and outcomes

Constraints:
- Do not change application logic under `src/`.
- Do not change automation behavior outside docs maintenance scope.
- Keep diff small and reviewable.
""".strip()


def _find_open_pr_for_branch(branch_name: str) -> tuple[str, str] | None:
    result = run_gh_command(
        ["pr", "list", "--head", branch_name, "--state", "open", "--json", "number,url"],
        check=False,
    )
    if result.returncode != 0:
        logger.error(
            "Failed to query PR for branch=%s stderr=%s", branch_name, result.stderr.strip()
        )
        return None

    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        logger.error("Failed to parse gh pr list output for branch=%s", branch_name)
        return None

    if not data:
        return None

    pr = data[0]
    return str(pr.get("number", "")), str(pr.get("url", ""))


def _run_check(cmd: list[str]) -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(
            "Check failed cmd=%s stdout=%s stderr=%s",
            " ".join(cmd),
            (result.stdout or "").strip()[:500],
            (result.stderr or "").strip()[:500],
        )
        return False
    return True


def _docs_checks_pass() -> bool:
    return _run_check(
        ["uv", "run", "python", "scripts/check_docs_sync.py", "--check"]
    ) and _run_check(["npx", "--yes", "markdownlint-cli2", "--config", ".markdownlint-cli2.yaml"])


def main() -> int:
    run_id = _required_env("RUN_ID")
    trigger_event = (
        os.environ.get("TRIGGER_EVENT", "workflow_dispatch").strip() or "workflow_dispatch"
    )
    source_run_url = os.environ.get("SOURCE_RUN_URL", "").strip()
    branch_name = f"claude/docs-autofix-{run_id}"

    logger.info(
        "Starting docs autofix run_id=%s trigger=%s branch=%s",
        run_id,
        trigger_event,
        branch_name,
    )

    prompt = _build_prompt(
        branch_name=branch_name, source_run_url=source_run_url, trigger_event=trigger_event
    )
    allowed_tools = ["Bash", "Edit", "MultiEdit", "Write", "Read", "Glob", "Grep", "LS", "Skill"]

    client = AgentSDKClient(model=os.environ.get("ANTHROPIC_MODEL", "").strip() or None)
    response = client.chat(
        prompt=prompt,
        max_turns=int(os.environ.get("CLAUDE_MAX_TURNS", "30")),
        allowed_tools=allowed_tools,
    )

    logger.info("Docs autofix response chars=%s", len(response))

    pr_ref = _find_open_pr_for_branch(branch_name)
    if not pr_ref:
        if _docs_checks_pass():
            logger.info(
                "Docs are already healthy and no PR was needed for branch=%s",
                branch_name,
            )
            return 0
        raise RuntimeError(
            f"Docs checks still failing and no PR was created for branch `{branch_name}`"
        )

    pr_number, pr_url = pr_ref
    logger.info("Docs autofix created PR #%s %s", pr_number, pr_url)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Docs autofix failed: %s", exc)
        raise SystemExit(1) from exc
