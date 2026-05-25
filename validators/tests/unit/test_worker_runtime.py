"""Unit tests for the Slice 2I-R worker isolation runtime (worker_runtime).

Strict-TDD coverage for the §e syscall entry points implemented in this gate:
``allocate_worker``, ``terminate_worker``, ``garbage_collect_worker`` and the
pure command-construction / loading helpers.

All container-engine and credential-broker interactions go through injectable
seams (``FakeRunner`` / ``FakeBroker``); no real Podman is invoked and no real
secret value is ever handled.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from creator_engine_validator import worker_runtime
from creator_engine_validator.checks.container_instance import validate_container_instance


_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64
CONTROLLER = "hermes-primary"
LANE = "pco-slice2ir-worker"


# ---------------------------------------------------------------------------
# Injectable seams (fakes)
# ---------------------------------------------------------------------------


@dataclass
class FakeRunResult:
    returncode: int = 0
    stdout: str = "container-deadbeef\n"
    stderr: str = ""
    container_id: str | None = "container-deadbeef"


@dataclass
class FakeRunner:
    available_flag: bool = True
    egress_primitive_value: str | None = None
    run_result: FakeRunResult = field(default_factory=FakeRunResult)
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def available(self) -> bool:
        return self.available_flag

    def egress_primitive(self, allowlist):
        self.calls.append(("egress_primitive", list(allowlist)))
        return self.egress_primitive_value

    def run_detached(self, argv):
        self.calls.append(("run_detached", list(argv)))
        return self.run_result

    def stop(self, container_ref, *, signal="SIGTERM"):
        self.calls.append(("stop", (container_ref, signal)))
        return FakeRunResult(returncode=0, container_id=container_ref)

    @property
    def did_run(self) -> bool:
        return any(name == "run_detached" for name, _ in self.calls)


@dataclass
class FakeBroker:
    events: list[tuple[str, str]] = field(default_factory=list)  # (action, ref)
    _counter: int = 0

    def grant(self, secret_name, ttl_seconds):
        self._counter += 1
        grant_id = f"grant-{secret_name}-{self._counter:03d}"
        self.events.append(("grant", grant_id))
        return worker_runtime.BrokerGrant(
            broker_grant_id=grant_id,
            secret_name=secret_name,
            mode="env",
            granted_at="2026-05-25T05:33:05Z",
            ttl_seconds=ttl_seconds,
        )

    def revoke(self, broker_grant_id):
        self.events.append(("revoke", broker_grant_id))
        return "2026-05-25T06:00:00Z"

    @property
    def granted_ids(self):
        return [ref for action, ref in self.events if action == "grant"]

    @property
    def revoked_ids(self):
        return [ref for action, ref in self.events if action == "revoke"]


# ---------------------------------------------------------------------------
# Fixtures: policy / claim / lease writers
# ---------------------------------------------------------------------------


def policy_record(**overrides) -> dict:
    record = {
        "kind": "worker-container-policy-record",
        "record_type": "worker_container_policy",
        "schema_version": "1",
        "policy_id": "podman-verification-v1",
        "policy_sha": _POLICY_SHA,
        "role": "verification",
        "runtime_engine": "podman-rootless",
        "image_ref": {"name": "ghcr.io/example/verification:latest", "sha": _IMAGE_SHA},
        "mount_manifest": [{"path": "governance", "mode": "ro"}],
        "egress_allowlist": [],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }
    record.update(overrides)
    return record


def write_policy(path: Path, **overrides) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(policy_record(**overrides), sort_keys=True), encoding="utf-8")
    return path


def write_claim(awl: Path, controller=CONTROLLER, lane=LANE, released=False) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": "2026-05-25T05:00:00Z",
        "worktree_path": f"/worktrees/{lane}",
        "envelope_ref": f".hermes/envelopes/{lane}.md",
        "lease_seconds": 3600,
        "claimed_at": "2026-05-25T05:00:00Z",
        "last_heartbeat_at": "9999-01-01T00:00:00Z",
    }
    if released:
        record["released_at"] = "2026-05-25T07:00:00Z"
    path = awl / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def write_lease(awl: Path, controller=CONTROLLER, lane=LANE) -> Path:
    record = {
        "kind": "worktree-lease-record",
        "record_type": "worktree_lease",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": "2026-05-25T05:00:00Z",
        "lease_id": "lease-001",
        "worktree_path": f"/worktrees/{lane}",
        "acquired_at": "2026-05-25T05:00:00Z",
        "lease_seconds": 3600,
        "expires_at": "9999-01-01T00:00:00Z",
    }
    path = awl / "leases" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _allocate(tmp_path, *, runner, broker, policy_overrides=None, details=None,
              side_effect=True, instance_id="inst-worker-001"):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    write_claim(awl)
    write_lease(awl)
    policy_path = write_policy(tmp_path / "governance" / "policies" / "worker-container" / "p.yaml",
                               **(policy_overrides or {}))
    cir = tmp_path / "container-instances"
    kwargs = dict(
        policy_path=policy_path,
        controller_id=CONTROLLER,
        lane_id=LANE,
        claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
        lease_ref=f"leases/{CONTROLLER}/{LANE}.yaml",
        active_work_ledger_root=awl,
        container_instance_root=cir,
        instance_id=instance_id,
        runner=runner,
        broker=broker,
        details=details,
    )
    if side_effect:
        kwargs.update(
            side_effect_ledger_root=tmp_path / "side-effect-ledger",
            repo_root=tmp_path,
        )
    return worker_runtime.allocate_worker(**kwargs), cir, awl


def _ledger_records(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.json") if p.name != "_head.json")


# ---------------------------------------------------------------------------
# allocate_worker
# ---------------------------------------------------------------------------


def test_allocate_writes_valid_instance_after_successful_runner(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    result, cir, _ = _allocate(tmp_path, runner=runner, broker=broker)

    assert result.instance_path.is_file()
    assert runner.did_run
    record = yaml.safe_load(result.instance_path.read_text())
    # The persisted record is a fully schema-valid container-instance record.
    assert validate_container_instance(record, result.instance_path) == []
    assert record["claim_id"] == LANE
    assert record["instance_id"] == "inst-worker-001"
    assert record["policy_sha"] == record["policy_ref"]["policy_sha"] == _POLICY_SHA
    assert record["image_sha"] == _IMAGE_SHA
    assert record["stopped_at"] is None
    # one secret grant, recorded by name only, never a value
    assert record["secret_grants"][0]["secret_name"] == "model-provider-key"
    assert record["secret_grants"][0]["revoked_at"] is None
    assert "secret_value" not in record["secret_grants"][0]


def test_allocate_podman_run_argv_is_rootless_and_value_free(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    _allocate(tmp_path, runner=runner, broker=broker)
    argv = [a for name, a in runner.calls if name == "run_detached"][0]
    joined = " ".join(argv)
    assert argv[:3] == ["podman", "run", "--detach"]
    assert "--name" in argv and "inst-worker-001" in argv
    assert "no-new-privileges" in joined
    assert "--userns" in joined or any(a.startswith("--userns") for a in argv)
    assert "--network" in argv and "none" in argv  # empty egress → no network
    # The broker never yields a value; no secret value can appear in argv.
    assert "model-provider-key" in joined  # name is fine
    assert "super-secret" not in joined


def test_allocate_fails_closed_when_podman_unavailable(tmp_path):
    runner, broker = FakeRunner(available_flag=False), FakeBroker()
    with pytest.raises(worker_runtime.PodmanUnavailable):
        _allocate(tmp_path, runner=runner, broker=broker)
    cir = tmp_path / "container-instances"
    assert _ledger_records(cir) == [] and not any(cir.rglob("*.yaml")) if cir.exists() else True
    assert not runner.did_run
    assert broker.granted_ids == []
    assert _ledger_records(tmp_path / "side-effect-ledger") == []


def test_allocate_refuses_secret_shaped_details_before_side_effects(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    with pytest.raises(worker_runtime.SecretMaterialRefused):
        _allocate(tmp_path, runner=runner, broker=broker,
                  details={"api_key": "super-secret-value-1234567890"})
    assert not runner.did_run
    assert broker.granted_ids == []
    assert not (tmp_path / "container-instances").exists() or \
        not any((tmp_path / "container-instances").rglob("*.yaml"))
    assert _ledger_records(tmp_path / "side-effect-ledger") == []


def test_allocate_refuses_controller_key_secret_name_before_side_effects(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    with pytest.raises(worker_runtime.ControllerKeyRefused):
        _allocate(tmp_path, runner=runner, broker=broker,
                  policy_overrides={"secret_allowlist": ["hermes-controller-key"]})
    assert not runner.did_run
    assert broker.granted_ids == []
    assert _ledger_records(tmp_path / "side-effect-ledger") == []


def test_allocate_empty_egress_records_enforcement_none(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    result, _, _ = _allocate(tmp_path, runner=runner, broker=broker)
    record = yaml.safe_load(result.instance_path.read_text())
    assert record["enforcement_primitive"] == "none"
    assert record["egress_allowlist_applied"] == []


def test_allocate_refuses_nonempty_egress_without_proven_primitive(tmp_path):
    runner = FakeRunner(available_flag=True, egress_primitive_value=None)
    broker = FakeBroker()
    overrides = {"egress_allowlist": [{"host": "api.anthropic.com", "protocol": "https"}]}
    with pytest.raises(worker_runtime.EgressNotEnforceable):
        _allocate(tmp_path, runner=runner, broker=broker, policy_overrides=overrides)
    assert not runner.did_run  # refused before container start
    assert broker.granted_ids == []
    assert _ledger_records(tmp_path / "side-effect-ledger") == []


def test_allocate_nonempty_egress_with_proven_primitive_records_it(tmp_path):
    runner = FakeRunner(available_flag=True, egress_primitive_value="pasta")
    broker = FakeBroker()
    overrides = {"egress_allowlist": [{"host": "api.anthropic.com", "protocol": "https"}]}
    result, _, _ = _allocate(tmp_path, runner=runner, broker=broker, policy_overrides=overrides)
    record = yaml.safe_load(result.instance_path.read_text())
    assert record["enforcement_primitive"] == "pasta"
    assert record["egress_allowlist_applied"] == overrides["egress_allowlist"]
    argv = [a for name, a in runner.calls if name == "run_detached"][0]
    assert "pasta" in " ".join(argv)


def test_allocate_records_container_started_side_effect(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    _allocate(tmp_path, runner=runner, broker=broker)
    records = _ledger_records(tmp_path / "side-effect-ledger")
    assert len(records) == 1
    payload = json.loads(records[0].read_text())
    assert payload["effect_kind"] == "container_action"
    assert payload["effect_status"] == "started"


def test_allocate_refuses_released_claim(tmp_path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    write_claim(awl, released=True)
    write_lease(awl)
    policy_path = write_policy(tmp_path / "governance" / "policies" / "worker-container" / "p.yaml")
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    with pytest.raises(worker_runtime.ClaimBindingError):
        worker_runtime.allocate_worker(
            policy_path=policy_path, controller_id=CONTROLLER, lane_id=LANE,
            claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
            lease_ref=f"leases/{CONTROLLER}/{LANE}.yaml",
            active_work_ledger_root=awl,
            container_instance_root=tmp_path / "container-instances",
            instance_id="inst-worker-001", runner=runner, broker=broker,
        )
    assert not runner.did_run


def test_allocate_refuses_missing_policy(tmp_path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    write_claim(awl)
    write_lease(awl)
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    with pytest.raises(worker_runtime.PolicyMissing):
        worker_runtime.allocate_worker(
            policy_path=tmp_path / "nope.yaml", controller_id=CONTROLLER, lane_id=LANE,
            claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
            lease_ref=f"leases/{CONTROLLER}/{LANE}.yaml",
            active_work_ledger_root=awl,
            container_instance_root=tmp_path / "container-instances",
            instance_id="inst-worker-001", runner=runner, broker=broker,
        )
    assert not runner.did_run


# ---------------------------------------------------------------------------
# terminate_worker
# ---------------------------------------------------------------------------


def test_terminate_revokes_grants_before_writing_stopped_record(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    result, cir, awl = _allocate(tmp_path, runner=runner, broker=broker)
    grant_id = broker.granted_ids[0]

    term = worker_runtime.terminate_worker(
        instance_id="inst-worker-001",
        claim_id=LANE,
        container_instance_root=cir,
        reason="normal_release",
        runner=runner,
        broker=broker,
        controller_id=CONTROLLER,
        lane_id=LANE,
        claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
        active_work_ledger_root=awl,
        side_effect_ledger_root=tmp_path / "side-effect-ledger",
        repo_root=tmp_path,
    )

    # The broker grant was revoked.
    assert grant_id in broker.revoked_ids
    # The persisted stopped record proves revoke happened before the write:
    # its secret grant carries revoked_at, and the container is stopped.
    record = yaml.safe_load(term.instance_path.read_text())
    assert record["stopped_at"] is not None
    assert record["exit_code"] is not None
    assert record["secret_grants"][0]["revoked_at"] is not None
    # PCO-043 is cleared (stopped) and the record stays schema-valid.
    assert validate_container_instance(record, term.instance_path) == []
    # a container_stopped side-effect was recorded (claim still live at release)
    payloads = [json.loads(p.read_text()) for p in _ledger_records(tmp_path / "side-effect-ledger")]
    assert any(p["effect_kind"] == "container_action" and p["effect_status"] == "succeeded"
               for p in payloads)
    assert ("stop", ) or runner.calls  # runner.stop invoked
    assert any(name == "stop" for name, _ in runner.calls)


def test_terminate_unknown_instance_fails(tmp_path):
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    with pytest.raises(worker_runtime.InstanceNotFound):
        worker_runtime.terminate_worker(
            instance_id="inst-absent",
            claim_id=LANE,
            container_instance_root=tmp_path / "container-instances",
            reason="normal_release",
            runner=runner,
            broker=broker,
        )


# ---------------------------------------------------------------------------
# garbage_collect_worker
# ---------------------------------------------------------------------------


def _write_instance(cir: Path, instance_id: str, claim_id: str, *,
                    claim_released_at=None, stopped_at=None) -> Path:
    record = {
        "kind": "container-instance-record",
        "record_type": "container_instance",
        "schema_version": "1",
        "instance_id": instance_id,
        "policy_ref": {"policy_id": "podman-implementer-v1", "policy_sha": _POLICY_SHA,
                       "image_sha": _IMAGE_SHA},
        "image_sha": _IMAGE_SHA,
        "claim_id": claim_id,
        "lease_id": "lease-001",
        "started_at": "2026-05-25T05:33:05Z",
        "stopped_at": stopped_at,
        "exit_code": 0 if stopped_at else None,
        "mount_manifest_applied": [{"path": "governance", "mode": "ro", "source": "policy"}],
        "secret_grants": [],
        "egress_allowlist_applied": [],
        "enforcement_primitive": "none",
        "policy_sha": _POLICY_SHA,
    }
    if claim_released_at is not None:
        record["claim_released_at"] = claim_released_at
    path = cir / claim_id / f"{instance_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def test_gc_reaps_orphaned_released_claim_instances(tmp_path):
    cir = tmp_path / "container-instances"
    orphan = _write_instance(cir, "inst-orphan", "pco-released",
                             claim_released_at="2026-05-25T07:00:00Z", stopped_at=None)
    healthy = _write_instance(cir, "inst-healthy", "pco-live", stopped_at=None)
    runner, broker = FakeRunner(available_flag=True), FakeBroker()

    result = worker_runtime.garbage_collect_worker(
        container_instance_root=cir, runner=runner, broker=broker,
    )

    assert result.reaped_instance_ids == ["inst-orphan"]
    reaped = yaml.safe_load(orphan.read_text())
    assert reaped["stopped_at"] is not None
    assert reaped["exit_code"] is not None
    # PCO-043 condition is cleared on the reaped record.
    assert validate_container_instance(reaped, orphan) == []
    # The healthy running instance is untouched.
    assert yaml.safe_load(healthy.read_text())["stopped_at"] is None
    assert any(name == "stop" for name, _ in runner.calls)


def test_gc_is_a_noop_when_no_orphans(tmp_path):
    cir = tmp_path / "container-instances"
    _write_instance(cir, "inst-healthy", "pco-live", stopped_at=None)
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    result = worker_runtime.garbage_collect_worker(
        container_instance_root=cir, runner=runner, broker=broker,
    )
    assert result.reaped_instance_ids == []
    assert not any(name == "stop" for name, _ in runner.calls)
