"""Generate one auto-fix candidate PR via Claude Agent SDK."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from shared.agent_sdk import AgentSDKClient
from shared.utils import comment_issue, run_gh_command

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STAGES = ("triage", "plan", "implement", "verify", "finalize")


@dataclass(frozen=True)
class FixContext:
    issue_number: str
    issue_title: str
    issue_url: str
    candidate_id: str
    run_id: str

    @property
    def branch_name(self) -> str:
        return f"claude/issue-{self.issue_number}-candidate-{self.candidate_id}-{self.run_id}"

    @property
    def scorecard_path(self) -> str:
        return (
            f".flywheel/scorecards/issue-{self.issue_number}/"
            f"candidate-{self.candidate_id}-{self.run_id}.json"
        )

    @property
    def state_file(self) -> Path:
        return (
            Path(".flywheel")
            / "runs"
            / f"issue-{self.issue_number}"
            / f"candidate-{self.candidate_id}-{self.run_id}.json"
        )


@dataclass(frozen=True)
class RuntimeConfig:
    max_turns: int
    stage_max_retries: int
    token_budget_chars: int
    stage_turn_overrides: dict[str, int]


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"completed": [], "responses": {}, "updated_at": None}
    try:
        return cast(dict[str, Any], json.loads(path.read_text()))
    except json.JSONDecodeError:
        logger.warning("State file is corrupted, resetting: %s", path)
        return {"completed": [], "responses": {}, "updated_at": None}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")


def _parse_runtime_config() -> RuntimeConfig:
    max_turns = int(os.environ.get("CLAUDE_MAX_TURNS", "60"))
    stage_max_retries = int(os.environ.get("CLAUDE_STAGE_MAX_RETRIES", "4"))
    token_budget_chars = int(os.environ.get("CLAUDE_TOKEN_BUDGET_CHARS", "1500000"))
    stage_turn_overrides: dict[str, int] = {}
    raw_overrides = os.environ.get("CLAUDE_STAGE_MAX_TURNS_JSON", "").strip()

    if raw_overrides:
        try:
            payload = cast(dict[str, Any], json.loads(raw_overrides))
            for key, value in payload.items():
                if key in STAGES and isinstance(value, int) and value > 0:
                    stage_turn_overrides[key] = value
        except json.JSONDecodeError:
            logger.warning("Invalid CLAUDE_STAGE_MAX_TURNS_JSON, ignore override")

    return RuntimeConfig(
        max_turns=max_turns,
        stage_max_retries=max(stage_max_retries, 0),
        token_budget_chars=max(token_budget_chars, 1000),
        stage_turn_overrides=stage_turn_overrides,
    )


def _build_stage_prompt(context: FixContext, stage: str) -> str:
    common = f"""
You are candidate #{context.candidate_id} for issue #{context.issue_number}.
First, load and follow the local skill `.claude/skills/flywheel-candidate-fix/SKILL.md`.

Issue:
- Number: #{context.issue_number}
- Title: {context.issue_title}
- URL: {context.issue_url}

Required branch name:
`{context.branch_name}`

Structured scorecard file path (must exist before finalize):
`{context.scorecard_path}`
""".strip()

    stage_instructions = {
        "triage": """
Stage TRIAGE:
1. Read issue and relevant code paths.
2. Identify likely root cause and risk points.
3. Output concise triage summary with proposed verification targets.
Do not modify files in this stage.
""".strip(),
        "plan": """
Stage PLAN:
1. Propose a minimal TDD plan with exact files to touch.
2. Define failing regression test first, then implementation sequence.
3. Define final verification commands (`uv run pytest ...`, `uv run ruff check ...`).
Do not create PR in this stage.
""".strip(),
        "implement": """
Stage IMPLEMENT:
1. Create/update failing regression test first.
2. Implement minimal fix.
3. Commit changes on branch `{branch}` using conventional commit with issue number.
""".strip().format(branch=context.branch_name),
        "verify": """
