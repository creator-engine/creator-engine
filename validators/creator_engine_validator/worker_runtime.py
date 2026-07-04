"""Worker isolation runtime (Slice 2I-R) — ``allocate``/``terminate``/``gc``.

Implements the §e syscall entry points that turn the Slice 2I-S
worker-container substrate (static schema/predicate validation) into a local
``ce worker`` runtime surface:

* :func:`allocate_worker` — start a container instance bound to a live claim
  and lease under a ratified worker-container policy (rootless Podman), wiring
  mounts, credential-broker secret grants (names only — never values), and the
  egress enforcement primitive; then write a ``PCO-041``/``PCO-046``-valid
  container-instance record **after** the container start succeeds.
* :func:`terminate_worker` — revoke broker grants, stop the container, and
  persist a stopped record (revocation precedes the write).
* :func:`garbage_collect_worker` — reap container-instance records that
  outlived a released claim (the ``PCO-043`` condition) and update them.

Boundary (v1.0 / Slice 2I-R, per the worker-isolation-runtime spec):

* the container engine and the credential broker are reached **only** through
  injectable seams (:class:`PodmanCommandRunner`, :class:`NullCredentialBroker`),
  so the command construction and safety behavior are unit-tested with fakes
  and the live CLI fails closed when ``podman`` is unavailable;
* no image build / pull / push, no registry login, no Podman installation;
* secret VALUES never enter argv, instance records, secret-grant manifests,
  side-effect details, or broker metadata — only names, modes, grant ids, TTLs;
* the controller-key private key is refused as worker secret material
  (defense-in-depth on top of ``PCO-045``);
* a non-empty egress allowlist with no proven enforcement primitive is refused
  *before* the container starts — broad egress is never silently labelled
  governed;
* every refusal raises **before any side effect** (no broker grant, no
  ``podman run``, no record write), so a refused call leaves the tree
  byte-identical.

Container lifecycle side effects are recorded through the already-landed
Side-Effect Ledger runtime (``effect_kind=container_action``) when the
Side-Effect Ledger root, Active-Work Ledger root, and repo root are supplied.

Prose contract: ``docs/operations/WORKER_CONTAINER_PROTOCOL.md``;
spec: ``specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md``.
"""
from __future__ import annotations

import copy
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import yaml

from . import container_launcher
from . import side_effect_ledger_runtime
from .checks.active_work_ledger_schema import validate_active_work_ledger_record
from .checks.container_instance import validate_container_instance
from .checks.side_effect_ledger import _unsafe_secret_fields
from .checks.worker_container_policy import (
    _is_controller_key_secret,
    validate_worker_container_policy,
)
from .checks.worktree_lease_schema import validate_worktree_lease_record
from .loader import LoaderError, load_yaml


# ---------------------------------------------------------------------------
# Errors (each carries a stable ``code``)
# ---------------------------------------------------------------------------


class WorkerRuntimeError(Exception):
    code = "G5-WORKER-ERROR"


class WorkerAllocateError(WorkerRuntimeError):
    code = "G5-ALLOCATE-ERROR"


class PolicyMissing(WorkerAllocateError):
    code = "G5-POLICY-MISSING"


class PolicyInvalid(WorkerAllocateError):
    code = "G5-POLICY-INVALID"


class SecretMaterialRefused(WorkerAllocateError):
    code = "G5-SECRET-REFUSED"


class ControllerKeyRefused(SecretMaterialRefused):
    code = "G5-CONTROLLER-KEY-REFUSED"


class ClaimBindingError(WorkerAllocateError):
    code = "G5-CLAIM-BINDING"


class LeaseBindingError(WorkerAllocateError):
    code = "G5-LEASE-BINDING"


class EgressNotEnforceable(WorkerAllocateError):
    code = "G5-EGRESS-UNENFORCEABLE"


class PodmanUnavailable(WorkerAllocateError):
    code = "G5-PODMAN-UNAVAILABLE"


class ContainerStartFailed(WorkerAllocateError):
    code = "G5-CONTAINER-START-FAILED"


class InstanceCollision(WorkerAllocateError):
    code = "G5-INSTANCE-COLLISION"


class WorkerTerminateError(WorkerRuntimeError):
    code = "G5-TERMINATE-ERROR"


