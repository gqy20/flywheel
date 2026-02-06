from scripts.shared.select_issue import (
    IssueCandidate,
    _busy_issue_numbers_from_titles,
    _select_best_issue,
)
from scripts.shared.select_merge_eligible import _is_pr_candidate_eligible


def test_busy_issue_numbers_extracts_autofix_prefix_only() -> None:
    titles = [
        "[AUTOFIX][ISSUE-12][CANDIDATE-1] fix",
        "[AUTOFIX][ISSUE-3][CANDIDATE-2] fix",
        "normal pr title",
        "[AUTOFIX][ISSUE-x][CANDIDATE-1] invalid",
    ]
    assert _busy_issue_numbers_from_titles(titles) == {3, 12}


def test_select_best_issue_filters_labels_and_busy_and_sorts() -> None:
    issues = [
        IssueCandidate(5, "a", "u5", {"p1"}, 1),
        IssueCandidate(2, "b", "u2", {"p0", "frozen"}, 0),
        IssueCandidate(3, "c", "u3", {"p0"}, 0),
        IssueCandidate(4, "d", "u4", {"p2"}, 2),
    ]
    picked = _select_best_issue(issues, busy={3})
    assert [i.number for i in picked] == [5, 4]


def test_pr_candidate_eligibility_requires_clean_ready_and_checks() -> None:
    pr = {"number": 10, "draft": False, "mergeable_state": "clean", "head": {"sha": "abc"}}
    assert _is_pr_candidate_eligible(pr, checks_ok=True) is True
    assert _is_pr_candidate_eligible(pr, checks_ok=False) is False

    dirty = {"number": 10, "draft": False, "mergeable_state": "dirty", "head": {"sha": "abc"}}
    assert _is_pr_candidate_eligible(dirty, checks_ok=True) is False

    draft = {"number": 10, "draft": True, "mergeable_state": "clean", "head": {"sha": "abc"}}
    assert _is_pr_candidate_eligible(draft, checks_ok=True) is False
