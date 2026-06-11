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