class InstanceNotFound(WorkerRuntimeError):
    code = "G5-INSTANCE-NOT-FOUND"


class WorkerGcError(WorkerRuntimeError):
    code = "G5-GC-ERROR"


# ---------------------------------------------------------------------------
# Seams: command runner + credential broker (injectable, fake-able in tests)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    container_id: str | None = None


@dataclass(frozen=True)
class BrokerGrant:
    """A credential-broker grant. Carries names/ids/TTL only — never a value."""

    broker_grant_id: str
    secret_name: str
    mode: str  # "env" | "file"
    granted_at: str
    ttl_seconds: int


class PodmanCommandRunner:
    """Default rootless-Podman seam.

    ``available()`` is the fail-closed gate: when ``podman`` is not on PATH the
    runtime refuses before any side effect. ``egress_primitive`` returns ``None``
    for any non-empty allowlist at this gate (no enforcement primitive is proven
    here), so the live CLI refuses non-empty egress rather than running broad.
    """

    def __init__(self, binary: str = "podman") -> None:
        self.binary = binary
        self._command_runner = container_launcher.SubprocessCommandRunner()

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def egress_primitive(self, allowlist: Sequence[Any]) -> str | None:
        return None

    def run_detached(self, argv: Sequence[str]) -> RunResult:  # pragma: no cover - gated by available()
        result = container_launcher.run_detached_podman(argv, runner=self._command_runner)
        return RunResult(result.returncode, result.stdout, result.stderr, result.container_id)

    def stop(self, container_ref: str, *, signal: str = "SIGTERM") -> RunResult:  # pragma: no cover
        proc = subprocess.run(
            [self.binary, "stop", "--signal", signal, container_ref],
            capture_output=True, text=True, check=False,
        )
        return RunResult(proc.returncode, proc.stdout, proc.stderr, container_ref)


class NullCredentialBroker:
    """Default broker seam: issues opaque grant ids; never handles values.

    Real deployments inject a broker backed by §n's contract. This stand-in
    has no access to secret values at all — it only mints/records opaque grant
    identifiers, which is exactly the substrate boundary against value leakage.
    """

    def grant(self, secret_name: str, ttl_seconds: int) -> BrokerGrant:
        return BrokerGrant(
            broker_grant_id=f"grant-{uuid.uuid4().hex[:12]}",
            secret_name=secret_name,
            mode="env",
            granted_at=_utc_now_str(None),
            ttl_seconds=ttl_seconds,
        )

    def revoke(self, broker_grant_id: str) -> str:
        return _utc_now_str(None)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AllocateResult:
    instance_path: Path
    record: dict[str, Any]
    container_id: str | None
    secret_grants: tuple[BrokerGrant, ...]
    side_effect_path: Path | None


@dataclass(frozen=True)
class TerminateResult:
    instance_path: Path
    record: dict[str, Any]
    side_effect_path: Path | None


