"""Merge arbiter for candidate PRs via Claude Agent SDK."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, cast

from shared.agent_sdk import AgentSDKClient
from shared.utils import run_gh_command

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BRANCH_PATTERN = re.compile(
    r"^claude/issue-(?P<issue>\d+)-candidate-(?P<candidate>\d+)-(?P<run>.+)$"
)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _required_repo() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repo:
        return repo

    result = run_gh_command(["repo", "view", "--json", "nameWithOwner"], check=False)
    if result.returncode != 0:
        raise ValueError("Unable to determine repository from GITHUB_REPOSITORY or gh repo view")

    payload = json.loads(result.stdout or "{}")
    repo = str(payload.get("nameWithOwner", "")).strip()
    if not repo:
        raise ValueError("Unable to parse repository name")
    return repo


def _scorecard_path(issue_number: str, candidate_id: str, run_id: str) -> str:
    return f".flywheel/scorecards/issue-{issue_number}/candidate-{candidate_id}-{run_id}.json"


def _load_structured_scorecard(
    repo: str, issue_number: str, pr_data: dict[str, Any]
) -> dict[str, Any]:
    pr_number = int(pr_data.get("number", 0))
    head_branch = str(pr_data.get("headRefName", ""))

    match = BRANCH_PATTERN.match(head_branch)
    if not match:
        return {
            "pr": pr_number,
            "branch": head_branch,
            "source": "fallback",
            "reason": "branch_name_not_matching_candidate_pattern",
        }

    candidate_id = match.group("candidate")
    run_id = match.group("run")
    path = _scorecard_path(issue_number=issue_number, candidate_id=candidate_id, run_id=run_id)

    endpoint = f"repos/{repo}/contents/{path}?ref={head_branch}"
    result = run_gh_command(["api", endpoint], check=False)
    if result.returncode != 0:
        return {
            "pr": pr_number,
            "branch": head_branch,
            "candidate": int(candidate_id),
            "run_id": run_id,
            "source": "fallback",
            "reason": "scorecard_file_not_found",
            "path": path,
        }

    payload = json.loads(result.stdout or "{}")
    encoded = payload.get("content", "")
    if not isinstance(encoded, str) or not encoded.strip():
        return {
            "pr": pr_number,
            "branch": head_branch,
            "candidate": int(candidate_id),
            "run_id": run_id,
            "source": "fallback",
            "reason": "scorecard_payload_empty",
            "path": path,
        }

    decoded = base64.b64decode(encoded.encode("ascii"), validate=False).decode("utf-8")
    parsed = cast(dict[str, Any], json.loads(decoded))
    parsed["source"] = "scorecard_file"
    parsed["path"] = path
    parsed["pr"] = pr_number
    parsed["branch"] = head_branch
    return parsed


def _collect_candidate_data(
    repo: str, issue_number: str, eligible_csv: str
) -> list[dict[str, Any]]:
    candidate_data: list[dict[str, Any]] = []
    for raw in eligible_csv.split(","):
        value = raw.strip()
        if not value:
            continue
        pr_number = int(value)
        result = run_gh_command(
            [
                "pr",
                "view",
                str(pr_number),
                "--json",
                "number,title,url,headRefName,body,changedFiles,additions,deletions",
            ],
            check=False,
        )
        if result.returncode != 0:
            logger.warning("Failed to load PR metadata for #%s", pr_number)
            continue

        pr_data = json.loads(result.stdout or "{}")
        scorecard = _load_structured_scorecard(
            repo=repo, issue_number=issue_number, pr_data=pr_data
        )
        candidate_data.append({"pr": pr_data, "scorecard": scorecard})

    return candidate_data


def _persist_bundle(issue_number: str, candidates: list[dict[str, Any]]) -> Path:
    bundle_path = Path(".flywheel") / "arbiter" / f"issue-{issue_number}-candidates.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(candidates, indent=2, ensure_ascii=True) + "\n")
    return bundle_path


def build_prompt(issue_number: str, eligible_csv: str, candidates_json: str) -> str:
    return f"""
You are the dedicated merge arbiter for auto-fix candidates.
First, load and follow the local skill at `.claude/skills/flywheel-merge-arbiter/SKILL.md`.

Target issue: #{issue_number}
Eligible candidate PRs (CSV): {eligible_csv}

Structured candidate data (PR metadata + scorecard files when available):
```json
{candidates_json}
```

Required workflow:
1. Compare only the eligible candidates (all checks already green, non-draft, mergeable).
2. Use structured scorecard files as primary evidence where available.
3. Score each candidate using this weighted rubric (0-10 each dimension):
   - Correctness and issue coverage (weight 0.45)
   - Regression risk (weight 0.30, lower risk means higher score)
   - Simplicity and maintainability (weight 0.15)
   - Test quality and verification evidence (weight 0.10)
4. Compute total score = weighted sum and rank all candidates.
5. Publish a machine-readable scorecard comment on the winner PR before merge, exactly:
   <!-- arbiter-scorecard -->
   {{"issue":<issue_number>,"winner_pr":<pr_number>,"scores":[{{"pr":<number>,"correctness":<0-10>,"risk":<0-10>,"maintainability":<0-10>,"tests":<0-10>,"total":<0-10>,"verdict":"winner|rejected","reason":"..."}}]}}
6. Merge exactly one winner to `master` using squash merge.
7. Comment and close non-winner candidate PRs with brief reasons and score deltas.
8. If no candidate is safe after deep review, do not merge and comment on issue #{issue_number}.

Constraints:
- Never merge more than one PR.
- Use GitHub CLI for PR/issue operations.
- Do not modify workflows or repository settings.
""".strip()


def main() -> int:
    issue_number = _required_env("ISSUE_NUMBER")
    eligible_csv = _required_env("ELIGIBLE_CSV")
    repo = _required_repo()

    logger.info(
        "Starting merge arbiter issue=%s eligible=%s repo=%s",
        issue_number,
        eligible_csv,
        repo,
    )

    candidates = _collect_candidate_data(
        repo=repo, issue_number=issue_number, eligible_csv=eligible_csv
    )
    bundle_path = _persist_bundle(issue_number=issue_number, candidates=candidates)
    logger.info("Persisted candidate evidence bundle: %s", bundle_path)

    prompt = build_prompt(
        issue_number=issue_number,
        eligible_csv=eligible_csv,
        candidates_json=json.dumps(candidates, ensure_ascii=True, indent=2),
    )
    allowed_tools = ["Bash", "Read", "Glob", "Grep", "LS", "Skill"]

    client = AgentSDKClient(model=os.environ.get("ANTHROPIC_MODEL", "").strip() or None)
    response = client.chat(
        prompt=prompt,
        max_turns=int(os.environ.get("CLAUDE_MAX_TURNS", "25")),
        allowed_tools=allowed_tools,
    )

    logger.info("Merge arbiter completed issue=%s response_chars=%s", issue_number, len(response))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Merge arbiter failed: %s", exc)
        raise SystemExit(1) from exc
