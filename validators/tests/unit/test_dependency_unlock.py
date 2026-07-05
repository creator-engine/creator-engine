from __future__ import annotations

import json
import subprocess

from creator_engine_validator import dependency_unlock as du

MERGED = du.MergedItem(
    repo="creator-engine/creator-engine",
    number=900,
    merge_sha="abc123def",
    merged_at="2026-07-05T00:00:00Z",
)


def _issue(
    number: int,
    *,
    repo: str = "creator-engine/ce-ops",
    labels=(),
    body: str = "",
    state: str = "open",
    title: str | None = None,
    extra: dict | None = None,
) -> dict:
    payload = {
        "number": number,
        "title": title or f"issue {number}",
        "state": state,
        "body": body,
        "repository_url": f"https://api.github.com/repos/{repo}",
        "labels": [{"name": label} for label in labels],
        "assignees": [],
    }
    if extra:
        payload.update(extra)
    return payload


def _pull(number: int, *, merged: bool, state: str = "closed") -> dict:
    return {"number": number, "merged": merged, "state": state}


class FakeGhRunner:
    """Fake ``gh api`` seam: search + single-issue/pull GET + label DELETE."""

    def __init__(
        self,
        *,
        search_issues=(),
        issues=None,
        pulls=None,
        fail_search: bool = False,
        fail_remove_numbers=(),
    ):
        self.search_issues = list(search_issues)
        self.issues = dict(issues or {})
        self.pulls = dict(pulls or {})
        self.fail_search = fail_search
        self.fail_remove_numbers = set(fail_remove_numbers)
        self.calls: list[tuple[list[str], str | None]] = []
        self.write_calls: list[tuple[str, str]] = []

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append((argv, input_text))
        method = self._method(argv)
        path = self._path(argv)
        if method in {"POST", "PATCH", "DELETE"}:
            self.write_calls.append((method, path))

        if path.startswith("search/issues"):
            if self.fail_search:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="search unavailable")
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps({"items": self.search_issues}), stderr=""
            )

        if "/pulls/" in path and method == "GET":
            key = self._repo_number(path, "pulls")
            payload = self.pulls.get(key)
            if payload is None:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="not found")
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        if "/labels/" in path and method == "DELETE":
            number = self._issue_number_from_label_path(path)
            if number in self.fail_remove_numbers:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="remove failed")
            return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

        if "/issues/" in path and "/labels" not in path and method == "GET":
            key = self._repo_number(path, "issues")
            payload = self.issues.get(key)
            if payload is None:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="not found")
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    @staticmethod
    def _method(argv: list[str]) -> str:
        if "--method" in argv:
            return argv[argv.index("--method") + 1]
        return "GET"

    @staticmethod
    def _path(argv: list[str]) -> str:
        for index, token in enumerate(argv):
            if token != "api":
                continue
            rest = argv[index + 1 :]
            if rest[:2] == ["--method", FakeGhRunner._method(argv)]:
                rest = rest[2:]
            return next(item for item in rest if not item.startswith("-"))
        raise AssertionError(f"no gh api path in {argv!r}")

    @staticmethod
    def _repo_number(path: str, kind: str) -> tuple[str, int]:
        parts = path.split("?")[0].split("/")
        idx = parts.index(kind)
        owner, name = parts[1], parts[2]
        number = parts[idx + 1]
        return f"{owner}/{name}", int(number)

    @staticmethod
    def _issue_number_from_label_path(path: str) -> int:
        parts = path.split("/")
        return int(parts[parts.index("issues") + 1])


# ---------------------------------------------------------------------------
# resolve_apply_mode / switches
# ---------------------------------------------------------------------------


def test_resolve_apply_mode_matrix():
    assert du.resolve_apply_mode(run_mode=None, kill_switch=None) == (False, "shadow")
    assert du.resolve_apply_mode(run_mode="other", kill_switch=None) == (False, "shadow")
    assert du.resolve_apply_mode(run_mode="live", kill_switch=None) == (True, "live")
    assert du.resolve_apply_mode(run_mode="LIVE", kill_switch="") == (True, "live")
    assert du.resolve_apply_mode(run_mode="live", kill_switch="true") == (False, "shadow")
    assert du.resolve_apply_mode(run_mode="live", kill_switch="halt") == (False, "shadow")


# ---------------------------------------------------------------------------
# merged_item_from_event
# ---------------------------------------------------------------------------