Stage VERIFY:
1. Run targeted pytest and ruff checks for changed scope.
2. If checks fail, fix and re-run until green.
3. Summarize exact verification commands and outcomes.
""".strip(),
        "finalize": """
Stage FINALIZE:
1. Ensure exactly one PR to `master` with title prefix:
   `[AUTOFIX][ISSUE-{issue}][CANDIDATE-{candidate}]`
2. PR body must include summary, tests run, risks/limitations and `Closes #{issue}`.
3. Ensure `{score_path}` exists and contains valid JSON metadata for this candidate.
4. Output one machine-readable line at end:
   - `PR_CREATED: <pr_url>` or
   - `BLOCKED: <reason>`
""".strip().format(
            issue=context.issue_number,
            candidate=context.candidate_id,
            score_path=context.scorecard_path,
        ),
    }

    return f"{common}\n\n{stage_instructions[stage]}"


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


def _run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True)


def _ensure_scorecard_file(
    context: FixContext,
    pr_number: str,
    pr_url: str,
    stage_state: dict[str, Any],
) -> None:
    scorecard = {
        "issue": int(context.issue_number),
        "candidate": int(context.candidate_id),
        "run_id": context.run_id,
        "branch": context.branch_name,
        "pr_number": int(pr_number),
        "pr_url": pr_url,
        "generated_at": datetime.now(UTC).isoformat(),
        "stages_completed": stage_state.get("completed", []),
        "stage_response_sizes": {
            name: len(text) for name, text in stage_state.get("responses", {}).items()
        },
    }

    # Keep branch update idempotent and recoverable.
    _run_git(["fetch", "origin", f"{context.branch_name}:{context.branch_name}"], check=False)
    _run_git(["checkout", context.branch_name], check=False)

    file_path = Path(context.scorecard_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(scorecard, indent=2, ensure_ascii=True) + "\n")

    _run_git(["add", context.scorecard_path])
    diff = _run_git(["diff", "--cached", "--name-only"], check=False)
    if context.scorecard_path not in diff.stdout:
        logger.info("Scorecard file unchanged, skip commit: %s", context.scorecard_path)
        return

    commit = _run_git(
        [
            "commit",
            "-m",
            (
                f"chore: persist candidate scorecard for issue #{context.issue_number} "
                f"(candidate {context.candidate_id})"
            ),
        ],
        check=False,
    )
    if commit.returncode != 0:
        logger.warning("Scorecard commit skipped: %s", commit.stderr.strip())
        return

    push = _run_git(["push", "origin", context.branch_name], check=False)
    if push.returncode != 0:
        logger.warning("Failed to push scorecard commit: %s", push.stderr.strip())
    else:
        logger.info("Scorecard file persisted to branch: %s", context.branch_name)


def _comment_issue_failure(issue_number: str, candidate_id: str, run_id: str, reason: str) -> None:
    message = (
        f"[AUTO-FIX] Candidate {candidate_id} failed to create PR in run {run_id}.\\n\\n"
        f"Reason: {reason}\\n\\n"
        "Action needed: inspect workflow logs for `Generate candidate PR via SDK`."
    )
    try:
        comment_issue(int(issue_number), message)
    except Exception as exc:
        logger.warning("Failed to comment issue #%s: %s", issue_number, exc)


def _run_stages(
    client: AgentSDKClient, context: FixContext, config: RuntimeConfig
) -> dict[str, Any]:
    state = _load_state(context.state_file)
    completed = set(state.get("completed", []))
    total_response_chars = int(state.get("total_response_chars", 0))

    allowed_tools = ["Bash", "Edit", "MultiEdit", "Write", "Read", "Glob", "Grep", "LS", "Skill"]

    for stage in STAGES:
        if stage in completed:
            logger.info(
                "Skipping completed stage issue=%s candidate=%s stage=%s",
                context.issue_number,
                context.candidate_id,
                stage,
            )
            continue

        stage_turns = config.stage_turn_overrides.get(stage, config.max_turns)
        max_attempts = config.stage_max_retries + 1
        stage_response = ""
        stage_failed = True
        stage_error = ""
        stage_attempt_count = 0

        for attempt in range(1, max_attempts + 1):
            stage_attempt_count = attempt
            if total_response_chars >= config.token_budget_chars:
                raise RuntimeError(
                    "Token budget exhausted by response char budget: "
                    f"{total_response_chars}/{config.token_budget_chars}"
                )

            logger.info(
                "Running stage issue=%s candidate=%s stage=%s attempt=%s/%s turns=%s budget=%s/%s",
                context.issue_number,
                context.candidate_id,
                stage,
                attempt,
                max_attempts,
                stage_turns,
                total_response_chars,
                config.token_budget_chars,
            )

            prompt = _build_stage_prompt(context, stage)
            try:
                stage_response = client.chat(
                    prompt=prompt,
                    max_turns=stage_turns,
                    allowed_tools=allowed_tools,
                )
                stage_failed = False
                break
            except Exception as exc:
                stage_error = str(exc)
                logger.warning(
                    "Stage failed issue=%s candidate=%s stage=%s attempt=%s/%s error=%s",
                    context.issue_number,
                    context.candidate_id,
                    stage,
                    attempt,
                    max_attempts,
                    stage_error[:240],
                )

        if stage_failed:
            state.setdefault("errors", {})[stage] = stage_error or "unknown_error"
            _save_state(context.state_file, state)
            raise RuntimeError(
                f"Stage {stage} failed after {max_attempts} attempts: {stage_error or 'unknown_error'}"
            )

        logger.info(
            "Stage complete issue=%s candidate=%s stage=%s response_chars=%s",
            context.issue_number,
            context.candidate_id,
            stage,
            len(stage_response),
        )

        total_response_chars += len(stage_response)
        state["total_response_chars"] = total_response_chars
        state.setdefault("responses", {})[stage] = stage_response[-4000:]
        state.setdefault("attempts", {})[stage] = stage_attempt_count
        state.setdefault("completed", []).append(stage)
        _save_state(context.state_file, state)

    return state


def main() -> int:
    context = FixContext(
        issue_number=_required_env("ISSUE_NUMBER"),
        issue_title=_required_env("ISSUE_TITLE"),
        issue_url=_required_env("ISSUE_URL"),
        candidate_id=_required_env("CANDIDATE_ID"),
        run_id=_required_env("RUN_ID"),
    )

    logger.info(
        "Starting staged candidate generation issue=%s candidate=%s branch=%s",
        context.issue_number,
        context.candidate_id,
        context.branch_name,
    )

    client = AgentSDKClient(model=os.environ.get("ANTHROPIC_MODEL", "").strip() or None)
    config = _parse_runtime_config()
    logger.info(
        "Runtime config issue=%s candidate=%s max_turns=%s stage_max_retries=%s token_budget_chars=%s stage_turn_overrides=%s",
        context.issue_number,
        context.candidate_id,
        config.max_turns,
        config.stage_max_retries,
        config.token_budget_chars,
        config.stage_turn_overrides,
    )
    stage_state = _run_stages(
        client=client,
        context=context,
        config=config,
    )

    pr_ref = _find_open_pr_for_branch(context.branch_name)
    if not pr_ref:
        reason = (
            "SDK staged run completed without creating an open PR for expected branch "
            f"`{context.branch_name}`"
        )
        logger.error(reason)
        _comment_issue_failure(context.issue_number, context.candidate_id, context.run_id, reason)
        raise RuntimeError(reason)

    pr_number, pr_url = pr_ref
    _ensure_scorecard_file(context, pr_number, pr_url, stage_state)

    logger.info(
        "Candidate generation produced PR issue=%s candidate=%s pr_number=%s pr_url=%s",
        context.issue_number,
        context.candidate_id,
        pr_number,
        pr_url,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Auto-fix candidate generation failed: %s", exc)
        raise SystemExit(1) from exc
