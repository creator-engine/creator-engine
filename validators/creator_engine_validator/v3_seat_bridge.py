"""v3.1-G1 — the assemble→spawn bridge (a ratified Scope's DispatchPlan → a REAL
governed, OS-bounded tmux seat).

This is the live-spawn keystone the shadow self-host trial named: ``cev3 drive``
assembles a :class:`coordination.DispatchPlan` (the front gate held) but stops at
the deferred seam — it produces inputs, executes nothing. This module crosses the
last gap to the proven v1 spawn mechanics.

**The v1⊥v3 boundary (the crux).** The HARD invariant forbids any import across
the boundary, in either direction (``_versions``/``VERSION_BOUNDARY.md``). So this
module imports **NO v1 module**. Instead it re-enters the v1 product through its
own CLI contract: it invokes the ``ce`` console_script as a **subprocess**
(``ce launch --json …``) and consumes its machine-readable ``LaunchResult`` JSON.
The dispatch crosses as **files + argv + JSON (DATA)**, never as a module edge —
exactly how the Operator uses v1 today. The ``version_boundary`` check (an
AST-import-graph guard) stays green by construction; ``test_v3_seat_bridge``
asserts the AST names no v1 module, making the design a tested invariant.

Every subprocess edge — ``ce launch``, ``tmux send-keys`` — is an **injected seam**
(``runner=``), so CI drives fakes and there is **zero live tmux/claude/systemd**
in the test envelope (the same discipline as ``run_assembly``).

Scope (G1-codex): the default **claude** path is conserved and remains the
stronger Ring-1-hook-pack path. The **codex** path is explicitly selected,
guarded to low-risk classes unless separately ratified, and launch-confirmed
against CE's managed Codex PreToolUse hook-pack.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from . import coordination, work_claims

DEFAULT_BRIDGE_HARNESS = "claude"
CODEX_BRIDGE_HARNESS = "codex"


@dataclass(frozen=True)
class HarnessBridge:
    harness: str
    v1_harness: str
    unattended_args: tuple[str, ...]
    requires_transcript_locator: bool
    in_band_boundary: str


HARNESS_BRIDGES: dict[str, HarnessBridge] = {
    "claude": HarnessBridge(
        harness="claude",
        v1_harness="claude",
        unattended_args=("--claude-arg=--dangerously-skip-permissions",),
        requires_transcript_locator=False,
        in_band_boundary="claude_ring1_hookpack",
    ),
    "codex": HarnessBridge(
        harness="codex",
        v1_harness="codex",
        unattended_args=(),
        requires_transcript_locator=True,
        in_band_boundary="codex_managed_pretooluse",
    ),
}

# Backward-compatible alias for existing tests/callers; not a claim that only
# Claude is bridged.
BRIDGE_HARNESS = DEFAULT_BRIDGE_HARNESS

#: Where dispatch records live, relative to the v3 local-state ``root``.
DISPATCHES_SUBDIR = "dispatches"

#: The conserved dispatch-record envelope (``schemas/dispatch-record.schema.yaml``).
_KIND = "dispatch-record"
_RECORD_TYPE = "dispatch"
_SCHEMA_VERSION = "1"

#: The conserved terminal-outcome vocabulary (``schemas/runtime-evidence.schema.yaml``),
#: surfaced in the seat brief so the seat reports against the closed enum.
OUTCOME_VOCABULARY = (
    "pr_opened",
    "pr_merged",
    "review_submitted",
    "research_delivered",
    "no_change",
)

#: Seat-spawn PATH preflight (G1-followup): the bridge process must resolve these
#: before ANY side effect. ``tmux`` carries the seed/readiness choreography; the
#: harness binary is the seat. A miss is a fail-closed ``SpawnRefused`` (the common
#: live failure — it bit 2026-06-11 — is the BRIDGE env, caught here; a pane whose
#: tmux-server PATH diverges is caught by the readiness poll, not the preflight).
SPAWN_PREFLIGHT_BASE_BINARIES = ("tmux",)

#: Seed readiness poll (G1-followup): the pointer line must not be typed before the
#: harness REPL owns the pane foreground, else it is swallowed by the still-init shell
#: and silently lost. Bounded; on timeout the spawn is fail-closed (pane CONSERVED for
#: autopsy — a failure is evidence).
DEFAULT_READINESS_TIMEOUT_S = 30.0
READINESS_POLL_INTERVAL_S = 0.5

#: Codex transcript-locator settle window (ce-ops#56). On a cold/idle TUI the codex
#: harness has not yet written its ``~/.codex/sessions/**/*.jsonl`` when the locator's
#: first poll fires immediately after ``seed_brief`` — the poll sees zero hits and, on a
#: short budget, fail-closes with a spurious ``SpawnRefused`` (live-reproduced 2026-06-13,
#: codex v0.139.0 / gpt-5.5 xhigh). A bounded settle precedes the FIRST poll iteration so
#: the session file exists by the time we look; it is capped at the locator deadline (it
#: spends from the same timeout budget, never extends it).
CODEX_TRANSCRIPT_SETTLE_S = 2.5

#: Foreground commands that mean the harness REPL has NOT yet taken the pane (the
#: still-initializing login/launch shell). Readiness = the foreground command has
#: LEFT this set (claude may itself exec as ``node``, so we test shell-departure, not
#: an exact harness-name match — robust to the live exec shape, and the fake runner's
#: ``shell -> claude`` transition satisfies it).
_READINESS_SHELL_COMMANDS = frozenset(
    {"bash", "sh", "zsh", "fish", "dash", "ksh", "tcsh", "csh",
     "-bash", "-sh", "-zsh", "-fish", "login"}
)

#: Seed SUBMIT guard (S8 live-dogfood defect). The literal seed line is DELIVERED
#: (``send-keys`` rc 0) but the harness input box can SWALLOW the Enter sent on its
#: heels — the key arrives, the submit is lost, and the rc check passes because tmux
#: itself succeeded. So after Enter we POLL that the line has LEFT the input box (it is
#: no longer sitting at the prompt tail); while it is still pending we re-send Enter,
#: bounded, then fail closed (pane CONSERVED for autopsy). A ``>=1s`` settle between the
#: literal send and the FIRST Enter mirrors the proven manual cadence.
SEED_SUBMIT_SETTLE_S = 1.0
SEED_SUBMIT_MAX_ATTEMPTS = 3
#: How many bottom pane lines constitute the input-box "prompt tail" scanned for the
#: still-pending (unsubmitted) seed line.
_SEED_PROMPT_TAIL_LINES = 8


class SeatBridgeError(Exception):
    """Base class for bridge refusals (fail-closed; never a silent half-spawn)."""


class SpawnRefused(SeatBridgeError):
    """The v1 launch leg refused or returned an unusable result."""


class HarnessNotSupported(SeatBridgeError):
    """An unknown bridge harness was requested."""


class DispatchWorktreeBridgeError(SeatBridgeError):
    """The dispatch-worktree bridge refused a v1 subprocess/data leg."""


class SubprocessDispatchWorktreeBridge:
    """Runtime provider for ``dispatch_worktree`` using bridge-safe v1 seams.

    The shared dispatch core injects this provider. PCO and worker environment
    operations cross to the v1 runtime as subprocess + JSON/stdout data; this
    class imports no v1 modules.
    """

    def __init__(
        self,
        *,
        runner: Callable[..., Any] = subprocess.run,
        gh_runner: work_claims.GhRunner | None = None,
        validator_exe: str | None = None,
        ce_exe: str | None = None,
    ) -> None:
        self._runner = runner
        self._gh_runner = gh_runner or work_claims.default_gh_runner
        self._validator_exe = validator_exe
        self._ce_exe = ce_exe

    def acquire_work_claim(
        self,
        work_key: work_claims.WorkKey,
        *,
        holder: str,
        host: str,
        reason: str,
        now: datetime,
    ) -> work_claims.ClaimResult:
        return work_claims.acquire(
            work_key,
            self._gh_runner,
            holder=holder,
            host=host,
            reason=reason,
            now=now,
        )

    def release_work_claim(
        self,
        work_key: work_claims.WorkKey,
        *,
        holder: str,
        host: str,
        claim_id: str,
        reason: str,
        now: datetime,
    ) -> work_claims.ClaimResult:
        return work_claims.release(
            work_key,
            self._gh_runner,
            holder=holder,
            host=host,
            claim_id=claim_id,
            reason=reason,
            now=now,
        )

    def best_effort_release_work_claim(
        self,
        work_key: work_claims.WorkKey,
        claim_id: str | None,
        *,
        holder: str,
        host: str,
        reason: str,
        now: datetime,
    ) -> bool:
        return work_claims.best_effort_release(
            work_key,
            self._gh_runner,
            claim_id,
            holder=holder,
            host=host,
            reason=reason,
            now=now,
        )

    def allocate_worktree(
        self,
        *,
        repo_root: Path,
        ledger_root: Path,
        lane_id: str,
        worktree_path: Path,
        envelope_ref: str,
        branch: str,
        controller_id: str,
        lease_seconds: int,
    ) -> None:
        argv = [
            _resolve_validator_exe(self._validator_exe),
            "pco-allocate",
            "--lane-id", lane_id,
            "--worktree-path", str(worktree_path),
            "--branch", branch,
            "--envelope-ref", envelope_ref,
            "--controller-id", controller_id,
            "--ledger-root", str(ledger_root),
            "--repo-root", str(repo_root),
            "--lease-seconds", str(lease_seconds),
            "--pane-label", "implementer",
        ]
        completed = self._runner(argv, capture_output=True, text=True)
        if getattr(completed, "returncode", 1) != 0:
            reason = (getattr(completed, "stderr", "") or "").strip() or "(no stderr)"
            raise DispatchWorktreeBridgeError(f"pco-allocate refused: {reason}")

    def release_worktree(
        self,
        *,
        repo_root: Path,
        ledger_root: Path,
        lane_id: str,
        controller_id: str,
        release_reason: str,
    ) -> None:
        argv = [
            _resolve_validator_exe(self._validator_exe),
            "pco-release",
            "--lane-id", lane_id,
            "--controller-id", controller_id,
            "--ledger-root", str(ledger_root),
            "--repo-root", str(repo_root),
            "--release-reason", release_reason,
        ]
        completed = self._runner(argv, capture_output=True, text=True)
        if getattr(completed, "returncode", 1) != 0:
            reason = (getattr(completed, "stderr", "") or "").strip() or "(no stderr)"
            raise DispatchWorktreeBridgeError(f"pco-release refused: {reason}")

    def scrub_worker_environment(
        self,
        *,
        worker_id: str,
        role: str,
        scope_id: str,
        depth: int,
        parent_id: str | None,
        home_path: Path,
    ) -> tuple[dict[str, str], tuple[str, ...]]:
        argv = [
            _resolve_ce_exe(self._ce_exe),
            "worker",
            "scrub-env",
            "--worker-id", worker_id,
            "--role", role,
            "--scope-id", scope_id,
            "--depth", str(depth),
            "--home-path", str(home_path),
            "--json",
        ]
        if parent_id:
            argv.extend(["--parent-id", parent_id])
        completed = self._runner(argv, capture_output=True, text=True)
        if getattr(completed, "returncode", 1) != 0:
            reason = (getattr(completed, "stderr", "") or "").strip() or "(no stderr)"
            raise DispatchWorktreeBridgeError(f"ce worker scrub-env refused: {reason}")
        try:
            payload = json.loads(getattr(completed, "stdout", "") or "")
        except (json.JSONDecodeError, TypeError) as exc:
            raise DispatchWorktreeBridgeError(
                f"ce worker scrub-env produced unparsable JSON: {exc}"
            ) from exc
        child_env = payload.get("child_env")
        scrubbed = payload.get("scrubbed_env_names", ())
        if not isinstance(child_env, dict):
            raise DispatchWorktreeBridgeError("ce worker scrub-env returned no child_env object")
        return {str(k): str(v) for k, v in child_env.items()}, tuple(str(v) for v in scrubbed)


def get_harness_bridge(harness: str) -> HarnessBridge:
    """Return the bridge registry entry or fail closed."""
    try:
        return HARNESS_BRIDGES[harness]
    except KeyError as exc:
        raise HarnessNotSupported(
            f"harness {harness!r} is not bridged (available: {', '.join(sorted(HARNESS_BRIDGES))})"
        ) from exc


def _utcstamp(now: datetime) -> str:
    """Compact, filename/tmux-safe UTC stamp (no ``:`` / ``.``)."""
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ce-ops#89 (PCO-020): the review run_id is fed to ``pco-allocate`` AS the ledger
# lane id, and pco derives the lease id as ``lease-<lane_id>-<14-digit stamp>``.
# The worktree-lease schema bounds ``lease_id`` at 64 chars, so the lane id (this
# run_id) must leave room for pco's fixed 21-char envelope ("lease-" + "-" + a
# 14-digit compact UTC stamp). For long scope_ids the naive ``rev-<scope>-<stamp>``
# overflowed that bound and fail-closed refused the venue. Clamp the run_id to the
# residual budget, hash-suffixing the scope segment when it must be clipped so two
# distinct long scope_ids never collide into the same lane.
_LEASE_ID_MAX = 64
_LEASE_DERIVE_OVERHEAD = len("lease-") + len("-") + 14  # pco's ``lease-<lane>-<YYYYmmddHHMMSS>``
_REVIEW_RUN_ID_MAX = _LEASE_ID_MAX - _LEASE_DERIVE_OVERHEAD  # == 43
_REVIEW_RUN_ID_HASH_LEN = 8


def _derive_review_run_id(scope_id: str, stamp: str) -> str:
    """Mint ``rev-<scope_id>-<stamp>`` clamped so the pco-derived lease id stays
    within the 64-char ``worktree-lease`` bound (PCO-020) for ANY scope_id length.

    Short scope_ids keep the readable, lossless form. When the full id would
    overflow the lane budget, the scope segment is clipped and a deterministic
    8-hex digest of the *full* scope_id is appended — so distinct long scope_ids
    sharing a clipped prefix still mint distinct (collision-free) lane ids.
    """
    stamp_lc = stamp.lower()
    full = f"rev-{scope_id}-{stamp_lc}"
    if len(full) <= _REVIEW_RUN_ID_MAX:
        return full
    prefix = "rev-"
    suffix = f"-{stamp_lc}"
    scope_budget = _REVIEW_RUN_ID_MAX - len(prefix) - len(suffix)
    digest = hashlib.sha256(scope_id.encode("utf-8")).hexdigest()[:_REVIEW_RUN_ID_HASH_LEN]
    head_len = scope_budget - len(digest) - 1  # 1 for the joining dash
    if head_len < 1:
        # Pathological (tiny budget): fall back to a pure-digest scope segment,
        # still bounded by scope_budget so the lane never overflows.
        scope_segment = digest[:scope_budget]
    else:
        scope_segment = f"{scope_id[:head_len]}-{digest}"
    return f"{prefix}{scope_segment}{suffix}"


@dataclass
class DispatchRecord:
    """A materialized dispatch — the on-disk handoff between drive and the seat.

    VALUE-FREE: opaque digests + shape refs only. The launch evidence
    (``terminal``/``resource_bound``/``spawned_at``) is stamped after the spawn.
    ``data`` is the JSON/YAML-serializable record body persisted to ``dispatch.yaml``;
    the read-model (L2) is designed to fold it later.
    """

    run_id: str
    scope_id: str
    dispatch_dir: Path
    data: dict[str, Any]
    runtime_policy_ref: str
    mcp_config_ref: str
    brief_ref: str = ""

    @property
    def dispatch_path(self) -> Path:
        return self.dispatch_dir / "dispatch.yaml"

    @property
    def session(self) -> str:
        return str(self.data["session"])

    @property
    def window(self) -> str:
        return str(self.data["window"])

    @property
    def unattended(self) -> bool:
        return bool(self.data["unattended"])

    @property
    def harness_session_id(self) -> str | None:
        sid = self.data.get("harness_session_id")
        return str(sid) if sid else None

    @property
    def pane_id(self) -> str | None:
        terminal = self.data.get("terminal") or {}
        pane = terminal.get("pane_id")
        return str(pane) if pane else None


@dataclass
class SpawnResult:
    """The outcome of the v1 launch leg (value-free shape only)."""

    run_id: str
    terminal: dict[str, Any]
    resource_bound: Any = None
    launch_result: dict[str, Any] = field(default_factory=dict)


def _yaml_bytes(data: dict[str, Any]) -> str:
    """Deterministic YAML (sorted keys, block style) — matches the v3 scope writer."""
    return yaml.safe_dump(data, sort_keys=True, default_flow_style=False)


def _render_brief(
    *,
    run_id: str,
    scope_id: str,
    mutation_class: str,
    harness: str,
    runtime_policy: dict[str, Any],
    root: Path,
    dispatch_dir: Path,
) -> str:
    """The seat mandate brief: the Scope card, run identity, evidence-handoff, vocab.

    The plan is value-free by design, so the authoritative Goal / Done-when text
    is sourced by reference to the ratified Scope artifact (the seat reads it),
    while Budget and Change-type render from the conserved fields the plan carries.
    """
    envelopes = runtime_policy.get("spend_envelopes") or []
    budget = json.dumps(envelopes, sort_keys=True) if envelopes else "(none declared)"
    scope_ref = root / "scopes" / f"{scope_id}.scope.yaml"
    evidence_ref = root / "runs" / f"{run_id}.runtime-evidence.yaml"
    vocab = " | ".join(OUTCOME_VOCABULARY)
    if harness == CODEX_BRIDGE_HARNESS:
        boundary = (
            "Your in-band boundary is CE's managed Codex PreToolUse hook-pack. "
            "It is a strong native gate for Codex tools, while containment and "
            "external `cev3 pr`, `cev3 review`, and `cev3 merge` gates remain load-bearing."
        )
    else:
        boundary = "The Ring-1 hook-pack is your enforced boundary."
    return (
        f"# ◆ CE seat mandate — run {run_id}\n\n"
        f"You are a governed, OS-bounded CE seat spawned from a ratified Scope by "
        f"`cev3 drive --spawn`. Execute the Scope below. {boundary}\n\n"
        f"## Scope card\n"
        f"- **Goal** — read the ratified Scope artifact: `{scope_ref}`\n"
        f"- **Done-when** — the acceptance criteria in that artifact (you are graded against them)\n"
        f"- **Budget** — {budget}\n"
        f"- **Change-type** — {mutation_class}\n\n"
        f"## Run identity\n"
        f"- run_id: `{run_id}`\n"
        f"- scope_id: `{scope_id}`\n"
        f"- dispatch record: `{dispatch_dir / 'dispatch.yaml'}`\n\n"
        f"## Evidence handoff (for `cev3 collect`)\n"
        f"When you finish, the run is folded by:\n"
        f"`cev3 collect {scope_id} --run {run_id} --outcome <outcome> [--pr <n>]`\n"
        f"Your harness transcript is resolved automatically from the session id stamped "
        f"at spawn — do NOT pass `--transcript` (the salvage-only `--transcript-override` "
        f"is documented for a crashed/relocated transcript).\n"
        f"The conserved evidence chain lands at `{evidence_ref}`.\n\n"
        f"## Terminal outcome vocabulary (closed)\n"
        f"{vocab}\n"
    )


def materialize_dispatch(
    plan: coordination.DispatchPlan,
    root: Path | str,
    *,
    harness: str = DEFAULT_BRIDGE_HARNESS,
    unattended: bool = True,
    now: datetime | None = None,
    session: str | None = None,
    window: str = "drive",
    harness_session_id: str | None = None,
    codex_risk_override: str | None = None,
) -> DispatchRecord:
    """Persist a :class:`coordination.DispatchPlan` as the on-disk seat handoff.

    Writes, under ``<root>/dispatches/<run_id>/``:

    * ``dispatch.yaml`` — the value-free dispatch record (digests + shape refs);
    * ``runtime-policy.yaml`` — the plan's merged ``runtime_policy`` (spend
      envelope included), so the v1 leg can consume it AS DATA via
      ``--runtime-policy`` (the ``_versions.py`` data-coupling precedent, now
      driven from the v3 side);
    * ``brief.md`` — the seat mandate brief.

    The run_id is minted ``run-<scope_id>-<utcstamp>``. No spawn happens here; the
    launch evidence is stamped by :func:`spawn_seat`.
    """
    # D3 (F5): absolutize the state root at materialize time so every derived ref
    # (dispatch_dir, brief_ref, the brief's scope/evidence pointers, the seeded line)
    # is absolute and survives the worktree boundary — the in-venue Ring-1 hook and the
    # launch-time validator both resolve an absolute ref from ANY cwd.
    bridge = get_harness_bridge(harness)
    root_path = Path(root).resolve()
    stamp = _utcstamp(now or datetime.now(timezone.utc))
    run_id = f"run-{plan.scope_id}-{stamp}"
    dispatch_dir = root_path / DISPATCHES_SUBDIR / run_id
    dispatch_dir.mkdir(parents=True, exist_ok=True)

    seat_session = session or run_id
    # Claude keeps the F9 pre-minted UUID key. Codex stamps its real session id after
    # the session_meta transcript appears, because the live CLI has no equivalent
    # --session-id launch arg.
    seat_harness_session_id = (
        (harness_session_id or str(uuid.uuid4()))
        if bridge.harness == DEFAULT_BRIDGE_HARNESS
        else harness_session_id
    )
    runtime_policy_ref = str(dispatch_dir / "runtime-policy.yaml")
    mcp_config_ref = str(dispatch_dir / "mcp" / "ce-mcp.json")
    brief_ref = str(dispatch_dir / "brief.md")

    # The plan's merged runtime policy, written for the v1 leg to read AS DATA.
    (dispatch_dir / "runtime-policy.yaml").write_text(
        _yaml_bytes(dict(plan.runtime_policy)), encoding="utf-8"
    )
    # The seat mandate brief (pointer target for the tmux seed line).
    (dispatch_dir / "brief.md").write_text(
        _render_brief(
            run_id=run_id,
            scope_id=plan.scope_id,
            mutation_class=plan.mutation_class,
            harness=bridge.harness,
            runtime_policy=plan.runtime_policy,
            root=root_path,
            dispatch_dir=dispatch_dir,
        ),
        encoding="utf-8",
    )

    record: dict[str, Any] = {
        "kind": _KIND,
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "scope_id": plan.scope_id,
        "run_id": run_id,
        "mutation_class": plan.mutation_class,
        # value-free opaque 64-hex digests (approver_ref / ratified_scope_sha)
        "scope_ratification": dict(plan.scope_ratification),
        "harness": bridge.harness,
        "harness_boundary": bridge.in_band_boundary,
        "unattended": bool(unattended),
        "session": seat_session,
        "window": window,
        "runtime_policy_ref": runtime_policy_ref,
        "brief_ref": brief_ref,
        # launch evidence — populated post-spawn by spawn_seat (value-free shape).
        "terminal": None,
        "resource_bound": None,
        "spawned_at": None,
    }
    if seat_harness_session_id:
        record["harness_session_id"] = seat_harness_session_id
    if bridge.harness == CODEX_BRIDGE_HARNESS and codex_risk_override:
        record["codex_risk_override"] = codex_risk_override
    rec = DispatchRecord(
        run_id=run_id,
        scope_id=plan.scope_id,
        dispatch_dir=dispatch_dir,
        data=record,
        runtime_policy_ref=runtime_policy_ref,
        mcp_config_ref=mcp_config_ref,
        brief_ref=brief_ref,
    )
    _write_record(rec)
    return rec


def _write_record(record: DispatchRecord) -> None:
    record.dispatch_path.write_text(_yaml_bytes(record.data), encoding="utf-8")


def mark_spawn_failed(
    record: DispatchRecord,
    reason: Any,
    *,
    now: datetime | None = None,
) -> DispatchRecord:
    """Fail-closed: stamp a value-free spawn failure on the record (not a pending run).

    A refused spawn (or a post-spawn seed failure) must NEVER be left shaped like a
    live dispatch — the read-model keys Build/RUN off ``spawned_at``/``terminal``
    AND the absence of this stamp, so a half/refused spawn projects as neither
    pending nor live. The failed attempt is conserved (stamped, never deleted): a
    failure is evidence. ``reason`` is the refusal text already surfaced to the
    operator — value-free, no credential/host/account.
    """
    record.data["spawn_failed_at"] = _utcstamp(now or datetime.now(timezone.utc))
    record.data["spawn_failure_reason"] = str(reason)
    _write_record(record)
    return record


def _resolve_ce_exe(ce_exe: str | None) -> str:
    """Resolve the v1 ``ce`` console_script; refuse if absent (fail-closed)."""
    if ce_exe:
        return ce_exe
    candidate = Path(sys.executable).parent / "ce"
    if candidate.exists():
        return str(candidate)
    found = shutil.which("ce")
    if found:
        return found
    raise SpawnRefused(
        "cannot resolve the v1 `ce` entry point (not next to the interpreter, "
        "not on PATH); refusing to spawn"
    )


def _preflight_spawn_binaries(
    record: DispatchRecord,
    binaries: tuple[str, ...] | None = None,
    *,
    now: datetime | None = None,
) -> None:
    """Resolve the spawn-critical binaries on the BRIDGE PATH before any side effect.

    A miss is stamped :func:`mark_spawn_failed` (the record is already materialized —
    conserve the autopsy) and raised :class:`SpawnRefused`. This catches the common
    live failure (the bridge env missing ``tmux``/the harness — it bit 2026-06-11).
    """
    bridge = get_harness_bridge(str(record.data.get("harness") or DEFAULT_BRIDGE_HARNESS))
    required = binaries or (*SPAWN_PREFLIGHT_BASE_BINARIES, bridge.v1_harness)
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        reason = (
            f"spawn preflight failed: required binaries not on PATH: "
            f"{', '.join(missing)}"
        )
        mark_spawn_failed(record, reason, now=now)
        raise SpawnRefused(f"{reason} (for run {record.run_id!r})")


def spawn_seat(
    record: DispatchRecord,
    *,
    runner: Callable[..., Any] = subprocess.run,
    ce_exe: str | None = None,
    now: datetime | None = None,
) -> SpawnResult:
    """Spawn the governed seat via the v1 product contract (subprocess + DATA).

    Invokes ``ce launch --session <session> --window <window> --json
    --mcp-config <CE-owned> --runtime-policy <dispatch>/runtime-policy.yaml``,
    appending ``--claude-arg=--dangerously-skip-permissions`` iff the seat is
    unattended (CC-D-6 stays the gate on the v1 side: an unconfirmed hook-pack is
    a fail-closed ``LaunchRefused``). Parses the ``--json`` ``LaunchResult`` and
    stamps ``terminal`` + ``resource_bound`` + ``spawned_at`` into ``dispatch.yaml``.

    Non-zero exit / unparsable JSON / un-spawned result ⇒ :class:`SpawnRefused`
    with the v1 stderr surfaced (never a silent half-spawn).
    """
    _preflight_spawn_binaries(record, now=now)
    exe = _resolve_ce_exe(ce_exe)
    bridge = get_harness_bridge(str(record.data.get("harness") or DEFAULT_BRIDGE_HARNESS))
    argv = [
        exe,
        "launch",
    ]
    if bridge.harness != DEFAULT_BRIDGE_HARNESS:
        argv.extend(["--harness", bridge.v1_harness])
    argv.extend([
        "--session",
        record.session,
        "--window",
        record.window,
        "--json",
        "--runtime-policy",
        record.runtime_policy_ref,
    ])
    if bridge.harness == DEFAULT_BRIDGE_HARNESS:
        # D3 (CC-D-7): the dispatch RECORD keeps ``mcp_config_ref`` ABSOLUTE (D3
        # conserved), but Ring-0 CC-D-7 requires launched ``--mcp-config`` to be a
        # CE-owned RELATIVE path.
        mcp_config_arg = os.path.relpath(record.mcp_config_ref, Path.cwd())
        if mcp_config_arg.startswith(".."):
            reason = (
                "mcp_config_ref does not compose a CE-owned relative --mcp-config from the "
                "launch cwd (relpath escapes with '..'); CC-D-7 would refuse the seat"
            )
            mark_spawn_failed(record, reason, now=now)
            raise SpawnRefused(f"{reason} (for run {record.run_id!r})")
        argv.extend(["--mcp-config", mcp_config_arg])
    if record.unattended:
        # The governance for this already exists (CC-D-6): the flag is honored
        # ONLY when the committed hook-pack is confirmed — the v1 leg fails closed
        # otherwise. For a governed seat the Ring-1 hook-pack is the boundary;
        # approval modals are not load-bearing and hang unattended seats.
        argv.extend(bridge.unattended_args)
    if bridge.harness == DEFAULT_BRIDGE_HARNESS and record.harness_session_id:
        # D6 (F9): pin the harness transcript to a KNOWN key so `cev3 collect`
        # resolves it by exact id — never by an mtime guess (the #14/#21 mis-fold).
        # Ring 0 passes `--session-id=<uuid>` unmodified (the lenient parser; not a
        # CC-D clause), so this is zero governance churn.
        argv.append(f"--claude-arg=--session-id={record.harness_session_id}")

    completed = runner(argv, capture_output=True, text=True)
    returncode = getattr(completed, "returncode", 1)
    stdout = getattr(completed, "stdout", "") or ""
    stderr = getattr(completed, "stderr", "") or ""
    if returncode != 0:
        raise SpawnRefused(
            f"v1 `ce launch` refused (exit {returncode}) for run {record.run_id!r}: "
            f"{stderr.strip() or '(no stderr)'}"
        )
    try:
        launch_result = json.loads(stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SpawnRefused(
            f"v1 `ce launch --json` produced unparsable output for run "
            f"{record.run_id!r}: {exc}; stderr={stderr.strip() or '(none)'}"
        ) from exc
    if not launch_result.get("spawned"):
        raise SpawnRefused(
            f"v1 `ce launch` did not spawn a seat for run {record.run_id!r} "
            f"(spawned={launch_result.get('spawned')!r})"
        )
    terminal = launch_result.get("terminal") or {}
    if not terminal.get("pane_id"):
        raise SpawnRefused(
            f"v1 `ce launch` returned no terminal pane for run {record.run_id!r}; "
            "refusing a half-spawn"
        )
    resource_bound = (launch_result.get("plan") or {}).get("resource_bound")

    record.data["terminal"] = dict(terminal)
    record.data["resource_bound"] = resource_bound
    record.data["spawned_at"] = _utcstamp(now or datetime.now(timezone.utc))
    # ce-ops#26: stamp the seat's lifecycle events surface (additive, value-free
    # path ref) so the cockpit/Monitor join the events.jsonl to this run by run_id.
    events_ref = launch_result.get("events_ref")
    if isinstance(events_ref, str) and events_ref:
        record.data["events_ref"] = events_ref
    if bridge.harness == CODEX_BRIDGE_HARNESS:
        codex_bypass_mode = (launch_result.get("plan") or {}).get("codex_bypass_mode")
        if isinstance(codex_bypass_mode, str) and codex_bypass_mode:
            record.data["codex_bypass_mode"] = codex_bypass_mode
    _write_record(record)

    return SpawnResult(
        run_id=record.run_id,
        terminal=dict(terminal),
        resource_bound=resource_bound,
        launch_result=launch_result,
    )


#: The pointer-only mandate line seeded into the pane. The brief itself is the
#: pointer target — markers / the brief body NEVER appear in seed text (a positional
#: prompt leaks into ``ps``; the monitor lesson). Kept literal via ``send-keys -l``.
def _seed_line(record: DispatchRecord) -> str:
    return f"Read {record.brief_ref} and execute under it."


def _pane_foreground_command(
    pane: str, runner: Callable[..., Any]
) -> str:
    """Read the pane's foreground command via ``tmux display-message`` (subprocess seam)."""
    res = runner(
        ["tmux", "display-message", "-p", "-t", pane, "#{pane_current_command}"],
        capture_output=True,
        text=True,
    )
    return (getattr(res, "stdout", "") or "").strip()