def test_merged_item_from_event_parses_pull_request_payload():
    event = {
        "pull_request": {
            "number": 900,
            "merged": True,
            "merge_commit_sha": "abc123def",
            "merged_at": "2026-07-05T00:00:00Z",
        },
        "repository": {"full_name": "creator-engine/creator-engine"},
    }
    assert du.merged_item_from_event(event) == MERGED


def test_merged_item_from_event_none_when_not_merged():
    event = {"pull_request": {"number": 1, "merged": False}}
    assert du.merged_item_from_event(event) is None


def test_merged_item_from_event_none_when_missing_evidence():
    event = {"pull_request": {"number": 1, "merged": True}}
    assert du.merged_item_from_event(event) is None


def test_merged_item_from_event_none_when_not_a_pull_request_event():
    assert du.merged_item_from_event({"issue": {"number": 1}}) is None


# ---------------------------------------------------------------------------
# search helper -- new surface
# ---------------------------------------------------------------------------


def test_search_dependency_candidates_dedupes_by_number():
    runner = FakeGhRunner(search_issues=[_issue(200), _issue(200), _issue(201)])
    items, ok, warning = du.search_dependency_candidates(MERGED, gh_runner=runner)
    assert ok is True
    assert warning is None
    assert sorted(item["number"] for item in items) == [200, 201]


def test_search_dependency_candidates_failure_is_inconclusive_not_partial():
    runner = FakeGhRunner(search_issues=[_issue(200)], fail_search=True)
    items, ok, warning = du.search_dependency_candidates(MERGED, gh_runner=runner)
    assert ok is False
    assert items == ()
    assert warning is not None


def test_evaluate_pr_merge_refuses_when_search_inconclusive():
    runner = FakeGhRunner(fail_search=True)
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["status"] == "refused"
    assert result["refusal_reason"] == "search_inconclusive"
    assert result.get("proposals", []) == []
    assert runner.write_calls == []


# ---------------------------------------------------------------------------
# (a) same event twice -> one proposal
# ---------------------------------------------------------------------------


def test_duplicate_search_hits_dedupe_to_one_proposal():
    issue = _issue(100, labels=["blocked:creator-engine/creator-engine#900"])
    runner = FakeGhRunner(
        search_issues=[issue, issue],
        issues={("creator-engine/ce-ops", 100): issue},
    )
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 1


def test_same_event_evaluated_twice_yields_identical_dedup_key():
    issue = _issue(101, labels=["blocked:creator-engine/creator-engine#900"])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 101): issue})
    result1 = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    result2 = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result1["proposals"][0]["dedup_key"] == result2["proposals"][0]["dedup_key"]


# ---------------------------------------------------------------------------
# (b) fail-closed on unparseable / ambiguous multi-resolving refs
# ---------------------------------------------------------------------------


def test_unparseable_secondary_blocker_ref_stays_blocked_despite_matching_primary():
    issue = _issue(
        110,
        labels=[
            "blocked:creator-engine/creator-engine#900",
            "blocked:!!!not-a-valid-ref!!!",
        ],
    )
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 110): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    candidate = result["candidates"][0]
    assert candidate["status"] == "blocked"
    assert candidate["reason"] == "unparseable_blocker_ref"


def test_ambiguous_blocker_ref_token_stays_blocked():
    issue = _issue(
        111,
        labels=["blocked:creator-engine/creator-engine#900"],
        extra={"blocked_by": "creator-engine/ce-ops#123 creator-engine/ce-ops#456"},
    )
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 111): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    candidate = result["candidates"][0]
    assert candidate["status"] == "blocked"
    assert candidate["reason"] == "ambiguous_blocker_ref"


def test_multiple_blockers_all_must_resolve_union_rule():
    issue = _issue(
        170,
        labels=[
            "blocked:creator-engine/creator-engine#900",
            "blocked:creator-engine/ce-ops#999",
        ],
    )
    runner = FakeGhRunner(
        search_issues=[issue],
        issues={
            ("creator-engine/ce-ops", 170): issue,
            ("creator-engine/ce-ops", 999): _issue(999, state="open"),
        },
    )
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    candidate = result["candidates"][0]
    assert candidate["status"] == "blocked"
    assert candidate["reason"] == "blocker_unresolved"


# ---------------------------------------------------------------------------
# (c) non-dependency hold blocks despite resolved deps
# ---------------------------------------------------------------------------


