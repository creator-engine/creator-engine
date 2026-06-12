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

Scope (v3.1-G1): the **claude** harness only. A codex drive-spawn (codex
launch-spec + bounded wrap + bypass-mode as a spec field) is the named follow-up
gate G1-codex; ``cev3 drive --spawn`` refuses ``harness != claude``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from . import coordination

#: The harness this gate bridges. Non-claude drive-spawn is the named follow-up
#: (G1-codex); the bridge refuses anything else (defect-c declared out).
BRIDGE_HARNESS = "claude"

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


class SeatBridgeError(Exception):
    """Base class for bridge refusals (fail-closed; never a silent half-spawn)."""


class SpawnRefused(SeatBridgeError):
    """The v1 launch leg refused or returned an unusable result."""


class HarnessNotSupported(SeatBridgeError):
    """A non-claude harness was requested — G1-codex follow-up (defect-c)."""


def _utcstamp(now: datetime) -> str:
    """Compact, filename/tmux-safe UTC stamp (no ``:`` / ``.``)."""
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    return (
        f"# ◆ CE seat mandate — run {run_id}\n\n"
        f"You are a governed, OS-bounded CE seat spawned from a ratified Scope by "
        f"`cev3 drive --spawn`. Execute the Scope below; the Ring-1 hook-pack is your "
        f"enforced boundary.\n\n"
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
        f"`cev3 collect {scope_id} --run {run_id} --transcript <your harness .jsonl> "
        f"--outcome <outcome> [--pr <n>]`\n"
        f"The conserved evidence chain lands at `{evidence_ref}`.\n\n"
        f"## Terminal outcome vocabulary (closed)\n"
        f"{vocab}\n"
    )


