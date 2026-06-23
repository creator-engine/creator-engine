from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator import publish_gate

REPO = "creator-engine/creator-engine"
BRANCH = "ce-contained-publish-gate"
LOCAL = "a" * 40
REMOTE = "b" * 40
AUTHOR_NAME = "ce-dev-1"
AUTHOR_EMAIL = "ce-dev-1@example.invalid"
CONTROLLER = "host-substrate"
LANE = "publish-gate"


class ScriptedGit:
    def __init__(
        self,
        *,
        remote_head: str | None = None,
        fast_forward: bool = True,
        status: str = "",
        author_email: str = AUTHOR_EMAIL,
    ):
        self.remote_head = remote_head
        self.fast_forward = fast_forward
        self.status = status
        self.author_email = author_email
        self.pushed = False
        self.calls: list[dict] = []

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "input": input_text, "env": dict(env)})
        if "remote" in argv and "get-url" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=f"https://github.com/{REPO}.git\n", stderr="")
        if "rev-parse" in argv:
            if argv[-1] == "HEAD":
                return subprocess.CompletedProcess(argv, 0, stdout=f"{LOCAL}\n", stderr="")
            if argv[-1] == f"refs/heads/{BRANCH}":
                return subprocess.CompletedProcess(argv, 0, stdout=f"{LOCAL}\n", stderr="")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=self.status, stderr="")
        if "show" in argv:
            out = "\x00".join([LOCAL, AUTHOR_NAME, self.author_email, AUTHOR_NAME, self.author_email])
            return subprocess.CompletedProcess(argv, 0, stdout=out + "\n", stderr="")
        if "ls-remote" in argv:
            head = LOCAL if self.pushed else self.remote_head
            out = f"{head}\trefs/heads/{BRANCH}\n" if head else ""
            return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")
        if "merge-base" in argv and "--is-ancestor" in argv:
            return subprocess.CompletedProcess(argv, 0 if self.fast_forward else 1, stdout="", stderr="")
        if "push" in argv:
            self.pushed = True
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover

    def argv_for(self, verb: str) -> list[str] | None:
        for call in self.calls:
            if verb in call["argv"]:
                return call["argv"]
        return None

    def env_for(self, verb: str) -> dict | None:
        for call in self.calls:
            if verb in call["argv"]:
                return call["env"]
        return None


def _claim(awl_root: Path) -> None:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": CONTROLLER,
        "lane_id": LANE,
        "record_timestamp": f"source-controlled:claims/{CONTROLLER}/{LANE}.yaml",
        "worktree_path": "/worktrees/publish-gate",
        "envelope_ref": ".hermes/envelopes/publish-gate.md",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{CONTROLLER}/{LANE}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{CONTROLLER}/{LANE}.yaml",
    }
    path = awl_root / "claims" / CONTROLLER / f"{LANE}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")


def _expected() -> publish_gate.SeatIdentityExpectation:
    return publish_gate.SeatIdentityExpectation(author_email=AUTHOR_EMAIL)


def _ledger_context(tmp_path: Path) -> publish_gate.PublishLedgerContext:
    awl_root = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl_root)
    return publish_gate.PublishLedgerContext(
        controller_id=CONTROLLER,
        lane_id=LANE,
        claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
        repo_root=tmp_path,
        side_effect_ledger_root=tmp_path / "side-effect-ledger",
        active_work_ledger_root=awl_root,
        actor="host-substrate",
        seat_id="ce-dev-1",
        now=datetime(2026, 6, 23, 17, 0, 0, tzinfo=UTC),
    )


def _ledger_records(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if path.name != "_head.json")


def test_dry_run_verifies_clean_attributed_new_branch_without_push(tmp_path: Path):
    git = ScriptedGit(remote_head=None)

    result = publish_gate.publish_branch(
        BRANCH,
        repo=REPO,
        repo_root=tmp_path,
        expected_identity=_expected(),
        apply=False,
        runner=git,
    )

    assert result.ok is True
    assert result.verified is True
    assert result.changed is True
    assert result.applied is False
    assert result.pushed is False
    assert git.argv_for("push") is None


def test_attributed_fast_forward_publish_pushes_with_host_helper_and_records_ledger(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    git = ScriptedGit(remote_head=REMOTE, fast_forward=True)

    result = publish_gate.publish_branch(
        BRANCH,
        repo=REPO,
        repo_root=tmp_path,
        expected_identity=_expected(),
        ledger_context=_ledger_context(tmp_path),
        runner=git,
    )

    assert result.ok is True
    assert result.pushed is True
    push = git.argv_for("push")
    assert push is not None
    assert "credential.helper=" in push
    assert "credential.helper=!gh auth git-credential" in push
    assert f"refs/heads/{BRANCH}:refs/heads/{BRANCH}" in push
    assert "--force" not in push and "--force-with-lease" not in push
    assert "GH_TOKEN" not in git.env_for("push")
    records = _ledger_records(tmp_path / "side-effect-ledger")
    assert len(records) == 1
    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["effect_kind"] == "git_mutation"
    assert payload["effect_status"] == "succeeded"
    assert payload["subject_ref"] == f"refs/heads/{BRANCH}"
    assert payload["subject_git_sha"] == LOCAL
    assert payload["details"]["actor"] == "host-substrate"
    assert payload["details"]["seat"] == "ce-dev-1"
    assert payload["details"]["policy_verdict"] == "allow"
    assert payload["details"]["sandbox_auth_env_required"] is False
    assert payload["details"]["sandbox_auth_mount_required"] is False


def test_non_fast_forward_is_refused_before_push_and_writes_no_ledger(tmp_path: Path):
    git = ScriptedGit(remote_head=REMOTE, fast_forward=False)

    result = publish_gate.publish_branch(
        BRANCH,
        repo=REPO,
        repo_root=tmp_path,
        expected_identity=_expected(),
        ledger_context=_ledger_context(tmp_path),
        runner=git,
    )

    assert result.ok is False
    assert result.refusal_reason == "non_fast_forward"
    assert result.pushed is False
    assert git.argv_for("push") is None
    assert _ledger_records(tmp_path / "side-effect-ledger") == []


def test_unattributed_head_is_refused_before_remote_read_or_push(tmp_path: Path):
    git = ScriptedGit(remote_head=None, author_email="intruder@example.invalid")

    result = publish_gate.publish_branch(
        BRANCH,
        repo=REPO,
        repo_root=tmp_path,
        expected_identity=_expected(),
        ledger_context=_ledger_context(tmp_path),
        runner=git,
    )

    assert result.ok is False
    assert result.refusal_reason == "head_identity_mismatch"
    assert git.argv_for("ls-remote") is None
    assert git.argv_for("push") is None
    assert _ledger_records(tmp_path / "side-effect-ledger") == []


def test_cli_json_reports_machine_readable_refusal(monkeypatch, tmp_path: Path, capsys):
    git = ScriptedGit(remote_head=REMOTE, fast_forward=False)
    monkeypatch.setattr(ce_cli, "_make_publish_branch_runner", lambda: git)

    rc = ce_cli.main(
        [
            "publish-branch",
            BRANCH,
            "--repo",
            REPO,
            "--repo-root",
            str(tmp_path),
            "--seat-id",
            "ce-dev-1",
            "--expect-author-email",
            AUTHOR_EMAIL,
            "--dry-run",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["ok"] is False
    assert payload["refusal_reason"] == "non_fast_forward"
    assert payload["branch"] == BRANCH