def test_non_dependency_hold_label_blocks_despite_resolved_deps():
    issue = _issue(120, labels=["blocked:creator-engine/creator-engine#900", "hold"])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 120): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    candidate = result["candidates"][0]
    assert candidate["status"] == "blocked"
    assert candidate["reason"] == "non_dependency_hold_present"


# ---------------------------------------------------------------------------
# (d) shadow mode makes ZERO write-verb calls
# ---------------------------------------------------------------------------


def test_shadow_mode_zero_write_calls():
    issue = _issue(130, labels=["blocked:creator-engine/creator-engine#900"])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 130): issue})
    result = du.evaluate_pr_merge(
        MERGED, gh_runner=runner, run_mode=None, kill_switch=None, now="2026-07-05T00:00:00Z"
    )
    assert result["mode"] == "shadow"
    assert result["proposal_count"] == 1
    assert result["proposals"][0]["applied"] is False
    assert runner.write_calls == []


# ---------------------------------------------------------------------------
# (e) kill-switch truthy forces shadow even with RUN_MODE=live
# ---------------------------------------------------------------------------


def test_kill_switch_forces_shadow_even_with_run_mode_live():
    issue = _issue(140, labels=["blocked:creator-engine/creator-engine#900"])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 140): issue})
    result = du.evaluate_pr_merge(
        MERGED, gh_runner=runner, run_mode="live", kill_switch="true", now="2026-07-05T00:00:00Z"
    )
    assert result["mode"] == "shadow"
    assert result["apply_requested"] is False
    assert runner.write_calls == []


def test_live_mode_removes_resolved_dependency_hold_label():
    label = "blocked:creator-engine/creator-engine#900"
    issue = _issue(150, labels=[label])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 150): issue})
    result = du.evaluate_pr_merge(
        MERGED, gh_runner=runner, run_mode="live", kill_switch=None, now="2026-07-05T00:00:00Z"
    )
    assert result["mode"] == "live"
    assert result["proposals"][0]["applied"] is True
    assert result["proposals"][0]["removed"] == [label]
    assert any(method == "DELETE" for method, _ in runner.write_calls)


def test_apply_unlock_label_already_absent_is_success_noop():
    repo = "creator-engine/ce-ops"
    label = "blocked:creator-engine/creator-engine#900"
    already_clean = _issue(160, labels=[])
    runner = FakeGhRunner(issues={(repo, 160): already_clean})
    outcome = du._apply_unlock(repo=repo, number=160, labels_to_remove=(label,), gh_runner=runner)
    assert outcome == {"applied": True, "removed": [label]}
    assert runner.write_calls == []


def test_apply_unlock_aborts_when_non_dependency_hold_appeared():
    repo = "creator-engine/ce-ops"
    label = "blocked:creator-engine/creator-engine#900"
    stale = _issue(161, labels=[label, "hold"])
    runner = FakeGhRunner(issues={(repo, 161): stale})
    outcome = du._apply_unlock(repo=repo, number=161, labels_to_remove=(label,), gh_runner=runner)
    assert outcome == {"applied": False, "warning": "stale_mutation_target"}
    assert runner.write_calls == []


# ---------------------------------------------------------------------------
# (f) closed-without-merge rule
# ---------------------------------------------------------------------------


def test_resolve_blocker_pr_closed_without_merge_stays_blocking():
    ref = du.BlockerRef(repo="creator-engine/creator-engine", number=901)
    runner = FakeGhRunner(
        issues={("creator-engine/creator-engine", 901): {"number": 901, "state": "closed", "pull_request": {}}},
        pulls={("creator-engine/creator-engine", 901): _pull(901, merged=False, state="closed")},
    )
    resolution = du.resolve_blocker(ref, merged=MERGED, gh_runner=runner)
    assert resolution.resolved is False
    assert resolution.state == "closed_unmerged"


def test_resolve_blocker_issue_closed_not_planned_stays_blocking():
    ref = du.BlockerRef(repo="creator-engine/ce-ops", number=902)
    runner = FakeGhRunner(
        issues={("creator-engine/ce-ops", 902): {"number": 902, "state": "closed", "state_reason": "not_planned"}},
    )
    resolution = du.resolve_blocker(ref, merged=MERGED, gh_runner=runner)
    assert resolution.resolved is False
    assert resolution.state == "closed_not_planned"


def test_resolve_blocker_issue_closed_completed_resolves():
    ref = du.BlockerRef(repo="creator-engine/ce-ops", number=903)
    runner = FakeGhRunner(
        issues={("creator-engine/ce-ops", 903): {"number": 903, "state": "closed", "state_reason": "completed"}},
    )
    resolution = du.resolve_blocker(ref, merged=MERGED, gh_runner=runner)
    assert resolution.resolved is True
    assert resolution.state == "closed_completed"


