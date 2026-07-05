"""``ce onboard`` — the first-run one-shot orchestrator (ce-ops#197, PR-5).

``ce onboard`` is the *kernel-level* first-run command: it wraps the brittle
hand-typed trust-verify → install → ``ce brain init`` → first governed launch
sequence into one guided, idempotent, resumable, gracefully-degrading flow. It
is a thin **composition + UX** layer: every consequential leg is delegated to an
existing surface (``ce doctor``, ``install.sh`` / a detected install,
``ce verify-install``, the profile-PATH writer, ``ce init``, ``ce brain init``,
``ce launch``). This module never re-implements adoption (``cev3 install``) and
never re-types the §0 trust-verify (the published one-liner owns that).

Design authority: ``.ce/state/research/DESIGN_197_CE_ONBOARD.md`` (§A three
install modes, §B the governed-install rail, §1.1 the six phases). The phase
table below is the **single source of truth** for the §B.2 consequence-class /
reversibility classification: both the runner and ``--emit-manifest`` read it,
so the manifest the user's agent plans + gates against is the same data the
orchestrator executes.

The orchestrator is built around **injectable legs** (:class:`OnboardLegs`): a
bundle of callables, each defaulting to the real composed surface, every one
replaceable in a test. The module performs no I/O of its own except through a
leg, so the happy path and every degradation branch are exercised offline with
mocked legs.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from inspect import Parameter, signature
from pathlib import Path
from typing import Any, Callable

from ._versions import V3_LOCAL_STATE_ROOT

# --- §B.2 consequence-class taxonomy (the governed-install rail) -------------
# These are the data-table classifications the orchestrator + --emit-manifest
# both read. Operator-confirmed table lives in DESIGN_197 §B.2.
CLASS_READ_ONLY = "read_only"
CLASS_LOW = "low"
CLASS_MEDIUM = "medium"
CLASS_HIGH = "high"
CLASS_BINDING = "binding"

REVERSIBLE = "reversible"
PARTIALLY_IRREVERSIBLE = "partially_irreversible"
IRREVERSIBLE = "irreversible"

# §B.2 default behaviors (autonomous vs gated).
DECISION_AUTO = "auto"
DECISION_CONFIRM = "confirm"
DECISION_RATIFIED = "ratified"
DECISION_HUMAN_ACTION = "human_action"

# --- §A install modes --------------------------------------------------------
INSTALL_MODES = ("agent", "guided", "hybrid", "print", "skip")

# Phase status values surfaced in each --json record.
STATUS_OK = "ok"
STATUS_SKIPPED = "skipped"
STATUS_REFUSED = "refused"
STATUS_BLOCKED = "blocked"
STATUS_HUMAN_ACTION = "human_action"

GITHUB_APP_OPERATOR_INPUT = {
    "id": "github.app",
    "required_for": "contained-seat-onboarding",
    "kind": "own",
    "human_action": (
        "Create an operator-owned per-user GitHub App for this seat, install it "
        "on the target repo/account, and provide github.app.app_id, "
        "github.app.client_id, github.app.pem as a tmpfs SecretRef, and "
        "github.app.installation_id. Do not use the CE shared App or another "
        "seat's App id."
    ),
}

STATE_PATH_GUIDANCE = (
    ".hermes/ must be git-ignored before CE writes local governed state. "
    "Add a .gitignore line containing `.hermes/`, run `ce init --repo-root {repo_root}`, "
    "then re-run `ce onboard --repo-root {repo_root}`."
)


class OnboardError(Exception):
    """A hard, fail-closed onboard refusal (never a silent proceed)."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase_id: str | None = None,
        verify: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.phase_id = phase_id
        self.verify = verify or {}
        self.data = data or {}


