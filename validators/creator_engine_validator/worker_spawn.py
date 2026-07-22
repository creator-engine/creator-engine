"""Harness-agnostic CE worker-spawn primitive (ce-ops#163 REQ-2).

This module defines a first-class CE ``worker`` spawn plan separate from the
older container-allocation runtime in :mod:`worker_runtime`. It is intentionally
bounded: role/depth/worktree/prompt validation, credential-scrubbed launch
environment construction, value-free worker records, and a thin injectable seam
over the retained v1 ``launch_runtime.launch`` surface.

It does not implement born-a-foreman injection, hard-deny enforcement, reviewer
author gates, or controller merge gates. Those later gates consume the
``.ce/state/workers/<worker_id>/worker.yaml`` artifact written here.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from . import (
    brain_bootstrap,
    codex_launch_spec,
    codex_worker_config,
    lane_runtime,
    launch_runtime,
)


WORKER_ROLES: dict[str, str] = {
    "architect_research": "read-only",
    "researcher": "read-only",
    "implementer": "implementation",
    "reviewer": "review",
    "verification": "audit",
}
# The worker's execution lane is not itself a model-tier policy.  Keep this
# translation explicit at the live spawn boundary so adding a worker role
# cannot silently inherit the permissive ``role=None`` (seat) default.
WORKER_POLICY_ROLES: dict[str, str] = {
    "architect_research": "verify",
    "researcher": "verify",
    "implementer": "implementation",
    "reviewer": "advisory",
    "verification": "verify",
}
GOVERNED_WORKER_ROLES = frozenset({"researcher", "implementer", "reviewer"})
WORKER_TIER_CONTRACT_SCHEMA = "schemas/worker-tier-contract.schema.yaml"
WORKER_TIER_FOREMAN_DISPATCH_REF = "docs/contracts/harness-seat-contract.md#foreman_dispatch"
WORKER_TIER_PROHIBITED_CAPABILITIES = (
    "push",
    "self_approve",
    "create_issues",
    "task_other_seats",
)
WORKER_TIER_ROLE_SURFACE_REFS = {
    "researcher": ".claude/agents/architect_research.md",
    "implementer": ".claude/agents/implementer.md",
    "reviewer": ".claude/agents/reviewer.md",
}
WORKER_TIER_DECLARED_CAPABILITIES = {
    "researcher": ("read", "research", "structured_result"),
    "implementer": ("read", "edit", "test", "structured_result"),
    "reviewer": ("read", "review", "structured_result"),
}
DEFAULT_MAX_DEPTH = 3
WORKER_RECORD_REL = Path(".ce/state/workers")

_EXACT_CREDENTIAL_ENV = frozenset(
    {
        *codex_launch_spec.CREDENTIAL_ENV_UNSETS,
        "GITHUB_PAT",
        "GITHUB_APP_PRIVATE_KEY",
        "GIT_ASKPASS",
        "SSH_ASKPASS",
        "SSH_AUTH_SOCK",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "CE_PICKUP_TOKEN",
        "CE_FORGE_MINT_BROKER_USER_TOKEN",
    }
)
_SECRET_ENV_TOKENS = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE_KEY", "API_KEY", "CREDENTIAL", "AUTH")
_SAFE_BASE_ENV_NAMES = frozenset({"PATH", "SHELL", "TERM", "LANG"})
_SAFE_CE_METADATA_ENV_NAMES = frozenset(
    {
        "CE_CONTROLLER_ID",
        "CE_FOREMAN_ID",
        "CE_HOST_ID",
        "CE_RUN_ID",
        "CE_SEAT_ID",
    }
)


class WorkerSpawnError(Exception):
    code = "CE163-WORKER-SPAWN-ERROR"


class InvalidWorkerRole(WorkerSpawnError):
    code = "CE163-WORKER-ROLE"


class InvalidWorkerHarness(WorkerSpawnError):
    code = "CE163-WORKER-HARNESS"


class InvalidWorkerDepth(WorkerSpawnError):
    code = "CE163-WORKER-DEPTH"


class InvalidWorkerWorktree(WorkerSpawnError):
    code = "CE163-WORKER-WORKTREE"


class InvalidWorkerPrompt(WorkerSpawnError):
    code = "CE163-WORKER-PROMPT"


class WorkerRecordCollision(WorkerSpawnError):
    code = "CE163-WORKER-RECORD-COLLISION"


class WorkerRecordReservationFailed(WorkerSpawnError):
    code = "CE163-WORKER-RECORD-RESERVATION-FAILED"


class WorkerLaunchFailed(WorkerSpawnError):
    code = "CE163-WORKER-LAUNCH-FAILED"


class WorkerManagedConfigRefused(WorkerSpawnError):
    code = "CE607-MANAGED-CONFIG-REFUSED"


class WorkerForemanContractRefused(WorkerSpawnError):
    code = "CE163-WORKER-FOREMAN-CONTRACT-REFUSED"


@dataclass(frozen=True)
class WorkerPrompt:
    kind: str
    ref: str
    sha256: str

    def to_record(self) -> dict[str, str]:
        return {"kind": self.kind, "ref": self.ref, "sha256": self.sha256}


@dataclass(frozen=True)
class WorkerSpawnPlan:
    worker_id: str
    role: str
    lane_kind: str
    harness: str
    scope_id: str
    parent_id: str | None
    worktree_path: Path
    prompt: WorkerPrompt
    depth: int
    max_depth: int
    record_path: Path
    launch_command: tuple[str, ...]
    child_env: dict[str, str]
    scrubbed_env_names: tuple[str, ...]
    dry_run: bool
    managed_config_receipt: codex_worker_config.WorkerConfigReceipt | None = None

    def to_record(self) -> dict[str, Any]:
        command = list(self.launch_command)
        record = {
            "kind": "ce-worker-spawn-record",
            "schema_version": "1",
            "worker_id": self.worker_id,
            "role": self.role,
            "lane_kind": self.lane_kind,
            "harness": self.harness,
            "scope_id": self.scope_id,
            "parent_id": self.parent_id,
            "worktree_path": str(self.worktree_path),
            "prompt": self.prompt.to_record(),
            "depth": self.depth,
            "max_depth": self.max_depth,
            "record_path": str(self.record_path),
            "launch_command": command,
            "launch_command_sha256": _hash_text("\0".join(command)),
            "scrubbed_env_names": list(self.scrubbed_env_names),
            "child_env_names": sorted(self.child_env),
            "dry_run": self.dry_run,
            "launch_state": "dry_run" if self.dry_run else "planned",
            "seat_refs": {},
        }
        contract = governed_worker_contract(role=self.role, max_depth=self.max_depth)
        if contract is not None:
            record["governed_worker_contract"] = contract
        return record


@dataclass(frozen=True)
class WorkerLaunchOutcome:
    spawned: bool
    attached: bool
    plan: dict[str, Any] | None = None
    terminal: dict[str, Any] | None = None
    events_ref: str | None = None
    seat_record_ref: str | None = None
    seat_lifecycle_state: str | None = None


@dataclass(frozen=True)
class WorkerSpawnResult:
    plan: WorkerSpawnPlan
    record: dict[str, Any]
    record_path: Path
    written: bool
    launch_outcome: WorkerLaunchOutcome | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record,
            "record_path": str(self.record_path),
            "written": self.written,
            "launch_outcome": self.launch_outcome.__dict__ if self.launch_outcome else None,
        }


class LaunchRuntimeWorkerLauncher:
    """Default live seam: call v1 ``launch_runtime.launch`` with scrubbed env."""

    def launch(self, plan: WorkerSpawnPlan) -> WorkerLaunchOutcome:
        try:
            policy_role = WORKER_POLICY_ROLES[plan.role]
        except KeyError as exc:  # defensive: plan construction validates this mapping too
            raise WorkerLaunchFailed(
                f"worker role {plan.role!r} has no model-tier policy mapping"
            ) from exc
        launch_worktree = plan.worktree_path
        if plan.managed_config_receipt is not None:
            try:
                launch_worktree = codex_worker_config.pinned_worktree_launch_path(plan.managed_config_receipt)
            except codex_worker_config.WorkerConfigRefused as exc:
                raise WorkerManagedConfigRefused(f"managed Codex worker config refused: {exc}") from exc
        old_environ = dict(os.environ)
        os.environ.clear()
        os.environ.update(plan.child_env)
        try:
            result = launch_runtime.launch(
                harness=plan.harness,
                session=plan.worker_id,
                window=f"worker-{plan.role}",
                invoked_as="worker-spawn",
                dry_run=False,
                repo_root=launch_worktree,
                owner_controller_id=plan.parent_id,
                purpose=f"worker:{plan.role}:{plan.scope_id}",
                launch_cwd=launch_worktree,
                launch_env=plan.child_env,
                role=policy_role,
            )
        finally:
            os.environ.clear()
            os.environ.update(old_environ)
        return WorkerLaunchOutcome(
            spawned=result.spawned,
            attached=result.attached,
            plan=result.plan.to_dict(),
            terminal=result.terminal,
            events_ref=result.events_ref,
            seat_record_ref=result.seat_record_ref,
            seat_lifecycle_state=result.seat_lifecycle_state,
        )


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_text(text: str) -> str:
    return _hash_bytes(text.encode("utf-8"))


def governed_worker_contract(*, role: str, max_depth: int = DEFAULT_MAX_DEPTH) -> dict[str, Any] | None:
    """Return the ce-ops#244 machine-readable contract for governed worker roles."""
    normalized_role = role.strip().lower()
    if normalized_role not in GOVERNED_WORKER_ROLES:
        return None
    return {
        "schema_version": "1",
        "contract_ref": WORKER_TIER_CONTRACT_SCHEMA,
        "tier": "worker",
        "execution_model": "in_process_sub_agent",
        "role": normalized_role,
        "role_surface_ref": WORKER_TIER_ROLE_SURFACE_REFS[normalized_role],
        "foreman_dispatch_ref": WORKER_TIER_FOREMAN_DISPATCH_REF,
        "inherited_governance": {
            "ring": "ring_1",
            "refusal": "inherited",
            "envelope": "inherited",
            "ambient_credentials": "none",
        },
        "declared_capabilities": list(WORKER_TIER_DECLARED_CAPABILITIES[normalized_role]),
        "prohibited_capabilities": list(WORKER_TIER_PROHIBITED_CAPABILITIES),
        "bounds": {
            "max_depth": int(max_depth),
            "may_push": False,
            "may_self_approve": False,
            "may_create_issues": False,
            "may_task_other_seats": False,
            "may_receive_ambient_credentials": False,
        },
        "result_protocol": {
            "returns": "structured_result_to_foreman",
        },
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return slug or "worker"


def _default_parent_id(environ: Mapping[str, str]) -> str | None:
    for name in ("CE_WORKER_ID", "CE_FOREMAN_ID", "CE_CONTROLLER_ID"):
        value = environ.get(name)
        if value:
            return value
    return None


def _default_depth(environ: Mapping[str, str], explicit: int | None) -> int:
    if explicit is not None:
        return explicit
    raw = environ.get("CE_WORKER_DEPTH")
    if raw is None:
        return 1
    try:
        return int(raw) + 1
    except ValueError as exc:
        raise InvalidWorkerDepth("CE_WORKER_DEPTH must be an integer") from exc


def _is_credential_env_name(name: str) -> bool:
    upper = name.upper()
    if upper in _EXACT_CREDENTIAL_ENV:
        return True
    return any(token in upper for token in _SECRET_ENV_TOKENS)


def _is_safe_tmpdir(value: str, *, controller_home: str | None) -> bool:
    try:
        path = Path(value).expanduser()
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    if not path.is_absolute() or not path.is_dir():
        return False
    if controller_home:
        try:
            home = Path(controller_home).expanduser().resolve(strict=False)
        except OSError:
            home = None
        if home is not None and (resolved == home or home in resolved.parents):
            return False
    return True


def _allowed_child_env_name(name: str, value: str, *, controller_home: str | None) -> bool:
    upper = name.upper()
    if _is_credential_env_name(upper):
        return False
    if upper in _SAFE_BASE_ENV_NAMES:
        return True
    if upper.startswith("LC_"):
        return True
    if upper == "TMPDIR":
        return _is_safe_tmpdir(value, controller_home=controller_home)
    return upper in _SAFE_CE_METADATA_ENV_NAMES


def scrub_worker_environment(
    environ: Mapping[str, str] | None = None,
    *,
    worker_id: str,
    role: str,
    scope_id: str,
    depth: int,
    parent_id: str | None,
    home_path: Path | str,
) -> tuple[dict[str, str], tuple[str, ...]]:
    source = dict(os.environ if environ is None else environ)
    controller_home = source.get("HOME")
    child = {
        name: value
        for name, value in source.items()
        if _allowed_child_env_name(name, value, controller_home=controller_home)
    }
    scrubbed = sorted(name for name in source if name not in child)
    child.update(
        {
            "CE_WORKER_ID": worker_id,
            "CE_WORKER_ROLE": role,
            "CE_WORKER_SCOPE_ID": scope_id,
            "CE_WORKER_DEPTH": str(depth),
            "HOME": str(home_path),
        }
    )
    if parent_id:
        child["CE_PARENT_WORKER_ID"] = parent_id
    return child, tuple(scrubbed)


def _resolve_prompt(prompt_file: Path | str | None, brief: str | None) -> WorkerPrompt:
    if (prompt_file is None) == (brief is None):
        raise InvalidWorkerPrompt("exactly one of prompt_file or brief is required")
    if prompt_file is not None:
        path = Path(prompt_file)
        if not path.is_file():
            raise InvalidWorkerPrompt(f"prompt file {str(path)!r} does not exist")
        return WorkerPrompt(kind="prompt-file", ref=str(path), sha256=_hash_bytes(path.read_bytes()))
    assert brief is not None
    return WorkerPrompt(kind="brief", ref="inline-brief", sha256=_hash_text(brief))


def _resolve_worktree(worktree: Path | str, parent_worktree: Path | str | None) -> Path:
    supplied_path = os.fspath(worktree)
    if (
        not os.path.isabs(supplied_path)
        or supplied_path.startswith("//")
        or supplied_path != os.path.normpath(supplied_path)
    ):
        raise InvalidWorkerWorktree("worker worktree must be an absolute, lexically canonical path")
    path = Path(supplied_path)
    try:
        component_path = Path(path.anchor)
        details = os.lstat(component_path)
        for component in path.parts[1:]:
            component_path /= component
            details = os.lstat(component_path)
            if stat.S_ISLNK(details.st_mode):
                raise InvalidWorkerWorktree("worker worktree must not contain symlink components")
    except OSError as exc:
        raise InvalidWorkerWorktree(f"cannot inspect worker worktree {str(path)!r}: {exc}") from exc
    if not stat.S_ISDIR(details.st_mode):
        raise InvalidWorkerWorktree(f"worker worktree {str(path)!r} must be an existing directory")
    if parent_worktree is not None:
        parent = Path(parent_worktree).expanduser().resolve(strict=False)
        if path == parent:
            raise InvalidWorkerWorktree("worker worktree must be distinct from the spawning seat worktree")
    return path


def _worker_id(
    *,
    role: str,
    harness: str,
    scope_id: str,
    worktree: Path,
    prompt: WorkerPrompt,
    depth: int,
    supplied: str | None,
) -> str:
    if supplied:
        return _slug(supplied)
    digest = _hash_text("\0".join([role, harness, scope_id, str(worktree), prompt.sha256, str(depth)]))
    return f"worker-{role}-{digest[:12]}"


def plan_worker_spawn(
    *,
    role: str,
    harness: str,
    worktree: Path | str,
    scope_id: str,
    prompt_file: Path | str | None = None,
    brief: str | None = None,
    dry_run: bool = False,
    depth: int | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    parent_id: str | None = None,
    worker_id: str | None = None,
    parent_worktree: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> WorkerSpawnPlan:
    env = dict(os.environ if environ is None else environ)
    try:
        brain_bootstrap.require_foreman_dispatch_contract()
    except brain_bootstrap.BrainBootstrapRefused as exc:
        detail = "; ".join(exc.errors) if exc.errors else str(exc)
        raise WorkerForemanContractRefused(
            f"worker spawn requires a launch-pinned foreman dispatch contract: {detail}"
        ) from exc
    normalized_role = role.strip().lower()
    if normalized_role not in WORKER_ROLES:
        raise InvalidWorkerRole(
            f"role {role!r} is not supported; expected one of: {', '.join(sorted(WORKER_ROLES))}"
        )
    if normalized_role not in WORKER_POLICY_ROLES:
        raise InvalidWorkerRole(
            f"role {normalized_role!r} has no model-tier policy mapping; refusing implicit tier"
        )
    lane_kind = WORKER_ROLES[normalized_role]
    if lane_kind not in lane_runtime.LANE_KINDS:
        raise InvalidWorkerRole(f"role {normalized_role!r} maps to unknown lane_kind {lane_kind!r}")
    normalized_harness = harness.strip().lower()
    if normalized_harness not in launch_runtime.SUPPORTED_HARNESSES:
        raise InvalidWorkerHarness(
            f"harness {harness!r} is not supported; expected one of: "
            f"{', '.join(sorted(launch_runtime.SUPPORTED_HARNESSES))}"
        )
    if max_depth < 1:
        raise InvalidWorkerDepth("max_depth must be >= 1")
    resolved_depth = _default_depth(env, depth)
    if resolved_depth < 1 or resolved_depth > max_depth:
        raise InvalidWorkerDepth(f"worker depth {resolved_depth} exceeds allowed range 1..{max_depth}")
    if not str(scope_id).strip():
        raise InvalidWorkerPrompt("scope_id is required")

    prompt = _resolve_prompt(prompt_file, brief)
    resolved_worktree = _resolve_worktree(worktree, parent_worktree)
    resolved_parent_id = parent_id or _default_parent_id(env)
    resolved_worker_id = _worker_id(
        role=normalized_role,
        harness=normalized_harness,
        scope_id=scope_id,
        worktree=resolved_worktree,
        prompt=prompt,
        depth=resolved_depth,
        supplied=worker_id,
    )
    record_path = resolved_worktree / WORKER_RECORD_REL / resolved_worker_id / "worker.yaml"
    home_path = record_path.parent / "home"
    child_env, scrubbed = scrub_worker_environment(
        env,
        worker_id=resolved_worker_id,
        role=normalized_role,
        scope_id=scope_id,
        depth=resolved_depth,
        parent_id=resolved_parent_id,
        home_path=home_path,
    )
    launch_command = (
        "ce",
        "launch",
        "--harness",
        normalized_harness,
        "--session",
        resolved_worker_id,
        "--window",
        f"worker-{normalized_role}",
        "--repo-root",
        str(resolved_worktree),
        "--purpose",
        f"worker:{normalized_role}:{scope_id}",
    )
    if resolved_parent_id:
        launch_command = (*launch_command, "--controller-id", resolved_parent_id)
    return WorkerSpawnPlan(
        worker_id=resolved_worker_id,
        role=normalized_role,
        lane_kind=lane_kind,
        harness=normalized_harness,
        scope_id=str(scope_id),
        parent_id=resolved_parent_id,
        worktree_path=resolved_worktree,
        prompt=prompt,
        depth=resolved_depth,
        max_depth=max_depth,
        record_path=record_path,
        launch_command=launch_command,
        child_env=child_env,
        scrubbed_env_names=scrubbed,
        dry_run=dry_run,
    )


def _atomic_write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _reserve_worker_record(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as fh:
            fh.write(yaml.safe_dump(payload, sort_keys=True))
    except FileExistsError as exc:
        raise WorkerRecordCollision(f"worker record already exists at {path}") from exc
    except OSError as exc:
        raise WorkerRecordReservationFailed(f"could not reserve worker record at {path}: {exc}") from exc


def _prepare_worker_home(plan: WorkerSpawnPlan) -> None:
    home = Path(plan.child_env["HOME"])
    try:
        home.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkerRecordReservationFailed(f"could not create isolated worker HOME {home}: {exc}") from exc


def _materialize_codex_worker_config(plan: WorkerSpawnPlan) -> codex_worker_config.WorkerConfigReceipt | None:
    """Install the attested CDX-D-6 config before the injectable prompt seam."""
    if plan.harness != "codex":
        return None
    home = Path(plan.child_env["HOME"])
    try:
        home_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            attestation = codex_worker_config.attest_allocated_worktree(plan.worktree_path)
            template = codex_worker_config.render_worker_config(plan.worktree_path, attestation)
            return codex_worker_config.materialize_worker_config(home_fd, template, attestation)
        finally:
            os.close(home_fd)
    except (OSError, codex_worker_config.WorkerConfigRefused) as exc:
        raise WorkerManagedConfigRefused(f"managed Codex worker config refused: {exc}") from exc


def _revalidate_codex_worker_config(plan: WorkerSpawnPlan) -> None:
    """Refuse any changed, stale, or missing managed config at the launch seam."""
    if plan.harness != "codex":
        return
    try:
        receipt = plan.managed_config_receipt
        if receipt is None:
            raise codex_worker_config.WorkerConfigRefused("missing managed config receipt")
        codex_worker_config.revalidate_worker_config_receipt(receipt)
    except codex_worker_config.WorkerConfigRefused as exc:
        raise WorkerManagedConfigRefused(f"managed Codex worker config refused: {exc}") from exc


def spawn_worker(
    *,
    role: str,
    harness: str,
    worktree: Path | str,
    scope_id: str,
    prompt_file: Path | str | None = None,
    brief: str | None = None,
    dry_run: bool = False,
    depth: int | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    parent_id: str | None = None,
    worker_id: str | None = None,
    parent_worktree: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
    launcher: Any | None = None,
) -> WorkerSpawnResult:
    plan = plan_worker_spawn(
        role=role,
        harness=harness,
        worktree=worktree,
        scope_id=scope_id,
        prompt_file=prompt_file,
        brief=brief,
        dry_run=dry_run,
        depth=depth,
        max_depth=max_depth,
        parent_id=parent_id,
        worker_id=worker_id,
        parent_worktree=parent_worktree,
        environ=environ,
    )
    record = plan.to_record()
    if dry_run:
        return WorkerSpawnResult(plan=plan, record=record, record_path=plan.record_path, written=False)
    record["launch_state"] = "reserved"
    _prepare_worker_home(plan)
    _reserve_worker_record(plan.record_path, record)
    plan = replace(plan, managed_config_receipt=_materialize_codex_worker_config(plan))
    live_launcher = launcher or LaunchRuntimeWorkerLauncher()
    try:
        _revalidate_codex_worker_config(plan)
        outcome = live_launcher.launch(plan)
    except launch_runtime.LaunchError as exc:
        raise WorkerLaunchFailed(f"launch_runtime refused worker spawn [{exc.code}]: {exc}") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorkerLaunchFailed(f"worker launcher failed before record write: {exc}") from exc
    finally:
        codex_worker_config.release_worker_config_receipt(plan.managed_config_receipt)
    record["seat_refs"] = {
        "events_ref": outcome.events_ref,
        "seat_record_ref": outcome.seat_record_ref,
        "seat_lifecycle_state": outcome.seat_lifecycle_state,
        "terminal": outcome.terminal,
    }
    record["launch_state"] = "launched"
    _atomic_write_yaml(plan.record_path, record)
    return WorkerSpawnResult(
        plan=plan,
        record=record,
        record_path=plan.record_path,
        written=True,
        launch_outcome=outcome,
    )
