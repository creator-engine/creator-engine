from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import ce_ops_triage_queue as qt


def _issue(
    number: int,
    *,
    labels=None,
    title: str | None = None,
    body: str = "",
    assignees=None,
    state: str = "open",
) -> dict:
    return {
        "number": number,
        "title": title or f"issue {number}",
        "state": state,
        "body": body,
        "html_url": f"https://github.com/creator-engine/ce-ops/issues/{number}",
        "repository_url": "https://api.github.com/repos/creator-engine/ce-ops",
        "labels": labels or [],
        "assignees": assignees or [],
    }


def _entry(number: int, *, title: str | None = None, blockers=()) -> qt.QueueEntry:
    return qt.QueueEntry(
        issue_number=number,
        repo="creator-engine/ce-ops",
        title=title or f"issue {number}",
        work_class="S",
        mutation_class="code",
        lane="L3",
        readiness="blocked" if blockers else "ready",
        blockers=tuple(blockers),
        triaged_at="2026-06-30T00:00:00Z",
    )


class FakeGhRunner:
    def __init__(
        self,
        *,
        comments=None,
        issues=None,
        fail_search: bool = False,
        fail_patch: bool = False,
        fail_label_issues=None,
        existing_repo_labels=None,
    ):
        self.comments = comments if comments is not None else []
        self.issues = issues if issues is not None else []
        self.fail_search = fail_search
        self.fail_patch = fail_patch
        self.fail_label_issues = set(fail_label_issues or [])
        self.existing_repo_labels = set(existing_repo_labels or [])
        self.calls: list[tuple[list[str], str | None]] = []
        self.write_calls: list[tuple[list[str], str | None]] = []
        self.label_write_calls: list[tuple[list[str], str | None]] = []

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append((argv, input_text))
        path = self._path(argv)
        method = self._method(argv)
        if method in {"POST", "PATCH"}:
            self.write_calls.append((argv, input_text))
        if self._is_label_write(path, method):
            self.label_write_calls.append((argv, input_text))
        if path.startswith("repos/creator-engine/ce-ops/issues/67/comments"):
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.comments), stderr="")
        if path.startswith("search/issues"):
            if self.fail_search:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="search unavailable")
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=json.dumps({"items": self.issues}),
                stderr="",
            )
        if path.startswith("repos/creator-engine/ce-ops/issues/comments/"):
            if self.fail_patch:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="patch unavailable")
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 123}), stderr="")
        if path.startswith("repos/creator-engine/ce-ops/labels/"):
            label = path.rsplit("/", 1)[-1].replace("%3A", ":")
            if label in self.existing_repo_labels:
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"name": label}), stderr="")
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="not found")
        if path == "repos/creator-engine/ce-ops/labels" and method == "POST":
            body = json.loads(input_text or "{}")
            self.existing_repo_labels.add(body["name"])
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"name": body["name"]}), stderr="")
        if "/issues/" in path and "/labels" in path:
            issue_number = self._issue_number_from_label_path(path)
            if issue_number in self.fail_label_issues:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="label unavailable")
            return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")
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
    def _is_label_write(path: str, method: str) -> bool:
        if method not in {"POST", "DELETE"}:
            return False
        return path == "repos/creator-engine/ce-ops/labels" or (
            "/issues/" in path and "/labels" in path
        )

    @staticmethod
    def _issue_number_from_label_path(path: str) -> int:
        parts = path.split("/")
        return int(parts[parts.index("issues") + 1])


def _queue_comment(entries) -> dict:
    return {"id": 123, "body": qt.render_queue_body(entries)}


def test_empty_body_parses_to_no_entries():
    assert qt.parse_queue_entries("") == ()
    assert qt.parse_queue_entries(None) == ()


def test_render_parse_round_trip_and_idempotent_byte_equal():
    entries = (_entry(2, title="has | pipe"), _entry(1, blockers=("blocked_label",)))
    body = qt.render_queue_body(entries)

    parsed = qt.parse_queue_entries(body)

    assert parsed == (_entry(1, blockers=("blocked_label",)), _entry(2, title="has | pipe"))
    assert qt.render_queue_body(parsed) == body


def test_render_contains_sentinel_and_advisory_statement():
    body = qt.render_queue_body([_entry(1)])

    assert qt.QUEUE_SENTINEL in body
    assert qt.NON_AUTHORITY_STATEMENT in body


def test_malformed_rows_are_skipped():
    body = qt.render_queue_body([_entry(1)]) + "| not-an-int | x | y |\n"

    assert [entry.issue_number for entry in qt.parse_queue_entries(body)] == [1]


def test_scan_dedupes_by_issue_number_last_write_wins():
    fake = FakeGhRunner(
        comments=[_queue_comment([_entry(1, title="old")])],
        issues=[_issue(1, title="new"), _issue(2)],
    )

    result = qt.scan_and_triage(gh_runner=fake, apply=False, now="2026-06-30T00:00:00Z")

    by_number = {entry["issue_number"]: entry for entry in result["entries"]}
    assert sorted(by_number) == [1, 2]
    assert by_number[1]["title"] == "new"