def _pane_pid(pane: str, runner: Callable[..., Any]) -> str:
    """Read the pane's root process pid via ``tmux display-message`` (subprocess seam)."""
    res = runner(
        ["tmux", "display-message", "-p", "-t", pane, "#{pane_pid}"],
        capture_output=True,
        text=True,
    )
    return (getattr(res, "stdout", "") or "").strip()


def _pane_has_nonshell_child(pane: str, runner: Callable[..., Any]) -> bool:
    """Report whether the pane's root process has a non-shell child process.

    The #211 seat-sentinel wrapper runs the harness as a CHILD of ``sh`` (so the wrapper
    can write the ``exited`` event after the harness returns). With that shape the pane
    FOREGROUND stays a shell forever even though the REPL is healthy exactly one level
    down — ``_pane_foreground_command`` alone would poll to the readiness timeout. So when
    the foreground is still a shell we additionally read the pane's pid and inspect its
    direct children: the wrapper's harness child is non-shell (``claude`` / ``node``).

    Reached through the SAME injectable ``runner`` seam (CI exercises a fake; zero live
    subprocess). Fail-closed: an empty/failed ``ps`` yields no child → not-ready → the
    caller keeps polling and ultimately conserves the pane on timeout.
    """
    pid = _pane_pid(pane, runner)
    if not pid:
        return False
    res = runner(
        ["ps", "-o", "comm=", "--ppid", pid],
        capture_output=True,
        text=True,
    )
    out = getattr(res, "stdout", "") or ""
    for line in out.splitlines():
        comm = line.strip()
        if comm and comm not in _READINESS_SHELL_COMMANDS:
            return True
    return False