@dataclass(frozen=True)
class PhaseSpec:
    """Static description of one onboard phase (the §B.2 classification row).

    This is the machine-readable contract ``--emit-manifest`` serializes so the
    user's agent can *plan + gate* each phase before it runs.
    """

    id: str
    action: str
    blast_radius: str
    consequence_class: str
    reversibility: str
    decision: str  # the §B.2 default behavior for this phase

    def to_manifest_entry(self) -> dict[str, str]:
        return {
            "id": self.id,
            "action": self.action,
            "blast_radius": self.blast_radius,
            "consequence_class": self.consequence_class,
            "reversibility": self.reversibility,
            "decision": self.decision,
        }


# The six phases (DESIGN_197 §1.1), each carrying its §B.2 classification. This
# table is the SINGLE SOURCE: the runner iterates it; --emit-manifest serializes
# it. Order is the execution order.
PHASE_SPECS: tuple[PhaseSpec, ...] = (
    PhaseSpec(
        id="doctor",
        action="preflight environment doctor (+ low-TMPDIR + PATH-gap probes)",
        blast_radius="read-only host probe",
        consequence_class=CLASS_READ_ONLY,
        reversibility=REVERSIBLE,
        decision=DECISION_AUTO,
    ),
    PhaseSpec(
        id="install",
        action="detect a genuine install; else acquire it via the verified install.sh one-liner",
        blast_radius="user-local venv under ~/.local (or print-only)",
        consequence_class=CLASS_LOW,
        reversibility=REVERSIBLE,
        decision=DECISION_AUTO,
    ),
    PhaseSpec(
        id="verify_install",
        action="provenance self-check (ce verify-install): genuine-published-release gate",
        blast_radius="read-only",
        consequence_class=CLASS_READ_ONLY,
        reversibility=REVERSIBLE,
        decision=DECISION_AUTO,
    ),
    PhaseSpec(
        id="fix_path",
        action="idempotent CE-marked profile PATH block (~/.local/bin + npm global bin)",
        blast_radius="user shell profile (CE-marked, reversible block)",
        consequence_class=CLASS_LOW,
        reversibility=REVERSIBLE,
        decision=DECISION_AUTO,
    ),
    PhaseSpec(
        id="bootstrap",
        action="ce init + ce brain init (local kernel state + idempotent genesis ledger)",
        blast_radius="local repo-scoped kernel state",
        consequence_class=CLASS_LOW,
        reversibility=REVERSIBLE,
        decision=DECISION_AUTO,
    ),
    PhaseSpec(
        id="launch",
        action="drive exactly one ce launch + assert a single live controller",
        blast_radius="spawns one governed controller seat",
        consequence_class=CLASS_MEDIUM,
        reversibility=REVERSIBLE,
        decision=DECISION_AUTO,
    ),
)

_PHASE_BY_ID = {spec.id: spec for spec in PHASE_SPECS}


@dataclass
class PhaseRecord:
    """One executed phase's machine record (carries the §B.3 audit fields)."""

    id: str
    status: str
    detail: str
    consequence_class: str
    reversibility: str
    decision: str
    verify: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "detail": self.detail,
            # §B.3 audit fields: every phase record carries its rail classification
            # and the autonomous-vs-confirmed decision actually taken.
            "consequence_class": self.consequence_class,
            "reversibility": self.reversibility,
            "decision": self.decision,
            "verify": dict(self.verify),
            "data": dict(self.data),
        }


@dataclass
class OnboardResult:
    ok: bool
    install_mode: str
    phases: list[PhaseRecord] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "install_mode": self.install_mode,
            "reason": self.reason,
            "phases": [p.to_dict() for p in self.phases],
        }


# --- leg result shapes (small, JSON-safe) ------------------------------------
@dataclass
class DoctorLegResult:
    ok: bool
    refused_clauses: list[str] = field(default_factory=list)
    low_tmpdir: bool = False
    path_gap: bool = False
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstallDetectResult:
    present: bool
    command: str | None = None  # the canonical one-liner to print (modes guided/hybrid/print)
    detail: str = ""


@dataclass
class LaunchLegResult:
    ok: bool
    live_controllers: int
    seat_record_ref: str | None = None
    detail: str = ""
    events_ref: str | None = None
    command: list[str] = field(default_factory=list)