def materialize_dispatch(
    plan: coordination.DispatchPlan,
    root: Path | str,
    *,
    unattended: bool = True,
    now: datetime | None = None,
    session: str | None = None,
    window: str = "drive",
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
    root_path = Path(root)
    stamp = _utcstamp(now or datetime.now(timezone.utc))
    run_id = f"run-{plan.scope_id}-{stamp}"
    dispatch_dir = root_path / DISPATCHES_SUBDIR / run_id
    dispatch_dir.mkdir(parents=True, exist_ok=True)

    seat_session = session or run_id
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
        "harness": BRIDGE_HARNESS,
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
    exe = _resolve_ce_exe(ce_exe)
    argv = [
        exe,
        "launch",
        "--session",
        record.session,
        "--window",
        record.window,
        "--json",
        "--mcp-config",
        record.mcp_config_ref,
        "--runtime-policy",
        record.runtime_policy_ref,
    ]
    if record.unattended:
        # The governance for this already exists (CC-D-6): the flag is honored
        # ONLY when the committed hook-pack is confirmed — the v1 leg fails closed
        # otherwise. For a governed seat the Ring-1 hook-pack is the boundary;
        # approval modals are not load-bearing and hang unattended seats.
        argv.append("--claude-arg=--dangerously-skip-permissions")

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


def seed_brief(
    record: DispatchRecord,
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> None:
    """Seed the spawned pane with the pointer-only mandate line.

    Uses ``tmux send-keys -t <pane_id> -l <line>`` then ``send-keys … Enter`` (the
    proven controller tmux-seed method). ``tmux`` is reached as a **subprocess** —
    no ``tmux_adapter`` import (the v1 boundary). Refuses if the record carries no
    pane (spawn must precede seed).
    """
    pane = record.pane_id
    if not pane:
        raise SpawnRefused(
            f"cannot seed brief for run {record.run_id!r}: no pane_id "
            "(spawn_seat must run first)"
        )
    line = _seed_line(record)
    runner(["tmux", "send-keys", "-t", pane, "-l", line], capture_output=True, text=True)
    runner(["tmux", "send-keys", "-t", pane, "Enter"], capture_output=True, text=True)


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
        f"`cev3 collect {scope_id} --run {review_run_id} --transcript <your harness .jsonl> "
        f"--outcome review_submitted --pr {pr_number}`\n"
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
    now: datetime | None = None,
) -> DispatchRecord:
    """Materialize a ``role: reviewer`` dispatch (envelope + brief + ``review_of`` block).

    Reads the AUTHOR dispatch (scope_id, the author run_id, the value-free ratification + mutation
    class) AS DATA, mints a review run_id ``rev-<scope_id>-<lowercased utcstamp>`` (lowercased so
    the id satisfies the active-work-ledger lane pattern and the derived lease id stays within the
    worktree-lease length bound when fed to ``pco-allocate``), composes a
    schema-valid reviewer-authority envelope (bound to the author's ``ratified_scope_sha``), writes
    the reviewer mandate brief, and persists the review ``dispatch.yaml`` with ``role: reviewer`` +
    a value-free ``review_of`` block (author run_id, PR number, envelope path ref). No spawn happens
    here; :func:`spawn_review_venue` stamps the launch evidence.
    """
    root_path = Path(root)
    scope_id = str(author_dispatch["scope_id"])
    author_run_id = str(author_dispatch["run_id"])
    stamp = _utcstamp(now or datetime.now(timezone.utc))
    review_run_id = f"rev-{scope_id}-{stamp.lower()}"
    dispatch_dir = root_path / DISPATCHES_SUBDIR / review_run_id
    dispatch_dir.mkdir(parents=True, exist_ok=True)

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
        "unattended": True,
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
    runner: Callable[..., Any] = subprocess.run,
    validator_exe: str | None = None,
    ce_exe: str | None = None,
    now: datetime | None = None,
) -> SpawnResult:
    """Provision + launch the reviewer venue via the v1/shared product contracts (subprocess + DATA).

    The fail-closed chain, each leg surfacing stderr and stamping :func:`mark_spawn_failed` on ANY
    refusal (never a half-venue projecting live):

    1. ``creator-engine-validator pco-allocate`` (cwd = the out-of-root venue zone — pco refuses
       from the repo root) provisions the worktree + Active-Work claim, with NO tracked-file write
       authority (``--envelope-ref none --no-write-authority``); the venue's authority is the
       reviewer-authority envelope, not a pco write envelope.
    2. ``ce lane launch --role reviewer --lane-kind review --reviewer-authority-ref <envelope>
       --json`` validates + injects the envelope on a DISTINCT reviewer venue and returns the Pane
       Registry record (the G2b ``--json`` seam); its ``terminal`` is stamped into the dispatch.
    3. :func:`seed_brief` — the EXISTING seed seam (so the ce-ops#16 readiness-poll/PATH fix lands
       in exactly one place), pointer-only line. The reviewer token env is NOT seeded as text — the
       venue inherits it from the launching shell having sourced the host reviewer env file.
    """
    review_of = record.data.get("review_of") or {}
    envelope_ref = str(review_of.get("envelope_ref") or "")
    if not envelope_ref:
        raise SpawnRefused(
            f"review dispatch {record.run_id!r} carries no envelope_ref; refusing to launch"
        )
    venue_root_path = Path(venue_root)
    worktree_path = venue_root_path / record.run_id
    brief_sha = hashlib.sha256(Path(record.brief_ref).read_bytes()).hexdigest()

    # 1) pco-allocate — provision the worktree + claim (cwd outside the repo).
    validator = _resolve_validator_exe(validator_exe)
    pco_argv = [
        validator, "pco-allocate",
        "--lane-id", record.run_id,
        "--worktree-path", str(worktree_path),
        "--branch", f"review/{record.run_id}",
        "--envelope-ref", "none",
        "--no-write-authority",
        "--controller-id", controller_id,
        "--ledger-root", str(ledger_root),
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
    record.data["spawned_at"] = _utcstamp(now or datetime.now(timezone.utc))
    _write_record(record)

    # 3) seed the venue brief through the SAME seam (ce-ops#16 fix lands once).
    seed_brief(record, runner=runner)

    return SpawnResult(
        run_id=record.run_id,
        terminal=dict(terminal),
        resource_bound=None,
        launch_result=launch_result,
    )