def _await_pane_ready(
    pane: str,
    *,
    runner: Callable[..., Any],
    timeout_s: float,
    interval_s: float,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> bool:
    """Poll the pane until the harness REPL owns it (foreground left the shell, OR a
    non-shell child is up under the seat-sentinel wrapper), bounded.

    Returns ``True`` when ready, ``False`` on timeout. The pane is never killed — a
    timeout is conserved for autopsy by the caller.
    """
    deadline = clock() + timeout_s
    while True:
        cmd = _pane_foreground_command(pane, runner)
        if cmd and cmd not in _READINESS_SHELL_COMMANDS:
            return True
        # Foreground is still a shell: under the #211 wrapper the harness lives one level
        # down as a non-shell child, so probe the pane pid's child tree before deciding.
        if _pane_has_nonshell_child(pane, runner):
            return True
        if clock() >= deadline:
            return False
        sleep(interval_s)


def _seed_line_pending(
    pane: str, line: str, runner: Callable[..., Any]
) -> bool:
    """Report whether the seed LINE is still sitting unsubmitted in the input-box prompt tail.

    Captures the pane (``tmux capture-pane -p``) and scans its bottom region (the input box
    lives at the prompt tail): if the literal line is still there, the Enter was swallowed
    (the S8 submit-lost signature); a submitted line clears the box and falls out of the tail.
    """
    res = runner(
        ["tmux", "capture-pane", "-p", "-t", pane], capture_output=True, text=True
    )
    content = getattr(res, "stdout", "") or ""
    needle = line.strip()
    if not needle:
        return False
    tail = content.splitlines()[-_SEED_PROMPT_TAIL_LINES:]
    return any(needle in row for row in tail)


def seed_brief(
    record: DispatchRecord,
    *,
    runner: Callable[..., Any] = subprocess.run,
    readiness_timeout_s: float = DEFAULT_READINESS_TIMEOUT_S,
    poll_interval_s: float = READINESS_POLL_INTERVAL_S,
    submit_settle_s: float = SEED_SUBMIT_SETTLE_S,
    submit_max_attempts: int = SEED_SUBMIT_MAX_ATTEMPTS,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> None:
    """Seed the spawned pane with the pointer-only mandate line.

    First POLLS the pane until the harness REPL owns the foreground (G1-followup):
    the pointer line typed before the REPL is up is swallowed by the still-init shell
    and silently lost. On readiness timeout the spawn is fail-closed
    (:func:`mark_spawn_failed` + :class:`SpawnRefused`) with the pane CONSERVED for
    autopsy. Then ``tmux send-keys -t <pane_id> -l <line>`` (the proven controller
    tmux-seed method), CHECKING the rc and failing closed on non-zero.

    The Enter is GUARDED (S8 live-dogfood defect): a ``>=1s`` settle precedes the first
    Enter (the proven manual cadence), and after each Enter we POLL that the line LEFT the
    input box — because the harness can swallow an Enter (the rc is 0; tmux delivered the
    key but the submit was lost). While the line is still pending we re-send Enter, bounded
    (:data:`SEED_SUBMIT_MAX_ATTEMPTS`), then fail closed (pane CONSERVED). ``tmux`` is
    reached as a **subprocess** — no ``tmux_adapter`` import (the v1 boundary). Refuses if
    the record carries no pane (spawn must precede seed).
    """
    pane = record.pane_id
    if not pane:
        raise SpawnRefused(
            f"cannot seed brief for run {record.run_id!r}: no pane_id "
            "(spawn_seat must run first)"
        )
    if not _await_pane_ready(
        pane,
        runner=runner,
        timeout_s=readiness_timeout_s,
        interval_s=poll_interval_s,
        clock=clock,
        sleep=sleep,
    ):
        reason = (
            f"seed readiness poll timed out after {readiness_timeout_s:.0f}s: pane "
            f"{pane} foreground never left the shell (harness REPL not up)"
        )
        mark_spawn_failed(record, reason, now=now)
        raise SpawnRefused(f"{reason} (for run {record.run_id!r})")

    line = _seed_line(record)
    literal = runner(
        ["tmux", "send-keys", "-t", pane, "-l", line], capture_output=True, text=True
    )
    if getattr(literal, "returncode", 1) != 0:
        reason = (getattr(literal, "stderr", "") or "").strip() or "(no stderr)"
        msg = f"tmux send-keys (literal seed line) failed: {reason}"
        mark_spawn_failed(record, msg, now=now)
        raise SpawnRefused(f"{msg} (for run {record.run_id!r})")

    # Settle before the FIRST Enter — the proven manual cadence: an Enter sent on the
    # heels of the literal line is swallowed by the harness input box (S8 defect).
    sleep(submit_settle_s)
    submitted = False
    for _attempt in range(submit_max_attempts):
        enter = runner(
            ["tmux", "send-keys", "-t", pane, "Enter"], capture_output=True, text=True
        )
        if getattr(enter, "returncode", 1) != 0:
            reason = (getattr(enter, "stderr", "") or "").strip() or "(no stderr)"
            msg = f"tmux send-keys (Enter) failed: {reason}"
            mark_spawn_failed(record, msg, now=now)
            raise SpawnRefused(f"{msg} (for run {record.run_id!r})")
        # Give the submit a moment to register, then confirm the line LEFT the input box.
        sleep(poll_interval_s)
        if not _seed_line_pending(pane, line, runner):
            submitted = True
            break
    if not submitted:
        msg = (
            f"seed line never left the input box after {submit_max_attempts} Enter "
            f"attempt(s) on pane {pane}: tmux delivered the key (rc 0) but the harness "
            "swallowed the submit"
        )
        mark_spawn_failed(record, msg, now=now)
        raise SpawnRefused(f"{msg} (for run {record.run_id!r})")


def _codex_sessions_root(sessions_root: Path | str | None = None) -> Path:
    if sessions_root is not None:
        return Path(sessions_root)
    return Path.home() / ".codex" / "sessions"


def snapshot_codex_transcripts(sessions_root: Path | str | None = None) -> set[Path]:
    """Snapshot existing Codex JSONL transcripts before spawn."""
    root = _codex_sessions_root(sessions_root)
    return {p.resolve() for p in root.glob("**/*.jsonl") if p.is_file()}


def _read_codex_session_meta(path: Path) -> dict[str, Any] | None:
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        record = json.loads(first)
    except (OSError, IndexError, json.JSONDecodeError):
        return None
    if record.get("type") != "session_meta":
        return None
    payload = record.get("payload")
    return payload if isinstance(payload, dict) else None


def _same_cwd(left: Any, right: Path) -> bool:
    if not left:
        return False
    try:
        return Path(str(left)).expanduser().resolve() == right.resolve()
    except OSError:
        return str(left) == str(right)


def _find_codex_transcripts(
    *,
    sessions_root: Path | str | None = None,
    session_id: str | None = None,
    cwd: Path | str | None = None,
    exclude: set[Path] | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    root = _codex_sessions_root(sessions_root)
    excluded = {p.resolve() for p in (exclude or set())}
    cwd_path = Path(cwd).resolve() if cwd is not None else None
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("**/*.jsonl")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in excluded:
            continue
        meta = _read_codex_session_meta(path)
        if not meta:
            continue
        if session_id and str(meta.get("id") or "") != session_id:
            continue
        if cwd_path is not None and not _same_cwd(meta.get("cwd"), cwd_path):
            continue
        matches.append((resolved, meta))
    return matches


def stamp_codex_transcript_locator(
    record: DispatchRecord,
    *,
    before: set[Path],
    launched_cwd: Path | str,
    sessions_root: Path | str | None = None,
    timeout_s: float = DEFAULT_READINESS_TIMEOUT_S,
    poll_interval_s: float = READINESS_POLL_INTERVAL_S,
    settle_s: float = CODEX_TRANSCRIPT_SETTLE_S,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> DispatchRecord:
    """Stamp the Codex session id + transcript path after the pointer seed.

    The lookup is exact and bounded: new JSONL files only, first record must be
    ``session_meta``, and ``payload.cwd`` must equal the launched worktree cwd.
    Zero or ambiguous matches are a failed spawn, not a live dispatch.

    A bounded ``settle_s`` window (ce-ops#56) precedes the FIRST poll so a cold/idle
    codex has written its session file by the time we look; it is capped at the deadline
    (spent from the same ``timeout_s`` budget) and uses the existing poll machinery.
    """
    if record.data.get("harness") != CODEX_BRIDGE_HARNESS:
        return record
    deadline = clock() + timeout_s
    # ce-ops#56: settle before the first poll — bounded by the remaining budget so the
    # total wait never exceeds the deadline (a no-op when settle_s <= 0).
    settle = min(max(settle_s, 0.0), max(deadline - clock(), 0.0))
    if settle:
        sleep(settle)
    while True:
        hits = _find_codex_transcripts(
            sessions_root=sessions_root,
            cwd=Path(launched_cwd),
            exclude=before,
        )
        if len(hits) == 1:
            path, meta = hits[0]
            session_id = str(meta.get("id") or "")
            if not session_id:
                break
            record.data["harness_session_id"] = session_id
            record.data["transcript_ref"] = str(path)
            _write_record(record)
            return record
        if len(hits) > 1:
            reason = (
                f"Codex transcript locator ambiguous: {len(hits)} new session_meta JSONL "
                f"files matched cwd {Path(launched_cwd).resolve()}"
            )
            mark_spawn_failed(record, reason, now=now)
            raise SpawnRefused(f"{reason} (for run {record.run_id!r})")
        if clock() >= deadline:
            break
        sleep(poll_interval_s)
    reason = (
        f"Codex transcript locator missing after {timeout_s:.0f}s: no new session_meta "
        f"JSONL matched cwd {Path(launched_cwd).resolve()}"
    )
    mark_spawn_failed(record, reason, now=now)
    raise SpawnRefused(f"{reason} (for run {record.run_id!r})")


# ===========================================================================
# v3.1-G2b — the reviewer-venue leg (v3→v1 subprocess + DATA, the G1 pattern)
# ===========================================================================
# A distinct CE-governed reviewer venue is provisioned the SAME way the author
# seat is — by re-entering the v1/shared PRODUCT CONTRACTS as subprocesses
# (`creator-engine-validator pco-allocate`, `ce lane launch --json`), never as a
# module edge (the bridge still imports NO v1 module). The venue's authority is a
# `reviewer_authority_envelope` file (one `pr_review` mechanic on one PR), and the
# review SUBMISSION (`gh pr review`) stays the venue's OWN governed act under the
# live Ring-1 hook — v3 only RECORDS the venue (this dispatch) and later folds its
# outcome via the unchanged `cev3 collect ... --outcome review_submitted`.

#: The tmux window the reviewer venue occupies.
REVIEW_WINDOW = "review"

#: The argv prefix that sources a seat env file into a child process, then execs the
#: command. A LOCAL copy of ``lane_runtime._SEAT_ENV_WRAP_SCRIPT`` — the bridge imports
#: NO v1 module (``lane_runtime`` is v1-classified), and the ce-ops#58 identity guard
#: MUST source the seat-env IDENTICALLY to how ``ce lane launch --seat-env-file`` will,
#: so the ``gh`` probe sees the exact identity the review submission will run under. A
#: drift-guard test (``test_lane_runtime_reviewer_venue.py``) keeps the two byte-identical.
_SEAT_ENV_WRAP_SCRIPT = 'set -a; . "$1"; set +a; shift; exec "$@"'


def _envelope_actor(envelope_ref: str | Path) -> str:
    """Read the host-bound reviewer login (``actor``) from a reviewer-authority envelope."""
    doc = yaml.safe_load(Path(envelope_ref).read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return ""
    return str((doc.get("reviewer_authority_envelope") or {}).get("actor") or "")


def _resolve_validator_exe(validator_exe: str | None) -> str:
    """Resolve the shared ``creator-engine-validator`` console_script; refuse if absent."""
    if validator_exe:
        return validator_exe
    candidate = Path(sys.executable).parent / "creator-engine-validator"
    if candidate.exists():
        return str(candidate)
    found = shutil.which("creator-engine-validator")
    if found:
        return found
    raise SpawnRefused(
        "cannot resolve the `creator-engine-validator` entry point (not next to the "
        "interpreter, not on PATH); refusing to provision a reviewer venue"
    )


def _resolve_repo_root(
    ledger_root: Path | str,
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> str | None:
    """Resolve the git worktree root enclosing ``ledger_root`` (ce-ops#89).

    pco-allocate needs a real ``--repo-root`` to run ``git worktree add`` from; the
    bridge runs pco with its cwd set to the out-of-repo venue zone (PCO-031), so the
    repo context must be passed explicitly. The active-work-ledger lives inside the
    controller's (secondary) worktree, so its enclosing git toplevel is exactly the
    non-root repo_root pco needs. Returns the absolute toplevel, or ``None`` when
    ``ledger_root`` is not inside a git worktree (caller fails closed).
    """
    probe = runner(
        ["git", "-C", str(ledger_root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if getattr(probe, "returncode", 1) != 0:
        return None
    toplevel = (getattr(probe, "stdout", "") or "").strip()
    return toplevel or None


def compose_reviewer_envelope(
    dispatch_dir: Path | str,
    *,
    scope_id: str,
    pr_number: int,
    head_sha: str,
    actor: str,
    ratified_prompt_sha: str,
    emitting_role: str = "controller",
    operating_mode: str = "strict",
    now: datetime | None = None,
) -> str:
    """Write a schema-valid ``reviewer_authority_envelope`` YAML under the review-dispatch dir.

    The envelope authorizes EXACTLY one ``pr_review`` mechanic on EXACTLY one PR. ``actor`` is the
    host-bound reviewer LOGIN passed in AS DATA (a login by schema design — never a token);
    ``ratified_prompt_sha`` binds the grant to the SAME ratified Scope the author ran under (the
    author dispatch's ``scope_ratification.ratified_scope_sha``). The envelope FILE carries the
    login (its schema requires it; the Ring-1 hook records it); the dispatch RECORD carries only the
    envelope path ref. Returns the envelope file path.
    """
    stamp = _utcstamp(now or datetime.now(timezone.utc))
    envelope_id = f"rva-rev-{scope_id}-{stamp.lower()}"
    recorded_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    envelope = {
        "reviewer_authority_envelope": {
            "envelope_id": envelope_id,
            "mechanic": "pr_review",
            "pr_number": int(pr_number),
            "head_sha": str(head_sha),
            "actor": str(actor),
            "ratified_prompt_sha": str(ratified_prompt_sha),
            "emitting_role": emitting_role,
            "operating_mode": operating_mode,
            "recorded_at": recorded_at,
        }
    }
    path = Path(dispatch_dir) / "reviewer-authority-envelope.yaml"
    path.write_text(_yaml_bytes(envelope), encoding="utf-8")
    return str(path)


def _render_reviewer_brief(
    *,
    review_run_id: str,
    scope_id: str,
    author_run_id: str,
    pr_number: int,
    head_sha: str,
    envelope_ref: str,
    root: Path,
) -> str:
    """The reviewer-venue mandate brief: the PR pointer, Done-when grading, the mechanic, handoff."""
    scope_ref = root / "scopes" / f"{scope_id}.scope.yaml"
    review_evidence_ref = root / "runs" / f"{review_run_id}.runtime-evidence.yaml"
    return (
        f"# ◆ CE reviewer-venue mandate — run {review_run_id}\n\n"
        f"You are a distinct, governed CE reviewer venue. You review PR #{pr_number} "
        f"(head `{head_sha}`) authored by run `{author_run_id}` for Scope `{scope_id}`. "
        f"The Ring-1 hook-pack + your reviewer-authority envelope are your enforced boundary.\n\n"
        f"## What to grade\n"
        f"- **Done-when** — read the ratified Scope artifact `{scope_ref}` and grade the PR "
        f"against its acceptance criteria, with evidence (the diff, the CI, the manifest), not vibes.\n\n"
        f"## Your authority (one mechanic, one PR)\n"
        f"- Envelope: `{envelope_ref}` — it authorizes EXACTLY `pr_review` on PR #{pr_number}.\n"
        f"- Submit your review with `gh pr review {pr_number}` (the Ring-1 hook honors the envelope "
        f"by mechanic + PR number). You CANNOT push or merge — a governed venue is push-denied.\n\n"
        f"## Evidence handoff (for `cev3 collect`)\n"
        f"When you finish, your venue run is folded by:\n"
        f"`cev3 collect {scope_id} --run {review_run_id} "
        f"--outcome review_submitted --pr {pr_number}`\n"
        f"Your harness transcript is resolved automatically from the session id stamped "
        f"at spawn — do NOT pass `--transcript`.\n"
        f"The conserved evidence chain lands at `{review_evidence_ref}`.\n"
    )


def materialize_review_dispatch(
    author_dispatch: dict[str, Any],
    root: Path | str,
    *,
    reviewer_actor: str,
    pr_number: int,
    head_sha: str,
    emitting_role: str = "controller",
    unattended: bool = True,
    now: datetime | None = None,
    harness_session_id: str | None = None,
) -> DispatchRecord:
    """Materialize a ``role: reviewer`` dispatch (envelope + brief + ``review_of`` block).

    Reads the AUTHOR dispatch (scope_id, the author run_id, the value-free ratification + mutation
    class) AS DATA, mints a review run_id ``rev-<scope_id>-<lowercased utcstamp>`` (lowercased so
    the id satisfies the active-work-ledger lane pattern; clamped + hash-suffixed for long scope_ids
    via :func:`_derive_review_run_id` so the derived lease id stays within the worktree-lease length
    bound when fed to ``pco-allocate`` — ce-ops#89/PCO-020), composes a
    schema-valid reviewer-authority envelope (bound to the author's ``ratified_scope_sha``), writes
    the reviewer mandate brief, and persists the review ``dispatch.yaml`` with ``role: reviewer`` +
    a value-free ``review_of`` block (author run_id, PR number, envelope path ref). No spawn happens
    here; :func:`spawn_review_venue` stamps the launch evidence.
    """
    # D3 (F5): absolutize the state root so the envelope_ref + brief_ref + seeded line
    # resolve from the venue worktree cwd (the in-venue Ring-1 hook denied the relative
    # ref correctly, leaving the venue stillborn — G2.007.2).
    root_path = Path(root).resolve()
    scope_id = str(author_dispatch["scope_id"])
    author_run_id = str(author_dispatch["run_id"])
    stamp = _utcstamp(now or datetime.now(timezone.utc))
    # ce-ops#89: clamp the run_id so the pco-derived lease id stays schema-valid
    # (<=64) for long scope_ids while remaining unique (see _derive_review_run_id).
    review_run_id = _derive_review_run_id(scope_id, stamp)
    dispatch_dir = root_path / DISPATCHES_SUBDIR / review_run_id
    dispatch_dir.mkdir(parents=True, exist_ok=True)
    # D6 (F9): mint the harness session id at materialize (pre-spawn) for the venue too.
    seat_harness_session_id = harness_session_id or str(uuid.uuid4())

    ratified_scope_sha = str(
        (author_dispatch.get("scope_ratification") or {}).get("ratified_scope_sha") or ""
    )
    envelope_ref = compose_reviewer_envelope(
        dispatch_dir,
        scope_id=scope_id,
        pr_number=pr_number,
        head_sha=head_sha,
        actor=reviewer_actor,
        ratified_prompt_sha=ratified_scope_sha,
        emitting_role=emitting_role,
        now=now,
    )
    brief_ref = str(dispatch_dir / "brief.md")
    (dispatch_dir / "brief.md").write_text(
        _render_reviewer_brief(
            review_run_id=review_run_id,
            scope_id=scope_id,
            author_run_id=author_run_id,
            pr_number=pr_number,
            head_sha=head_sha,
            envelope_ref=envelope_ref,
            root=root_path,
        ),
        encoding="utf-8",
    )

    record: dict[str, Any] = {
        "kind": _KIND,
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "scope_id": scope_id,
        "run_id": review_run_id,
        "mutation_class": str(author_dispatch.get("mutation_class", "none")),
        "scope_ratification": dict(author_dispatch.get("scope_ratification") or {}),
        "harness": BRIDGE_HARNESS,
        "harness_session_id": seat_harness_session_id,
        "unattended": bool(unattended),
        "session": review_run_id,
        "window": REVIEW_WINDOW,
        "brief_ref": brief_ref,
        # v3.1-G2b additive fields — value-free.
        "role": "reviewer",
        "review_of": {
            "author_run_id": author_run_id,
            "pr_number": int(pr_number),
            "envelope_ref": envelope_ref,
        },
        # launch evidence — populated post-spawn (value-free shape).
        "terminal": None,
        "resource_bound": None,
        "spawned_at": None,
    }
    rec = DispatchRecord(
        run_id=review_run_id,
        scope_id=scope_id,
        dispatch_dir=dispatch_dir,
        data=record,
        runtime_policy_ref="",
        mcp_config_ref="",
        brief_ref=brief_ref,
    )
    _write_record(rec)
    return rec


def spawn_review_venue(
    record: DispatchRecord,
    *,
    controller_id: str,
    venue_root: Path | str,
    ledger_root: Path | str,
    seat_env_file: Path | str | None = None,
    runner: Callable[..., Any] = subprocess.run,
    validator_exe: str | None = None,
    ce_exe: str | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> SpawnResult:
    """Provision + launch the reviewer venue via the v1/shared product contracts (subprocess + DATA).

    The fail-closed chain, each leg surfacing stderr and stamping :func:`mark_spawn_failed` on ANY
    refusal (never a half-venue projecting live):

    0. PATH preflight (G1-followup): ``tmux`` + the harness binary must resolve on the bridge PATH
       before any side effect — a miss is a fail-closed refusal.
    1. ``creator-engine-validator pco-allocate`` (cwd = the out-of-root venue zone — pco refuses
       from the repo root) provisions the worktree + Active-Work claim, with NO tracked-file write
       authority (``--envelope-ref none --no-write-authority``); the venue's authority is the
       reviewer-authority envelope, not a pco write envelope.
    2. ``ce lane launch --role reviewer --lane-kind review --reviewer-authority-ref <envelope>
       --json`` validates + injects the envelope on a DISTINCT reviewer venue and returns the Pane
       Registry record (the G2b ``--json`` seam); its ``terminal`` is stamped into the dispatch.
       When the seat is unattended (D1) the launch carries
       ``--claude-arg=--dangerously-skip-permissions`` (mirror of the author seat — CC-D-6 on the
       venue worktree's committed hook-pack stays the gate, zero new authority); when a
       ``seat_env_file`` is given (D2/F4) the launch carries ``--seat-env-file <path>`` so the
       reviewer credential is sourced into the venue claude's process via an explicit exec-wrap —
       the SECRET never transits argv/tmux/the records, only the path ref is recorded.
    3. :func:`seed_brief` — the EXISTING seed seam (so the ce-ops#16 readiness-poll/PATH fix lands
       in exactly one place), pointer-only line. The reviewer credential is NOT seeded as text and
       is NOT inherited as ambient tmux-server env (the live refutation, F4) — it arrives ONLY via
       the D2 ``--seat-env-file`` exec-wrap above.
    """
    review_of = record.data.get("review_of") or {}
    envelope_ref = str(review_of.get("envelope_ref") or "")
    if not envelope_ref:
        raise SpawnRefused(
            f"review dispatch {record.run_id!r} carries no envelope_ref; refusing to launch"
        )
    _preflight_spawn_binaries(record, now=now)
    venue_root_path = Path(venue_root)
    worktree_path = venue_root_path / record.run_id
    brief_sha = hashlib.sha256(Path(record.brief_ref).read_bytes()).hexdigest()

    # 1) pco-allocate — provision the worktree + claim.
    #
    # ce-ops#89: pco-allocate runs ``git worktree add`` from its ``repo_root``, which
    # defaults to the process cwd (cli.py:578). The bridge runs pco with cwd = the
    # out-of-repo venue zone (so PCO-031's root-checkout refusal does not trip) — but
    # that zone is NOT a git repo, so without an explicit ``--repo-root`` the worktree
    # add exits 128 and the venue never provisions. Resolve a REAL repo context from
    # the ledger-root's enclosing git worktree and pass it explicitly. PCO-031 stays
    # enforced inside pco-allocate (it refuses if that resolves to the root checkout),
    # so a secondary worktree ledger-root yields a valid, non-root repo_root.
    validator = _resolve_validator_exe(validator_exe)
    repo_root = _resolve_repo_root(ledger_root, runner=runner)
    if not repo_root:
        mark_spawn_failed(
            record,
            "pco-allocate repo-root unresolved: --ledger-root "
            f"{str(ledger_root)!r} is not inside a git worktree",
            now=now,
        )
        raise SpawnRefused(
            f"reviewer-venue pco-allocate cannot resolve a repo-root for run "
            f"{record.run_id!r}: ledger-root {str(ledger_root)!r} is not inside a git worktree"
        )
    pco_argv = [
        validator, "pco-allocate",
        "--lane-id", record.run_id,
        "--worktree-path", str(worktree_path),
        "--branch", f"review/{record.run_id}",
        "--envelope-ref", "none",
        "--no-write-authority",
        "--controller-id", controller_id,
        "--ledger-root", str(ledger_root),
        "--repo-root", repo_root,
        "--pane-label", "reviewer",
    ]
    pco = runner(pco_argv, capture_output=True, text=True, cwd=str(venue_root_path))
    if getattr(pco, "returncode", 1) != 0:
        reason = (getattr(pco, "stderr", "") or "").strip() or "(no stderr)"
        mark_spawn_failed(record, f"pco-allocate refused: {reason}", now=now)
        raise SpawnRefused(
            f"reviewer-venue pco-allocate refused for run {record.run_id!r}: {reason}"
        )

    # 2) ce lane launch --role reviewer --json — bind the envelope, capture the pane record.
    exe = ce_exe or _resolve_ce_exe(None)
    launch_argv = [
        exe, "lane", "launch",
        "--controller-id", controller_id,
        "--lane-id", record.run_id,
        "--role", "reviewer",
        "--lane-kind", "review",
        "--reviewer-authority-ref", envelope_ref,
        "--prompt", record.brief_ref,
        "--prompt-sha", brief_sha,
        "--repo-root", str(worktree_path),
        # cwd the venue pane IN its allocated worktree — lane_runtime sets cwd only from
        # --worktree-path; without it the relative --mcp-config fails under --strict-mcp-config
        # and the venue claude dies at birth while launch reports success.
        "--worktree-path", str(worktree_path),
        "--ledger-root", str(ledger_root),
        "--command", "claude",
        "--json",
    ]
    if seat_env_file is not None:
        # D2 (F4): the reviewer credential is sourced into the venue claude's process
        # via the lane-runtime exec-wrap — the file PATH transits argv, never the value.
        launch_argv.extend(["--seat-env-file", str(seat_env_file)])
    if record.unattended:
        # D1 (F3): mirror the author-seat mechanism (spawn_seat) — CC-D-6 on the venue
        # worktree's committed hook-pack stays the gate; zero new authority.
        launch_argv.append("--claude-arg=--dangerously-skip-permissions")
    if record.harness_session_id:
        # D6 (F9): pin the venue transcript to a known key for collect.
        launch_argv.append(f"--claude-arg=--session-id={record.harness_session_id}")
    launch = runner(launch_argv, capture_output=True, text=True)
    if getattr(launch, "returncode", 1) != 0:
        reason = (getattr(launch, "stderr", "") or "").strip() or "(no stderr)"
        mark_spawn_failed(record, f"ce lane launch refused: {reason}", now=now)
        raise SpawnRefused(
            f"reviewer-venue ce lane launch refused for run {record.run_id!r}: {reason}"
        )
    try:
        launch_result = json.loads(getattr(launch, "stdout", "") or "")
        terminal = (launch_result.get("record") or {}).get("terminal") or {}
    except (json.JSONDecodeError, TypeError, AttributeError) as exc:
        mark_spawn_failed(record, f"ce lane launch --json unparsable: {exc}", now=now)
        raise SpawnRefused(
            f"reviewer-venue ce lane launch --json produced unparsable output for run "
            f"{record.run_id!r}: {exc}"
        ) from exc
    if not terminal.get("pane_id"):
        mark_spawn_failed(record, "ce lane launch returned no terminal pane", now=now)
        raise SpawnRefused(
            f"reviewer-venue ce lane launch returned no terminal pane for run "
            f"{record.run_id!r}; refusing a half-venue"
        )

    record.data["terminal"] = dict(terminal)
    if seat_env_file is not None:
        # value-free: the PATH ref only (the credential value never lands here).
        record.data["seat_env_file_ref"] = str(seat_env_file)
    record.data["spawned_at"] = _utcstamp(now or datetime.now(timezone.utc))
    _write_record(record)

    # 2.5) Fail-closed gh-identity guard (ce-ops#58): the venue's EFFECTIVE `gh` login
    # MUST equal the envelope `actor` before the venue may seed (and thus review). The
    # envelope records the actor as DATA but never checked it; with GH_TOKEN/GITHUB_TOKEN
    # unset, the venue's `gh` falls back to ambient auth — the #218 wrong-login leak. We
    # probe `gh api user --jq .login` through the SAME `runner` seam (CI fakes it), sourcing
    # the SAME seat-env the review will (so the probe sees the review's identity); on
    # mismatch or probe error we fail closed — pane CONSERVED for autopsy, claim released,
    # venue NEVER seeds.
    expected_actor = _envelope_actor(envelope_ref)
    if not expected_actor:
        reason = f"reviewer envelope {envelope_ref!r} carries no actor; refusing to seed"
        mark_spawn_failed(record, reason, now=now)
        raise SpawnRefused(f"{reason} (for run {record.run_id!r})")
    gh_argv = ["gh", "api", "user", "--jq", ".login"]
    if seat_env_file is not None:
        # source the credential the SAME way lane_runtime's exec-wrap does (value never
        # transits argv — only the file PATH does), so `gh` IS the envelope actor.
        gh_argv = ["sh", "-c", _SEAT_ENV_WRAP_SCRIPT, "ce-seat-env", str(seat_env_file), *gh_argv]
    identity = runner(gh_argv, capture_output=True, text=True)
    if getattr(identity, "returncode", 1) != 0:
        reason = (getattr(identity, "stderr", "") or "").strip() or "(no stderr)"
        mark_spawn_failed(record, f"reviewer gh-identity probe failed: {reason}", now=now)
        raise SpawnRefused(
            f"reviewer-venue gh-identity probe failed for run {record.run_id!r}: {reason}"
        )
    effective_login = (getattr(identity, "stdout", "") or "").strip()
    if effective_login != expected_actor:
        reason = (
            f"reviewer venue gh-login != envelope actor; refusing to seed "
            "(the #218 wrong-identity leak)"
        )
        mark_spawn_failed(record, reason, now=now)
        raise SpawnRefused(f"{reason} (for run {record.run_id!r})")

    # 3) seed the venue brief through the SAME seam (ce-ops#16 fix lands once).
    seed_brief(record, runner=runner, clock=clock, sleep=sleep, now=now)

    return SpawnResult(
        run_id=record.run_id,
        terminal=dict(terminal),
        resource_bound=None,
        launch_result=launch_result,
    )
