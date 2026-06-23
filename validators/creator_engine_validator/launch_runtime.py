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

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import (
    _versions,
    brain_bootstrap,
    claude_launch_spec,
    codex_launch_spec,
    hermes_launch_spec,
    resource_bound_spec,
    runtime_backend_bridge,
    seat_lifecycle,
    seat_sentinel,
)
from .checks import ce_runtime_policy
from .loader import LoaderError, load_yaml
from .tmux_adapter import TmuxUnavailable
from .visibility_backend import TmuxVisibilityBackend, VisibilityBackendError

DEFAULT_HARNESS = "claude"
DEFAULT_SESSION = "ce-controller"
DEFAULT_WINDOW = "controller"
SUPPORTED_HARNESSES = frozenset({"claude", "codex", "hermes", "openclaw"})
VISIBILITY = "operator_visible"


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
    brain_bootstrap_ref: str | None = None
    brain_bootstrap_sha256: str | None = None

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
            "brain_bootstrap_ref": self.brain_bootstrap_ref,
            "brain_bootstrap_sha256": self.brain_bootstrap_sha256,
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
        }


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


def _has_launched_event(seat_dir: Path | str) -> bool:
    events_path = Path(seat_dir) / seat_sentinel.EVENTS_FILENAME
    return any(
        event.get("event") == seat_sentinel.EVENT_LAUNCHED
        for event in seat_sentinel.iter_events_file(events_path)
    )


def _build_controller_brain_bootstrap(repo_root: Path | str | None) -> dict[str, Any]:
    try:
        return brain_bootstrap.build_bootstrap_payload(
            state_root=_brain_state_root(repo_root),
            role=brain_bootstrap.DEFAULT_ROLE,
            seat_class=brain_bootstrap.DEFAULT_SEAT_CLASS,
        )
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

    # The CE-owned strict MCP config path for the claude harness, resolved in the
    # Ring-0 branch below and provisioned just before the tmux spawn (defect-a).
    resolved_mcp: str | None = None

    # CC-G-D Ring 0: refuse prohibited Claude surfaces and pin the governed
    # command BEFORE any side effect (hidden/dry-run/tmux branches below).
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

    # CDX-D Ring 0: Codex launches require the repo-shipped managed PreToolUse
    # hook-pack to be confirmed before spawn, then refuse unsafe launch surfaces
    # and wrap the command with an ambient repo-write credential scrub before any
    # tmux/resource-bound side effect.
    elif harness == "codex":
        requested = list(extra_args) if extra_args else []
        if not _confirm_codex_managed_pack(repo_root):
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
        plan = replace(
            plan,
            command=codex_launch_spec.build_governed_codex_command(
                base_argv=requested, codex_bin=codex_bin
            ),
            codex_bypass_mode=spec_result.bypass_mode,
        )

    # CE Ring 0 Hermes governance: pin the creator-engine profile and refuse
    # prohibited Hermes surfaces BEFORE any side effect. (Hermes has no
    # --strict-mcp-config equivalent; none is invented — see the gate closeout.)
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

    # v3.5-F Ring-0-adjacent: read the resource policy fragment (pure,
    # fail-closed) BEFORE any side effect, through the existing policy-read
    # seam (load_yaml). The bounding wrap is applied to the OUTPUT of the
    # Ring 0 builders above — never their input — so the governed tokens stay
    # byte-identical for every harness.
    resource_policy: resource_bound_spec.ResourcePolicy | None = None
    policy_data: Any | None = None
    runtime_policy_record: dict[str, Any] | None = None
    if runtime_policy is not None:
        try:
            policy_data = load_yaml(Path(runtime_policy))
        except LoaderError as exc:
            raise ResourceBoundRefused(
                f"runtime policy {str(runtime_policy)!r} is unreadable: {exc}"
            ) from exc
        if not isinstance(policy_data, dict):
            raise RuntimePolicyRefused(
                f"runtime policy {str(runtime_policy)!r} must be a YAML mapping"
            )
        is_runtime_policy_record = policy_data.get("kind") == ce_runtime_policy.KIND_VALUE
        if backend is not None or is_runtime_policy_record:
            if not is_runtime_policy_record:
                raise RuntimePolicyRefused(
                    "--backend requires --runtime-policy to point at a full "
                    "runtime-policy-record"
                )
            policy_errors = ce_runtime_policy.validate_runtime_policy(
                policy_data, Path(runtime_policy)
            )
            if policy_errors:
                detail = "; ".join(error.format() for error in policy_errors[:3])
                raise RuntimePolicyRefused(
                    f"runtime policy {str(runtime_policy)!r} did not validate clean: {detail}"
                )
            try:
                plan = replace(
                    plan,
                    runtime_policy=ce_runtime_policy.runtime_policy_launch_stamp(
                        policy_data,
                        policy_ref=runtime_policy,
                        requested_backend=backend,
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
            # Explicit ratified opt-down: launch unbounded, stamp the evidence.
            plan = replace(plan, resource_bound=f"none ({resource_policy.enforcement})")
    bounding = (
        resource_policy is not None
        and resource_policy.governed
        and not resource_policy.opted_down
    )
    if backend is not None and runtime_policy is None:
        raise RuntimePolicyRefused(
            "--backend requires --runtime-policy so the launch carries the "
            "digest-pinned image, mount manifest, and egress allowlist"
        )

    # No hidden fallback — a non-visible / detached continuation is refused.
    if allow_hidden or not visible:
        raise HiddenContinuationRefused(
            "refusing hidden/detached Controller-seat continuation; there is no hidden fallback "
            "(harness exit/crash/auth-loss must not continue headless)"
        )

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

    seat_dir, seat_id, seat_run_id = _resolve_seat_surface(
        repo_root=repo_root, session=session, window=window, runtime_policy=runtime_policy
    )
    if _has_launched_event(seat_dir):
        raise SeatSurfaceReuseRefused(
            f"seat surface {str(seat_dir)!r} already has a launched sentinel event; "
            "refusing to reuse it before spawn"
        )

    # v3.5-F live bounding — still BEFORE any side effect: refuse loudly when
    # user-level bounding is unavailable under `enforce` (Fork F-2), resolve a
    # collision-free unit name, then wrap the governed command.
    bound = None
    if bounding:
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

    brain_payload = _build_controller_brain_bootstrap(repo_root)

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
    if launch_cwd is not None:
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
            runtime_policy_ref=str(runtime_policy) if runtime_policy is not None else None,
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
    )