def test_resolve_blocker_pr_merged_resolves():
    ref = du.BlockerRef(repo="creator-engine/creator-engine", number=904)
    runner = FakeGhRunner(
        issues={("creator-engine/creator-engine", 904): {"number": 904, "state": "closed", "pull_request": {}}},
        pulls={("creator-engine/creator-engine", 904): _pull(904, merged=True, state="closed")},
    )
    resolution = du.resolve_blocker(ref, merged=MERGED, gh_runner=runner)
    assert resolution.resolved is True
    assert resolution.state == "merged"


def test_resolve_blocker_the_triggering_pr_itself_short_circuits_to_merged():
    resolution = du.resolve_blocker(MERGED.ref, merged=MERGED, gh_runner=FakeGhRunner())
    assert resolution.resolved is True
    assert resolution.kind == "pr"
    assert resolution.state == "merged"


def test_resolve_blocker_inaccessible_ref_stays_blocking():
    ref = du.BlockerRef(repo="creator-engine/ce-ops", number=905)
    runner = FakeGhRunner(issues={})
    resolution = du.resolve_blocker(ref, merged=MERGED, gh_runner=runner)
    assert resolution.resolved is False
    assert resolution.state == "inaccessible"


# ---------------------------------------------------------------------------
# candidate relevance / re-read / declaration-surface coverage
# ---------------------------------------------------------------------------


def test_candidate_not_relevant_to_event_is_skipped():
    issue = _issue(220, labels=["blocked:creator-engine/other-repo#5"])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 220): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    assert result["candidates"][0]["status"] == "skipped"
    assert result["candidates"][0]["reason"] == "not_a_declared_blocker"


def test_candidate_reread_failure_stays_blocked():
    issue = _issue(230, labels=["blocked:creator-engine/creator-engine#900"])
    runner = FakeGhRunner(search_issues=[issue], issues={})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    assert result["candidates"][0]["status"] == "blocked"
    assert result["candidates"][0]["reason"] == "reread_failed"


def test_body_only_declaration_without_hold_label_has_nothing_to_unlock():
    issue = _issue(240, body="Blocked by: creator-engine/creator-engine#900")
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 240): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    assert result["candidates"][0]["reason"] == "no_dependency_hold_label_present"


def test_structured_dependency_field_declares_blocker_and_unlocks_label():
    label = "blocked:creator-engine/creator-engine#900"
    issue = _issue(250, labels=[label], extra={"depends_on": ["creator-engine/creator-engine#900"]})
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 250): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 1
    assert result["proposals"][0]["labels_to_remove"] == [label]


def test_bare_number_hold_label_within_same_repo_resolves():
    same_repo_merged = du.MergedItem(
        repo="creator-engine/ce-ops", number=900, merge_sha="deadbeef", merged_at="2026-07-05T00:00:00Z"
    )
    label = "blocked:900"
    issue = _issue(260, labels=[label])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 260): issue})
    result = du.evaluate_pr_merge(same_repo_merged, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 1
    assert result["proposals"][0]["labels_to_remove"] == [label]


def test_candidate_closed_issue_is_skipped_not_evaluated():
    issue = _issue(270, labels=["blocked:creator-engine/creator-engine#900"], state="closed")
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 270): issue})
    result = du.evaluate_pr_merge(MERGED, gh_runner=runner, now="2026-07-05T00:00:00Z")
    assert result["proposal_count"] == 0
    assert result["candidates"][0]["status"] == "skipped"
    assert result["candidates"][0]["reason"] == "candidate_not_open"


# ---------------------------------------------------------------------------
# audit record
# ---------------------------------------------------------------------------


def test_evaluate_pr_merge_writes_audit_record(tmp_path):
    issue = _issue(210, labels=["blocked:creator-engine/creator-engine#900"])
    runner = FakeGhRunner(search_issues=[issue], issues={("creator-engine/ce-ops", 210): issue})
    result = du.evaluate_pr_merge(
        MERGED, gh_runner=runner, audit_root=tmp_path, now="2026-07-05T01-02-03Z"
    )
    files = list(tmp_path.glob("ce-dependency-unlock-*.json"))
    assert len(files) == 1
    on_disk = json.loads(files[0].read_text())
    assert on_disk["proposal_count"] == result["proposal_count"]
