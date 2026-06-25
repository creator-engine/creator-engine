"""Offline tests for the Integrator merge-queue belt poller."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess

from creator_engine_validator import v3_cli
from creator_engine_validator.search_rate_limiter import SearchRateLimiter
from creator_engine_validator.forge.approval_capability import (
    ApprovalCapabilityClaims,
    ApprovalCapabilityVerifier,
    ApprovalWallConfig,
    ApprovalWallState,
    approval_wall_secret_supplier_from_secret_identity_backend,
    extract_approval_capability_marker,
    issue_approval_capability,
    load_approval_wall_state,
    resolve_approval_wall,
    save_approval_wall_state,
)
from creator_engine_validator.secret_identity import (
    FakeSecretIdentityBackend,
    SecretRef,
    SecretRequest,
)
from creator_engine_validator.forge import integrator_belt as belt
from creator_engine_validator.forge.eviction_detection import RepairNeededEvent, RepairPollResult
from creator_engine_validator.forge.integrator_executor import ExecutorPublishResult, ExecutorRefs
from creator_engine_validator.forge.integrator_runner import ConflictSnapshot, RepairWorkItem

REPO = "creator-engine/creator-engine"
PR = 218
HEAD = "a" * 40
BASE = "b" * 40
BRANCH = "feature-integrator"
CARRIER = ".ce/pr-manifests/feature-integrator.md"
CARRIER_2 = ".ce/pr-manifests/feature-integrator-2.md"
AUTHORIZED_REVIEWER = "ce-reviewer"
APPROVER = AUTHORIZED_REVIEWER
POLICY_SHA = "approval-wall-policy-v1"
ISSUED_AT = 1_800_000_000
EXPIRES_AT = ISSUED_AT + 600
APPROVAL_SECRET = b"approval-wall-test-secret"
_OURS = "<" * 7 + " ours"
_SEP = "=" * 7
_THEIRS = ">" * 7 + " theirs"


def _test_limiter(tmp_path, clock=None):
    return SearchRateLimiter(
        tmp_path / "search-rate.json",
        rate_per_minute=6000,
        burst=1,
        jitter_seconds=0,
        clock=clock or (lambda: 0.0),
        random_float=lambda: 0.0,
    )


def _event(**overrides) -> RepairNeededEvent:
    data = {
        "repo": REPO,
        "pr_number": PR,
        "head_sha": HEAD,
        "merge_state_status": "DIRTY",
        "mergeable": "CONFLICTING",
        "reason": "dirty",
        "review_decision": "APPROVED",
        "rollup_state": "SUCCESS",
    }
    data.update(overrides)
    return RepairNeededEvent(**data)


def _append_conflict() -> str:
    return f"""existing
{_OURS}
beta
{_SEP}
alpha
{_THEIRS}
tail
"""


def _semantic_conflict() -> str:
    return f"""{{"lockfileVersion": 3,
{_OURS}
"packages": {{}}
{_SEP}
"dependencies": {{}}
{_THEIRS}
}}
"""


class FakeBeltAdapter:
    def __init__(self, conflicts: tuple[ConflictSnapshot, ...]):
        self.conflicts = conflicts
        self.applied: dict[str, str] = {}
        self.published = 0

    def repair_work_item(self, event: RepairNeededEvent) -> RepairWorkItem:
        return RepairWorkItem(
            expected_base_sha=BASE,
            conflicts=self.conflicts,
            executor_adapter=self,
        )

    def current_refs(self, repo: str, pr_number: int) -> ExecutorRefs:
        return ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE)

    def apply_resolved_content(self, repo: str, pr_number: int, files: dict[str, str]) -> tuple[str, ...]:
        self.applied.update(files)
        return tuple(sorted(files))

    def push_and_requeue(self, repo: str, pr_number: int) -> ExecutorPublishResult:
        self.published += 1
        return ExecutorPublishResult(pushed=True, requeued=True, evidence=("fake_requeue=true",))


def _poller(*, token, **_kwargs):
    assert token == "ghp_fake"
    return RepairPollResult(events=(_event(),), rate_limit={"remaining": 9})


def test_poll_loop_detects_resolves_executes_and_logs():
    adapter = FakeBeltAdapter(
        (
            ConflictSnapshot(
                path=".ce/registries/integrator-append.txt",
                conflicted_text=_append_conflict(),
            ),
        )
    )
    logs: list[dict] = []

    result = belt.run_poll_loop(
        token="ghp_fake",
        repair_adapter=adapter,
        repo=REPO,
        iterations=1,
        interval_seconds=0,
        poller=_poller,
        log_sink=lambda payload: logs.append(dict(payload)),
    )

    assert result.event_count == 1
    assert result.executed_count == 1
    assert result.escalated_count == 0
    assert result.refused_count == 0
    assert adapter.applied[".ce/registries/integrator-append.txt"] == "existing\nalpha\nbeta\ntail\n"
    assert adapter.published == 1
    assert [entry["action"] for entry in logs] == ["poll_start", "poll_complete", "event_outcome"]


def test_poll_loop_refuses_unscoped_fail_closed():
    # ce-ops#218 review: a live merge-queue belt must NOT poll/act across every PR a
    # token can see. run_poll_loop fails closed when neither repo nor org is scoped.
    adapter = FakeBeltAdapter(())
    raised = None
    try:
        belt.run_poll_loop(
            token="ghp_fake",
            repair_adapter=adapter,
            iterations=1,
            interval_seconds=0,
            poller=_poller,
        )
    except belt.IntegratorBeltError as exc:
        raised = exc
    assert raised is not None and "unscoped" in str(raised)
    assert adapter.published == 0

def test_live_action_runner_refuses_semantic_conflict_without_execute(tmp_path: Path):
    adapter = FakeBeltAdapter(
        (
            ConflictSnapshot(
                path="package-lock.json",
                conflicted_text=_semantic_conflict(),
            ),
        )
    )
    runner = belt.make_live_action_runner(
        action="enqueue",
        token="ghp_fake",
        repo=REPO,
        poller=_poller,
        repair_adapter=adapter,
    )

    result = runner(
        belt.LiveActionRequest(
            action="enqueue",
            request=tmp_path / "request.yaml",
            preview_root=tmp_path / "preview",
            repo_root=None,
            preview_id="preview-1",
        )
    )

    assert result.accepted is False
    assert result.refusal_reason == "integrator_belt_refused"
    assert "executed=0" in result.evidence
    assert "escalated=1" in result.evidence
    assert adapter.applied == {}
    assert adapter.published == 0


@dataclass(frozen=True)
class _CliResult:
    event_count: int = 0
    executed_count: int = 0
    escalated_count: int = 0
    refused_count: int = 0

    def to_dict(self) -> dict:
        return {
            "event_count": self.event_count,
            "executed_count": self.executed_count,
            "escalated_count": self.escalated_count,
            "refused_count": self.refused_count,
            "ticks": [],
        }


def test_ce_queue_poll_cli_is_bounded_and_json(monkeypatch, capsys):
    captured = {}

    monkeypatch.setattr(v3_cli.integrator_belt, "token_from_env", lambda name: "ghp_fake")
    monkeypatch.setattr(v3_cli.integrator_belt, "gh_runner_with_token", lambda token: object())
    monkeypatch.setattr(v3_cli.integrator_belt, "git_env_with_token", lambda token: {})
    monkeypatch.setattr(v3_cli.integrator_belt, "LiveGitHubRepairAdapter", lambda **kwargs: object())

    def fake_loop(**kwargs):
        captured.update(kwargs)
        return _CliResult()

    monkeypatch.setattr(v3_cli.integrator_belt, "run_poll_loop", fake_loop)

    ret = v3_cli.main([
        "queue-poll",
        "--repo", REPO,
        "--iterations", "1",
        "--interval-seconds", "0",
        "--json",
    ])

    assert ret == 0
    assert captured["token"] == "ghp_fake"
    assert captured["repo"] == REPO
    assert captured["iterations"] == 1
    assert '"event_count": 0' in capsys.readouterr().out


def _check(name: str, state: str = "SUCCESS") -> belt.DaemonStatusCheck:
    return belt.DaemonStatusCheck(name=name, state=state, kind="CheckRun")


def _daemon_pr(**overrides) -> belt.DaemonPullRequest:
    pr_number = overrides.get("pr_number", PR)
    head_sha = overrides.get("head_sha", HEAD)
    body = overrides.pop("body", _body_with_approval(pr_number=pr_number, head_sha=head_sha))
    approval_marker = extract_approval_capability_marker(body)
    data = {
        "repo": REPO,
        "pr_number": PR,
        "title": "ready",
        "url": f"https://github.com/{REPO}/pull/{PR}",
        "body": body,
        "head_ref": BRANCH,
        "head_sha": HEAD,
        "base_ref": "main",
        "review_decision": "APPROVED",
        "approving_review_commits": (HEAD,),
        "approving_reviewers": (APPROVER,),
        "approval_capability_present": approval_marker is not None,
        "approval_capability_marker": approval_marker,
        "mergeable": "MERGEABLE",
        "merge_state_status": "CLEAN",
        "rollup_state": "SUCCESS",
        "checks": (
            _check("Validate governance artifacts"),
            _check("unit tests"),
        ),
        "changed_paths": ("docs/a.md",),
        "files_complete": True,
        "checks_complete": True,
        "is_draft": False,
        "approval_witnesses": (
            belt.DaemonApprovalWitness(
                reviewer_login=AUTHORIZED_REVIEWER,
                commit_oid=HEAD,
                state="APPROVED",
                review_id="review-1",
            ),
        ),
    }
    data.update(overrides)
    return belt.DaemonPullRequest(**data)


def _approval_marker(
    *,
    repo: str = REPO,
    pr_number: int = PR,
    head_sha: str = HEAD,
    approved_by: str = APPROVER,
    issued_at: int = ISSUED_AT,
    expires_at: int = EXPIRES_AT,
    policy_sha: str = POLICY_SHA,
) -> str:
    return issue_approval_capability(
        ApprovalCapabilityClaims(
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            approved_by=approved_by,
            issued_at=issued_at,
            expires_at=expires_at,
            policy_sha=policy_sha,
        ),
        APPROVAL_SECRET,
    )


def _body_with_approval(marker: str | None = None, **claim_overrides) -> str:
    return f"Controller approval wall\n\n{marker or _approval_marker(**claim_overrides)}\n"


def _approval_verifier(*, now: int = ISSUED_AT + 1) -> ApprovalCapabilityVerifier:
    return ApprovalCapabilityVerifier(
        lambda: APPROVAL_SECRET,
        now=lambda: now,
        policy_sha=POLICY_SHA,
    )


def _approval_secret_ref() -> SecretRef:
    return SecretRef(
        backend="openbao",
        mount="ce-kv",
        path="forge/approval-capability/wall",
        field="secret",
        version=1,
        purpose="approval-capability-wall",
        owner_ref="controller:integrator",
        policy_sha="a" * 64,
    )


def _approval_secret_request(ref: SecretRef) -> SecretRequest:
    return SecretRequest(
        run_id="approval-wall-run",
        seat_id="dev-1",
        repo=REPO,
        secret_ref=ref,
        ttl_seconds=600,
        delivery="file",
        requested_capabilities=("read",),
        audit_context={"purpose": "approval-capability-wall"},
    )


class RecordingSecretIdentityBackend(FakeSecretIdentityBackend):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.calls: list[str] = []
        self.audit_records: list[dict[str, str]] = []

    def validate_config(self) -> None:
        self.calls.append("validate_config")
        return super().validate_config()

    def issue(self, request):
        self.calls.append("issue")
        return super().issue(request)

    def materialize(self, grant, target_ref: str):
        self.calls.append("materialize")
        return super().materialize(grant, target_ref)

    def revoke(self, grant):
        self.calls.append("revoke")
        return super().revoke(grant)

    def collect_audit(self, grant):
        self.calls.append("collect_audit")
        record = dict(super().collect_audit(grant))
        self.audit_records.append(record)
        return record


class FakeDaemonGh:
    def __init__(
        self,
        raw_contents: tuple[str | None, ...] = (),
        approval_witnesses: tuple[belt.DaemonApprovalWitness, ...] | None = None,
        review_decision: str = "APPROVED",
        head_sha: str = HEAD,
    ) -> None:
        self.calls: list[list[str]] = []
        self.raw_contents = list(raw_contents)
        self.approval_witnesses = approval_witnesses
        self.review_decision = review_decision
        self.head_sha = head_sha

    def __call__(self, argv, input_text=None):
        self.calls.append(list(argv))
        if len(argv) >= 3 and argv[:2] == ["gh", "api"] and "/contents/" in str(argv[2]):
            stdout = self.raw_contents.pop(0) if self.raw_contents else ""
            if stdout is None:
                return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="not found")
            return subprocess.CompletedProcess(list(argv), 0, stdout=stdout, stderr="")
        if len(argv) >= 4 and argv[:3] == ["gh", "api", "graphql"]:
            witnesses = self.approval_witnesses
            if witnesses is None:
                witnesses = (
                    belt.DaemonApprovalWitness(
                        reviewer_login=AUTHORIZED_REVIEWER,
                        commit_oid=HEAD,
                        state="APPROVED",
                        review_id="review-1",
                    ),
                )
            reviews = [
                {
                    "id": witness.review_id,
                    "state": witness.state,
                    "author": {"login": witness.reviewer_login},
                    "commit": {"oid": witness.commit_oid},
                }
                for witness in witnesses
            ]
            return subprocess.CompletedProcess(
                list(argv),
                0,
                stdout=json.dumps(
                    {
                        "data": {
                            "repository": {
                                "pullRequest": {
                                    "reviewDecision": self.review_decision,
                                    "headRefOid": self.head_sha,
                                    "latestOpinionatedReviews": {"nodes": reviews},
                                }
                            }
                        }
                    }
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    @property
    def merge_calls(self) -> list[list[str]]:
        return [call for call in self.calls if call[:3] == ["gh", "pr", "merge"]]


def _carrier_text(paths: tuple[str, ...]) -> str:
    normalized = "\n".join(sorted(set(paths))) + "\n"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return (
        f"PR_PATHS_COUNT={len(set(paths))}\n"
        f"PR_PATHS_SHA256={digest}\n"
        "```text\n"
        f"{normalized}"
        "```\n"
    )


def _settled(pr: belt.DaemonPullRequest) -> set[str]:
    witness = belt._current_approval_witness(pr)
    assert witness is not None
    return {belt._approval_settle_key(pr, witness)}


def test_daemon_default_direct_pass_defers_first_cycle_and_does_not_merge():
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))
    logs: list[dict] = []
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        log_sink=lambda payload: logs.append(dict(payload)),
    )

    assert result.enqueue_count == 0
    assert result.skip_count == 0
    assert result.defer_count == 1
    assert gh.merge_calls == []
    assert result.decisions[0].reason == "approval_settle_pending"
    assert logs[-1]["status"] == "defer"


def test_daemon_settle_window_defers_first_approval_cycle_then_enqueues():
    settle_seen: set[str] = set()
    first_gh = FakeDaemonGh()

    first = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=first_gh,
        approval_verifier=_approval_verifier(),
        candidates=(_daemon_pr(changed_paths=(CARRIER, "docs/a.md")),),
        approval_settle_seen=settle_seen,
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert first.enqueue_count == 0
    assert first.defer_count == 1
    assert first.decisions[0].reason == "approval_settle_pending"
    assert first_gh.merge_calls == []

    second_gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))
    second = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=second_gh,
        approval_verifier=_approval_verifier(),
        candidates=(_daemon_pr(changed_paths=(CARRIER, "docs/a.md")),),
        approval_settle_seen=settle_seen,
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert second.enqueue_count == 1
    assert second.decisions[0].reason == "eligible_enqueued"
    assert second_gh.merge_calls == [[
        "gh",
        "pr",
        "merge",
        str(PR),
        "--repo",
        REPO,
        "--auto",
        "--match-head-commit",
        HEAD,
    ]]


def test_daemon_settled_without_authorized_reviewers_fails_closed():
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
    )

    assert result.enqueue_count == 0
    assert result.decisions[0].reason == "authorized_reviewers_missing"
    assert gh.merge_calls == []


def test_daemon_skips_unvetted_reviewer_excluded_by_authorized_set():
    pr = _daemon_pr(
        changed_paths=(CARRIER, "docs/a.md"),
        body=_body_with_approval(_approval_marker(approved_by="unvetted-reviewer")),
        approving_reviewers=("unvetted-reviewer",),
        approval_witnesses=(
            belt.DaemonApprovalWitness(
                reviewer_login="unvetted-reviewer",
                commit_oid=HEAD,
                state="APPROVED",
                review_id="review-unvetted",
            ),
        ),
    )
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert result.decisions[0].reason == "approval_reviewer_unauthorized"
    assert gh.merge_calls == []


def test_daemon_reverifies_approval_immediately_before_enqueue():
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))
    gh = FakeDaemonGh(
        raw_contents=(_carrier_text((CARRIER, "docs/a.md")),),
        approval_witnesses=(
            belt.DaemonApprovalWitness(
                reviewer_login=AUTHORIZED_REVIEWER,
                commit_oid=HEAD,
                state="DISMISSED",
                review_id="review-1",
            ),
        ),
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "approval_not_reconfirmed"
    assert gh.merge_calls == []


def test_daemon_reverify_requires_same_authorized_reviewer():
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))
    gh = FakeDaemonGh(
        raw_contents=(_carrier_text((CARRIER, "docs/a.md")),),
        approval_witnesses=(
            belt.DaemonApprovalWitness(
                reviewer_login="other-reviewer",
                commit_oid=HEAD,
                state="APPROVED",
                review_id="review-2",
            ),
        ),
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert result.decisions[0].reason == "approval_not_reconfirmed"
    assert gh.merge_calls == []


def test_daemon_reverify_head_moved_fails_closed():
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))
    gh = FakeDaemonGh(
        raw_contents=(_carrier_text((CARRIER, "docs/a.md")),),
        head_sha="d" * 40,
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert result.decisions[0].reason == "approval_reverify_failed"
    assert "head_moved=true" in result.decisions[0].evidence
    assert gh.merge_calls == []


def test_daemon_reverify_review_decision_downgrade_fails_closed():
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))
    gh = FakeDaemonGh(
        raw_contents=(_carrier_text((CARRIER, "docs/a.md")),),
        review_decision="CHANGES_REQUESTED",
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert result.decisions[0].reason == "approval_not_reconfirmed"
    assert "review_decision=CHANGES_REQUESTED" in result.decisions[0].evidence
    assert gh.merge_calls == []


def test_daemon_dormant_wall_keeps_raw_approved_current_head_fallback():
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))
    logs: list[dict] = []
    pr = _daemon_pr(body="", changed_paths=(CARRIER, "docs/a.md"))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
        log_sink=lambda payload: logs.append(dict(payload)),
    )

    assert result.enqueue_count == 1
    assert result.skip_count == 0
    assert result.decisions[0].reason == "eligible_enqueued"
    assert "approval_wall: not armed" in result.decisions[0].evidence
    assert "approval_wall: not armed" in logs[-1]["evidence"]


def test_daemon_skips_raw_approval_without_capability_fail_closed():
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(_daemon_pr(body="", changed_paths=(CARRIER, "docs/a.md")),),
    )

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "approval_capability_missing"
    assert gh.merge_calls == []


def test_daemon_persisted_armed_wall_missing_secret_fails_closed(tmp_path: Path):
    state_path = tmp_path / "approval-wall.json"
    save_approval_wall_state(state_path, ApprovalWallState(armed=True))
    wall = resolve_approval_wall(
        ApprovalWallConfig(
            secret_supplier=lambda: None,
            state_path=state_path,
            policy_sha=POLICY_SHA,
        )
    )
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_wall=wall,
        candidates=(_daemon_pr(changed_paths=(CARRIER, "docs/a.md")),),
    )

    assert load_approval_wall_state(state_path).armed is True
    assert wall.misconfigured is True
    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "approval_wall_misconfigured"
    assert "approval_wall: misconfigured" in result.decisions[0].evidence
    assert gh.merge_calls == []


def test_daemon_skips_invalid_signature_head_mismatch_and_expired_capability_before_merge():
    valid = _approval_marker(pr_number=1)
    invalid_signature = valid[:-1] + ("A" if valid[-1] != "A" else "B")
    head_mismatch = _approval_marker(pr_number=2, head_sha="c" * 40)
    expired = _approval_marker(pr_number=3, expires_at=EXPIRES_AT)
    gh = FakeDaemonGh(raw_contents=(
        _carrier_text((CARRIER, "docs/a.md")),
        _carrier_text((CARRIER, "docs/b.md")),
        _carrier_text((CARRIER, "docs/c.md")),
    ))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(now=EXPIRES_AT),
        candidates=(
            _daemon_pr(pr_number=1, body=_body_with_approval(invalid_signature), changed_paths=(CARRIER, "docs/a.md")),
            _daemon_pr(pr_number=2, body=_body_with_approval(head_mismatch), changed_paths=(CARRIER, "docs/b.md")),
            _daemon_pr(pr_number=3, body=_body_with_approval(expired), changed_paths=(CARRIER, "docs/c.md")),
        ),
    )

    assert result.enqueue_count == 0
    assert [decision.reason for decision in result.decisions] == [
        "approval_capability_invalid",
        "approval_capability_invalid",
        "approval_capability_invalid",
    ]
    assert gh.merge_calls == []
    assert gh.calls == []


def test_approval_capability_audit_record_contains_no_secret():
    verifier = _approval_verifier()
    result = verifier.verify(
        _approval_marker(),
        repo=REPO,
        pr_number=PR,
        head_sha=HEAD,
        approved_by_candidates=(APPROVER,),
    )

    assert result.valid is True
    audit = result.to_audit_record()
    assert audit["reason"] == "valid"
    assert audit["repo"] == REPO
    assert APPROVAL_SECRET.decode("utf-8") not in str(audit)


def test_approval_wall_secret_identity_backend_supplier_reads_injected_value_without_leak(tmp_path: Path):
    secret = "backend-wall-secret"
    target_ref = "tmpfs:/run/ce/approval-wall-secret"
    ref = _approval_secret_ref()
    request = _approval_secret_request(ref)
    backend = RecordingSecretIdentityBackend(allowed_refs={ref})
    reads: list[str] = []

    def reader(target: str) -> str:
        reads.append(target)
        return secret

    supplier = approval_wall_secret_supplier_from_secret_identity_backend(
        backend=backend,
        request=request,
        target_ref=target_ref,
        value_reader=reader,
    )

    assert supplier() == secret
    assert reads == [target_ref]
    assert backend.calls == [
        "validate_config",
        "issue",
        "materialize",
        "collect_audit",
        "revoke",
        "collect_audit",
    ]
    assert all(secret not in str(record) for record in backend.audit_records)

    state_path = tmp_path / "approval-wall-state.json"
    runtime = resolve_approval_wall(
        ApprovalWallConfig(
            secret_supplier=supplier,
            state_path=state_path,
            policy_sha=POLICY_SHA,
        )
    )

    assert runtime.armed is True
    assert load_approval_wall_state(state_path).armed is True
    assert secret not in state_path.read_text(encoding="utf-8")
    assert all(secret not in str(record) for record in backend.audit_records)


def test_discover_daemon_candidates_uses_non_query_search_variable():
    calls: list[list[str]] = []

    def gh(argv, input_text=None):
        calls.append(list(argv))
        return subprocess.CompletedProcess(
            list(argv),
            0,
            stdout='{"data":{"search":{"pageInfo":{"hasNextPage":false},"nodes":[]}}}',
            stderr="",
        )

    assert belt.discover_daemon_candidates(repo=REPO, gh_runner=gh) == ()

    argv = calls[0]
    query_fields = [
        value
        for flag, value in zip(argv, argv[1:])
        if flag == "-f" and value.startswith("query=")
    ]
    assert len(query_fields) == 1
    assert f"searchQuery=repo:{REPO} is:pr is:open" in argv
    assert f"query=repo:{REPO} is:pr is:open" not in argv


def test_discover_daemon_candidates_retries_graphql_search_rate_limit(tmp_path):
    calls: list[list[str]] = []
    sleeps: list[float] = []
    now = {"value": 100.0}

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now["value"] += seconds

    def gh(argv, input_text=None):
        calls.append(list(argv))
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                list(argv),
                1,
                stdout="",
                stderr="HTTP 429: Search API rate limit exceeded\nRetry-After: 4",
            )
        return subprocess.CompletedProcess(
            list(argv),
            0,
            stdout='{"data":{"search":{"pageInfo":{"hasNextPage":false},"nodes":[]}}}',
            stderr="",
        )

    assert belt.discover_daemon_candidates(
        repo=REPO,
        gh_runner=gh,
        rate_limiter=_test_limiter(tmp_path, clock=lambda: now["value"]),
        sleep=sleep,
    ) == ()
    assert len(calls) == 2
    assert sleeps == [5.0]


def test_daemon_loop_does_not_crash_after_exhausted_search_rate_limit(tmp_path):
    logs = []

    def gh(argv, input_text=None):
        return subprocess.CompletedProcess(
            list(argv),
            1,
            stdout="",
            stderr="HTTP 429: Search API rate limit exceeded\nRetry-After: 4",
        )

    result = belt.run_daemon_loop(
        token="ghp_fake",
        repo=REPO,
        once=True,
        gh_runner=gh,
        sleep=lambda seconds: None,
        log_sink=logs.append,
        rate_limiter=_test_limiter(tmp_path),
    )

    assert result.ticks[0].result.decisions == ()
    assert any(log["action"] == "daemon_rate_limited" for log in logs)


def _assert_valid_daemon_search_query(query: str) -> None:
    assert query.count("{") == query.count("}")
    assert "$query" not in query


def _assert_invalid_daemon_search_query(query: str) -> None:
    try:
        _assert_valid_daemon_search_query(query)
    except AssertionError:
        return
    raise AssertionError("invalid daemon search query unexpectedly passed")


def test_daemon_search_query_is_balanced_and_avoids_query_variable_name():
    query = belt._DAEMON_SEARCH_QUERY

    _assert_invalid_daemon_search_query(query + "}")
    _assert_invalid_daemon_search_query(query.replace("$searchQuery", "$query", 1))
    _assert_valid_daemon_search_query(query)


def test_daemon_search_query_uses_latest_opinionated_reviews():
    # ``latestReviews`` is EMPTY for reviewers never formally requested, so the
    # gate must read approval commits from ``latestOpinionatedReviews`` instead.
    query = belt._DAEMON_SEARCH_QUERY
    assert "latestOpinionatedReviews(" in query
    assert "latestReviews(" not in query
    assert "body isDraft reviewDecision" in query
    assert "author{login}" in query


def test_parse_daemon_pr_reads_approval_and_capability_from_latest_opinionated_reviews():
    head = "a" * 40
    marker = _approval_marker(pr_number=7, head_sha=head)
    node = {
        "repository": {"nameWithOwner": REPO},
        "number": 7,
        "body": f"ready\n{marker}\n",
        "headRefOid": head,
        "headRefName": "feature",
        "baseRefName": "main",
        "reviewDecision": "APPROVED",
        # As GitHub returns it for a non-requested approver: latestReviews empty,
        # the approval (with its head commit oid) only in latestOpinionatedReviews.
        "latestReviews": {"nodes": []},
        "latestOpinionatedReviews": {
            "nodes": [
                {
                    "id": "review-7",
                    "state": "APPROVED",
                    "author": {"login": APPROVER},
                    "commit": {"oid": head},
                }
            ]
        },
    }
    pr = belt._parse_daemon_pr(node)
    assert pr.approving_review_commits == (head.lower(),)
    assert pr.approval_witnesses == (
        belt.DaemonApprovalWitness(
            reviewer_login=APPROVER,
            commit_oid=head.lower(),
            state="APPROVED",
            review_id="review-7",
        ),
    )
    assert pr.approving_reviewers == (APPROVER,)
    assert pr.approval_capability_present is True
    assert pr.approval_capability_marker == marker
    assert "approval_capability_marker" not in pr.to_dict()


def test_daemon_skips_stale_approval_red_and_missing_governance_fail_closed():
    gh = FakeDaemonGh()
    stale = _daemon_pr(pr_number=1, approving_review_commits=("c" * 40,))
    red = _daemon_pr(pr_number=2, body=_body_with_approval(pr_number=2), rollup_state="FAILURE")
    missing_governance = _daemon_pr(
        pr_number=3,
        body=_body_with_approval(pr_number=3),
        checks=(_check("unit tests"),),
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(stale, red, missing_governance),
    )

    assert result.enqueue_count == 0
    assert result.skip_count == 3
    assert [decision.reason for decision in result.decisions] == [
        "approval_not_current_head",
        "rollup_not_success",
        "governance_check_missing",
    ]
    assert gh.merge_calls == []


def test_daemon_skips_unconfirmed_reviewer_identity_fail_closed():
    gh = FakeDaemonGh()
    pr = _daemon_pr(
        approving_review_commits=(HEAD,),
        approval_witnesses=(
            belt.DaemonApprovalWitness(
                reviewer_login="",
                commit_oid=HEAD,
                state="APPROVED",
                review_id="review-blank",
            ),
        ),
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
    )

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "approval_reviewer_unconfirmed"
    assert gh.merge_calls == []


def test_daemon_skips_missing_carrier_fail_closed():
    gh = FakeDaemonGh()
    pr = _daemon_pr(changed_paths=("docs/a.md",))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "carrier_missing"
    assert result.decisions[0].path_set_source == CARRIER
    assert gh.merge_calls == []


def test_daemon_skips_unreadable_or_invalid_carrier_fail_closed():
    unreadable = _daemon_pr(pr_number=20, body=_body_with_approval(pr_number=20), changed_paths=(CARRIER, "docs/a.md"))
    invalid = _daemon_pr(pr_number=21, body=_body_with_approval(pr_number=21), changed_paths=(CARRIER, "docs/b.md"))
    gh = FakeDaemonGh(raw_contents=(None, "not a carrier"))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        approval_verifier=_approval_verifier(),
        candidates=(unreadable, invalid),
        approval_settle_seen={*_settled(unreadable), *_settled(invalid)},
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 0
    assert [decision.reason for decision in result.decisions] == [
        "carrier_unreadable",
        "carrier_invalid",
    ]
    assert gh.merge_calls == []


def test_daemon_dry_run_merges_nothing():
    gh = FakeDaemonGh(raw_contents=(_carrier_text((CARRIER, "docs/a.md")),))
    pr = _daemon_pr(changed_paths=(CARRIER, "docs/a.md"))

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        dry_run=True,
        approval_verifier=_approval_verifier(),
        candidates=(pr,),
        approval_settle_seen=_settled(pr),
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert result.enqueue_count == 1
    assert result.decisions[0].reason == "eligible_dry_run"
    assert gh.merge_calls == []


def test_daemon_manifest_overlap_defers_second_pr():
    gh = FakeDaemonGh(raw_contents=(
        _carrier_text((CARRIER, "docs/a.md", "validators/a.py")),
        _carrier_text((CARRIER_2, "docs/a.md", "docs/b.md")),
    ))
    first = _daemon_pr(
        pr_number=10,
        body=_body_with_approval(pr_number=10),
        changed_paths=(CARRIER, "docs/a.md", "validators/a.py"),
    )
    second = _daemon_pr(
        pr_number=11,
        head_ref="feature-integrator-2",
        body=_body_with_approval(
            _approval_marker(pr_number=11, head_sha=HEAD)
        ),
        changed_paths=(CARRIER_2, "docs/a.md", "docs/b.md"),
    )

    result = belt.run_daemon_pass(
        token="ghp_fake",
        repo=REPO,
        gh_runner=gh,
        dry_run=True,
        approval_verifier=_approval_verifier(),
        candidates=(first, second),
        approval_settle_seen={*_settled(first), *_settled(second)},
        authorized_reviewers=(AUTHORIZED_REVIEWER,),
    )

    assert [decision.status for decision in result.decisions] == ["enqueue", "defer"]
    assert result.decisions[1].reason == "path_overlap"
    assert result.decisions[1].overlap_with == f"{REPO}#10"
    assert "overlap_paths=docs/a.md" in result.decisions[1].evidence


def test_ce_queue_daemon_cli_once_json(monkeypatch, capsys, tmp_path: Path):
    captured = {}

    monkeypatch.setattr(v3_cli.integrator_belt, "token_from_env", lambda name: "ghp_fake")
    monkeypatch.setenv("CE_APPROVAL_CAPABILITY_SECRET", "daemon-secret")

    def fake_loop(**kwargs):
        captured.update(kwargs)
        return belt.DaemonLoopResult(
            ticks=(
                belt.DaemonLoopTick(
                    index=1,
                    result=belt.DaemonPassResult(decisions=(), dry_run=True),
                ),
            )
        )

    monkeypatch.setattr(v3_cli.integrator_belt, "run_daemon_loop", fake_loop)

    ret = v3_cli.main([
        "queue-daemon",
        "--repo", REPO,
        "--once",
        "--dry-run",
        "--authorized-reviewer", "ce-reviewer,ce-reviewer-2",
        "--root", str(tmp_path),
        "--json",
    ])

    assert ret == 0
    assert captured["token"] == "ghp_fake"
    assert captured["repo"] == REPO
    assert captured["once"] is True
    assert captured["dry_run"] is True
    assert captured["authorized_reviewers"] == ("ce-reviewer", "ce-reviewer-2")
    assert captured["approval_wall"].armed is True
    assert load_approval_wall_state(tmp_path / "approval-capability-wall" / "state.json").armed is True
    assert '"enqueue_count": 0' in capsys.readouterr().out


def test_dequeue_merge_queue_disables_auto_and_optionally_drafts():
    calls: list[list[str]] = []

    def gh(argv, input_text=None):
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    result = belt.dequeue_merge_queue(
        repo=REPO,
        pr_number=PR,
        gh_runner=gh,
        convert_to_draft=True,
    )

    assert result.ok is True
    assert result.disabled_auto_merge is True
    assert result.converted_to_draft is True
    assert calls == [
        ["gh", "pr", "merge", str(PR), "--repo", REPO, "--disable-auto"],
        ["gh", "pr", "ready", str(PR), "--repo", REPO, "--undo"],
    ]


def test_ce_queue_dequeue_cli_json(monkeypatch, capsys):
    captured = {}

    monkeypatch.setattr(v3_cli.integrator_belt, "token_from_env", lambda name: "ghp_fake")
    monkeypatch.setattr(v3_cli.integrator_belt, "gh_runner_with_token", lambda token: object())

    def fake_dequeue(**kwargs):
        captured.update(kwargs)
        return belt.MergeQueueDequeueResult(
            repo=kwargs["repo"],
            pr_number=kwargs["pr_number"],
            disabled_auto_merge=True,
            converted_to_draft=True,
            evidence=("gh_pr_merge_disable_auto=true", "draft_returncode=0"),
        )

    monkeypatch.setattr(v3_cli.integrator_belt, "dequeue_merge_queue", fake_dequeue)

    ret = v3_cli.main([
        "queue-dequeue",
        str(PR),
        "--repo", REPO,
        "--convert-to-draft",
        "--json",
    ])

    assert ret == 0
    assert captured["repo"] == REPO
    assert captured["pr_number"] == PR
    assert captured["convert_to_draft"] is True
    assert '"disabled_auto_merge": true' in capsys.readouterr().out