# --- install-mode selection (DESIGN_197 §A.5) --------------------------------
def select_install_mode(
    explicit: str | None,
    *,
    agent_present: bool,
) -> str:
    """Resolve the effective install mode per §A.5.

    Default selection: agent present → ``hybrid`` (hand-off when complexity is
    detected, else guided underneath); no agent → ``guided``. The default is
    **never** ``print`` — ``print`` is the explicit manual fallback (§A.4).
    """
    if explicit is not None:
        if explicit not in INSTALL_MODES:
            raise OnboardError(
                "CE-ONBOARD-BAD-MODE",
                f"unknown --install-mode {explicit!r}; choose from {', '.join(INSTALL_MODES)}",
            )
        return explicit
    return "hybrid" if agent_present else "guided"


# Ordered agent-discovery probe (DESIGN_197 §A.3 handoff discovery). Pure +
# offline: it only reads $CE_INSTALL_AGENT and which()s known harness binaries.
# It NEVER invokes the agent (that is PR-7's install.sh hand-off, explicitly out
# of scope here — ce onboard only MODELS the hybrid mode + emits the manifest).
_KNOWN_AGENT_BINARIES = ("claude", "codex")


def detect_agent_present(*, which: Callable[[str], str | None] = shutil.which) -> bool:
    """True when the user has a discoverable coding agent (§A.3 discovery order)."""
    if os.environ.get("CE_INSTALL_AGENT"):
        return True
    return any(which(name) for name in _KNOWN_AGENT_BINARIES)


# --- injectable legs ---------------------------------------------------------
def _default_doctor_leg(
    repo_root: str,
    *,
    require_visible_launch: bool,
    harness: str = "claude",
) -> DoctorLegResult:
    from . import doctor_runtime

    report = doctor_runtime.run_doctor(
        repo_root,
        require_visible_launch=require_visible_launch,
        harness=harness,
    )
    payload = report.payload
    probes = payload.get("onboard_probes", {})
    return DoctorLegResult(
        ok=report.ok,
        refused_clauses=list(payload.get("refused_clauses", [])),
        low_tmpdir=bool(probes.get("low_tmpdir", False)),
        path_gap=bool(probes.get("path_gap", False)),
        detail="doctor PASS" if report.ok else "doctor refused",
        payload=payload,
    )


def _default_install_detect_leg(
    repo_root: str,
    *,
    install_root: str | None = None,
) -> InstallDetectResult:
    # Detection is rooted in the configured install root, not in this running
    # package import path. ``ce onboard`` commonly executes from a source tree,
    # so importing creator_engine_validator would falsely mark an empty
    # --install-root as installed and bypass the human-action install gate.
    from . import ce_provenance

    one_liner = (
        "curl --proto '=https' --tlsv1.2 -fsSL "
        "https://creator-engine.dev/install.sh | bash"
    )
    del repo_root
    root = Path(install_root) if install_root is not None else ce_provenance.default_install_root()
    state_path = root / "install-state"
    present = state_path.is_file()
    detail = f"install detected under {root}" if present else f"install absent under {root}"
    return InstallDetectResult(present=present, command=one_liner, detail=detail)

def _default_active_work_ledger_root(repo_root: str | Path) -> Path:
    return Path(repo_root) / V3_LOCAL_STATE_ROOT / "active-work-ledger"


def _default_verify_install_leg(install_root: str | None, *, offline: bool) -> dict[str, Any]:
    from . import ce_provenance

    result = ce_provenance.verify_install(install_root, offline=offline)
    return result.to_json()


def _default_fix_path_leg() -> dict[str, Any]:
    from . import ce_profile_path

    result = ce_profile_path.ensure_profile_path_block()
    return result.to_dict()


def _default_init_leg(repo_root: str) -> dict[str, Any]:
    from . import init_runtime

    return init_runtime.init_repo(repo_root).to_dict()


def _default_brain_init_leg(state_root: str) -> dict[str, Any]:
    from . import ce_cli

    return ce_cli.brain_init(state_root).to_dict()