def test_classify_issue_uses_work_mutation_and_lane_labels():
    entry = qt.classify_issue(
        _issue(
            3,
            labels=[
                {"name": "work:XS"},
                {"name": "mutation/docs"},
                {"name": "team lane:L3"},
            ],
        ),
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert entry is not None
    assert entry.work_class == "XS"
    assert entry.mutation_class == "docs"
    assert entry.lane == "L3"


def test_infer_lane_match_and_default():
    assert qt.infer_lane(["foo", "route lane/l10"]) == "L10"
    assert qt.infer_lane(["foo"]) == "unclassified"


def test_readiness_ready_and_blocked():
    ready = qt.classify_issue(_issue(4), triaged_at="2026-06-30T00:00:00Z")
    blocked = qt.classify_issue(
        _issue(5, labels=[{"name": "blocked"}]),
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert ready is not None and ready.readiness == "ready" and ready.blockers == ()
    assert blocked is not None and blocked.readiness == "blocked"
    assert blocked.blockers == ("blocked_label",)


def test_pickup_filter_ready_unblocked_unassigned_included():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(
                21,
                labels=[
                    {"name": "lane:l2"},
                    {"name": "mutation:docs"},
                    {"name": "work:M"},
                    {"name": "customer-visible"},
                ],
            )
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert len(candidates) == 1
    payload = candidates[0].to_dict()
    assert payload == {
        "issue_number": 21,
        "repo": "creator-engine/ce-ops",
        "labels": ["customer-visible", "lane:l2", "mutation:docs", "work:M"],
        "work_class": "M",
        "mutation_class": "docs",
        "lane": "L2",
        "readiness": "ready",
    }


def test_pickup_filter_blocked_assigned_and_in_progress_excluded():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(31, labels=[{"name": "blocked"}]),
            _issue(32, assignees=[{"login": "ce-dev-2"}]),
            _issue(33, labels=[{"name": "status:running"}]),
            _issue(34, labels=[{"name": "lane:l4"}]),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [34]


def test_pickup_filter_deterministic_ordering():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(43, labels=[{"name": "lane:l2"}, {"name": "work:XS"}]),
            _issue(42, labels=[{"name": "lane:l1"}, {"name": "work:M"}]),
            _issue(41, labels=[{"name": "lane:l1"}, {"name": "work:XS"}]),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [41, 42, 43]


def test_pickup_filter_excludes_awaiting_operator_hold_marker():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(61, body="Parked. ⏸ AWAITING-OPERATOR confirm before proceeding."),
            _issue(62),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [62]


def test_pickup_filter_excludes_awaiting_operator_label_no_body_marker():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(69, labels=[{"name": "awaiting-operator"}]),
            _issue(70),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [70]


def test_pickup_filter_excludes_awaiting_operator_hold_label_variant_case_and_whitespace():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(75, labels=[{"name": " Awaiting-Operator/Hold "}]),
            _issue(76),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [76]


def test_pickup_payload_carries_requires_live_recheck_signal():
    payload = qt.pickup_payload(
        qt.pickup_candidates_from_issues(
            [_issue(77)],
            triaged_at="2026-06-30T00:00:00Z",
        )
    )

    assert payload["requires_live_recheck"] is True
    assert "gh_runner" in payload["requires_live_recheck_note"]


def test_pickup_filter_excludes_aggregate_epic_issue():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(63, labels=[{"name": "epic"}]),
            _issue(64),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [64]


def test_pickup_filter_excludes_closed_issue():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(65, state="closed"),
            _issue(66),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [66]


def test_pickup_filter_excludes_done_labeled_issue():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(67, labels=[{"name": "done"}]),
            _issue(68),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert [candidate.issue_number for candidate in candidates] == [68]


def test_pickup_filter_dedupes_by_issue_number_last_write_wins():
    candidates = qt.pickup_candidates_from_issues(
        [
            _issue(71, title="stale", labels=[{"name": "lane:l1"}]),
            _issue(71, title="fresh", labels=[{"name": "lane:l1"}, {"name": "work:M"}]),
        ],
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert len(candidates) == 1
    assert candidates[0].issue_number == 71
    assert candidates[0].work_class == "M"


def test_pickup_filter_emit_mode_dry_run_no_mutation():
    fake = FakeGhRunner(comments=[_queue_comment([])], issues=[_issue(51)])

    result = qt.scan_and_triage(gh_runner=fake, apply=False, now="2026-06-30T00:00:00Z")

    assert result["applied"] is False
    assert result["pickup"]["candidate_count"] == 1
    assert result["pickup"]["advisory"] == qt.NON_AUTHORITY_STATEMENT
    assert result["pickup"]["candidates"][0]["issue_number"] == 51
    assert fake.write_calls == []
    assert fake.label_write_calls == []


def test_pickup_filter_empty_set():
    payload = qt.pickup_payload(
        qt.pickup_candidates_from_issues([], triaged_at="2026-06-30T00:00:00Z")
    )

    assert payload["candidate_count"] == 0
    assert payload["candidates"] == []
    assert payload["advisory"] == qt.NON_AUTHORITY_STATEMENT


def test_plan_triage_entry_is_pure_and_stable():
    raw = _issue(6, labels=[{"name": "mutation:code"}])

    first = qt.plan_triage_entry(raw, triaged_at="2026-06-30T00:00:00Z")
    second = qt.plan_triage_entry(raw, triaged_at="2026-06-30T00:00:00Z")

    assert first == second


def test_plan_triage_entry_reuses_private_forge_inference(monkeypatch):
    calls: list[str] = []

    def fake_work(candidate):
        calls.append(f"work:{candidate.number}")
        return "M"

    def fake_mutation(candidate):
        calls.append(f"mutation:{candidate.number}")
        return "security"

    monkeypatch.setattr(qt.forge_triage, "_infer_work_class", fake_work)
    monkeypatch.setattr(qt.forge_triage, "_infer_mutation_class", fake_mutation)

    entry = qt.plan_triage_entry(_issue(7), triaged_at="2026-06-30T00:00:00Z")

    assert entry is not None
    assert entry.work_class == "M"
    assert entry.mutation_class == "security"
    assert calls == ["work:7", "mutation:7"]


def test_dry_run_makes_zero_write_calls():
    fake = FakeGhRunner(comments=[_queue_comment([])], issues=[_issue(8)])

    result = qt.scan_and_triage(gh_runner=fake, apply=False, now="2026-06-30T00:00:00Z")

    assert result["applied"] is False
    assert fake.write_calls == []
    assert result["labels"]["planned"] is True
    assert result["labels"]["deltas"][0]["add"] == ["triage:ready", "wc:S"]
    assert fake.label_write_calls == []


def test_apply_patches_existing_queue_comment():
    fake = FakeGhRunner(
        comments=[_queue_comment([])],
        issues=[_issue(9, labels=[{"name": "triage:ready"}, {"name": "wc:S"}])],
    )

    result = qt.scan_and_triage(gh_runner=fake, apply=True, now="2026-06-30T00:00:00Z")

    assert result["applied"] is True
    assert len(fake.write_calls) == 1
    argv, body = fake.write_calls[0]
    assert "--method" in argv and "PATCH" in argv
    assert "repos/creator-engine/ce-ops/issues/comments/123" in argv
    assert body is not None and qt.QUEUE_SENTINEL in json.loads(body)["body"]
    assert fake.label_write_calls == []


def test_label_delta_only_manages_work_class_and_readiness_namespaces():
    delta = qt.plan_label_delta(
        _entry(10, blockers=("dependency",)),
        ["wc:S", "triage:ready", "external", "lane:l3"],
    )

    assert delta.current_managed == ("triage:ready", "wc:S")
    assert delta.desired == ("triage:blocked", "wc:S")
    assert delta.add == ("triage:blocked",)
    assert delta.remove == ("triage:ready",)


def test_apply_label_idempotent_re_run_is_noop_for_managed_labels():
    fake = FakeGhRunner(
        comments=[_queue_comment([])],
        issues=[_issue(11, labels=[{"name": "triage:ready"}, {"name": "wc:S"}])],
    )

    result = qt.scan_and_triage(gh_runner=fake, apply=True, now="2026-06-30T00:00:00Z")

    assert result["labels"]["delta_count"] == 0
    assert result["labels"]["deltas"][0]["add"] == []
    assert result["labels"]["deltas"][0]["remove"] == []
    assert fake.label_write_calls == []


def test_apply_label_error_isolated_per_issue_and_queue_still_posts():
    fake = FakeGhRunner(
        comments=[_queue_comment([])],
        issues=[
            _issue(12, labels=[{"name": "wc:M"}, {"name": "triage:blocked"}]),
            _issue(13, labels=[{"name": "wc:M"}, {"name": "triage:blocked"}]),
        ],
        fail_label_issues={12},
    )

    result = qt.scan_and_triage(gh_runner=fake, apply=True, now="2026-06-30T00:00:00Z")

    label_deltas = {delta["issue_number"]: delta for delta in result["labels"]["deltas"]}
    assert result["applied"] is True
    assert result["labels"]["error_count"] == 1
    assert result["labels"]["missing_label_policy"] == "create_missing"
    assert label_deltas[12]["applied"] is False
    assert "error" in label_deltas[12]
    assert label_deltas[13]["applied"] is True
    assert any("label_apply_failed:creator-engine/ce-ops#12" in warning for warning in result["warnings"])


def test_audit_record_is_valid_json_with_advisory_statement(tmp_path):
    path = qt.write_audit_record(
        tmp_path,
        {"kind": "test-audit", "entries": []},
        triaged_at="2026-06-30T00:00:00Z",
    )

    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["advisory"] == qt.NON_AUTHORITY_STATEMENT
    assert payload["kind"] == "test-audit"


@pytest.mark.parametrize(
    "argv",
    [["triage", "queue", "scan", "--help"], ["triage", "queue", "inspect", "--help"]],
)
def test_triage_queue_cli_help_exits_zero(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)

    assert exc.value.code == 0
