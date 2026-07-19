"""RV1-063 — ``ce launch`` / ``ce hud`` deterministic Controller-seat launcher.

DP-2 = B: v1.0 ships a deterministic launcher that opens/attaches a **visible**
tmux Controller seat running the chosen harness (Claude Code / Codex / Hermes).
``ce hud`` is an **alias / seam label** for this same launcher — it is *not* a
CE-native HUD/TUI commitment.

Fail-closed properties:

* There is **no hidden fallback**. A request for a non-visible / detached
  continuation is refused (``HiddenContinuationRefused``); on harness
  exit/crash/auth-loss the launcher must not silently continue in a headless
  pane.
* ``--resume`` attaches to an *existing* launcher session; resuming a missing /
  dead session is refused (``ResumeTargetMissing``) rather than spawning hidden.
* ``--dry-run`` produces a deterministic plan with **no** side effect and **no**
  provider login — used to prove the launch/hud alias offline.

This module does NOT replace ``ce lane launch`` (the governed per-lane
primitive), which remains intact. tmux is reached only through an injected
adapter; no secrets or environment values are printed.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import socket
import sqlite3
import urllib.error
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import (
    _versions,
    brain_bootstrap,
    brain_embedding_openai_endpoint,
    brain_recall_surface,
    claude_launch_spec,
    codex_controller_evidence,
    codex_launch_spec,
    hermes_launch_spec,
    resource_bound_spec,
    runtime_backend_bridge,
    seat_lifecycle,
    seat_sentinel,
)
from .checks import ce_runtime_policy
from .loader import LoaderError, load_yaml
from .tmux_adapter import TmuxUnavailable, is_proc_self_fd_path
from .visibility_backend import TmuxVisibilityBackend, VisibilityBackendError

DEFAULT_HARNESS = "claude"
DEFAULT_SESSION = "ce-controller"
DEFAULT_WINDOW = "controller"
SUPPORTED_HARNESSES = frozenset({"claude", "codex", "hermes", "openclaw"})
VISIBILITY = "operator_visible"
LOGGER = logging.getLogger(__name__)
RECALL_EMBEDDER_ENV = "CE_BRAIN_RECALL_EMBEDDER"
RECALL_ENDPOINT_ENV = "CE_BRAIN_RECALL_ENDPOINT"
RECALL_ENDPOINT_MODEL_ID_ENV = "CE_BRAIN_RECALL_ENDPOINT_MODEL_ID"
RECALL_ENDPOINT_DIM_ENV = "CE_BRAIN_RECALL_ENDPOINT_DIM"
_RECALL_ENDPOINT_EMBEDDERS = {"vllm-openai", "openai-endpoint", "openai"}
LAUNCH_RECALL_ENDPOINT_TIMEOUT_SECONDS = 5
DEFAULT_RUNTIME_POLICY_RELATIVE = (
    Path(_versions.V3_LOCAL_STATE_ROOT) / "onboard" / "runtime" / "runtime-policy.yaml"
)
HOST_BACKEND_OPT_OUT = "host"
CONTROLLER_ROLE = "controller"
TAKEOVER_EVIDENCE_KIND = "ce-takeover-evidence-packet"
TAKEOVER_INITIAL_STATE = "AWAITING-OPERATOR"
TAKEOVER_EVIDENCE_MAX_AGE_SECONDS = 15 * 60
TAKEOVER_EVIDENCE_CLOCK_SKEW_SECONDS = 60
READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED = (
    "READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED"
)


class LaunchError(Exception):
    code = "G6-LAUNCH-ERROR"


class HiddenContinuationRefused(LaunchError):
    code = "G6-LAUNCH-HIDDEN-REFUSED"


class TmuxUnavailableError(LaunchError):
    code = "G6-LAUNCH-TMUX-UNAVAILABLE"


class TmuxPanePinningRefused(LaunchError):
    code = "G6-LAUNCH-TMUX-PANE-PINNING-REFUSED"


class ResumeTargetMissing(LaunchError):
    code = "G6-LAUNCH-RESUME-MISSING"


class UnsupportedHarness(LaunchError):
    code = "G6-LAUNCH-UNSUPPORTED-HARNESS"


class LaunchRefused(LaunchError):
    """CC-G-D Ring 0: a governed Claude launch surface is refused before side effects."""

    code = "G6-LAUNCH-CLAUDE-REFUSED"


class CodexLaunchRefused(LaunchRefused):
    """CDX-D Ring 0: a governed Codex launch surface is refused before side effects."""

    code = "G6-LAUNCH-CODEX-REFUSED"


class HermesLaunchRefused(LaunchRefused):
    """CE Ring 0: a governed Hermes launch surface is refused before side effects.

    Subclasses ``LaunchRefused`` (so existing ``except LaunchRefused`` handlers still
    catch it) but carries a Hermes-specific code instead of the Claude one."""

    code = "G6-LAUNCH-HERMES-REFUSED"


class ResourceBoundRefused(LaunchError):
    """v3.5-F: a resource-bounded launch is refused — malformed/unratified resource
    policy, an unsupported host under ``enforce``, a unit-name collision, or a
    failed launch-confirm (fleet cap / ``memory.oom.group``). Fail-closed."""

    code = "G6-LAUNCH-RESOURCE-REFUSED"


class RuntimePolicyRefused(LaunchError):
    """Runtime backend/policy resolution refused before launch side effects."""

    code = "G6-LAUNCH-RUNTIME-POLICY-REFUSED"


class ContainedLaunchPreflightRefused(LaunchError):
    """Raised when contained-launch plan validation fails before spawn.

    This fires before any docker/runtime side effect. Its error code is distinct
    from the post-spawn runtime policy refusal so operators get the actionable
    plan-time cause instead of a launch-probe timeout.
    """

    code = "G6-LAUNCH-POLICY-INVALID"


class ContainedLaunchPlanUnverifiable(ContainedLaunchPreflightRefused):
    """A subset of ``ContainedLaunchPreflightRefused``: host-environment-dependent
    plan facts (does a bind source exist on THIS host; is the sentinel wrapper
    under a surviving mount) could not be verified.

    Unlike the placeholder-digest case (a policy-content defect, refused
    unconditionally), these two checks read the real filesystem of whatever
    host happens to be running ``ce launch`` and cannot be evaluated against a
    runtime-policy-record's ``mount_manifest`` without assuming it encodes real,
    resolvable host paths — the v3 runner backends (``gvisor-proxy``/``docker``)
    deliberately keep their plan-translation step pure/I-O-free (see
    ``runner/gvisor_proxy_backend.py``'s "translate-vs-execute split"), so
    launch-time callers may legitimately supply symbolic or not-yet-materialized
    mount sources. ``launch()`` therefore treats this subclass as a *warning*
    (logged, non-fatal) rather than a hard refusal, while direct callers of
    ``_validate_contained_launch_plan`` (this module's own fast unit tests) keep
    exercising it as the strict, fail-closed check it is.
    """


class GovernedControllerLaunchRefused(LaunchError):
    """Raw controller-role launch refused until takeover evidence is supplied."""

    code = READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED

    def __init__(self, evidence: Mapping[str, Any]):
        self.evidence = dict(evidence)
        super().__init__(
            "raw role=controller launch is read-only until governed takeover "
            "evidence is confirmed; recovery command: "
            f"{self.evidence['recovery_command']}"
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(self.evidence)


class _TakeoverEvidenceValidationError(ValueError):
    def __init__(self, evidence_status: str, detail: str):
        self.evidence_status = evidence_status
        super().__init__(detail)


class SeatSurfaceReuseRefused(LaunchError):
    """A target seat events surface already has a launched event; refuse reuse."""

    code = "G6-LAUNCH-SEAT-SURFACE-REUSE"


class BrainBootstrapLaunchRefused(LaunchError):
    """ce-ops#178: Knowledge-SSOT bootstrap refused before controller spawn."""

    code = "G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED"


class SeatLifecycleRegistrationFailed(LaunchError):
    """ce-ops#95: post-spawn lifecycle registration failed.

    Phase 1 compatibility posture warns + escalates while allowing success.
    When ``seat_lifecycle.SEAT_LIFECYCLE_FAIL_CLOSED`` flips to true this error
    becomes the fail-closed launch result.
    """

    code = "G6-LAUNCH-SEAT-LIFECYCLE-FAILED"


def _confirm_pack(repo_root: Path | str | None) -> bool:
    """Seam: confirm the committed hook-pack is loaded (monkeypatchable in tests).

    Delegates to :func:`hook_pack_confirm.confirm_hook_pack`. Never launches
    Claude and never makes a network call.
    """
    from . import hook_pack_confirm

    return hook_pack_confirm.confirm_hook_pack(Path(repo_root or ".")).confirmed


def _confirm_codex_managed_pack(repo_root: Path | str | None) -> bool:
    """Seam: confirm the committed Codex managed PreToolUse hook-pack.

    Delegates to :func:`hook_pack_confirm.confirm_codex_managed_hook_pack`.
    Never launches Codex and never makes a network call.
    """
    from . import hook_pack_confirm

    return hook_pack_confirm.confirm_codex_managed_hook_pack(Path(repo_root or ".")).confirmed


def _default_mcp_config_path(session: str) -> str:
    """CE-owned, repo-relative MCP config path for a Controller-seat launch."""
    return f"{_versions.V3_LOCAL_STATE_ROOT}/launch/{session}/mcp/ce-mcp.json"


def _default_runtime_policy_path(repo_root: Path | str | None) -> Path:
    return Path(repo_root or ".") / DEFAULT_RUNTIME_POLICY_RELATIVE


def _missing_default_runtime_policy_message(path: Path) -> str:
    return (
        f"bare ce launch requires the onboarded runtime policy record at {str(path)!r}; "
        "re-run `ce onboard --apply` for this tenant so it emits "
        f"{DEFAULT_RUNTIME_POLICY_RELATIVE.as_posix()}, or explicitly opt out of "
        "contained launch with `ce launch --backend host`"
    )


def _quote_command(tokens: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(token)) for token in tokens)


_OPTIONAL_AGENT_DOTFILE_SUFFIXES: tuple[str, ...] = (
    "/.claude",
    "/.config/claude",
    "/.codex",
    "/.config/codex",
)
_ZERO_IMAGE_DIGEST = "sha256:" + "0" * 64


def _validate_contained_launch_plan(
    policy_record: dict[str, Any],
    sentinel_wrapper_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Pre-spawn policy validation for runtime-policy-backed launch.

    Returns an updated policy record plus warning strings. The updated policy
    omits absent optional agent dotfile mounts so the runtime backend receives a
    manifest that Docker can create.
    """
    image_ref = policy_record.get("image_ref") or {}
    if isinstance(image_ref, Mapping) and image_ref.get("sha") == _ZERO_IMAGE_DIGEST:
        raise ContainedLaunchPreflightRefused(
            "image digest is a placeholder (sha256:000...000); re-run ce onboard "
            "after runtime_posture resolves"
        )

    warnings: list[str] = []
    surviving_mounts: list[Any] = []
    mount_manifest = policy_record.get("mount_manifest") or []
    for entry in mount_manifest:
        if not isinstance(entry, dict):
            surviving_mounts.append(entry)
            continue
        source_path = str(entry.get("path") or "")
        if source_path and not Path(source_path).exists():
            if any(
                source_path.endswith(suffix)
                for suffix in _OPTIONAL_AGENT_DOTFILE_SUFFIXES
            ):
                warnings.append(
                    f"optional agent-config dir absent; skipping mount: {source_path}"
                )
                continue
            raise ContainedLaunchPlanUnverifiable(
                f"bind source path does not exist: {source_path}"
            )
        surviving_mounts.append(entry)

    wrapper = Path(sentinel_wrapper_path)
    mounted_sources = [
        Path(entry["path"])
        for entry in surviving_mounts
        if isinstance(entry, dict) and entry.get("path")
    ]
    if not any(wrapper == source or wrapper.is_relative_to(source) for source in mounted_sources):
        raise ContainedLaunchPlanUnverifiable(
            f"container command path {str(wrapper)!r} is not under any mounted source"
        )

    updated_policy = dict(policy_record)
    updated_policy["mount_manifest"] = surviving_mounts
    return updated_policy, warnings


def takeover_evidence_host_id() -> str:
    return seat_lifecycle.default_host_id()


def takeover_evidence_generated_at(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _controller_recovery_command(
    *,
    harness: str,
    repo_root: Path | str | None,
    predecessor: str | None,
) -> str:
    root = str(Path(repo_root or "."))
    if harness in {"claude", "codex"}:
        return _quote_command(
            [
                "ce",
                "takeover",
                "--from",
                predecessor or DEFAULT_SESSION,
                "--harness",
                harness,
                "--repo-root",
                root,
                "--dry-run",
                "--json",
            ]
        )
    return _quote_command(
        ["ce", "launch", "--harness", harness, "--repo-root", root]
    )


def raw_controller_launch_refusal_evidence(
    *,
    harness: str,
    repo_root: Path | str | None,
    predecessor: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "ce-controller-launch-refusal",
        "schema_version": 1,
        "code": READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED,
        "role": CONTROLLER_ROLE,
        "read_only": True,
        "required_evidence": TAKEOVER_EVIDENCE_KIND,
        "recovery_command": _controller_recovery_command(
            harness=harness,
            repo_root=repo_root,
            predecessor=predecessor,
        ),
    }


def _load_takeover_evidence(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(payload, Mapping):
        raise ValueError("takeover evidence must be a JSON object")
    return payload


def _takeover_refusal(
    *,
    harness: str,
    repo_root: Path | str | None,
    session: str,
    evidence_path: Path,
    evidence_status: str,
    detail: str,
) -> GovernedControllerLaunchRefused:
    refusal = raw_controller_launch_refusal_evidence(
        harness=harness,
        repo_root=repo_root,
        predecessor=session,
    )
    refusal.update(
        {
            "evidence_ref": str(evidence_path),
            "evidence_status": evidence_status,
            "detail": detail,
        }
    )
    return GovernedControllerLaunchRefused(refusal)


def _parse_takeover_generated_at(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise _TakeoverEvidenceValidationError(
            "invalid",
            "takeover evidence generated_at must be an RFC3339 UTC timestamp",
        )
    raw = value.strip()
    parseable = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        generated_at = datetime.fromisoformat(parseable)
    except ValueError as exc:
        raise _TakeoverEvidenceValidationError(
            "invalid",
            "takeover evidence generated_at must be an RFC3339 UTC timestamp",
        ) from exc
    if generated_at.tzinfo is None:
        raise _TakeoverEvidenceValidationError(
            "invalid",
            "takeover evidence generated_at must include a timezone",
        )
    return generated_at.astimezone(timezone.utc)


def _validate_takeover_evidence_payload(
    payload: Mapping[str, Any],
    *,
    harness: str,
    now: datetime | None = None,
) -> None:
    if (
        payload.get("kind") != TAKEOVER_EVIDENCE_KIND
        or payload.get("initial_state") != TAKEOVER_INITIAL_STATE
        or payload.get("selected_harness") != harness
    ):
        raise _TakeoverEvidenceValidationError(
            "mismatch",
            (
                "takeover evidence must be a ce-takeover-evidence-packet "
                f"for harness {harness!r} in {TAKEOVER_INITIAL_STATE}"
            ),
        )

    generated_at = _parse_takeover_generated_at(payload.get("generated_at"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    age_seconds = (current - generated_at).total_seconds()
    if age_seconds < -TAKEOVER_EVIDENCE_CLOCK_SKEW_SECONDS:
        raise _TakeoverEvidenceValidationError(
            "invalid",
            "takeover evidence generated_at is too far in the future",
        )
    if age_seconds > TAKEOVER_EVIDENCE_MAX_AGE_SECONDS:
        raise _TakeoverEvidenceValidationError(
            "stale",
            (
                "takeover evidence is stale: generated_at is older than "
                f"{TAKEOVER_EVIDENCE_MAX_AGE_SECONDS} seconds"
            ),
        )

    host_id = payload.get("host_id")
    expected_host_id = takeover_evidence_host_id()
    if not isinstance(host_id, str) or not host_id.strip():
        raise _TakeoverEvidenceValidationError(
            "invalid",
            "takeover evidence host_id is required",
        )
    if host_id != expected_host_id:
        raise _TakeoverEvidenceValidationError(
            "wrong-host",
            (
                f"takeover evidence host_id {host_id!r} does not match "
                f"current host {expected_host_id!r}"
            ),
        )


def _validate_governed_controller_launch(
    *,
    role: str | None,
    harness: str,
    repo_root: Path | str | None,
    session: str,
    takeover_evidence: Path | str | None,
) -> None:
    if role != CONTROLLER_ROLE:
        return
    if takeover_evidence is None:
        raise GovernedControllerLaunchRefused(
            raw_controller_launch_refusal_evidence(
                harness=harness,
                repo_root=repo_root,
                predecessor=session,
            )
        )
    evidence_path = Path(takeover_evidence)
    try:
        payload = _load_takeover_evidence(evidence_path)
    except ValueError as exc:
        raise _takeover_refusal(
            harness=harness,
            repo_root=repo_root,
            session=session,
            evidence_path=evidence_path,
            evidence_status="invalid",
            detail=str(exc),
        ) from exc
    try:
        _validate_takeover_evidence_payload(payload, harness=harness)
    except _TakeoverEvidenceValidationError as exc:
        raise _takeover_refusal(
            harness=harness,
            repo_root=repo_root,
            session=session,
            evidence_path=evidence_path,
            evidence_status=exc.evidence_status,
            detail=str(exc),
        ) from exc


def _corrupt_default_runtime_policy_message(path: Path) -> str:
    return (
        f"the onboarded runtime policy record at {str(path)!r} is present but is not a "
        f"clean {ce_runtime_policy.KIND_VALUE!r} record (missing/mismatched 'kind'); "
        "re-run `ce onboard --apply` to re-emit it, or repair/replace the file, or "
        "explicitly opt out of contained launch with `ce launch --backend host`"
    )


@dataclass(frozen=True)
class LaunchPlan:
    mode: str  # "launch" | "resume"
    invoked_as: str  # "launch" | "hud"
    alias_of: str  # always "launch" — hud is an alias label
    harness: str
    session: str
    window: str
    command: list[str]
    visibility: str
    dry_run: bool
    resume: bool
    # v3.5-F: the resource-bounding evidence stamp. A dict (the applied
    # ResourceBound + optional fleet cap) when the seat launches bounded;
    # the literal string "none (advisory)" / "none (off)" on an explicit
    # ratified opt-down; None when the policy declares no resource governance.
    resource_bound: dict | str | None = None
    runtime_policy: dict | None = None
    codex_bypass_mode: str | None = None
    codex_controller_authority: str | None = None
    codex_promotion_packet_ref: str | None = None
    codex_promotion_packet_status: dict[str, Any] | None = None
    codex_argv_after_rewrite: list[str] | None = None
    codex_cdxd_result: dict[str, Any] | None = None
    codex_managed_hook_confirmed: bool | None = None
    brain_bootstrap_ref: str | None = None
    brain_bootstrap_sha256: str | None = None
    brain_recall_status: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "invoked_as": self.invoked_as,
            "alias_of": self.alias_of,
            "harness": self.harness,
            "session": self.session,
            "window": self.window,
            "command": list(self.command),
            "visibility": self.visibility,
            "dry_run": self.dry_run,
            "resume": self.resume,
            "resource_bound": self.resource_bound,
            "runtime_policy": self.runtime_policy,
            "codex_bypass_mode": self.codex_bypass_mode,
            "codex_controller_authority": self.codex_controller_authority,
            "codex_promotion_packet_ref": self.codex_promotion_packet_ref,
            "codex_promotion_packet_status": self.codex_promotion_packet_status,
            "codex_argv_after_rewrite": self.codex_argv_after_rewrite,
            "codex_cdxd_result": self.codex_cdxd_result,
            "codex_managed_hook_confirmed": self.codex_managed_hook_confirmed,
            "brain_bootstrap_ref": self.brain_bootstrap_ref,
            "brain_bootstrap_sha256": self.brain_bootstrap_sha256,
            "brain_recall_status": self.brain_recall_status,
        }


@dataclass(frozen=True)
class LaunchResult:
    plan: LaunchPlan
    spawned: bool = False
    attached: bool = False
    terminal: dict | None = None
    # v3.5-F: live launch-confirm facts (memory.oom.group write + fleet cap),
    # None for dry-run / unbounded launches.
    resource_confirm: dict | None = None
    # ce-ops#26: the absolute path to this seat's append-only lifecycle events
    # surface; None on dry-run (no side effect). The v3 bridge stamps it onto the
    # dispatch record so the cockpit/Monitor join events ↔ run by run_id.
    events_ref: str | None = None
    # ce-ops#95: registry record for the CE-substrate lifecycle object. None for
    # dry-run or for Phase-1 compatibility launches whose post-spawn registration
    # failed and proceeded ungoverned with an AWAITING-OPERATOR escalation.
    seat_record_ref: str | None = None
    seat_lifecycle_state: str | None = None
    runner_runtime: dict | None = None
    stale_surface_archive: dict | None = None

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict(),
            "spawned": self.spawned,
            "attached": self.attached,
            "terminal": self.terminal,
            "resource_confirm": self.resource_confirm,
            "events_ref": self.events_ref,
            "seat_record_ref": self.seat_record_ref,
            "seat_lifecycle_state": self.seat_lifecycle_state,
            "runner_runtime": self.runner_runtime,
            "stale_surface_archive": self.stale_surface_archive,
        }


@dataclass(frozen=True)
class LaunchPreflightGate:
    name: str
    status: str
    detail: str | None = None
    code: str | None = None
    critical: bool = False  # gate cannot be fully evaluated without a live launch

    def format_line(self) -> str:
        if self.status == "PASS":
            return f"{self.name}: PASS" if not self.detail else f"{self.name}: PASS {self.detail}"
        if self.status == "WOULD-REFUSE":
            code = f" [{self.code}]" if self.code else ""
            return f"{self.name}: WOULD-REFUSE{code}: {self.detail or ''}"
        if self.status == "SKIPPED":
            return f"{self.name}: SKIPPED: {self.detail or 'requires live launch'}"
        return f"{self.name}: {self.status}: {self.detail or ''}"

    def to_dict(self) -> dict[str, Any]:
        payload = {"name": self.name, "status": self.status}
        if self.detail is not None:
            payload["detail"] = self.detail
        if self.code is not None:
            payload["code"] = self.code
        if self.critical:
            payload["critical"] = True
        return payload


# Exit code returned by preflight when all evaluable gates PASS but one or
# more CRITICAL gates were SKIPPED because they require a live launch to
# evaluate (e.g. containment provisioning). Exit 0 means no critical skips;
# exit 3 means a distinct "passed-but-critical-gates-skipped" signal.
PREFLIGHT_EXIT_CRITICAL_SKIP = 3


@dataclass(frozen=True)
class LaunchPreflightReport:
    gates: tuple[LaunchPreflightGate, ...]

    @property
    def ok(self) -> bool:
        return all(gate.status != "WOULD-REFUSE" for gate in self.gates)

    @property
    def has_critical_skips(self) -> bool:
        return any(
            gate.critical and gate.status == "SKIPPED" for gate in self.gates
        )

    @property
    def exit_code(self) -> int:
        if not self.ok:
            return 1
        if self.has_critical_skips:
            return PREFLIGHT_EXIT_CRITICAL_SKIP
        return 0

    def format_lines(self) -> list[str]:
        lines = [gate.format_line() for gate in self.gates]
        critical_skipped = [
            gate for gate in self.gates if gate.critical and gate.status == "SKIPPED"
        ]
        if critical_skipped:
            names = ", ".join(g.name for g in critical_skipped)
            lines.append(
                f"{len(critical_skipped)} gate(s) require live launch to evaluate "
                f"({names}) — preflight PASS does not verify these gates"
            )
        return lines

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "has_critical_skips": self.has_critical_skips,
            "exit_code": self.exit_code,
            "gates": [gate.to_dict() for gate in self.gates],
        }


@dataclass(frozen=True)
class _HarnessGateResult:
    plan: LaunchPlan
    resolved_mcp: str | None = None


@dataclass(frozen=True)
class _RuntimePolicyGateResult:
    plan: LaunchPlan
    resolved_runtime_policy: Path | str | None
    runtime_policy_record: dict[str, Any] | None
    resource_policy: resource_bound_spec.ResourcePolicy | None
    bounding: bool


@dataclass(frozen=True)
class _SeatSurfaceGateResult:
    seat_dir: Path
    seat_id: str
    seat_run_id: str | None
    stale_surface_archive: SeatSurfaceArchiveResult | None = None
    skipped_reason: str | None = None


def plan_launch(
    *,
    harness: str = DEFAULT_HARNESS,
    session: str = DEFAULT_SESSION,
    window: str = DEFAULT_WINDOW,
    invoked_as: str = "launch",
    resume: bool = False,
    dry_run: bool = False,
    extra_args: Sequence[str] | None = None,
) -> LaunchPlan:
    """Build the deterministic launch plan (pure; no side effects)."""
    if harness not in SUPPORTED_HARNESSES:
        raise UnsupportedHarness(
            f"harness {harness!r} is not a supported Controller-seat harness "
            f"({', '.join(sorted(SUPPORTED_HARNESSES))})"
        )
    command = [harness, *(list(extra_args) if extra_args else [])]
    return LaunchPlan(
        mode="resume" if resume else "launch",
        invoked_as=invoked_as,
        alias_of="launch",
        harness=harness,
        session=session,
        window=window,
        command=command,
        visibility=VISIBILITY,
        dry_run=dry_run,
        resume=resume,
    )


def _resource_stamp(
    bound: "resource_bound_spec.ResourceBound",
    policy: "resource_bound_spec.ResourcePolicy",
) -> dict:
    """The launch-evidence ``resource_bound`` block: the applied bound + fleet cap."""
    stamp = bound.to_dict()
    if policy.fleet_memory_max:
        stamp["fleet_memory_max"] = policy.fleet_memory_max
    return stamp


def _session_exists(adapter: Any, session: str) -> bool:
    probe = getattr(adapter, "session_exists", None)
    if callable(probe):
        return bool(probe(session))
    # Fall back to the existing TmuxAdapter private probe without modifying it.
    private = getattr(adapter, "_session_exists", None)
    if callable(private):
        return bool(private(session))
    return False


def _seat_slug(session: str, window: str) -> str:
    """Slugify ``<session>--<window>`` into a seat_id for a bare Controller seat."""
    slug = re.sub(r"[^a-z0-9-]+", "-", f"{session}--{window}".lower()).strip("-")
    return slug or "seat"


def _resolve_seat_surface(
    *, repo_root: Path | str | None, session: str, window: str, runtime_policy: Path | str | None
) -> tuple[Path, str, str | None]:
    """Resolve (seat_dir, seat_id, run_id) for the ce-ops#26 events surface.

    Dispatch-driven (the ``v3_seat_bridge.spawn_seat`` path passes
    ``--runtime-policy <state_root>/dispatches/<run_id>/runtime-policy.yaml``):
    seat_id = run_id = the dispatch dir name; events land NEXT TO ``dispatch.yaml``.
    Otherwise a bare/lane-less Controller seat: seat_id = ``<session>--<window>``
    slug under ``<repo_root>/.ce/state/dispatches/``; run_id = None.
    """
    if runtime_policy is not None:
        dispatch_dir = Path(runtime_policy).parent
        if dispatch_dir.parent.name == seat_sentinel.DISPATCHES_SUBDIR:
            return dispatch_dir, dispatch_dir.name, dispatch_dir.name
    state_root = Path(repo_root or ".") / ".ce" / "state"
    seat_id = _seat_slug(session, window)
    return seat_sentinel.seat_dir_for(state_root, seat_id), seat_id, None


def _brain_state_root(repo_root: Path | str | None) -> Path:
    return Path(repo_root or ".") / _versions.V3_LOCAL_STATE_ROOT


def _controller_recall_context(repo_root: Path | str | None, payload: Mapping[str, Any]) -> str:
    context = payload.get("context")
    role = None
    seat_class = None
    if isinstance(context, Mapping):
        role = context.get("role")
        seat_class = context.get("seat_class")
    repo = Path(repo_root or ".")
    return (
        "Controller launch brain hydration "
        f"role={role or brain_bootstrap.DEFAULT_ROLE} "
        f"seat_class={seat_class or brain_bootstrap.DEFAULT_SEAT_CLASS} "
        f"repo_root={repo}"
    )


@dataclass(frozen=True)
class _ControllerRecallConfig:
    configured: bool
    embedder_name: str | None = None
    endpoint: str | None = None
    endpoint_configured: bool = False
    endpoint_model_id: str | None = None
    endpoint_dim: int | None = None
    reason: str | None = None

    @property
    def label(self) -> str:
        return self.embedder_name or "unconfigured"


def _env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _status_payload(
    state: str,
    *,
    reason: str,
    endpoint: str | None = None,
    endpoint_configured: bool = False,
    embedder: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "state": state,
        "reason": reason,
        "endpoint": endpoint,
        "endpoint_configured": endpoint_configured,
    }
    if embedder is not None:
        payload["embedder"] = embedder
    payload["line"] = _recall_status_line(payload)
    return payload


def _recall_status_line(status: Mapping[str, Any]) -> str:
    state = str(status.get("state") or "unknown").upper()
    reason = str(status.get("reason") or "no detail")
    endpoint = status.get("endpoint")
    endpoint_part = f" endpoint {endpoint}" if endpoint else ""
    enabled = "enabled" if status.get("state") == "hydrated" else "disabled"
    return (
        f"brain recall: {state} ({reason}{endpoint_part}) - "
        f"semantic recall {enabled} for this session; SSOT assertions unaffected"
    )


def _configured_endpoint_for(embedder_name: str | None, endpoint: str | None) -> str | None:
    normalized = (embedder_name or "").strip().lower().replace("_", "-")
    if normalized in _RECALL_ENDPOINT_EMBEDDERS:
        return endpoint or brain_embedding_openai_endpoint.DEFAULT_ENDPOINT
    return None


def _controller_recall_config_from_env() -> _ControllerRecallConfig:
    raw_embedder = _env_value(RECALL_EMBEDDER_ENV)
    raw_endpoint = _env_value(RECALL_ENDPOINT_ENV)
    raw_model_id = _env_value(RECALL_ENDPOINT_MODEL_ID_ENV)
    raw_dim = _env_value(RECALL_ENDPOINT_DIM_ENV)
    if raw_embedder is None and raw_endpoint is None and raw_model_id is None and raw_dim is None:
        return _ControllerRecallConfig(
            configured=False,
            reason=f"{RECALL_EMBEDDER_ENV} is not set",
        )
    embedder_name = raw_embedder or "vllm-openai"
    endpoint = _configured_endpoint_for(embedder_name, raw_endpoint)
    endpoint_configured = raw_endpoint is not None
    endpoint_dim = None
    if raw_dim is not None:
        try:
            endpoint_dim = int(raw_dim)
        except ValueError:
            return _ControllerRecallConfig(
                configured=True,
                embedder_name=embedder_name,
                endpoint=endpoint,
                endpoint_configured=endpoint_configured,
                endpoint_model_id=raw_model_id,
                reason=f"{RECALL_ENDPOINT_DIM_ENV} must be a positive integer",
            )
        if endpoint_dim <= 0:
            return _ControllerRecallConfig(
                configured=True,
                embedder_name=embedder_name,
                endpoint=endpoint,
                endpoint_configured=endpoint_configured,
                endpoint_model_id=raw_model_id,
                reason=f"{RECALL_ENDPOINT_DIM_ENV} must be a positive integer",
            )
    return _ControllerRecallConfig(
        configured=True,
        embedder_name=embedder_name,
        endpoint=endpoint,
        endpoint_configured=endpoint_configured,
        endpoint_model_id=raw_model_id,
        endpoint_dim=endpoint_dim,
    )


def _open_surface_kwargs(
    repo_root: Path | str | None,
    config: _ControllerRecallConfig,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "state_root": _brain_state_root(repo_root),
        "embedder_name": config.embedder_name,
    }
    if config.endpoint is not None:
        kwargs["endpoint"] = config.endpoint
    if config.endpoint_model_id is not None:
        kwargs["endpoint_model_id"] = config.endpoint_model_id
    if config.endpoint_dim is not None:
        kwargs["endpoint_dim"] = config.endpoint_dim
    if config.endpoint is not None:
        adapter_kwargs: dict[str, Any] = {
            "endpoint": config.endpoint,
            "timeout": LAUNCH_RECALL_ENDPOINT_TIMEOUT_SECONDS,
        }
        if config.endpoint_model_id is not None:
            adapter_kwargs["model_id"] = config.endpoint_model_id
        if config.endpoint_dim is not None:
            adapter_kwargs["dim"] = config.endpoint_dim
        kwargs["embedder"] = brain_embedding_openai_endpoint.OpenAIEndpointEmbeddingAdapter(
            **adapter_kwargs
        )
    return kwargs


def _emit_recall_status(status: Mapping[str, Any]) -> None:
    line = str(status.get("line") or _recall_status_line(status))
    state = status.get("state")
    if state == "unconfigured":
        LOGGER.debug(line)
    elif state == "hydrated":
        LOGGER.info(line)
    elif status.get("endpoint") and status.get("endpoint_configured"):
        endpoint = status["endpoint"]
        LOGGER.warning(
            "Semantic recall hydration skipped: configured embedding endpoint "
            "unreachable at %s; launch proceeds, but recall quality is reduced. "
            "Fix the endpoint or unset %s to use launch without semantic recall hydration.",
            endpoint,
            RECALL_ENDPOINT_ENV,
        )
    else:
        LOGGER.debug(line)


def probe_controller_recall_endpoint(repo_root: Path | str | None = None) -> dict[str, Any]:
    """Return the non-fatal doctor probe for launch-time recall configuration."""
    del repo_root  # Reserved for a future CE state config convention.
    config = _controller_recall_config_from_env()
    if not config.configured:
        return _status_payload(
            "unconfigured",
            reason=config.reason or "recall is not configured",
            embedder=config.embedder_name,
        )
    if config.reason:
        return _status_payload(
            "unavailable",
            reason=config.reason,
            endpoint=config.endpoint,
            endpoint_configured=config.endpoint_configured,
            embedder=config.embedder_name,
        )
    if config.endpoint is None:
        return _status_payload(
            "hydrated",
            reason=f"{config.label} does not require an endpoint",
            embedder=config.embedder_name,
        )
    try:
        import urllib.parse

        parsed = urllib.parse.urlparse(config.endpoint)
        host = parsed.hostname
        if not host:
            raise OSError("endpoint URL has no host")
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        with socket.create_connection((host, port), timeout=1.0):
            pass
    except (OSError, ValueError) as exc:
        return _status_payload(
            "unavailable",
            reason=f"unreachable: {exc}",
            endpoint=config.endpoint,
            endpoint_configured=config.endpoint_configured,
            embedder=config.embedder_name,
        )
    return _status_payload(
        "hydrated",
        reason=f"endpoint {config.endpoint} reachable",
        endpoint=config.endpoint,
        endpoint_configured=config.endpoint_configured,
        embedder=config.embedder_name,
    )


def _parse_positive_pid(raw_pid: Any) -> int | None:
    """Strict pid parse: a positive int, excluding ``bool`` (``isinstance(True,
    int)`` is ``True`` in Python) and excluding non-integral/negative/zero
    values. Returns ``None`` when ``raw_pid`` is not a confirmable live-pid
    candidate.
    """
    if isinstance(raw_pid, bool):
        return None
    if isinstance(raw_pid, int):
        return raw_pid if raw_pid > 0 else None
    if isinstance(raw_pid, str):
        stripped = raw_pid.strip()
        if stripped.isdigit():
            value = int(stripped)
            return value if value > 0 else None
        return None
    return None


def _strict_events_file_scan(seat_dir: Path | str) -> tuple[bool, list[dict[str, Any]]]:
    """Strictly scan ``events.jsonl`` for the launch-gate reuse check ONLY.

    This is deliberately stricter than :func:`seat_sentinel.iter_events_file`
    (which is tolerant read-side observability code that must keep skipping
    malformed lines for other consumers). The launch gate must fail closed:

    * missing file (is_file() False) -> ``(False, [])`` — proceed as today,
      no launched-event history to reconcile.
    * file exists but is unreadable (OSError on read_text) -> ``(True, [])``
      — ambiguous; caller must refuse.  The file could have been locked,
      permission-flipped, or deleted in the is_file/read_text window — any
      of those shapes is indistinguishable from a sentinel we cannot verify.
    * any non-blank line that isn't a parseable JSON object -> ``(True, [])``
      — ambiguous, caller must refuse.
    * otherwise -> ``(False, <parsed event dicts>)``.
    """
    events_path = Path(seat_dir) / seat_sentinel.EVENTS_FILENAME
    if not events_path.is_file():
        return False, []
    try:
        text = events_path.read_text(encoding="utf-8")
    except OSError:
        # File exists (is_file() passed) but is unreadable — ambiguous.
        return True, []
    if not text.strip():
        return False, []
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except ValueError:
            return True, []
        if not isinstance(obj, dict):
            return True, []
        events.append(obj)
    return False, events


STALE_SURFACE_RECOVERY_COMMAND = "ce reap once"
HARNESS_BINARY_BY_HARNESS = {
    "claude": "claude",
    "codex": "codex",
    "hermes": "hermes",
    "openclaw": "openclaw",
}


@dataclass(frozen=True)
class SeatSurfaceArchiveResult:
    archived: bool
    archive_path: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class _StaleDecision:
    """Outcome of a pure stale-surface liveness decision (no side effects)."""

    action: str  # "exit_event" | "all_pids_dead"
    reason: str


def _decide_stale_surface(
    *,
    seat_dir: Path,
    session: str,
    tmux_adapter: Any,
    launched: list[dict[str, Any]],
) -> "_StaleDecision":
    """Pure decision step shared by the live archive path and the preflight
    diagnostic.  Raises :exc:`SeatSurfaceReuseRefused` on any refusal;
    otherwise returns a :class:`_StaleDecision` describing what the archive
    step would do.  No filesystem mutations occur here.

    ``launched`` must be a non-empty list of already-validated launched events
    (all pids confirmed parseable by the strict scanner or by the caller).
    """
    if _session_exists(tmux_adapter, session):
        raise SeatSurfaceReuseRefused(
            _refuse_reuse_message(seat_dir, "live tmux session still exists")
        )

    latest = _latest_event(seat_dir)
    if latest and latest.get("event") == seat_sentinel.EVENT_EXITED:
        return _StaleDecision(
            action="exit_event",
            reason="sentinel exit event observed and no live tmux session exists",
        )

    pids: list[int] = []
    for event in launched:
        pid = _parse_positive_pid(event.get("pid"))
        if pid is not None:
            pids.append(pid)
    if not pids:
        raise SeatSurfaceReuseRefused(
            _refuse_reuse_message(seat_dir, "ambiguous (no sentinel pid recorded)")
        )

    for pid in pids:
        alive = _pid_is_alive(pid)
        if alive is True:
            raise SeatSurfaceReuseRefused(
                _refuse_reuse_message(seat_dir, f"live pid {pid} still exists")
            )
        if alive is None:
            raise SeatSurfaceReuseRefused(
                _refuse_reuse_message(seat_dir, f"ambiguous for pid {pid}")
            )

    return _StaleDecision(
        action="all_pids_dead",
        reason="sentinel pid is dead and no live tmux session exists",
    )


def _pid_is_alive(pid: int) -> bool | None:
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError:
        return None
    return True


def _latest_event(seat_dir: Path | str) -> dict[str, Any] | None:
    events_path = Path(seat_dir) / seat_sentinel.EVENTS_FILENAME
    latest = None
    for event in seat_sentinel.iter_events_file(events_path):
        latest = event
    return latest


def _launched_events(seat_dir: Path | str) -> list[dict[str, Any]]:
    events_path = Path(seat_dir) / seat_sentinel.EVENTS_FILENAME
    return [
        event
        for event in seat_sentinel.iter_events_file(events_path)
        if event.get("event") == seat_sentinel.EVENT_LAUNCHED
    ]


def _archive_path_for(seat_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = seat_dir.with_name(f"{seat_dir.name}.archived-{stamp}")
    suffix = 1
    while candidate.exists():
        candidate = seat_dir.with_name(f"{seat_dir.name}.archived-{stamp}-{suffix}")
        suffix += 1
    return candidate


def _refuse_reuse_message(seat_dir: Path, reason: str) -> str:
    return (
        f"seat surface {str(seat_dir)!r} already has a launched sentinel event; "
        f"refusing to reuse it before spawn because liveness is {reason}. "
        f"Supported recovery command: `{STALE_SURFACE_RECOVERY_COMMAND}` "
        f"--repo-root <repo-root> --root <state-root>."
    )


def _archive_stale_launched_surface(
    *,
    seat_dir: Path,
    session: str,
    tmux_adapter: Any,
) -> SeatSurfaceArchiveResult:
    """Mutating path: decide + rename.  Both steps delegate to shared helpers."""
    launched = _launched_events(seat_dir)
    if not launched:
        return SeatSurfaceArchiveResult(False, reason="no launched event")
    decision = _decide_stale_surface(
        seat_dir=seat_dir,
        session=session,
        tmux_adapter=tmux_adapter,
        launched=launched,
    )
    archive_path = _archive_path_for(seat_dir)
    seat_dir.rename(archive_path)
    return SeatSurfaceArchiveResult(True, archive_path=str(archive_path), reason=decision.reason)


def configured_harness_binary(harness: str) -> str:
    return HARNESS_BINARY_BY_HARNESS.get(harness, harness)


def harness_binary_check(
    harness: str = DEFAULT_HARNESS,
    *,
    which: Any | None = None,
) -> dict[str, Any]:
    binary = configured_harness_binary(harness)
    if harness == "codex":
        # Desync guard: delegate to the SAME resolution the real launcher uses
        # (codex_launch_spec.resolve_codex_harness_binary) rather than a
        # bare shutil.which(binary) — that seam honors CE_CODEX_HARNESS
        # (used EXCLUSIVELY when set) and the composed PATH (live PATH merged
        # with KNOWN_GOOD_PATH), so doctor never reports green for a harness
        # the launcher would actually refuse to resolve.
        try:
            resolved = codex_launch_spec.resolve_codex_harness_binary()
        except codex_launch_spec.GovernedCommandError as exc:
            detail = (
                f"configured codex harness binary could not be resolved: {exc}; "
                f"tried the {codex_launch_spec.CODEX_HARNESS_ENV} override path and the "
                "composed launch PATH (live PATH + known-good sbin/bin dirs); set "
                f"{codex_launch_spec.CODEX_HARNESS_ENV} to an absolute executable path "
                "or install codex on PATH before running `ce launch --harness codex`"
            )
            return {
                "clause": "RED-G-HARNESS-PATH",
                "name": "configured harness binary on PATH",
                "applicable": True,
                "ok": False,
                "detail": detail,
                "harness": harness,
                "binary": binary,
                "resolved": None,
            }
        return {
            "clause": "RED-G-HARNESS-PATH",
            "name": "configured harness binary on PATH",
            "applicable": True,
            "ok": True,
            "detail": (
                f"configured codex harness binary {binary!r} resolves via the "
                f"launcher's codex resolution (override/composed-PATH) at {resolved}"
            ),
            "harness": harness,
            "binary": binary,
            "resolved": resolved,
        }

    resolver = which or shutil.which
    resolved = resolver(binary)
    ok = resolved is not None
    if ok:
        detail = (
            f"configured {harness} harness binary {binary!r} resolves on PATH at {resolved}"
        )
    else:
        detail = (
            f"configured {harness} harness binary {binary!r} is not on PATH; "
            f"install {harness} CLI or fix PATH before running `ce launch --harness {harness}`"
        )
    return {
        "clause": "RED-G-HARNESS-PATH",
        "name": "configured harness binary on PATH",
        "applicable": True,
        "ok": ok,
        "detail": detail,
        "harness": harness,
        "binary": binary,
        "resolved": resolved,
    }


def _evaluate_harness_governance(
    *,
    plan: LaunchPlan,
    harness: str,
    session: str,
    extra_args: Sequence[str] | None,
    repo_root: Path | str | None,
    mcp_config_path: str | None,
    closeout_file: str | None,
    completion_report_ref: str | None,
    host_id: str | None = None,
) -> _HarnessGateResult:
    resolved_mcp: str | None = None
    if harness == "claude":
        requested = list(extra_args) if extra_args else []
        spec = claude_launch_spec.parse_claude_argv(requested)
        # The pack confirmation only changes the decision when skip-permissions is
        # requested, so the (possibly I/O-bound) probe is invoked only then.
        confirmed = _confirm_pack(repo_root) if spec.skip_permissions else False
        spec_result = claude_launch_spec.evaluate_claude_launch(
            spec, hook_pack_confirmed=confirmed
        )
        if not spec_result.ok:
            codes = ", ".join(r.clause for r in spec_result.refusals)
            surfaces = ", ".join(r.surface for r in spec_result.refusals)
            raise LaunchRefused(
                f"refusing governed Claude launch: {codes} ({surfaces}) — "
                "Ring 0 refuses before any side effect"
            )
        resolved_mcp = mcp_config_path or _default_mcp_config_path(session)
        try:
            governed = claude_launch_spec.build_governed_claude_command(
                base_argv=requested,
                mcp_config_path=resolved_mcp,
                closeout_file=closeout_file,
                completion_report_ref=completion_report_ref,
            )
        except claude_launch_spec.GovernedCommandError as exc:
            clause = (
                claude_launch_spec.CLAUSE_MCP
                if "MCP config" in str(exc)
                else claude_launch_spec.CLAUSE_LOCAL_SETTINGS
            )
            raise LaunchRefused(
                f"refusing governed Claude launch: {clause} — {exc}"
            ) from exc
        plan = replace(plan, command=governed)

    elif harness == "codex":
        requested = list(extra_args) if extra_args else []
        managed_confirmed = _confirm_codex_managed_pack(repo_root)
        if not managed_confirmed:
            raise CodexLaunchRefused(
                f"refusing governed Codex launch: {codex_launch_spec.CLAUSE_MANAGED_HOOK_PACK} "
                "(managed-hook-pack) — Ring 0 refuses before any side effect"
            )
        spec = codex_launch_spec.parse_codex_argv(requested)
        config_bypass = (
            None if spec.explicit_bypass else codex_launch_spec.detect_config_bypass_mode()
        )
        spec_result = codex_launch_spec.evaluate_codex_launch(
            spec,
            allowed_root=Path(repo_root or "."),
            config_bypass_mode=config_bypass,
        )
        if not spec_result.ok:
            codes = ", ".join(r.clause for r in spec_result.refusals)
            surfaces = ", ".join(r.surface for r in spec_result.refusals)
            raise CodexLaunchRefused(
                f"refusing governed Codex launch: {codes} ({surfaces}) — "
                "Ring 0 refuses before any side effect"
            )
        try:
            codex_bin = codex_launch_spec.resolve_codex_harness_binary()
        except codex_launch_spec.GovernedCommandError as exc:
            raise CodexLaunchRefused(
                f"refusing governed Codex launch: {exc} — "
                "Ring 0 refuses before any side effect"
            ) from exc
        promotion = codex_controller_evidence.read_packet(repo_root, host_id=host_id)
        remote_control_status = codex_controller_evidence.normalize_remote_control_status()
        authority = "foreman" if promotion.ok else "read-only"
        authority_reason = (
            "promotion evidence packet complete"
            if promotion.ok
            else f"promotion evidence packet {promotion.status}; controller authority downgraded"
        )
        if authority == "foreman" and remote_control_status == "explicit-posture":
            authority = "read-only"
            authority_reason = (
                "remote-control explicit posture is non-authoring; controller authority downgraded"
            )
        env_overrides = {
            "CE_CONTROLLER_ROLE": authority,
            "CE_CONTROLLER_AUTHORITY": authority,
            "CE_CODEX_PROMOTION_PACKET": str(promotion.path),
            "CE_CODEX_PROMOTION_STATUS": promotion.status,
            "CE_REMOTE_CONTROL_STATUS": remote_control_status,
        }
        governed = codex_launch_spec.build_governed_codex_command(
            base_argv=requested, codex_bin=codex_bin, env_overrides=env_overrides
        )
        plan = replace(
            plan,
            command=governed,
            codex_bypass_mode=spec_result.bypass_mode,
            codex_controller_authority=authority,
            codex_promotion_packet_ref=str(promotion.path),
            codex_promotion_packet_status={
                **promotion.to_dict(),
                "authority_reason": authority_reason,
                "remote_control_status": remote_control_status,
            },
            codex_argv_after_rewrite=list(governed),
            codex_cdxd_result=spec_result.to_dict(),
            codex_managed_hook_confirmed=managed_confirmed,
        )

    elif harness == "hermes":
        requested = list(extra_args) if extra_args else []
        spec_result = hermes_launch_spec.evaluate_hermes_launch(
            hermes_launch_spec.parse_hermes_argv(requested)
        )
        if not spec_result.ok:
            codes = ", ".join(r.clause for r in spec_result.refusals)
            surfaces = ", ".join(r.surface for r in spec_result.refusals)
            raise HermesLaunchRefused(
                f"refusing governed Hermes launch: {codes} ({surfaces}) — "
                "Ring 0 refuses before any side effect"
            )
        plan = replace(
            plan,
            command=hermes_launch_spec.build_governed_hermes_command(base_argv=requested),
        )
    return _HarnessGateResult(plan=plan, resolved_mcp=resolved_mcp)


def _evaluate_runtime_policy_gates(
    *,
    plan: LaunchPlan,
    repo_root: Path | str | None,
    runtime_policy: Path | str | None,
    backend: str | None,
    dry_run: bool,
    resume: bool,
) -> _RuntimePolicyGateResult:
    host_backend_opt_out = backend == HOST_BACKEND_OPT_OUT
    runtime_backend = None if host_backend_opt_out else backend
    resolved_runtime_policy: Path | str | None = runtime_policy
    if host_backend_opt_out and runtime_policy is not None:
        raise RuntimePolicyRefused(
            "--backend host is the explicit raw-host opt-out and cannot be combined "
            "with --runtime-policy"
        )

    runtime_policy_auto_resolved = False
    if (
        resolved_runtime_policy is None
        and not dry_run
        and not resume
        and not host_backend_opt_out
    ):
        default_runtime_policy = _default_runtime_policy_path(repo_root)
        if default_runtime_policy.is_file():
            resolved_runtime_policy = default_runtime_policy
            runtime_policy_auto_resolved = True
        else:
            raise RuntimePolicyRefused(
                _missing_default_runtime_policy_message(default_runtime_policy)
            )

    resource_policy: resource_bound_spec.ResourcePolicy | None = None
    policy_data: Any | None = None
    runtime_policy_record: dict[str, Any] | None = None
    if resolved_runtime_policy is not None:
        try:
            policy_data = load_yaml(Path(resolved_runtime_policy))
        except LoaderError as exc:
            raise ResourceBoundRefused(
                f"runtime policy {str(resolved_runtime_policy)!r} is unreadable: {exc}"
            ) from exc
        if not isinstance(policy_data, dict):
            raise RuntimePolicyRefused(
                f"runtime policy {str(resolved_runtime_policy)!r} must be a YAML mapping"
            )
        is_runtime_policy_record = policy_data.get("kind") == ce_runtime_policy.KIND_VALUE
        if runtime_policy_auto_resolved and not is_runtime_policy_record:
            raise RuntimePolicyRefused(
                _corrupt_default_runtime_policy_message(Path(resolved_runtime_policy))
            )
        if runtime_backend is not None or is_runtime_policy_record:
            if not is_runtime_policy_record:
                raise RuntimePolicyRefused(
                    "--backend requires --runtime-policy to point at a full "
                    "runtime-policy-record"
                )
            policy_errors = ce_runtime_policy.validate_runtime_policy(
                policy_data, Path(resolved_runtime_policy)
            )
            if policy_errors:
                detail = "; ".join(error.format() for error in policy_errors[:3])
                raise RuntimePolicyRefused(
                    f"runtime policy {str(resolved_runtime_policy)!r} did not validate clean: {detail}"
                )
            try:
                plan = replace(
                    plan,
                    runtime_policy=ce_runtime_policy.runtime_policy_launch_stamp(
                        policy_data,
                        policy_ref=resolved_runtime_policy,
                        requested_backend=runtime_backend,
                    ),
                )
            except ce_runtime_policy.RuntimePolicyResolutionError as exc:
                raise RuntimePolicyRefused(str(exc)) from exc
            runtime_policy_record = dict(policy_data)
        try:
            resource_policy = resource_bound_spec.parse_resource_policy(policy_data)
        except resource_bound_spec.ResourcePolicyError as exc:
            raise ResourceBoundRefused(str(exc)) from exc
        if resource_policy.opted_down:
            plan = replace(plan, resource_bound=f"none ({resource_policy.enforcement})")
    bounding = (
        resource_policy is not None
        and resource_policy.governed
        and not resource_policy.opted_down
    )
    if runtime_backend is not None and resolved_runtime_policy is None:
        raise RuntimePolicyRefused(
            "--backend requires --runtime-policy so the launch carries the "
            "digest-pinned image, mount manifest, and egress allowlist"
        )
    return _RuntimePolicyGateResult(
        plan=plan,
        resolved_runtime_policy=resolved_runtime_policy,
        runtime_policy_record=runtime_policy_record,
        resource_policy=resource_policy,
        bounding=bounding,
    )


def _evaluate_seat_surface_reuse(
    *,
    repo_root: Path | str | None,
    session: str,
    window: str,
    runtime_policy: Path | str | None,
    tmux_adapter: Any,
    mutate: bool,
) -> _SeatSurfaceGateResult:
    seat_dir, seat_id, seat_run_id = _resolve_seat_surface(
        repo_root=repo_root,
        session=session,
        window=window,
        runtime_policy=runtime_policy,
    )
    ambiguous_events, strict_events = _strict_events_file_scan(seat_dir)
    if ambiguous_events:
        raise SeatSurfaceReuseRefused(
            _refuse_reuse_message(seat_dir, "ambiguous (corrupt sentinel event record)")
        )
    strict_launched_events = [
        event for event in strict_events if event.get("event") == seat_sentinel.EVENT_LAUNCHED
    ]
    if not strict_launched_events:
        return _SeatSurfaceGateResult(seat_dir=seat_dir, seat_id=seat_id, seat_run_id=seat_run_id)
    for event in strict_launched_events:
        if _parse_positive_pid(event.get("pid")) is None:
            raise SeatSurfaceReuseRefused(
                _refuse_reuse_message(seat_dir, "ambiguous (corrupt sentinel event record)")
            )
    if not mutate:
        # Diagnostic (no-mutation) path: share the pure decision step with the
        # live archive path so the two branches cannot desync.
        decision = _decide_stale_surface(
            seat_dir=seat_dir,
            session=session,
            tmux_adapter=tmux_adapter,
            launched=strict_launched_events,
        )
        skip_label = (
            "stale launched surface would be archived during live launch"
            if decision.action == "exit_event"
            else "dead launched surface would be archived during live launch"
        )
        return _SeatSurfaceGateResult(
            seat_dir=seat_dir,
            seat_id=seat_id,
            seat_run_id=seat_run_id,
            skipped_reason=skip_label,
        )
    stale_surface_archive = _archive_stale_launched_surface(
        seat_dir=seat_dir,
        session=session,
        tmux_adapter=tmux_adapter,
    )
    return _SeatSurfaceGateResult(
        seat_dir=seat_dir,
        seat_id=seat_id,
        seat_run_id=seat_run_id,
        stale_surface_archive=stale_surface_archive,
    )


def _apply_resource_bounding_gate(
    *,
    plan: LaunchPlan,
    bounding: bool,
    resource_policy: resource_bound_spec.ResourcePolicy | None,
    session: str,
    systemctl_runner: Any | None,
    support_probe: Any | None,
) -> tuple[LaunchPlan, resource_bound_spec.ResourceBound | None]:
    bound = None
    if bounding:
        if resource_policy is None:
            raise ResourceBoundRefused("resource policy was not resolved for bounded launch")
        probe = support_probe or resource_bound_spec.probe_user_bounding
        ok, reason = probe(systemctl_runner)
        if not ok:
            raise ResourceBoundRefused(
                f"resource_enforcement is 'enforce' but user-level systemd bounding "
                f"is unavailable: {reason}; the ratified opt-down is "
                "resource_enforcement: advisory with a resource_optout binding"
            )
        try:
            unit = resource_bound_spec.resolve_unit_name(session, systemctl_runner)
        except resource_bound_spec.ResourceBoundError as exc:
            raise ResourceBoundRefused(str(exc)) from exc
        bound = resource_policy.seat_bound(unit)
        plan = replace(
            plan,
            command=resource_bound_spec.build_bounded_command(plan.command, bound),
            resource_bound=_resource_stamp(bound, resource_policy),
        )
    return plan, bound


def tail_event_diagnosis(
    events_ref: str | Path | None,
    *,
    command: Sequence[str] | None = None,
    harness: str | None = None,
) -> dict[str, Any] | None:
    if events_ref is None:
        return None
    latest = None
    for event in seat_sentinel.iter_events_file(events_ref):
        latest = event
    if latest is None:
        return None
    payload: dict[str, Any] = {"event": latest.get("event"), "events_ref": str(events_ref)}
    if "exit_code" in latest:
        payload["exit_code"] = latest.get("exit_code")
    if command is not None:
        payload["command"] = list(command)
        if command:
            payload["harness_binary"] = str(command[0])
    elif harness is not None:
        payload["harness_binary"] = configured_harness_binary(harness)
    if payload.get("exit_code") == 127:
        binary = payload.get("harness_binary") or (configured_harness_binary(harness) if harness else "harness")
        payload["remediation"] = (
            f"{binary} CLI not found on PATH - install Claude Code/Codex or fix PATH, "
            f"then re-run `ce onboard --harness {harness or DEFAULT_HARNESS}`"
        )
    return payload


def format_tail_event_diagnosis(diagnosis: Mapping[str, Any] | None) -> str:
    if not diagnosis:
        return ""
    parts = [f"tail_event={diagnosis.get('event')}"]
    if "exit_code" in diagnosis:
        parts.append(f"exit_code={diagnosis.get('exit_code')}")
    if diagnosis.get("command"):
        parts.append(f"command={diagnosis.get('command')!r}")
    if diagnosis.get("remediation"):
        parts.append(f"remediation: {diagnosis.get('remediation')}")
    return "; ".join(parts)


def _build_controller_brain_bootstrap(repo_root: Path | str | None) -> dict[str, Any]:
    try:
        payload = brain_bootstrap.build_bootstrap_payload(
            state_root=_brain_state_root(repo_root),
            role=brain_bootstrap.DEFAULT_ROLE,
            seat_class=brain_bootstrap.DEFAULT_SEAT_CLASS,
        )
    except brain_bootstrap.BrainBootstrapRefused as exc:
        details = "; ".join(exc.errors) if exc.errors else str(exc)
        raise BrainBootstrapLaunchRefused(
            "refusing Controller launch before spawn: "
            f"{details}; recovery: run `ce brain init` from the tenant repo root"
        ) from exc
    config = _controller_recall_config_from_env()
    if not config.configured:
        payload["recall_status"] = _status_payload(
            "unconfigured",
            reason=config.reason or "recall is not configured",
            embedder=config.embedder_name,
        )
        return payload
    if config.reason:
        payload["recall_status"] = _status_payload(
            "unavailable",
            reason=config.reason,
            endpoint=config.endpoint,
            endpoint_configured=config.endpoint_configured,
            embedder=config.embedder_name,
        )
        return payload
    if config.endpoint is not None:
        probe_status = probe_controller_recall_endpoint(repo_root)
        if probe_status.get("state") != "hydrated":
            payload["recall_status"] = _status_payload(
                "unavailable",
                reason=str(probe_status.get("reason") or "endpoint pre-probe failed"),
                endpoint=config.endpoint,
                endpoint_configured=config.endpoint_configured,
                embedder=config.embedder_name,
            )
            return payload
    try:
        surface = brain_recall_surface.open_surface(**_open_surface_kwargs(repo_root, config))
        hydration = surface.hydrate_session(
            _controller_recall_context(repo_root, payload),
            top_k=5,
            allow_confidential_egress=False,
        )
        recall_payload = hydration.to_dict()
        recall_payload["advisory"] = True
        recall_payload["source"] = "brain_recall_surface.hydrate_session"
        recall_payload["embedder"] = config.label
        recall_payload["top_k"] = 5
        recall_payload["allow_confidential_egress"] = False
        payload["recall"] = recall_payload
        payload["recall_status"] = _status_payload(
            "hydrated",
            reason=f"semantic recall hydrated with {config.label}",
            endpoint=config.endpoint,
            endpoint_configured=config.endpoint_configured,
            embedder=config.embedder_name,
        )
    except (
        brain_recall_surface.BrainRecallInvalid,
        brain_recall_surface.BrainRecallPrivacyRefused,
        brain_embedding_openai_endpoint.BrainEmbeddingEndpointError,
        OSError,
        urllib.error.URLError,
        sqlite3.Error,
    ) as exc:
        payload["recall_status"] = _status_payload(
            "unavailable",
            reason=str(exc),
            endpoint=config.endpoint,
            endpoint_configured=config.endpoint_configured,
            embedder=config.embedder_name,
        )
    except Exception as exc:
        payload["recall_status"] = _status_payload(
            "unavailable",
            reason=f"unexpected recall error: {exc}",
            endpoint=config.endpoint,
            endpoint_configured=config.endpoint_configured,
            embedder=config.embedder_name,
        )
    return payload


def _require_launch_pinned_foreman_contract() -> None:
    try:
        brain_bootstrap.require_foreman_dispatch_contract()
    except brain_bootstrap.BrainBootstrapRefused as exc:
        details = "; ".join(exc.errors) if exc.errors else str(exc)
        raise BrainBootstrapLaunchRefused(
            f"refusing Controller launch before spawn: {details}"
        ) from exc


def _materialize_brain_bootstrap(
    *,
    seat_dir: Path,
    payload: dict[str, Any] | None,
) -> tuple[dict[str, str] | None, str | None, str | None]:
    if payload is None:
        return None, None, None
    ref = seat_dir / "brain-bootstrap.json"
    digest = brain_bootstrap.write_payload(ref, payload)
    return brain_bootstrap.payload_env(ref, digest), str(ref), digest


def launch(
    *,
    harness: str = DEFAULT_HARNESS,
    session: str = DEFAULT_SESSION,
    window: str = DEFAULT_WINDOW,
    invoked_as: str = "launch",
    resume: bool = False,
    dry_run: bool = False,
    visible: bool = True,
    allow_hidden: bool = False,
    role: str | None = None,
    takeover_evidence: Path | str | None = None,
    extra_args: Sequence[str] | None = None,
    tmux_adapter: Any | None = None,
    repo_root: Path | str | None = None,
    ledger_root: Path | str | None = None,
    owner_controller_id: str | None = None,
    host_id: str | None = None,
    purpose: str | None = None,
    work_claim: Any | None = None,
    mcp_config_path: str | None = None,
    closeout_file: str | None = None,
    completion_report_ref: str | None = None,
    runtime_policy: Path | str | None = None,
    backend: str | None = None,
    launch_cwd: Path | str | None = None,
    launch_env: Mapping[str, str] | None = None,
    container_runner: Any | None = None,
    gvisor_plan_kwargs: Mapping[str, Any] | None = None,
    containment_proc_root: Path | str = "/proc",
    containment_host_pid: int | str = 1,
    systemctl_runner: Any | None = None,
    support_probe: Any | None = None,
    cgroupfs_root: Path | str = "/sys/fs/cgroup",
) -> LaunchResult:
    """Open or attach a visible Controller-seat tmux session.

    All refusals raise before any side effect (no tmux spawn). For the Claude
    harness, the CC-G-D Ring 0 launch-spec is evaluated and the governed command
    (pinned ``--setting-sources project`` + strict MCP) is built **before** the
    hidden/dry-run/tmux branches.

    v3.5-F: when ``runtime_policy`` names a policy file declaring
    ``resource_envelopes``, the seat is launched inside an OS-enforced
    ``systemd-run --user --scope`` bound. The wrap is applied to the OUTPUT of
    Ring 0 (the governed tokens pass through byte-identical) for EVERY
    supported harness identically. ``systemctl_runner`` / ``support_probe`` /
    ``cgroupfs_root`` are test seams for the systemd I/O edges.
    """
    plan = plan_launch(
        harness=harness,
        session=session,
        window=window,
        invoked_as=invoked_as,
        resume=resume,
        dry_run=dry_run,
        extra_args=extra_args,
    )
    _validate_governed_controller_launch(
        role=role,
        harness=harness,
        repo_root=repo_root,
        session=session,
        takeover_evidence=takeover_evidence,
    )
    _require_launch_pinned_foreman_contract()

    # The CE-owned strict MCP config path for the claude harness, resolved in the
    # Ring-0 branch below and provisioned just before the tmux spawn (defect-a).
    harness_gate = _evaluate_harness_governance(
        plan=plan,
        harness=harness,
        session=session,
        extra_args=extra_args,
        repo_root=repo_root,
        mcp_config_path=mcp_config_path,
        closeout_file=closeout_file,
        completion_report_ref=completion_report_ref,
        host_id=host_id,
    )
    plan = harness_gate.plan
    resolved_mcp = harness_gate.resolved_mcp

    # No hidden fallback — a non-visible / detached continuation is refused.
    if allow_hidden or not visible:
        raise HiddenContinuationRefused(
            "refusing hidden/detached Controller-seat continuation; there is no hidden fallback "
            "(harness exit/crash/auth-loss must not continue headless)"
        )

    # v3.5-F Ring-0-adjacent: read the resource policy fragment (pure,
    # fail-closed) BEFORE any side effect, through the existing policy-read
    # seam (load_yaml). The bounding wrap is applied to the OUTPUT of the
    # Ring 0 builders above — never their input — so the governed tokens stay
    # byte-identical for every harness.
    runtime_gate = _evaluate_runtime_policy_gates(
        plan=plan,
        repo_root=repo_root,
        runtime_policy=runtime_policy,
        backend=backend,
        dry_run=dry_run,
        resume=resume,
    )
    plan = runtime_gate.plan
    resolved_runtime_policy = runtime_gate.resolved_runtime_policy
    runtime_policy_record = runtime_gate.runtime_policy_record
    resource_policy = runtime_gate.resource_policy
    bounding = runtime_gate.bounding

    # Dry-run is pure: deterministic plan, no tmux, no provider login, and no
    # systemd probe — the bounding posture is rendered offline (the plan JSON
    # gains the `resource_bound` block) with the sanitized base unit name.
    if dry_run:
        if bounding:
            unit = resource_bound_spec.sanitize_unit_name(session)
            bound = resource_policy.seat_bound(unit)
            plan = replace(
                plan,
                command=resource_bound_spec.build_bounded_command(plan.command, bound),
                resource_bound=_resource_stamp(bound, resource_policy),
            )
        return LaunchResult(plan=plan, spawned=False, attached=False)

    if plan.runtime_policy is not None and resume:
        raise RuntimePolicyRefused(
            "--backend/--runtime-policy cannot be combined with --resume until the "
            "runtime backend exposes attach semantics; refusing raw fallback"
        )

    if tmux_adapter is None:
        from .tmux_adapter import TmuxAdapter

        tmux_adapter = TmuxAdapter()

    if not tmux_adapter.is_available():
        raise TmuxUnavailableError(
            "tmux is unavailable; refusing visible Controller-seat launch before any side effect"
        )
    visibility_backend = TmuxVisibilityBackend(tmux_adapter)

    if resume:
        if not _session_exists(tmux_adapter, session):
            raise ResumeTargetMissing(
                f"no live launcher session {session!r} to resume; refusing to spawn a hidden seat"
            )
        return LaunchResult(plan=plan, spawned=False, attached=True)

    seat_surface_gate = _evaluate_seat_surface_reuse(
        repo_root=repo_root,
        session=session,
        window=window,
        runtime_policy=resolved_runtime_policy,
        tmux_adapter=tmux_adapter,
        mutate=True,
    )
    seat_dir = seat_surface_gate.seat_dir
    seat_id = seat_surface_gate.seat_id
    seat_run_id = seat_surface_gate.seat_run_id
    stale_surface_archive = seat_surface_gate.stale_surface_archive

    # v3.5-F live bounding — still BEFORE any side effect: refuse loudly when
    # user-level bounding is unavailable under `enforce` (Fork F-2), resolve a
    # collision-free unit name, then wrap the governed command.
    plan, bound = _apply_resource_bounding_gate(
        plan=plan,
        bounding=bounding,
        resource_policy=resource_policy,
        session=session,
        systemctl_runner=systemctl_runner,
        support_probe=support_probe,
    )

    brain_payload = _build_controller_brain_bootstrap(repo_root)
    recall_status = (
        brain_payload.get("recall_status") if isinstance(brain_payload, Mapping) else None
    )
    if isinstance(recall_status, Mapping):
        _emit_recall_status(recall_status)
        plan = replace(plan, brain_recall_status=dict(recall_status))

    # Defect-a fix (v3.1-G1): plain `ce launch` pins claude at the strict MCP
    # config but never created it, so the seat exits 1 silently. Provision it
    # idempotently — reusing the lane helper (v1->v1) — into the seat's cwd
    # (repo_root) just before the spawn, the last fail-closed point before any
    # side effect. A relative path resolves against repo_root, mirroring the lane.
    if resolved_mcp is not None:
        from . import lane_runtime

        mcp_target = Path(resolved_mcp)
        if not mcp_target.is_absolute():
            mcp_target = Path(repo_root or ".") / mcp_target
        try:
            lane_runtime.ensure_lane_mcp_config(mcp_target)
        except lane_runtime.ClaudeLaunchRefused as exc:
            raise LaunchRefused(str(exc)) from exc

    # ce-ops#26 seat sentinels: wrap the OUTERMOST plan.command (the OUTPUT of the
    # Ring-0 + bounding builders) in the launcher-generated supervisor so every
    # lifecycle event — including an OOM group-kill the wrapper OUTSIDE the seat
    # scope survives to record — is machine-watchable; the seat's model never
    # writes the file (silence≠success).
    brain_env, brain_ref, brain_sha = _materialize_brain_bootstrap(
        seat_dir=seat_dir,
        payload=brain_payload,
    )
    if brain_ref is not None:
        plan = replace(
            plan,
            brain_bootstrap_ref=brain_ref,
            brain_bootstrap_sha256=brain_sha,
        )
    sentinel = seat_sentinel.prepare_seat_sentinel(
        seat_dir=seat_dir,
        inner_argv=plan.command,
        seat_id=seat_id,
        run_id=seat_run_id,
        exports=brain_env,
    )
    if plan.runtime_policy is not None and runtime_policy_record is not None:
        # The placeholder-digest defect is a policy-content fact, verifiable
        # from the record alone, so it stays a hard pre-spawn refusal
        # regardless of host. The mount-existence and sentinel-coverage facts
        # depend on THIS host's filesystem matching the record's
        # (potentially symbolic, not-yet-materialized) mount_manifest; when
        # they cannot be verified, refusing outright would fail closed on
        # every launch whose runtime-policy-record predates real bind-source
        # materialization, so we warn and fall back to running the
        # unfiltered manifest through the runtime backend the same way a
        # launch without this preflight would.
        try:
            runtime_policy_record, preflight_warnings = _validate_contained_launch_plan(
                runtime_policy_record,
                sentinel.wrapper_path,
            )
        except ContainedLaunchPlanUnverifiable as exc:
            LOGGER.warning("contained-launch preflight: %s", exc)
        else:
            for warning in preflight_warnings:
                LOGGER.warning("contained-launch preflight: %s", warning)

    ensure_kwargs = {"session": session, "window": window, "command": sentinel.pane_command}
    if launch_cwd is not None:
        ensure_kwargs["cwd"] = launch_cwd
    if launch_env is not None:
        ensure_kwargs["env"] = dict(launch_env)
    ensure_kwargs["seat_dir"] = str(seat_dir)
    runner_runtime: dict | None = None
    try:
        if plan.runtime_policy is not None:
            if runtime_policy_record is None:
                raise RuntimePolicyRefused(
                    "runtime backend launch requires a full runtime-policy-record"
                )
            execution = runtime_backend_bridge.run_visible_runtime(
                resolved_backend=str(plan.runtime_policy["resolved_backend"]),
                runtime_policy=runtime_policy_record,
                run_id=seat_run_id or seat_id,
                command=sentinel.pane_command,
                visibility_backend=visibility_backend,
                session=session,
                window=window,
                cwd=str(launch_cwd) if launch_cwd is not None else None,
                env=dict(launch_env) if launch_env is not None else None,
                seat_dir=str(seat_dir),
                container_runner=container_runner,
                gvisor_plan_kwargs=gvisor_plan_kwargs,
                containment_proc_root=containment_proc_root,
                containment_host_pid=containment_host_pid,
            )
            surface = execution.surface
            runner_runtime = execution.to_dict()
        else:
            surface = visibility_backend.ensure_surface(**ensure_kwargs)
    except runtime_backend_bridge.RuntimeBackendBridgeError as exc:
        raise RuntimePolicyRefused(str(exc)) from exc
    except TmuxUnavailable as exc:
        raise TmuxUnavailableError(str(exc)) from exc
    except VisibilityBackendError as exc:
        raise TmuxUnavailableError(str(exc)) from exc
    except TypeError as exc:
        if launch_cwd is not None or launch_env is not None:
            raise TmuxPanePinningRefused(
                "tmux adapter does not support launch cwd/env pinning; refusing before "
                "marking the seat spawned"
            ) from exc
        raise
    pane = surface.native
    if launch_cwd is not None and not is_proc_self_fd_path(launch_cwd):
        observed = getattr(pane, "pane_cwd", None)
        if observed is None or os.path.realpath(str(observed)) != os.path.realpath(str(launch_cwd)):
            raise TmuxPanePinningRefused(
                f"tmux pane did not verify requested cwd {str(launch_cwd)!r}; "
                "refusing before marking the seat spawned"
            )
    terminal = dict(surface.terminal)

    # v3.5-F launch-confirm: the seat scope must materialize. Write
    # memory.oom.group=1 (kernel kills the SEAT, never a random child) and
    # apply the collective fleet cap from the policy (idempotent, runtime-only).
    resource_confirm = None
    if bound is not None:
        try:
            oom_path = resource_bound_spec.write_oom_group(
                bound.unit, runner=systemctl_runner, cgroupfs_root=cgroupfs_root
            )
            if resource_policy.fleet_memory_max:
                resource_bound_spec.apply_fleet_cap(
                    resource_policy.fleet_memory_max,
                    slice_name=bound.slice,
                    runner=systemctl_runner,
                )
        except resource_bound_spec.ResourceBoundError as exc:
            raise ResourceBoundRefused(
                f"launch-confirm failed for bounded seat {bound.unit!r}: {exc} "
                "(pane left for forensics; retire it per the seat-retirement procedure)"
            ) from exc
        resource_confirm = {
            "oom_group_written": True,
            "oom_group_path": str(oom_path),
            "fleet_memory_max": resource_policy.fleet_memory_max,
        }

    seat_record_ref: str | None = None
    seat_lifecycle_state: str | None = None
    resolved_repo_root = Path(repo_root or ".")
    resolved_ledger_root = Path(ledger_root) if ledger_root is not None else (
        resolved_repo_root / _versions.V3_LOCAL_STATE_ROOT / "active-work-ledger"
    )
    state_root = (
        seat_dir.parent.parent
        if seat_dir.parent.name == seat_sentinel.DISPATCHES_SUBDIR
        else resolved_repo_root / ".ce" / "state"
    )
    dispatch_ref = seat_dir / "dispatch.yaml"
    try:
        registration = seat_lifecycle.register_spawn(
            ledger_root=resolved_ledger_root,
            repo_root=resolved_repo_root,
            seat_id=seat_id,
            owner_controller_id=owner_controller_id,
            host_id=host_id,
            launch_surface="ce_launch",
            terminal=terminal,
            harness_kind=harness,
            purpose=purpose,
            cwd=resolved_repo_root,
            launch_command=plan.command,
            work_claim=work_claim,
            ticket=purpose,
            dispatch_ref=str(dispatch_ref) if dispatch_ref.exists() else None,
            events_ref=str(sentinel.events_path),
            sentinel_wrapper_ref=str(sentinel.wrapper_path),
            run_id=seat_run_id,
            runtime_policy_ref=(
                str(resolved_runtime_policy) if resolved_runtime_policy is not None else None
            ),
            resource_bound=plan.resource_bound,
            resource_confirm=resource_confirm,
        )
        seat_record_ref = str(registration.record_path)
        seat_lifecycle_state = registration.state
        if seat_lifecycle.reconcile_from_sentinel_events(registration.record_path):
            reconciled = seat_lifecycle.load_record(registration.record_path)
            seat_lifecycle_state = str(reconciled["lifecycle"]["state"])
    except seat_lifecycle.SeatLifecycleError as exc:
        escalation_ref = seat_lifecycle.write_registration_failure_escalation(
            state_root=state_root,
            host_id=host_id,
            seat_id=seat_id,
            source_ref=str(sentinel.events_path),
            error=exc,
        )
        seat_lifecycle.warn_registration_failure(
            surface=f"ce {invoked_as}", escalation_ref=escalation_ref, error=exc
        )
        if seat_lifecycle.SEAT_LIFECYCLE_FAIL_CLOSED:
            raise SeatLifecycleRegistrationFailed(str(exc)) from exc
        seat_lifecycle_state = seat_lifecycle.REGISTRATION_STATE_UNGOVERNED

    if harness == "codex" and plan.codex_cdxd_result is not None:
        packet = codex_controller_evidence.build_packet(
            repo_root=repo_root,
            host_id=host_id,
            argv_after_rewrite=plan.codex_argv_after_rewrite or plan.command,
            managed_hook_confirmed=bool(plan.codex_managed_hook_confirmed),
            cdxd_result=plan.codex_cdxd_result,
            bypass_mode_source=plan.codex_bypass_mode,
            remote_control_status=codex_controller_evidence.normalize_remote_control_status(),
            lifecycle_sentinel_refs=(str(sentinel.events_path), str(sentinel.wrapper_path)),
            ring1_smoke_result={
                "status": "pass",
                "checks": [
                    "cdxd-ring0-evaluator-pass",
                    "managed-hook-pack-confirmed",
                    "sentinel-wrapper-materialized",
                    "visible-surface-spawned",
                ],
                "events_ref": str(sentinel.events_path),
                "wrapper_ref": str(sentinel.wrapper_path),
            },
        )
        packet_ref = codex_controller_evidence.write_packet(repo_root, packet)
        validation = codex_controller_evidence.validate_packet(
            packet, path=packet_ref, host_id=host_id
        )
        plan = replace(
            plan,
            codex_promotion_packet_ref=str(packet_ref),
            codex_promotion_packet_status={
                **validation.to_dict(),
                "written": True,
                "authority_this_launch": plan.codex_controller_authority,
            },
        )

    return LaunchResult(
        plan=plan,
        spawned=True,
        attached=resume,
        terminal=terminal,
        resource_confirm=resource_confirm,
        events_ref=str(sentinel.events_path),
        seat_record_ref=seat_record_ref,
        seat_lifecycle_state=seat_lifecycle_state,
        runner_runtime=runner_runtime,
        stale_surface_archive=(
            {
                "archived": stale_surface_archive.archived,
                "archive_path": stale_surface_archive.archive_path,
                "reason": stale_surface_archive.reason,
            }
            if stale_surface_archive is not None
            else None
        ),
    )


def _gate_pass(name: str, detail: str | None = None) -> LaunchPreflightGate:
    return LaunchPreflightGate(name=name, status="PASS", detail=detail)


def _gate_skip(name: str, reason: str) -> LaunchPreflightGate:
    return LaunchPreflightGate(name=name, status="SKIPPED", detail=reason)


def _gate_critical_skip(name: str, reason: str) -> LaunchPreflightGate:
    """A SKIPPED gate that cannot be evaluated without a live launch; exit 3."""
    return LaunchPreflightGate(name=name, status="SKIPPED", detail=reason, critical=True)


def _gate_refusal(name: str, exc: LaunchError) -> LaunchPreflightGate:
    return LaunchPreflightGate(
        name=name,
        status="WOULD-REFUSE",
        detail=str(exc),
        code=getattr(exc, "code", None),
    )


def preflight_launch(
    *,
    harness: str = DEFAULT_HARNESS,
    session: str = DEFAULT_SESSION,
    window: str = DEFAULT_WINDOW,
    invoked_as: str = "launch",
    resume: bool = False,
    visible: bool = True,
    allow_hidden: bool = False,
    extra_args: Sequence[str] | None = None,
    tmux_adapter: Any | None = None,
    repo_root: Path | str | None = None,
    runtime_policy: Path | str | None = None,
    backend: str | None = None,
    mcp_config_path: str | None = None,
    closeout_file: str | None = None,
    completion_report_ref: str | None = None,
    systemctl_runner: Any | None = None,
    support_probe: Any | None = None,
    which: Any | None = None,
) -> LaunchPreflightReport:
    """Evaluate the live ``ce launch`` pre-spawn gates without side effects."""
    gates: list[LaunchPreflightGate] = []
    plan: LaunchPlan | None = None
    resolved_mcp: str | None = None
    runtime_gate: _RuntimePolicyGateResult | None = None
    tmux_ready = False

    try:
        plan = plan_launch(
            harness=harness,
            session=session,
            window=window,
            invoked_as=invoked_as,
            resume=resume,
            dry_run=False,
            extra_args=extra_args,
        )
    except LaunchError as exc:
        gates.append(_gate_refusal("plan", exc))
    else:
        gates.append(_gate_pass("plan"))

    try:
        _require_launch_pinned_foreman_contract()
    except LaunchError as exc:
        gates.append(_gate_refusal("foreman-dispatch-contract", exc))
    else:
        gates.append(_gate_pass("foreman-dispatch-contract"))

    if plan is None:
        gates.append(_gate_skip("harness-governance", "requires a valid launch plan"))
    else:
        try:
            harness_gate = _evaluate_harness_governance(
                plan=plan,
                harness=harness,
                session=session,
                extra_args=extra_args,
                repo_root=repo_root,
                mcp_config_path=mcp_config_path,
                closeout_file=closeout_file,
                completion_report_ref=completion_report_ref,
                host_id=None,
            )
        except LaunchError as exc:
            gates.append(_gate_refusal("harness-governance", exc))
        else:
            plan = harness_gate.plan
            resolved_mcp = harness_gate.resolved_mcp
            gates.append(_gate_pass("harness-governance"))

    if plan is None or harness != "codex":
        gates.append(_gate_skip("codex-controller-promotion", "Codex-only promotion packet gate"))
    else:
        status = plan.codex_promotion_packet_status or {}
        authority = plan.codex_controller_authority or "read-only"
        detail = f"authority={authority}; packet={status.get('status', 'unknown')}"
        if status.get("missing_field_classes"):
            detail += "; missing=" + ",".join(str(v) for v in status["missing_field_classes"])
        gates.append(_gate_pass("codex-controller-promotion", detail))

    try:
        if allow_hidden or not visible:
            raise HiddenContinuationRefused(
                "refusing hidden/detached Controller-seat continuation; there is no hidden fallback "
                "(harness exit/crash/auth-loss must not continue headless)"
            )
    except LaunchError as exc:
        gates.append(_gate_refusal("visibility", exc))
    else:
        gates.append(_gate_pass("visibility"))

    if plan is None:
        gates.append(_gate_skip("runtime-policy", "requires a valid launch plan"))
    else:
        try:
            runtime_gate = _evaluate_runtime_policy_gates(
                plan=plan,
                repo_root=repo_root,
                runtime_policy=runtime_policy,
                backend=backend,
                dry_run=False,
                resume=resume,
            )
        except LaunchError as exc:
            gates.append(_gate_refusal("runtime-policy", exc))
        else:
            plan = runtime_gate.plan
            gates.append(_gate_pass("runtime-policy"))

    # Gate: --resume + --backend/--runtime-policy combination is unconditionally
    # refused by launch() before any side effect; the diagnostic must surface it
    # rather than silently omit it (which would make preflight report all-PASS
    # for an invocation live launch unconditionally refuses).
    if resume and plan is not None:
        if plan.runtime_policy is not None:
            try:
                raise RuntimePolicyRefused(
                    "--backend/--runtime-policy cannot be combined with --resume until the "
                    "runtime backend exposes attach semantics; refusing raw fallback"
                )
            except LaunchError as exc:
                gates.append(_gate_refusal("resume-runtime-policy", exc))
        else:
            gates.append(_gate_skip("resume-runtime-policy", "no runtime-policy requested"))

    if tmux_adapter is None:
        from .tmux_adapter import TmuxAdapter

        tmux_adapter = TmuxAdapter()
    try:
        if not tmux_adapter.is_available():
            raise TmuxUnavailableError(
                "tmux is unavailable; refusing visible Controller-seat launch before any side effect"
            )
    except LaunchError as exc:
        gates.append(_gate_refusal("tmux-availability", exc))
    else:
        tmux_ready = True
        gates.append(_gate_pass("tmux-availability"))

    if resume:
        try:
            if not _session_exists(tmux_adapter, session):
                raise ResumeTargetMissing(
                    f"no live launcher session {session!r} to resume; refusing to spawn a hidden seat"
                )
        except LaunchError as exc:
            gates.append(_gate_refusal("resume-target", exc))
        else:
            gates.append(_gate_pass("resume-target"))
        gates.append(_gate_critical_skip("seat-surface-reuse", "resume attaches an existing live session"))
    elif runtime_gate is None:
        gates.append(_gate_skip("seat-surface-reuse", "requires runtime-policy resolution"))
    elif not tmux_ready:
        gates.append(_gate_skip("seat-surface-reuse", "requires tmux session liveness probe"))
    else:
        try:
            seat_surface = _evaluate_seat_surface_reuse(
                repo_root=repo_root,
                session=session,
                window=window,
                runtime_policy=runtime_gate.resolved_runtime_policy,
                tmux_adapter=tmux_adapter,
                mutate=False,
            )
        except LaunchError as exc:
            gates.append(_gate_refusal("seat-surface-reuse", exc))
        else:
            if seat_surface.skipped_reason:
                gates.append(_gate_skip("seat-surface-reuse", seat_surface.skipped_reason))
            else:
                gates.append(_gate_pass("seat-surface-reuse"))

    binary = harness_binary_check(harness, which=which)
    if binary["ok"]:
        gates.append(_gate_pass("harness-binary", str(binary["detail"])))
    else:
        gates.append(
            LaunchPreflightGate(
                name="harness-binary",
                status="WOULD-REFUSE",
                detail=str(binary["detail"]),
                code="RED-G-HARNESS-PATH",
            )
        )

    if runtime_gate is None or plan is None:
        gates.append(_gate_skip("resource-bounding", "requires runtime-policy resolution"))
    else:
        try:
            plan, _bound = _apply_resource_bounding_gate(
                plan=plan,
                bounding=runtime_gate.bounding,
                resource_policy=runtime_gate.resource_policy,
                session=session,
                systemctl_runner=systemctl_runner,
                support_probe=support_probe,
            )
        except LaunchError as exc:
            gates.append(_gate_refusal("resource-bounding", exc))
        else:
            gates.append(_gate_pass("resource-bounding"))

    if runtime_gate is not None and plan is not None and plan.runtime_policy is not None:
        gates.append(
            _gate_critical_skip(
                "visible-runtime-backend",
                "requires live launch to provision the contained visible runtime",
            )
        )
    else:
        gates.append(_gate_pass("visible-runtime-backend", "not requested"))

    gates.append(
        _gate_skip(
            "brain-bootstrap-materialization",
            "requires live launch to avoid bootstrap sync/hydration and payload writes",
        )
    )
    if resolved_mcp is not None:
        gates.append(_gate_skip("mcp-config-materialization", "requires live launch"))
    return LaunchPreflightReport(gates=tuple(gates))