def _default_launch_leg(
    *,
    harness: str,
    repo_root: str,
    ledger_root: str | None,
) -> LaunchLegResult:
    from . import launch_runtime, seat_lifecycle

    result = launch_runtime.launch(
        harness=harness,
        repo_root=repo_root,
        ledger_root=ledger_root,
        tmux_adapter=None,
    )
    resolved_ledger = Path(ledger_root) if ledger_root is not None else _default_active_work_ledger_root(repo_root)
    live = _count_live_controllers(seat_lifecycle, resolved_ledger)
    return LaunchLegResult(
        ok=result.seat_record_ref is not None,
        live_controllers=live,
        seat_record_ref=result.seat_record_ref,
        detail="launched governed controller",
        events_ref=getattr(result, "events_ref", None),
        command=list(getattr(getattr(result, "plan", None), "command", [])),
    )


def _count_live_controllers(seat_lifecycle: Any, ledger_root: str) -> int:
    live = 0
    for _path, record in seat_lifecycle.iter_records(ledger_root):
        lifecycle = record.get("lifecycle", {}) if isinstance(record, dict) else {}
        if lifecycle.get("state") == seat_lifecycle.STATE_ALIVE:
            live += 1
    return live


@dataclass
class OnboardLegs:
    """The composed surfaces, each replaceable in a test."""

    doctor: Callable[..., DoctorLegResult] = _default_doctor_leg
    install_detect: Callable[..., InstallDetectResult] = _default_install_detect_leg
    verify_install: Callable[..., dict[str, Any]] = _default_verify_install_leg
    fix_path: Callable[[], dict[str, Any]] = _default_fix_path_leg
    init: Callable[[str], dict[str, Any]] = _default_init_leg
    brain_init: Callable[[str], dict[str, Any]] = _default_brain_init_leg
    launch: Callable[..., LaunchLegResult] = _default_launch_leg


@dataclass
class OnboardConfig:
    repo_root: str = "."
    state_root: str = V3_LOCAL_STATE_ROOT
    ledger_root: str | None = None
    install_mode: str | None = None
    install_root: str | None = None
    harness: str = "claude"
    no_launch: bool = False
    no_fix_path: bool = False
    offline: bool = False
    assume_yes: bool = False


# --- the orchestrator --------------------------------------------------------
def emit_manifest() -> dict[str, Any]:
    """Machine-readable description of the onboard phases (DESIGN_197 §A.1).

    The user's agent reads this to plan + gate each phase against the §B.2
    governed-install rail BEFORE any step runs. It is a pure projection of the
    phase table — no host state, no I/O.
    """
    return {
        "schema": "ce.onboard.manifest/v1",
        "phases": [spec.to_manifest_entry() for spec in PHASE_SPECS],
        "consequence_classes": [
            CLASS_READ_ONLY,
            CLASS_LOW,
            CLASS_MEDIUM,
            CLASS_HIGH,
            CLASS_BINDING,
        ],
        "decisions": [
            DECISION_AUTO,
            DECISION_CONFIRM,
            DECISION_RATIFIED,
            DECISION_HUMAN_ACTION,
        ],
        "operator_inputs": [dict(GITHUB_APP_OPERATOR_INPUT)],
    }


def _record(spec_id: str, *, status: str, detail: str, verify: dict | None = None,
            data: dict | None = None, decision: str | None = None) -> PhaseRecord:
    spec = _PHASE_BY_ID[spec_id]
    return PhaseRecord(
        id=spec.id,
        status=status,
        detail=detail,
        consequence_class=spec.consequence_class,
        reversibility=spec.reversibility,
        decision=decision or spec.decision,
        verify=verify or {},
        data=data or {},
    )


def _wrap_leg_failure(phase_id: str, exc: Exception) -> OnboardError:
    phase = phase_id.replace("_", "-").upper()
    return OnboardError(
        f"CE-ONBOARD-{phase}-FAILED",
        f"{phase_id} failed: {exc.__class__.__name__}: {exc}",
        phase_id=phase_id,
        verify={"exception_class": exc.__class__.__name__},
    )


