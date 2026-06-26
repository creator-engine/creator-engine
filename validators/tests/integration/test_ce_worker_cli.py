"""Integration tests for the ``ce worker`` runtime end-to-end.

Exercises ``ce worker allocate`` -> ``terminate`` -> ``gc`` through
``ce_cli.main`` with injected fake Podman/broker seams, including the
Side-Effect Ledger (``container_action``) recording and ``ce lane`` / ``ce
ledger`` co-existence (the worker group must not regress the other groups).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli, worker_runtime
pytestmark = pytest.mark.slow



_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64
CONTROLLER = "hermes-primary"
LANE = "pco-slice2ir-worker"


@dataclass
class FakeRunner:
    available_flag: bool = True
    egress_primitive_value: str | None = None
    calls: list[str] = field(default_factory=list)

    def available(self):
        return self.available_flag

    def egress_primitive(self, allowlist):
        return self.egress_primitive_value

    def run_detached(self, argv):
        self.calls.append("run_detached")
        return worker_runtime.RunResult(0, "c\n", "", "c")

    def stop(self, container_ref, *, signal="SIGTERM"):
        self.calls.append(f"stop:{signal}")
        return worker_runtime.RunResult(0, "", "", container_ref)


class FakeBroker:
    def __init__(self):
        self.revoked = []

    def grant(self, secret_name, ttl_seconds):
        return worker_runtime.BrokerGrant(
            broker_grant_id=f"grant-{secret_name}", secret_name=secret_name,
            mode="env", granted_at="2026-05-25T05:33:05Z", ttl_seconds=ttl_seconds,
        )

    def revoke(self, broker_grant_id):
        self.revoked.append(broker_grant_id)
        return "2026-05-25T06:00:00Z"


def _write(path: Path, record: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _setup(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _write(awl / "claims" / CONTROLLER / f"{LANE}.yaml", {
        "kind": "active-work-ledger-record", "record_type": "claim", "schema_version": "1",
        "controller_id": CONTROLLER, "lane_id": LANE, "record_timestamp": "2026-05-25T05:00:00Z",
        "worktree_path": f"/worktrees/{LANE}", "envelope_ref": f".hermes/envelopes/{LANE}.md",
        "lease_seconds": 3600, "claimed_at": "2026-05-25T05:00:00Z",
        "last_heartbeat_at": "9999-01-01T00:00:00Z",
    })
    _write(awl / "leases" / CONTROLLER / f"{LANE}.yaml", {
        "kind": "worktree-lease-record", "record_type": "worktree_lease", "schema_version": "1",
        "controller_id": CONTROLLER, "lane_id": LANE, "record_timestamp": "2026-05-25T05:00:00Z",
        "lease_id": "lease-001", "worktree_path": f"/worktrees/{LANE}",
        "acquired_at": "2026-05-25T05:00:00Z", "lease_seconds": 3600,
        "expires_at": "9999-01-01T00:00:00Z",
    })
    policy = _write(tmp_path / "governance" / "policies" / "worker-container" / "p.yaml", {
        "kind": "worker-container-policy-record", "record_type": "worker_container_policy",
        "schema_version": "1", "policy_id": "podman-verification-v1", "policy_sha": _POLICY_SHA,
        "role": "verification", "runtime_engine": "podman-rootless",
        "image_ref": {"name": "ghcr.io/example/verification:latest", "sha": _IMAGE_SHA},
        "mount_manifest": [{"path": "governance", "mode": "ro"}],
        "egress_allowlist": [], "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False, "grant_authority": "controller",
    })
    return awl, policy, tmp_path / "container-instances", tmp_path / "side-effect-ledger"


def test_allocate_terminate_lifecycle_records_side_effects(tmp_path, monkeypatch, capsys):
    awl, policy, cir, sel = _setup(tmp_path)
    runner, broker = FakeRunner(), FakeBroker()
    monkeypatch.setattr(ce_cli, "_make_worker_runner", lambda: runner)
    monkeypatch.setattr(ce_cli, "_make_worker_broker", lambda: broker)

    rc = ce_cli.main([
        "worker", "allocate", "--policy", str(policy),
        "--controller-id", CONTROLLER, "--lane-id", LANE,
        "--claim-ref", f"claims/{CONTROLLER}/{LANE}.yaml",
        "--lease-ref", f"leases/{CONTROLLER}/{LANE}.yaml",
        "--active-work-ledger-root", str(awl), "--container-instance-root", str(cir),
        "--instance-id", "inst-001",
        "--side-effect-ledger-root", str(sel), "--repo-root", str(tmp_path),
        "--json",
    ])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["instance_path"].endswith("inst-001.yaml")

    started = [json.loads(p.read_text()) for p in sel.rglob("*.json") if p.name != "_head.json"]
    assert any(r["effect_kind"] == "container_action" and r["effect_status"] == "started"
               for r in started)

    rc = ce_cli.main([
        "worker", "terminate", "--instance-id", "inst-001", "--claim-id", LANE,
        "--container-instance-root", str(cir), "--reason", "normal_release",
        "--controller-id", CONTROLLER, "--lane-id", LANE,
        "--claim-ref", f"claims/{CONTROLLER}/{LANE}.yaml",
        "--active-work-ledger-root", str(awl),
        "--side-effect-ledger-root", str(sel), "--repo-root", str(tmp_path),
    ])
    assert rc == 0
    assert "grant-model-provider-key" in broker.revoked
    all_effects = [json.loads(p.read_text()) for p in sel.rglob("*.json") if p.name != "_head.json"]
    assert any(r["effect_status"] == "succeeded" for r in all_effects)
    # No secret value leaked into any side-effect record.
    assert all("super-secret" not in p.read_text() for p in sel.rglob("*.json"))


def test_gc_reaps_orphan_through_cli(tmp_path, monkeypatch, capsys):
    _awl, _policy, cir, _sel = _setup(tmp_path)
    runner, broker = FakeRunner(), FakeBroker()
    monkeypatch.setattr(ce_cli, "_make_worker_runner", lambda: runner)
    monkeypatch.setattr(ce_cli, "_make_worker_broker", lambda: broker)
    _write(cir / "pco-released" / "inst-orphan.yaml", {
        "kind": "container-instance-record", "record_type": "container_instance",
        "schema_version": "1", "instance_id": "inst-orphan",
        "policy_ref": {"policy_id": "podman-implementer-v1", "policy_sha": _POLICY_SHA,
                       "image_sha": _IMAGE_SHA},
        "image_sha": _IMAGE_SHA, "claim_id": "pco-released", "lease_id": "lease-001",
        "started_at": "2026-05-25T05:33:05Z", "stopped_at": None, "exit_code": None,
        "mount_manifest_applied": [{"path": "governance", "mode": "ro", "source": "policy"}],
        "secret_grants": [], "egress_allowlist_applied": [], "enforcement_primitive": "none",
        "policy_sha": _POLICY_SHA, "claim_released_at": "2026-05-25T07:00:00Z",
    })
    rc = ce_cli.main(["worker", "gc", "--container-instance-root", str(cir), "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["reaped_instance_ids"] == ["inst-orphan"]
    assert any(c.startswith("stop:SIGKILL") for c in runner.calls)


def test_worker_group_coexists_with_lane_and_ledger(capsys):
    # The worker group must not displace the existing groups; each bare group
    # prints its help and exits (SystemExit(0)), per the existing convention.
    for group in ("lane", "ledger", "worker"):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main([group])
        assert exc.value.code == 0
        capsys.readouterr()
