"""Regression contract for host-side substrate branch publishing.

The production API is expected at ``creator_engine_validator.forge.host_publish_gate`` with:

* ``PublishRequest`` - immutable request carrying repo/branch/ledger context.
* ``PublishRefused`` - fail-closed policy refusal raised before push.
* ``publish_branch(request, host_git_runner=...)`` - performs the publish through
  a host-side git runner/credential-helper seam and records a redaction-safe
  Side-Effect Ledger entry only after a successful push.

Until that module lands, this file runs the same cases through a tiny local
contract harness. The harness is intentionally shaped like the expected API so
the tests become production tests by replacing the fallback import.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

try:  # pragma: no cover - exercised once production module exists.
    from creator_engine_validator.forge.host_publish_gate import (  # type: ignore
        PublishRefused,
        PublishRequest,
        publish_branch,
    )
except ImportError:  # pragma: no cover - local executable contract harness.
    from creator_engine_validator import side_effect_ledger_runtime

    class PublishRefused(Exception):
        """Host publish gate refused before remote mutation."""

    @dataclass(frozen=True)
    class PublishRequest:
        repo: str
        branch: str
        repo_root: Path
        active_work_ledger_root: Path
        side_effect_ledger_root: Path
        controller_id: str
        lane_id: str
        claim_ref: str
        actor_role: str = "controller"
        force: bool = False
        sandbox_env: dict[str, str] | None = None
        sandbox_mounts: tuple[str, ...] = ()
        occurred_at: str = "2026-06-23T17:00:00Z"

    @dataclass(frozen=True)
    class _PublishResult:
        repo: str
        branch: str
        local_head: str
        remote_head: str | None
        pushed: bool
        ledger_record_path: Path

    def publish_branch(request: PublishRequest, *, host_git_runner):
        if request.force:
            raise PublishRefused("force-shaped publish request refused")
        local_head = host_git_runner.local_head(request.repo_root, request.branch)
        attribution = host_git_runner.head_attribution(request.repo_root, local_head)
        if not attribution:
            raise PublishRefused("unattributed HEAD refused")
        remote_head = host_git_runner.remote_head(request.repo, request.branch)
        if remote_head is not None and not host_git_runner.is_ancestor(remote_head, local_head):
            raise PublishRefused("non-fast-forward publish refused")
        helper_ref = host_git_runner.credential_helper_ref()
        host_git_runner.push(
            request.repo,
            request.branch,
            local_head,
            credential_helper_ref=helper_ref,
        )
        record = side_effect_ledger_runtime.record(
            controller_id=request.controller_id,
            lane_id=request.lane_id,
            claim_ref=request.claim_ref,
            effect_id=f"publish-{request.branch.replace('/', '-')}",
            effect_kind="git_mutation",
            effect_status="succeeded",
            summary=f"Published {request.branch} through host substrate gate.",
            occurred_at=request.occurred_at,
            repo_root=request.repo_root,
            side_effect_ledger_root=request.side_effect_ledger_root,
            active_work_ledger_root=request.active_work_ledger_root,
            actor_role=request.actor_role,
            subject_ref=f"refs/heads/{request.branch}",
            details={
                "repo": request.repo,
                "branch": request.branch,
                "local_head_short": local_head[:12],
                "remote_head_before_short": remote_head[:12] if remote_head else None,
                "attribution_source": attribution["source"],
                "author_login": attribution["author_login"],
                "attributed_actor_role": attribution["actor_role"],
                "attributed_head_short": attribution["head_short"],
                "sandbox_auth_env_required": False,
                "sandbox_auth_mount_required": False,
                "sandbox_env_seen": ",".join(sorted((request.sandbox_env or {}).keys())),
                "sandbox_mounts_seen": ",".join(request.sandbox_mounts),
                "host_git_runner": host_git_runner.name,
                "host_git_helper_ref": helper_ref,
            },
            now=datetime(2026, 6, 23, 17, 0, 0, tzinfo=UTC),
        )
        return _PublishResult(
            repo=request.repo,
            branch=request.branch,
            local_head=local_head,
            remote_head=remote_head,
            pushed=True,
            ledger_record_path=record.record_path,
        )


REPO = "creator-engine/creator-engine"
BRANCH = "worker-c/publish-gate-regression-tests"
CONTROLLER = "host-substrate"
LANE = "publish-gate"
LOCAL = "a" * 40
REMOTE = "b" * 40


class FakeHostGitRunner:
    """Value-free host git seam; tests assert all pushes pass through it."""

    name = "fake-host-git-runner"

    def __init__(
        self,
        *,
        remote_head: str | None = REMOTE,
        fast_forward: bool = True,
        attribution: dict[str, str] | None = None,
    ):
        self._remote_head = remote_head
        self._fast_forward = fast_forward
        self._attribution = attribution
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def local_head(self, repo_root: Path, branch: str) -> str:
        self.calls.append(("local_head", (repo_root, branch), {}))
        return LOCAL

    def head_attribution(self, repo_root: Path, head_sha: str) -> dict[str, str] | None:
        self.calls.append(("head_attribution", (repo_root, head_sha), {}))
        return self._attribution

    def remote_head(self, repo: str, branch: str) -> str | None:
        self.calls.append(("remote_head", (repo, branch), {}))
        return self._remote_head

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        self.calls.append(("is_ancestor", (ancestor, descendant), {}))
        return self._fast_forward

    def credential_helper_ref(self) -> str:
        self.calls.append(("credential_helper_ref", (), {}))
        return "host-git-helper://ce-publish"

    def push(
        self,
        repo: str,
        branch: str,
        head_sha: str,
        *,
        credential_helper_ref: str,
    ) -> None:
        self.calls.append(
            (
                "push",
                (repo, branch, head_sha),
                {"credential_helper_ref": credential_helper_ref},
            )
        )

    def call_names(self) -> list[str]:
        return [name for name, _, _ in self.calls]

    def push_calls(self) -> list[tuple[str, tuple[Any, ...], dict[str, Any]]]:
        return [call for call in self.calls if call[0] == "push"]


def _claim(awl_root: Path) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": CONTROLLER,
        "lane_id": LANE,
        "record_timestamp": "source-controlled:claims/host-substrate/publish-gate.yaml",
        "worktree_path": "/worktrees/publish-gate",
        "envelope_ref": ".hermes/envelopes/publish-gate.md",
        "lease_seconds": 3600,
        "claimed_at": "source-controlled:claims/host-substrate/publish-gate.yaml",
        "last_heartbeat_at": "source-controlled:claims/host-substrate/publish-gate.yaml",
    }
    path = awl_root / "claims" / CONTROLLER / f"{LANE}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _request(tmp_path: Path, **overrides: Any) -> PublishRequest:
    awl_root = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl_root)
    data = {
        "repo": REPO,
        "branch": BRANCH,
        "repo_root": tmp_path,
        "active_work_ledger_root": awl_root,
        "side_effect_ledger_root": tmp_path / "side-effect-ledger",
        "controller_id": CONTROLLER,
        "lane_id": LANE,
        "claim_ref": f"claims/{CONTROLLER}/{LANE}.yaml",
        "sandbox_env": {},
        "sandbox_mounts": (),
    }
    data.update(overrides)
    return PublishRequest(**data)


def _attribution() -> dict[str, str]:
    return {
        "source": "commit-trailer",
        "author_login": "worker-c[bot]",
        "actor_role": "implementer",
        "head_short": LOCAL[:12],
    }


def _ledger_records(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.json") if p.name != "_head.json")


def test_clean_fast_forward_attributed_publish_pushes_and_records_ledger(tmp_path: Path):
    runner = FakeHostGitRunner(remote_head=REMOTE, fast_forward=True, attribution=_attribution())
    request = _request(tmp_path)

    result = publish_branch(request, host_git_runner=runner)

    assert result.pushed is True
    assert runner.call_names() == [
        "local_head",
        "head_attribution",
        "remote_head",
        "is_ancestor",
        "credential_helper_ref",
        "push",
    ]
    push = runner.push_calls()[0]
    assert push[1] == (REPO, BRANCH, LOCAL)
    assert push[2] == {"credential_helper_ref": "host-git-helper://ce-publish"}

    records = _ledger_records(request.side_effect_ledger_root)
    assert records == [result.ledger_record_path]
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["effect_kind"] == "git_mutation"
    assert record["effect_status"] == "succeeded"
    assert record["subject_ref"] == f"refs/heads/{BRANCH}"
    assert record["details"]["local_head_short"] == LOCAL[:12]
    assert record["details"]["remote_head_before_short"] == REMOTE[:12]
    assert record["details"]["author_login"] == "worker-c[bot]"
    assert record["details"]["host_git_helper_ref"] == "host-git-helper://ce-publish"
    assert record["details"]["sandbox_auth_env_required"] is False
    assert record["details"]["sandbox_auth_mount_required"] is False


@pytest.mark.parametrize(
    "overrides,runner",
    [
        ({}, FakeHostGitRunner(remote_head=REMOTE, fast_forward=False, attribution=_attribution())),
        ({"force": True}, FakeHostGitRunner(remote_head=REMOTE, fast_forward=True, attribution=_attribution())),
    ],
)
def test_non_ff_or_force_shaped_publish_is_refused_with_no_push(tmp_path: Path, overrides, runner):
    request = _request(tmp_path, **overrides)

    with pytest.raises(PublishRefused):
        publish_branch(request, host_git_runner=runner)

    assert runner.push_calls() == []
    assert _ledger_records(request.side_effect_ledger_root) == []


def test_unattributed_head_is_refused_before_remote_read_or_push(tmp_path: Path):
    runner = FakeHostGitRunner(remote_head=REMOTE, fast_forward=True, attribution=None)
    request = _request(tmp_path)

    with pytest.raises(PublishRefused):
        publish_branch(request, host_git_runner=runner)

    assert runner.call_names() == ["local_head", "head_attribution"]
    assert runner.push_calls() == []
    assert _ledger_records(request.side_effect_ledger_root) == []


def test_host_side_boundary_needs_no_sandbox_auth_env_or_mount(tmp_path: Path):
    runner = FakeHostGitRunner(remote_head=None, fast_forward=True, attribution=_attribution())
    request = _request(
        tmp_path,
        sandbox_env={"PATH": "/usr/bin"},
        sandbox_mounts=("/workspace",),
    )

    result = publish_branch(request, host_git_runner=runner)

    assert result.pushed is True
    record = json.loads(result.ledger_record_path.read_text(encoding="utf-8"))
    assert record["details"]["sandbox_auth_env_required"] is False
    assert record["details"]["sandbox_auth_mount_required"] is False
    assert record["details"]["sandbox_env_seen"] == "PATH"
    assert record["details"]["sandbox_mounts_seen"] == "/workspace"
    assert runner.push_calls()[0][2]["credential_helper_ref"] == "host-git-helper://ce-publish"