def _run_leg(phase_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return func(*args, **kwargs)
    except OnboardError:
        raise
    except Exception as exc:
        raise _wrap_leg_failure(phase_id, exc) from exc


def _run_install_detect(
    func: Callable[..., InstallDetectResult],
    repo_root: str,
    install_root: str | None,
) -> InstallDetectResult:
    kwargs = {"install_root": install_root}
    try:
        params = signature(func).parameters
    except (TypeError, ValueError):
        return _run_leg("install", func, repo_root, **kwargs)
    accepts_install_root = (
        "install_root" in params
        or any(param.kind == Parameter.VAR_KEYWORD for param in params.values())
    )
    if accepts_install_root:
        return _run_leg("install", func, repo_root, **kwargs)
    return _run_leg("install", func, repo_root)


def _run_doctor_leg(
    func: Callable[..., DoctorLegResult],
    repo_root: str,
    *,
    require_visible_launch: bool,
    harness: str,
) -> DoctorLegResult:
    kwargs = {"require_visible_launch": require_visible_launch, "harness": harness}
    try:
        params = signature(func).parameters
    except (TypeError, ValueError):
        return _run_leg("doctor", func, repo_root, **kwargs)
    accepts_var_kwargs = any(param.kind == Parameter.VAR_KEYWORD for param in params.values())
    if "harness" in params or accepts_var_kwargs:
        return _run_leg("doctor", func, repo_root, **kwargs)
    return _run_leg("doctor", func, repo_root, require_visible_launch=require_visible_launch)


def _state_path_guidance(repo_root: str) -> dict[str, Any]:
    return {
        "guidance": STATE_PATH_GUIDANCE.format(repo_root=repo_root),
        "next_steps": [
            "Add `.hermes/` to .gitignore",
            f"Run `ce init --repo-root {repo_root}`",
            f"Re-run `ce onboard --repo-root {repo_root}`",
        ],
    }


def _fail_result(result: OnboardResult, exc: OnboardError) -> OnboardResult:
    phase_id = exc.phase_id
    if phase_id in _PHASE_BY_ID:
        result.phases.append(_record(
            phase_id,
            status=STATUS_REFUSED,
            detail=str(exc),
            verify={"code": exc.code, **exc.verify},
            data=exc.data,
        ))
    result.ok = False
    result.reason = exc.code
    return result


def run_onboard(config: OnboardConfig, *, legs: OnboardLegs | None = None) -> OnboardResult:
    """Sequence the six phases, idempotently + gracefully-degrading.

    Each phase is preflight → action → verification, emitting a PhaseRecord with
    the §B.3 audit fields. The flow is fail-closed: a hard refusal stops the
    sequence (never a silent proceed); a soft degradation (offline / no-tmux)
    records a skip and continues where safe.
    """
    legs = legs or OnboardLegs()
    agent_present = detect_agent_present()
    mode = select_install_mode(config.install_mode, agent_present=agent_present)
    result = OnboardResult(ok=True, install_mode=mode)

    # Phase 1 — doctor. A hard refusal here (ungoverned host) STOPS before any
    # mutation. We require the visible-launch clause only when we will launch.
    require_visible = not config.no_launch
    try:
        doctor = _run_doctor_leg(
            legs.doctor,
            config.repo_root,
            require_visible_launch=require_visible,
            harness=config.harness,
        )
    except OnboardError as exc:
        return _fail_result(result, exc)
    if not doctor.ok:
        # A missing visible tmux terminal is a *soft* boundary: everything up to
        # launch can still run; we mark launch blocked later. Any other refusal
        # is a hard stop.
        non_tmux = [c for c in doctor.refused_clauses if c != "PCO-049"]
        if non_tmux:
            guidance_data = (
                _state_path_guidance(config.repo_root)
                if "RED-G-4" in doctor.refused_clauses
                else {}
            )
            result.phases.append(_record(
                "doctor", status=STATUS_REFUSED,
                detail=f"doctor refused: {', '.join(doctor.refused_clauses)}",
                verify={"refused_clauses": doctor.refused_clauses},
                data=guidance_data,
            ))
            result.ok = False
            result.reason = "doctor refused (ungoverned host)"
            return result
    result.phases.append(_record(
        "doctor", status=STATUS_OK,
        detail=doctor.detail,
        verify={
            "low_tmpdir": doctor.low_tmpdir,
            "path_gap": doctor.path_gap,
            "refused_clauses": doctor.refused_clauses,
        },
    ))
    no_visible_terminal = "PCO-049" in doctor.refused_clauses

    # Phase 2 — install detect / acquire.
    try:
        detect = _run_install_detect(legs.install_detect, config.repo_root, config.install_root)
    except OnboardError as exc:
        return _fail_result(result, exc)
    if mode == "skip":
        result.phases.append(_record(
            "install", status=STATUS_SKIPPED,
            detail="install skipped (--install-mode skip)",
            data={"present": detect.present},
        ))
    elif detect.present:
        result.phases.append(_record(
            "install", status=STATUS_OK,
            detail="genuine install already present",
            data={"present": True},
        ))
    elif mode in ("print", "guided", "hybrid", "agent"):
        # No install present: onboard never hand-builds the trust bind. It
        # surfaces the verified one-liner (print/guided/hybrid) or, in agent
        # mode, points at the signed spec. install.sh OWNS the trust-verify; we
        # do NOT execute a fresh-trust-boundary install in-process.
        result.phases.append(_record(
            "install", status=STATUS_HUMAN_ACTION,
            detail=f"install absent: run the verified one-liner ({mode})",
            decision=DECISION_HUMAN_ACTION,
            data={"present": False, "command": detect.command, "mode": mode},
        ))
        # Without an install we cannot verify/bootstrap/launch in-process.
        result.ok = False
        result.reason = "install required before onboard can continue"
        return result

    # Phase 3 — verify-install provenance gate. A failed provenance check is a
    # HARD gate: refuse to proceed to launch on an unverified install
    # (--install-mode skip allows the explicit dev-workspace override).
    if mode == "skip":
        result.phases.append(_record(
            "verify_install", status=STATUS_SKIPPED,
            detail="provenance check skipped (--install-mode skip)",
        ))
    else:
        try:
            verify = _run_leg("verify_install", legs.verify_install, config.install_root, offline=config.offline)
        except OnboardError as exc:
            return _fail_result(result, exc)
        v_ok = bool(verify.get("ok"))
        offline_note = " (offline: local state only)" if config.offline else ""
        if not v_ok:
            result.phases.append(_record(
                "verify_install", status=STATUS_REFUSED,
                detail=f"provenance check failed{offline_note}: {verify.get('reason', '')}",
                verify=verify,
            ))
            result.ok = False
            result.reason = "refuse-on-unverified-install"
            return result
        result.phases.append(_record(
            "verify_install", status=STATUS_OK,
            detail=f"provenance verified{offline_note}",
            verify=verify,
        ))

    # Phase 4 — PATH standardization (Decision 4 default-on; --no-fix-path opt-out).
    if config.no_fix_path:
        result.phases.append(_record(
            "fix_path", status=STATUS_SKIPPED,
            detail="profile PATH block skipped (--no-fix-path)",
        ))
    else:
        try:
            path_data = _run_leg("fix_path", legs.fix_path)
        except OnboardError as exc:
            return _fail_result(result, exc)
        result.phases.append(_record(
            "fix_path", status=STATUS_OK,
            detail="profile PATH block ensured (re-source your shell to apply)",
            data=path_data,
        ))

    # Phase 5 — workspace bootstrap (ce init + ce brain init). Idempotent: a
    # re-run is a safe no-op that reports current state.
    try:
        init_data = _run_leg("bootstrap", legs.init, config.repo_root)
        brain_data = _run_leg("bootstrap", legs.brain_init, config.state_root)
    except OnboardError as exc:
        return _fail_result(result, exc)
    result.phases.append(_record(
        "bootstrap", status=STATUS_OK,
        detail="workspace bootstrapped (init + brain genesis ledger)",
        data={"init": init_data, "brain": brain_data},
    ))

    # Phase 6 — first governed launch (exactly one) + single-controller assertion.
    if config.no_launch:
        result.phases.append(_record(
            "launch", status=STATUS_SKIPPED,
            detail="launch skipped (--no-launch); everything up to launch done",
        ))
        return result
    if no_visible_terminal:
        # Graceful degradation: no tmux / not a governed host. Stop before launch
        # with everything else already done (DESIGN_197 §1.3).
        result.phases.append(_record(
            "launch", status=STATUS_BLOCKED,
            detail="no visible tmux terminal: cannot drive a visible governed launch "
                   "(everything up to launch is complete)",
            verify={"refused_clauses": ["PCO-049"]},
        ))
        result.ok = False
        result.reason = "no-visible-launch"
        return result

    try:
        launch = _run_leg(
            "launch",
            legs.launch,
            harness=config.harness,
            repo_root=config.repo_root,
            ledger_root=config.ledger_root,
        )
    except OnboardError as exc:
        return _fail_result(result, exc)
    # The #212 single-controller assertion: exactly ONE live controller after a
    # first launch. More than one => stale/double-spawn; refuse rather than mask.
    if launch.live_controllers != 1:
        from . import launch_runtime

        tail = launch_runtime.tail_event_diagnosis(
            launch.events_ref,
            command=launch.command,
            harness=config.harness,
        )
        tail_detail = launch_runtime.format_tail_event_diagnosis(tail)
        detail = f"single-controller assertion failed: {launch.live_controllers} live controller(s)"
        if tail_detail:
            detail = f"{detail}; {tail_detail}"
        verify = {"live_controllers": launch.live_controllers}
        if tail:
            verify["tail_event"] = tail
        result.phases.append(_record(
            "launch", status=STATUS_REFUSED,
            detail=detail,
            verify=verify,
        ))
        result.ok = False
        result.reason = "single-controller-assertion-failed"
        return result
    result.phases.append(_record(
        "launch", status=STATUS_OK,
        detail=launch.detail,
        verify={"live_controllers": launch.live_controllers},
        data={"seat_record_ref": launch.seat_record_ref},
    ))
    return result


# --- CLI handler (called from ce_cli.main) -----------------------------------
def run_cli(args) -> int:
    """``ce onboard`` argparse handler.

    Lives here (not in ce_cli) so the orchestrator + its CLI surface are one
    cohesive v1 module. ce_cli wires the subparser + dispatch only.
    """
    if getattr(args, "emit_manifest", False):
        print(json.dumps(emit_manifest(), indent=2, sort_keys=True))
        return 0

    config = OnboardConfig(
        repo_root=getattr(args, "repo_root", "."),
        state_root=getattr(args, "state_root", V3_LOCAL_STATE_ROOT),
        ledger_root=getattr(args, "ledger_root", None),
        install_mode=getattr(args, "install_mode", None),
        install_root=getattr(args, "install_root", None),
        harness=getattr(args, "harness", "claude"),
        no_launch=getattr(args, "no_launch", False),
        no_fix_path=getattr(args, "no_fix_path", False),
        offline=getattr(args, "offline", False),
        assume_yes=getattr(args, "assume_yes", False),
    )
    try:
        result = run_onboard(config)
    except OnboardError as exc:
        print(f"ERROR: ce onboard refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(_render_human(result))
    return 0 if result.ok else 1


def _render_human(result: OnboardResult) -> str:
    head = f"ce onboard: {'OK' if result.ok else 'INCOMPLETE'} (install-mode={result.install_mode})"
    lines = [head]
    for phase in result.phases:
        lines.append(f"  [{phase.status}] {phase.id}: {phase.detail}")
        guidance = phase.data.get("guidance")
        if guidance:
            lines.append(f"    guidance: {guidance}")
        next_steps = phase.data.get("next_steps")
        if next_steps:
            lines.append("    next steps:")
            for step in next_steps:
                lines.append(f"      - {step}")
    if not result.ok and result.reason:
        lines.append(f"  reason: {result.reason}")
    return "\n".join(lines)
