"""Generate concise Chinese operations analysis from flywheel metrics."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from shared.agent_sdk import AgentSDKClient

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricsSnapshot:
    window_days: int
    now_utc: str
    cutoff_date: str
    open_issues: int
    p0: int
    p1: int
    p2: int
    p3: int
    open_candidate_prs: int
    merged_recent: int
    closed_unmerged_recent: int
    ci_recent_total: int
    ci_recent_failed: int
    ci_fail_rate: float
    max_issue_cap: int


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _to_snapshot(payload: dict[str, Any]) -> MetricsSnapshot:
    return MetricsSnapshot(
        window_days=int(payload.get("window_days", 7)),
        now_utc=str(payload.get("now_utc", "")),
        cutoff_date=str(payload.get("cutoff_date", "")),
        open_issues=int(payload.get("open_issues", 0)),
        p0=int(payload.get("p0", 0)),
        p1=int(payload.get("p1", 0)),
        p2=int(payload.get("p2", 0)),
        p3=int(payload.get("p3", 0)),
        open_candidate_prs=int(payload.get("open_candidate_prs", 0)),
        merged_recent=int(payload.get("merged_recent", 0)),
        closed_unmerged_recent=int(payload.get("closed_unmerged_recent", 0)),
        ci_recent_total=int(payload.get("ci_recent_total", 0)),
        ci_recent_failed=int(payload.get("ci_recent_failed", 0)),
        ci_fail_rate=float(payload.get("ci_fail_rate", 0.0)),
        max_issue_cap=int(payload.get("max_issue_cap", 20)),
    )


def _rule_based_analysis(s: MetricsSnapshot) -> dict[str, Any]:
    status = "OK"
    risks: list[str] = []
    actions: list[str] = []

    if s.open_issues > s.max_issue_cap:
        status = "WARN"
        risks.append(f"Issue 总量超上限：{s.open_issues}/{s.max_issue_cap}。")
        actions.append("执行 issue-curation 并优先关闭低价值 p3/p2 历史问题。")

    if s.ci_fail_rate >= 30 and s.ci_recent_total >= 5:
        status = "WARN"
        risks.append(
            f"CI 失败率偏高：{s.ci_fail_rate:.2f}%（{s.ci_recent_failed}/{s.ci_recent_total}）。"
        )
        actions.append("优先处理最近 24h 的 CI 失败根因，降低重复失败。")

    if s.open_candidate_prs >= 8:
        status = "WARN"
        risks.append(f"候选 PR 积压：{s.open_candidate_prs}。")
        actions.append("提高 merge-pr 调度频率或临时降低候选并行度。")

    if s.merged_recent == 0 and s.open_issues > 0:
        status = "WARN"
        risks.append(f"近 {s.window_days} 天无 AUTOFIX 合并，吞吐接近停滞。")
        actions.append("抽样复盘最近 3 个被关闭候选 PR，修正质量门与提示词。")

    if not risks:
        risks.append("核心指标稳定，无明显运营风险。")
    if not actions:
        actions.append("保持当前参数，继续观察 24h 趋势。")

    summary = (
        f"状态 {status}。"
        f"Issue={s.open_issues}，候选PR={s.open_candidate_prs}，"
        f"近{s.window_days}天合并={s.merged_recent}，CI失败率={s.ci_fail_rate:.2f}%。"
    )
    return {
        "status": status,
        "summary": summary,
        "risks": risks[:3],
        "actions": actions[:3],
        "source": "rule",
    }


def _try_sdk_analysis(s: MetricsSnapshot, fallback: dict[str, Any]) -> dict[str, Any]:
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    if not token:
        return fallback

    model = os.environ.get("ANTHROPIC_MODEL", "").strip() or None
    client = AgentSDKClient(model=model)
    prompt = f"""
你是飞轮运营分析助手。基于以下指标生成简洁中文结论。
要求：
1. 只输出 JSON，不要额外文本。
2. 字段必须包含：status, summary, risks, actions。
3. summary 不超过 60 字；risks 和 actions 各最多 3 条，每条不超过 40 字。
4. 结论必须可执行，不要空话。

指标：
{json.dumps(s.__dict__, ensure_ascii=False)}
""".strip()

    try:
        response = client.chat(
            prompt=prompt,
            max_turns=int(os.environ.get("CLAUDE_METRICS_MAX_TURNS", "8")),
            allowed_tools=["Read", "Grep", "Glob", "LS", "Skill"],
        )
        parsed: dict[str, Any]
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", response)
            if not match:
                raise
            parsed = json.loads(match.group(0))
        status = str(parsed.get("status", fallback["status"])).upper()
        summary = str(parsed.get("summary", fallback["summary"])).strip()
        risks = [str(x).strip() for x in parsed.get("risks", []) if str(x).strip()][:3]
        actions = [str(x).strip() for x in parsed.get("actions", []) if str(x).strip()][:3]
        if not risks:
            risks = fallback["risks"]
        if not actions:
            actions = fallback["actions"]
        return {
            "status": status if status in {"OK", "WARN"} else fallback["status"],
            "summary": summary or fallback["summary"],
            "risks": risks,
            "actions": actions,
            "source": "sdk",
        }
    except Exception as exc:
        logger.warning("SDK analysis failed; fallback to rule-only analysis: %s", exc)
        return fallback


def _to_markdown(result: dict[str, Any]) -> str:
    risks = result.get("risks", [])
    actions = result.get("actions", [])
    risk_lines = "\n".join(f"- {item}" for item in risks) if risks else "- 无"
    action_lines = "\n".join(f"- {item}" for item in actions) if actions else "- 无"
    return "\n".join(
        [
            "### 运营结论",
            f"- 状态：**{result.get('status', 'WARN')}**",
            f"- 一句话：{result.get('summary', '无')}",
            f"- 分析来源：`{result.get('source', 'rule')}`",
            "",
            "### 主要风险",
            risk_lines,
            "",
            "### 建议动作",
            action_lines,
        ]
    )


def main() -> int:
    payload = json.loads(_required_env("METRICS_JSON"))
    snapshot = _to_snapshot(payload)
    base = _rule_based_analysis(snapshot)
    result = _try_sdk_analysis(snapshot, base)
    markdown = _to_markdown(result)

    output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if output:
        with open(output, "a", encoding="utf-8") as fp:
            fp.write("analysis_md<<EOF\n")
            fp.write(markdown)
            fp.write("\nEOF\n")
            fp.write(f"analysis_source={result.get('source', 'rule')}\n")
            fp.write(f"analysis_status={result.get('status', 'WARN')}\n")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
