from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import ce_ops_triage_queue as qt


def _issue(number: int, *, labels=None, title: str | None = None, body: str = "") -> dict:
    return {
        "number": number,
        "title": title or f"issue {number}",
        "state": "open",
        "body": body,
        "html_url": f"https://github.com/creator-engine/ce-ops/issues/{number}",
        "repository_url": "https://api.github.com/repos/creator-engine/ce-ops",
        "labels": labels or [],
        "assignees": [],
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
    ):
        self.comments = comments if comments is not None else []
        self.issues = issues if issues is not None else []
        self.fail_search = fail_search
        self.fail_patch = fail_patch
        self.calls: list[tuple[list[str], str | None]] = []
        self.write_calls: list[tuple[list[str], str | None]] = []

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append((argv, input_text))
        path = self._path(argv)
        method = self._method(argv)
        if method in {"POST", "PATCH"}:
            self.write_calls.append((argv, input_text))
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


def test_apply_patches_existing_queue_comment():
    fake = FakeGhRunner(comments=[_queue_comment([])], issues=[_issue(9)])

    result = qt.scan_and_triage(gh_runner=fake, apply=True, now="2026-06-30T00:00:00Z")

    assert result["applied"] is True
    assert len(fake.write_calls) == 1
    argv, body = fake.write_calls[0]
    assert "--method" in argv and "PATCH" in argv
    assert "repos/creator-engine/ce-ops/issues/comments/123" in argv
    assert body is not None and qt.QUEUE_SENTINEL in json.loads(body)["body"]


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