@dataclass(frozen=True)
class GcResult:
    reaped_instance_ids: list[str]
    side_effect_paths: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_str(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def _instance_path(container_instance_root: Path, claim_id: str, instance_id: str) -> Path:
    return container_instance_root / claim_id / f"{instance_id}.yaml"


def _details_are_secret_shaped(details: dict[str, Any]) -> bool:
    return bool(_unsafe_secret_fields(details, Path("details"), "details"))


def _require_live_claim(
    awl_root: Path, claim_ref: str, controller_id: str, lane_id: str
) -> dict[str, Any]:
    claim_path = awl_root / claim_ref
    if not claim_path.is_file():
        raise ClaimBindingError(f"no Active-Work Ledger claim at {claim_path}; allocate a lane first")
    try:
        claim = load_yaml(claim_path)
    except LoaderError as exc:
        raise ClaimBindingError(f"claim at {claim_path} is unreadable: {exc}") from exc
    if not isinstance(claim, dict):
        raise ClaimBindingError(f"claim at {claim_path} is not a mapping")
    if validate_active_work_ledger_record(claim, claim_path):
        raise ClaimBindingError(f"claim at {claim_path} fails Active-Work Ledger schema validation")
    if claim.get("controller_id") != controller_id or claim.get("lane_id") != lane_id:
        raise ClaimBindingError(
            f"claim at {claim_path} names {claim.get('controller_id')!r}/{claim.get('lane_id')!r}, "
            f"expected {controller_id!r}/{lane_id!r}"
        )
    if claim.get("released_at"):
        raise ClaimBindingError(f"claim at {claim_path} is released; allocate a fresh lane")
    return claim


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or value.startswith(("commit:", "source-controlled:")):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _require_live_lease(
    awl_root: Path, lease_ref: str, controller_id: str, lane_id: str, now: datetime | None
) -> dict[str, Any]:
    lease_path = awl_root / lease_ref
    if not lease_path.is_file():
        raise LeaseBindingError(f"no Worktree Lease at {lease_path}; acquire a lease first")
    try:
        lease = load_yaml(lease_path)
    except LoaderError as exc:
        raise LeaseBindingError(f"lease at {lease_path} is unreadable: {exc}") from exc
    if not isinstance(lease, dict):
        raise LeaseBindingError(f"lease at {lease_path} is not a mapping")
    if validate_worktree_lease_record(lease, lease_path):
        raise LeaseBindingError(f"lease at {lease_path} fails Worktree Lease schema validation")
    if lease.get("controller_id") != controller_id or lease.get("lane_id") != lane_id:
        raise LeaseBindingError(
            f"lease at {lease_path} names {lease.get('controller_id')!r}/{lease.get('lane_id')!r}, "
            f"expected {controller_id!r}/{lane_id!r}"
        )
    expires = _parse_utc(lease.get("expires_at"))
    if expires is not None and expires <= (now or datetime.now(UTC)):
        raise LeaseBindingError(f"lease at {lease_path} is expired; acquire a fresh lease")
    return lease


def build_podman_run_argv(
    *,
    image_name: str,
    image_sha: str,
    instance_id: str,
    mounts: Sequence[dict[str, Any]],
    secret_grants: Sequence[BrokerGrant],
    network_mode: str,
) -> list[str]:
    """Construct a deterministic rootless ``podman run --detach`` argv.

    Rootless posture: ``--userns=keep-id`` and ``--security-opt
    no-new-privileges``. Secrets are referenced by NAME via ``--secret`` (the
    value never enters argv). The image is pinned by digest (``name@sha256:…``).
    """
    return container_launcher.build_podman_run_argv(
        image_name=image_name,
        image_sha=image_sha,
        mode="detached",
        instance_id=instance_id,
        mounts=mounts,
        secret_grants=secret_grants,
        network_mode=network_mode,
    )


def load_policy(policy_path: Path | str) -> dict[str, Any]:
    """Load + validate a worker-container policy (PCO-040/PCO-045)."""
    policy_path = Path(policy_path)
    if not policy_path.is_file():
        raise PolicyMissing(f"no worker-container policy at {policy_path}")
    try:
        policy = load_yaml(policy_path)
    except LoaderError as exc:
        raise PolicyInvalid(f"policy at {policy_path} is unreadable: {exc}") from exc
    if not isinstance(policy, dict):
        raise PolicyInvalid(f"policy at {policy_path} is not a mapping")
    # Defense-in-depth: refuse a controller-key secret name explicitly, before
    # any broker grant or Podman command construction (PCO-045 would also fire).
    for name in policy.get("secret_allowlist", []) or []:
        if isinstance(name, str) and _is_controller_key_secret(name):
            raise ControllerKeyRefused(
                f"policy at {policy_path} allowlists controller-key secret {name!r}; "
                "the controller-key private key MUST NOT enter any worker container"
            )
    errors = validate_worker_container_policy(policy, policy_path)
    if errors:
        raise PolicyInvalid(
            f"policy at {policy_path} fails validation: " + "; ".join(e.format() for e in errors)
        )
    return policy


def _record_container_side_effect(
    *,
    effect_status: str,
    summary: str,
    instance_id: str,
    controller_id: str,
    lane_id: str,
    claim_ref: str,
    repo_root: Path | str,
    side_effect_ledger_root: Path | str,
    active_work_ledger_root: Path | str,
    now: datetime | None,
) -> Path:
    result = side_effect_ledger_runtime.record(
        controller_id=controller_id,
        lane_id=lane_id,
        claim_ref=claim_ref,
        effect_id=f"container-{effect_status}-{instance_id}",
        effect_kind="container_action",
        effect_status=effect_status,
        summary=summary,
        occurred_at=_utc_now_str(now),
        repo_root=repo_root,
        side_effect_ledger_root=side_effect_ledger_root,
        active_work_ledger_root=active_work_ledger_root,
        actor_role="controller",
    )
    return result.record_path


# ---------------------------------------------------------------------------
# allocate_worker (§e.1)
# ---------------------------------------------------------------------------


def allocate_worker(
    *,
    policy_path: Path | str,
    controller_id: str,
    lane_id: str,
    claim_ref: str,
    lease_ref: str,
    active_work_ledger_root: Path | str,
    container_instance_root: Path | str,
    instance_id: str,
    started_at: str | None = None,
    details: dict[str, Any] | None = None,
    runner: Any | None = None,
    broker: Any | None = None,
    side_effect_ledger_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
) -> AllocateResult:
    """Allocate a worker container under a ratified policy, bound to a claim.

    Every refusal raises before any side effect (broker grant / ``podman run`` /
    record write). On a Podman start failure, broker grants are revoked and no
    instance or side-effect record is written.
    """
    awl_root = Path(active_work_ledger_root)
    cir = Path(container_instance_root)
    runner = runner if runner is not None else PodmanCommandRunner()
    broker = broker if broker is not None else NullCredentialBroker()

    # 1. Refuse secret-shaped caller details before any work.
    if details is not None:
        if not isinstance(details, dict):
            raise WorkerAllocateError("details must be a JSON object (not an array or scalar)")
        if _details_are_secret_shaped(details):
            raise SecretMaterialRefused(
                "allocate details contain secret-shaped material; refusing before any side effect"
            )

    # 2. Load + validate the policy (raises ControllerKeyRefused / PolicyInvalid).
    policy = load_policy(policy_path)

    # 3. Bind to a live, matching claim and lease.
    claim = _require_live_claim(awl_root, claim_ref, controller_id, lane_id)
    lease = _require_live_lease(awl_root, lease_ref, controller_id, lane_id, now)

    # 4. Egress decision — before Podman is touched.
    egress = policy.get("egress_allowlist") or []
    if not egress:
        enforcement_primitive = "none"
        network_mode = "none"
    else:
        primitive = runner.egress_primitive(egress)
        if not primitive or primitive == "none":
            raise EgressNotEnforceable(
                f"policy {policy.get('policy_id')!r} declares a non-empty egress allowlist but no "
                "enforcement primitive is proven; refusing before container start (broad egress is "
                "never silently labelled governed)"
            )
        enforcement_primitive = primitive
        network_mode = primitive

    # 5. Podman must be available — fail closed before any side effect.
    if not runner.available():
        raise PodmanUnavailable(
            "podman is unavailable; refusing worker allocation before any broker grant, container "
            "start, or record write"
        )

    # 6. Never overwrite an existing instance record.
    instance_path = _instance_path(cir, lane_id, instance_id)
    if instance_path.exists():
        raise InstanceCollision(f"container-instance record already exists: {instance_path}")

    # --- side effects begin here ---
    started = started_at or _utc_now_str(now)
    ttl_seconds = int(claim.get("lease_seconds") or 3600)
    grants: list[BrokerGrant] = [
        broker.grant(name, ttl_seconds)
        for name in policy.get("secret_allowlist") or []
        if isinstance(name, str) and name
    ]

    argv = build_podman_run_argv(
        image_name=policy["image_ref"]["name"],
        image_sha=policy["image_ref"]["sha"],
        instance_id=instance_id,
        mounts=[{"path": m["path"], "mode": m["mode"]} for m in policy.get("mount_manifest", [])],
        secret_grants=grants,
        network_mode=network_mode,
    )
    run_result = runner.run_detached(argv)
    if getattr(run_result, "returncode", 1) != 0:
        # Container did not start: revoke grants, write nothing (no misleading record).
        for grant in grants:
            broker.revoke(grant.broker_grant_id)
        raise ContainerStartFailed(
            f"podman run failed (returncode={getattr(run_result, 'returncode', '?')}); "
            "no container-instance or side-effect record written"
        )

    # 7. Build + write the container-instance record atomically, after start.
    record = {
        "kind": "container-instance-record",
        "record_type": "container_instance",
        "schema_version": "1",
        "instance_id": instance_id,
        "policy_ref": {
            "policy_id": policy["policy_id"],
            "policy_sha": policy["policy_sha"],
            "image_sha": policy["image_ref"]["sha"],
        },
        "image_sha": policy["image_ref"]["sha"],
        "claim_id": lane_id,
        "lease_id": lease["lease_id"],
        "started_at": started,
        "stopped_at": None,
        "exit_code": None,
        "mount_manifest_applied": [
            {"path": m["path"], "mode": m["mode"], "source": "policy"}
            for m in policy.get("mount_manifest", [])
        ],
        "secret_grants": [
            {
                "secret_name": grant.secret_name,
                "mode": grant.mode,
                "broker_grant_id": grant.broker_grant_id,
                "granted_at": grant.granted_at,
                "revoked_at": None,
                "ttl_seconds": grant.ttl_seconds,
            }
            for grant in grants
        ],
        "egress_allowlist_applied": copy.deepcopy(egress),
        "enforcement_primitive": enforcement_primitive,
        "policy_sha": policy["policy_sha"],
    }
    validation_errors = validate_container_instance(record, instance_path)
    if validation_errors:  # pragma: no cover - guards against an internal regression
        for grant in grants:
            broker.revoke(grant.broker_grant_id)
        raise WorkerAllocateError(
            "internal error: generated container-instance record is invalid: "
            + "; ".join(e.format() for e in validation_errors)
        )
    _atomic_write(instance_path, yaml.safe_dump(record, sort_keys=True))

    # 8. Record the container_started side effect when ledger roots are supplied.
    side_effect_path = None
    if side_effect_ledger_root is not None and repo_root is not None:
        side_effect_path = _record_container_side_effect(
            effect_status="started",
            summary=f"worker container {instance_id} started for lane {lane_id}",
            instance_id=instance_id,
            controller_id=controller_id,
            lane_id=lane_id,
            claim_ref=claim_ref,
            repo_root=repo_root,
            side_effect_ledger_root=side_effect_ledger_root,
            active_work_ledger_root=awl_root,
            now=now,
        )

    return AllocateResult(
        instance_path=instance_path,
        record=record,
        container_id=getattr(run_result, "container_id", None),
        secret_grants=tuple(grants),
        side_effect_path=side_effect_path,
    )


# ---------------------------------------------------------------------------
# terminate_worker (§e.8)
# ---------------------------------------------------------------------------


def _load_instance(instance_path: Path) -> dict[str, Any]:
    try:
        record = load_yaml(instance_path)
    except LoaderError as exc:
        raise WorkerTerminateError(f"instance record at {instance_path} is unreadable: {exc}") from exc
    if not isinstance(record, dict):
        raise WorkerTerminateError(f"instance record at {instance_path} is not a mapping")
    return record


def _revoke_open_grants(record: dict[str, Any], broker: Any, revoked_at: str) -> None:
    """Revoke every still-open broker grant and mark it on the record.

    Revocation happens here, before the record is persisted, so the persisted
    record's ``revoked_at`` is proof that revocation preceded the write.
    """
    for grant in record.get("secret_grants", []) or []:
        if not isinstance(grant, dict):
            continue
        if grant.get("revoked_at") is None and grant.get("broker_grant_id"):
            broker.revoke(grant["broker_grant_id"])
            grant["revoked_at"] = revoked_at


def terminate_worker(
    *,
    instance_id: str,
    claim_id: str,
    container_instance_root: Path | str,
    reason: str,
    runner: Any | None = None,
    broker: Any | None = None,
    exit_code: int = 0,
    stopped_at: str | None = None,
    signal: str = "SIGTERM",
    controller_id: str | None = None,
    lane_id: str | None = None,
    claim_ref: str | None = None,
    active_work_ledger_root: Path | str | None = None,
    side_effect_ledger_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
) -> TerminateResult:
    """Stop a worker container and persist a stopped record.

    Order: revoke broker grants → stop the container → write the stopped record
    → record the ``container_stopped`` side effect. Revocation precedes the
    write (§n.1).
    """
    cir = Path(container_instance_root)
    runner = runner if runner is not None else PodmanCommandRunner()
    broker = broker if broker is not None else NullCredentialBroker()

    instance_path = _instance_path(cir, claim_id, instance_id)
    if not instance_path.is_file():
        raise InstanceNotFound(f"no container-instance record at {instance_path}")
    record = _load_instance(instance_path)

    revoked_at = stopped_at or _utc_now_str(now)
    _revoke_open_grants(record, broker, revoked_at)

    runner.stop(instance_id, signal=signal)

    record["stopped_at"] = stopped_at or _utc_now_str(now)
    record["exit_code"] = exit_code
    errors = validate_container_instance(record, instance_path)
    if errors:  # pragma: no cover - guards against an internal regression
        raise WorkerTerminateError(
            "internal error: terminated container-instance record is invalid: "
            + "; ".join(e.format() for e in errors)
        )
    _atomic_write(instance_path, yaml.safe_dump(record, sort_keys=True))

    side_effect_path = None
    if (
        side_effect_ledger_root is not None
        and repo_root is not None
        and active_work_ledger_root is not None
        and controller_id is not None
        and lane_id is not None
        and claim_ref is not None
    ):
        try:
            side_effect_path = _record_container_side_effect(
                effect_status="succeeded",
                summary=f"worker container {instance_id} stopped ({reason})",
                instance_id=instance_id,
                controller_id=controller_id,
                lane_id=lane_id,
                claim_ref=claim_ref,
                repo_root=repo_root,
                side_effect_ledger_root=side_effect_ledger_root,
                active_work_ledger_root=Path(active_work_ledger_root),
                now=now,
            )
        except side_effect_ledger_runtime.LedgerRecordError:
            # The claim is no longer live (e.g. already released): the reap is
            # persisted; we do not write a misleading side-effect record.
            side_effect_path = None

    return TerminateResult(instance_path=instance_path, record=record, side_effect_path=side_effect_path)


# ---------------------------------------------------------------------------
# garbage_collect_worker (§e.9)
# ---------------------------------------------------------------------------


def garbage_collect_worker(
    *,
    container_instance_root: Path | str,
    runner: Any | None = None,
    broker: Any | None = None,
    claim_id: str | None = None,
    exit_code: int = 137,
    signal: str = "SIGKILL",
    now: datetime | None = None,
) -> GcResult:
    """Reap container-instance records that outlived a released claim.

    Identifies the ``PCO-043`` condition (``claim_released_at`` present and
    ``stopped_at`` null), revokes any open grants, force-reaps the container,
    and updates the record deterministically. Optionally scoped to ``claim_id``.
    """
    cir = Path(container_instance_root)
    runner = runner if runner is not None else PodmanCommandRunner()
    broker = broker if broker is not None else NullCredentialBroker()

    reaped: list[str] = []
    if not cir.exists():
        return GcResult(reaped_instance_ids=reaped)

    for path in sorted(cir.rglob("*.yaml")):
        if ".tmp." in path.name:
            continue
        try:
            record = load_yaml(path)
        except LoaderError:
            continue
        if not isinstance(record, dict) or record.get("kind") != "container-instance-record":
            continue
        if claim_id is not None and record.get("claim_id") != claim_id:
            continue
        # PCO-043 condition: claim released but container still running.
        if record.get("claim_released_at") is None or record.get("stopped_at") is not None:
            continue

        revoked_at = _utc_now_str(now)
        _revoke_open_grants(record, broker, revoked_at)
        runner.stop(record.get("instance_id", ""), signal=signal)
        record["stopped_at"] = _utc_now_str(now)
        record["exit_code"] = exit_code
        errors = validate_container_instance(record, path)
        if errors:  # pragma: no cover - guards against an internal regression
            raise WorkerGcError(
                f"internal error: reaped container-instance record at {path} is invalid: "
                + "; ".join(e.format() for e in errors)
            )
        _atomic_write(path, yaml.safe_dump(record, sort_keys=True))
        instance_id = record.get("instance_id")
        if isinstance(instance_id, str) and instance_id:
            reaped.append(instance_id)

    reaped.sort()
    return GcResult(reaped_instance_ids=reaped)
