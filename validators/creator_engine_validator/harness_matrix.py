"""ce-ops#220 — PROBED harness-support capability matrix (SSOT).

This module derives a HARNESS x CAPABILITY matrix **by inspecting the adapter
specs / committed config at runtime** so the matrix can never drift from reality.
It is the antidote to the containment-probe incident (ce-ops#221): governance
state must be *derived/probed*, never hand-asserted in prose. A false
"contained gVisor" claim that lives only in a comment cannot survive here —
every cell carries a *provenance* note naming the file that proves it, and a
capability that is asserted-but-unverifiable is marked explicitly.

Harnesses (rows):

* ``claude`` — the governed Claude Code authoring lane.
* ``codex``  — the governed Codex authoring seat.
* ``lane``   — the governed worker lane primitive (``ce lane launch``).

Capabilities (columns):

* **ring0** — the Ring-0 launch envelope / credential scrub (present?).
* **ring1** — the per-tool-call hook posture
  (``none`` / ``present`` / ``managed-non-bypassable``). For codex this detects
  whether a managed PreToolUse hook-pack pinning ``allow_managed_hooks_only`` is
  wired.
* **ring2** — the Stop / closeout verification surface.
* **containment** — the containment-probe capability (gVisor / herdr-contained /
  none), referencing :mod:`runner.herdr_containment` and the gVisor backend.
* **status** — the overall rollup (``full`` / ``partial`` / ``deferred`` /
  ``none``).

The module is PURE-ish I/O: it reads only the validator package source tree and,
for codex, the committed managed-hook config. It launches no harness, spawns no
process, and makes no network call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

# Capability column keys, in emit order.
CAPABILITIES = ("ring0", "ring1", "ring2", "containment", "status")
HARNESSES = ("claude", "codex", "lane")

# Ring-1 posture values.
RING1_NONE = "none"
RING1_PRESENT = "present"
RING1_MANAGED = "managed-non-bypassable"

# Status rollup values.
STATUS_FULL = "full"
STATUS_PARTIAL = "partial"
STATUS_DEFERRED = "deferred"
STATUS_NONE = "none"

#: The codex managed-hook-pack pin that, when present, makes the codex Ring-1
#: hook non-bypassable. Detected from the committed config at runtime.
CODEX_MANAGED_PIN = "allow_managed_hooks_only"


@dataclass(frozen=True)
class Cell:
    """One matrix cell: a probed value plus the provenance that proves it.

    ``verified`` is False when the capability is asserted but the backing file /
    pin that would prove it was not found at probe time. A False ``verified`` is
    surfaced explicitly so a prose-only claim can never read as a present
    capability.
    """

    value: str
    provenance: str
    verified: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "provenance": self.provenance,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class HarnessRow:
    harness: str
    cells: dict[str, Cell] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "harness": self.harness,
            "cells": {cap: self.cells[cap].to_dict() for cap in CAPABILITIES},
        }


@dataclass(frozen=True)
class HarnessMatrix:
    rows: tuple[HarnessRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "harness-support-matrix",
            "issue": "ce-ops#220",
            "capabilities": list(CAPABILITIES),
            "rows": [row.to_dict() for row in self.rows],
        }


# ---------------------------------------------------------------------------
# Probe helpers — every fact is DERIVED, never hard-asserted.
# ---------------------------------------------------------------------------


def _package_root() -> Path:
    """Absolute path to the ``creator_engine_validator`` package source tree."""
    return Path(__file__).resolve().parent


def _module_file(dotted: str) -> Path | None:
    """Resolve the on-disk file for an importable submodule, else None."""
    try:
        module = import_module(f"creator_engine_validator.{dotted}")
    except Exception:
        return None
    spec_file = getattr(module, "__file__", None)
    return Path(spec_file).resolve() if spec_file else None


def _rel(path: Path | None) -> str:
    """Render a probe path relative to the repo root for a stable provenance note."""
    if path is None:
        return "<not found>"
    try:
        # repo root is two levels up from the package (validators/creator_engine_validator).
        repo_root = _package_root().parent.parent
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return str(path)


def _module_has(dotted: str, *symbols: str) -> bool:
    """True when the submodule imports AND defines every named symbol."""
    try:
        module = import_module(f"creator_engine_validator.{dotted}")
    except Exception:
        return False
    return all(hasattr(module, sym) for sym in symbols)


# ---------------------------------------------------------------------------
# claude row
# ---------------------------------------------------------------------------


def _claude_row(repo_root: Path) -> HarnessRow:
    spec_path = _module_file("claude_launch_spec")
    confirm_path = _module_file("hook_pack_confirm")

    # Ring 0: the launch-spec evaluator + governed-command builder (cred/posture pin).
    ring0_present = _module_has(
        "claude_launch_spec",
        "evaluate_claude_launch",
        "build_governed_claude_command",
    )
    ring0 = Cell(
        "present" if ring0_present else "none",
        f"{_rel(spec_path)}: evaluate_claude_launch + build_governed_claude_command "
        "(pins --setting-sources project, --strict-mcp-config)",
        verified=ring0_present,
    )

    # Ring 1: the committed .claude/settings.json PreToolUse hook-pack. PROBED by
    # confirm_hook_pack against the real committed settings, never assumed.
    settings_path = repo_root / ".claude" / "settings.json"
    pretooluse_ok = False
    confirm_mod = None
    try:
        confirm_mod = import_module("creator_engine_validator.hook_pack_confirm")
        confirmation = confirm_mod.confirm_hook_pack(repo_root)
        pretooluse_ok = confirmation.pretooluse_registered
    except Exception:
        pretooluse_ok = False
    if pretooluse_ok:
        ring1 = Cell(
            RING1_PRESENT,
            f"{_rel(settings_path)}: PreToolUse matcher covers "
            "Edit|Write|MultiEdit|Read|Bash "
            f"(confirmed via {_rel(confirm_path)}:confirm_hook_pack)",
            verified=True,
        )
    else:
        ring1 = Cell(
            RING1_NONE,
            f"{_rel(settings_path)}: no PreToolUse matcher covering the governed "
            "tool set could be confirmed",
            verified=False,
        )

    # Ring 2: Stop/closeout verification. verify_closeout feeds hook_check Stop logic.
    ring2_present = _module_has("lane_runtime", "verify_closeout")
    ring2 = Cell(
        "present" if ring2_present else "none",
        f"{_rel(_module_file('lane_runtime'))}: verify_closeout -> hook_check Stop "
        "decision; committed .claude/hooks/ce-stop.sh (advisory)",
        verified=ring2_present,
    )

    # Containment: claude lanes route through the lane runtime; the containment
    # capability is the herdr/gVisor probe shared by all lanes (deferred — U2 stub).
    containment = _containment_cell()

    status = _rollup(ring0, ring1, ring2, containment)
    return HarnessRow(
        "claude",
        {
            "ring0": ring0,
            "ring1": ring1,
            "ring2": ring2,
            "containment": containment,
            "status": status,
        },
    )


# ---------------------------------------------------------------------------
# codex row
# ---------------------------------------------------------------------------


def _codex_ring1_probe(repo_root: Path) -> Cell:
    """Derive the codex Ring-1 posture from the committed managed-hook config.

    * managed-non-bypassable IFF the committed ``.codex/requirements.toml`` is
      TOML-parsed and pins ``allow_managed_hooks_only = true`` (boolean True).
      We REUSE :func:`hook_pack_confirm.confirm_codex_managed_hook_pack` — the
      same predicate PR #387 uses to gate the managed pack — so the matrix can
      never fork the managed-only policy. A config that merely mentions the key,
      or pins it ``false``, or omits it, is NOT managed-non-bypassable.
    * present IF that confirm predicate exists in-package but the committed config
      does not pin the flag true (asserted-but-unverifiable middle state).
    * none otherwise (the launch-spec module explicitly does NOT claim a Ring-1
      hook-pack — see its docstring).
    """
    # Reuse #387's parse/require logic — do NOT fork the policy with a substring
    # check. The confirm predicate TOML-parses .codex/requirements.toml and only
    # sets ``managed_hooks_only_pinned`` when ``allow_managed_hooks_only`` is the
    # boolean True. ``False`` / missing key -> not pinned -> NOT managed.
    confirm_present = _module_has(
        "hook_pack_confirm", "confirm_codex_managed_hook_pack"
    )
    requirements_path = repo_root / ".codex" / "requirements.toml"
    if confirm_present:
        try:
            confirm_mod = import_module("creator_engine_validator.hook_pack_confirm")
            confirmation = confirm_mod.confirm_codex_managed_hook_pack(repo_root)
        except Exception:
            confirmation = None
        if confirmation is not None and confirmation.managed_hooks_only_pinned:
            return Cell(
                RING1_MANAGED,
                f"{_rel(requirements_path)}: TOML-pins {CODEX_MANAGED_PIN} = true "
                "(managed PreToolUse hook-pack, non-bypassable) — confirmed via "
                f"{_rel(_module_file('hook_pack_confirm'))}:"
                "confirm_codex_managed_hook_pack",
                verified=True,
            )
        # The confirm predicate exists but the committed config does NOT pin
        # allow_managed_hooks_only = true (missing key, or pinned false, or no
        # requirements.toml at all) -> present-but-unverifiable, never managed.
        return Cell(
            RING1_PRESENT,
            f"{_rel(_module_file('hook_pack_confirm'))}: "
            "confirm_codex_managed_hook_pack exists but the committed config does "
            f"not pin {CODEX_MANAGED_PIN} = true",
            verified=False,
        )

    # Default: the codex launch-spec module explicitly disclaims a Ring-1 hook-pack.
    return Cell(
        RING1_NONE,
        f"{_rel(_module_file('codex_launch_spec'))}: module docstring explicitly "
        f"does not claim a Codex Ring-1 hook-pack; no committed config pins "
        f"{CODEX_MANAGED_PIN}",
        verified=True,
    )


def _codex_row(repo_root: Path) -> HarnessRow:
    spec_path = _module_file("codex_launch_spec")

    # Ring 0: evaluator + governed command builder that scrubs ambient repo-write creds.
    ring0_present = _module_has(
        "codex_launch_spec",
        "evaluate_codex_launch",
        "build_governed_codex_command",
    )
    ring0 = Cell(
        "present" if ring0_present else "none",
        f"{_rel(spec_path)}: evaluate_codex_launch + build_governed_codex_command "
        "(env -u scrubs GH_TOKEN/GITHUB_TOKEN/...)",
        verified=ring0_present,
    )

    ring1 = _codex_ring1_probe(repo_root)

    # Ring 2: codex has no CE-owned Stop/closeout verification surface of its own;
    # it relies on the visible-pane/transcript closeout, not a hook-driven Stop.
    ring2 = Cell(
        RING1_NONE,
        f"{_rel(spec_path)}: no codex-owned Stop/closeout hook surface in the "
        "launch spec (closeout via visible transcript only)",
        verified=True,
    )

    containment = _containment_cell()

    status = _rollup(ring0, ring1, ring2, containment)
    return HarnessRow(
        "codex",
        {
            "ring0": ring0,
            "ring1": ring1,
            "ring2": ring2,
            "containment": containment,
            "status": status,
        },
    )


# ---------------------------------------------------------------------------
# lane (worker) row
# ---------------------------------------------------------------------------


def _lane_ledger_root_env_wired() -> bool:
    """True only when ``lane_runtime.launch`` actually wires the §7 hook env.

    The lane Ring-1 hook is real ONLY because two file-backed facts hold:

    1. the launched harness carries the committed ``.claude/settings.json``
       PreToolUse hook-pack (probed by ``confirm_hook_pack``), and
    2. ``lane_runtime.launch`` exports ``CE_LEDGER_ROOT`` into the pane env so
       that in-band hook can resolve §7 posture from the seat's real claim.

    This probes (2) by inspecting the live ``lane_runtime`` source for the
    ledger-root env constant being wired into ``pane_env`` and passed through to
    the surface as ``env=pane_env``. It is NOT inferred from Ring-0 presence: if
    the env wiring is removed/renamed the probe flips, even though ``launch`` and
    ``ClaudeLaunchRefused`` (the Ring-0 symbols) still exist.
    """
    import inspect

    try:
        lane_runtime = import_module("creator_engine_validator.lane_runtime")
    except Exception:
        return False
    env_const = getattr(lane_runtime, "CE_LEDGER_ROOT_ENV", None)
    if not isinstance(env_const, str) or not env_const:
        return False
    launch = getattr(lane_runtime, "launch", None)
    if launch is None:
        return False
    try:
        src = inspect.getsource(launch)
    except (OSError, TypeError):
        return False
    # The §7 ledger-root env must be wired into the pane env AND that env must be
    # passed through to the launched surface — the wiring that makes the wrapped
    # harness's in-band Ring-1 hook resolve §7 from the seat's real claim.
    return (
        "CE_LEDGER_ROOT_ENV" in src
        and "pane_env" in src
        and "env=pane_env" in src
    )


def _lane_ring1_probe(repo_root: Path) -> Cell:
    """Derive the lane Ring-1 cell from the actual hook invariant, not Ring-0.

    The lane adds no per-call hook of its own; its Ring-1 is real ONLY via the
    wrapped harness's committed PreToolUse hook-pack PLUS the lane's ledger-root
    env wiring that lets that hook resolve §7. We probe BOTH independently of
    Ring-0:

    * ``confirm_hook_pack(repo_root).pretooluse_registered`` — the committed
      ``.claude/settings.json`` PreToolUse pack the wrapped harness loads.
    * ``_lane_ledger_root_env_wired()`` — ``lane_runtime.launch`` exports
      ``CE_LEDGER_ROOT`` into the pane env.

    If either invariant drifts (the PreToolUse pack is removed, or the lane stops
    wiring the §7 env) the cell flips to ``present``/``none`` + ``verified=False``
    — never a silent ``present`` inferred from launch presence.
    """
    lane_path = _module_file("lane_runtime")
    settings_path = repo_root / ".claude" / "settings.json"

    pretooluse_ok = False
    try:
        confirm_mod = import_module("creator_engine_validator.hook_pack_confirm")
        pretooluse_ok = confirm_mod.confirm_hook_pack(repo_root).pretooluse_registered
    except Exception:
        pretooluse_ok = False

    env_wired = _lane_ledger_root_env_wired()

    if pretooluse_ok and env_wired:
        return Cell(
            RING1_PRESENT,
            f"{_rel(settings_path)}: committed PreToolUse hook-pack + "
            f"{_rel(lane_path)}: launch() exports CE_LEDGER_ROOT into the pane env "
            "so the wrapped harness's in-band Ring-1 hook resolves §7 from the "
            "seat's real claim (probed, not inferred from Ring-0)",
            verified=True,
        )

    missing = []
    if not pretooluse_ok:
        missing.append("no committed .claude/settings.json PreToolUse hook-pack")
    if not env_wired:
        missing.append("lane_runtime.launch does not wire the CE_LEDGER_ROOT pane env")
    return Cell(
        RING1_PRESENT if (pretooluse_ok or env_wired) else RING1_NONE,
        f"{_rel(lane_path)}: lane Ring-1 invariant unconfirmed — {'; '.join(missing)}",
        verified=False,
    )


def _lane_row(repo_root: Path) -> HarnessRow:
    lane_path = _module_file("lane_runtime")

    # Ring 0: the governed lane launch refuses prohibited surfaces + pins the
    # governed Claude command before any side effect (delegates to claude Ring-0).
    ring0_present = _module_has("lane_runtime", "launch", "ClaudeLaunchRefused")
    ring0 = Cell(
        "present" if ring0_present else "none",
        f"{_rel(lane_path)}: launch() runs the CC-G-D Ring-0 gate "
        "(ClaudeLaunchRefused) + governed-command build before any side effect",
        verified=ring0_present,
    )

    # Ring 1: PROBED from the actual hook invariant (committed PreToolUse pack +
    # the lane's CE_LEDGER_ROOT env wiring), NOT inferred from Ring-0 presence.
    ring1 = _lane_ring1_probe(repo_root)

    # Ring 2: verify()/verify_closeout closeout-line + completion-report checks.
    ring2_present = _module_has("lane_runtime", "verify", "verify_closeout")
    ring2 = Cell(
        "present" if ring2_present else "none",
        f"{_rel(lane_path)}: verify() checks the stop line + optional completion "
        "report; verify_closeout drives the Stop decision",
        verified=ring2_present,
    )

    containment = _containment_cell()

    status = _rollup(ring0, ring1, ring2, containment)
    return HarnessRow(
        "lane",
        {
            "ring0": ring0,
            "ring1": ring1,
            "ring2": ring2,
            "containment": containment,
            "status": status,
        },
    )


# ---------------------------------------------------------------------------
# containment cell — shared probe (the ce-ops#221 antidote)
# ---------------------------------------------------------------------------


def _containment_cell() -> Cell:
    """Derive the containment capability from the runner backends, not from prose.

    The herdr containment wrapper (ce-ops#217 U2) is a SPEC + fail-closed STUB:
    ``HerdrContainmentLaunch.launch`` raises ``HerdrContainmentNotWired`` until U3
    wires it against a live gVisor/OpenShell RunnerBackend. We probe that fact at
    runtime so the matrix reports ``deferred`` — never a false "contained gVisor"
    claim that lives only in a comment (the ce-ops#221 incident).
    """
    herdr_path = _module_file("runner.herdr_containment")
    plan_present = _module_has("runner.herdr_containment", "plan_herdr_containment")
    launch_stub = _module_has("runner.herdr_containment", "HerdrContainmentNotWired")

    if not plan_present:
        return Cell(
            "none",
            "runner.herdr_containment not importable; no containment plan probe",
            verified=False,
        )

    # Probe whether the live launch is wired or still a fail-closed stub.
    wired = _herdr_launch_is_wired()
    if wired:
        return Cell(
            "gVisor/herdr-contained",
            f"{_rel(herdr_path)}: HerdrContainmentLaunch.launch is wired to a live "
            "RunnerBackend",
            verified=True,
        )
    return Cell(
        "deferred (U2 stub)",
        f"{_rel(herdr_path)}: plan_herdr_containment is live (pure §7 plan) but "
        "HerdrContainmentLaunch.launch raises HerdrContainmentNotWired (live "
        "gVisor/OpenShell launch is U3) — asserted-but-unverifiable as live",
        verified=False,
    )


def _herdr_launch_is_wired() -> bool:
    """True only if the live herdr containment launch no longer fails closed.

    PROBED by actually invoking the stub's ``launch`` on a minimal pure plan and
    observing whether it still raises ``HerdrContainmentNotWired``. This is the
    derive-don't-assert core: a future U3 that wires the launch flips this cell
    automatically, and a prose-only "it's contained" claim cannot fake it.
    """
    try:
        herdr = import_module("creator_engine_validator.runner.herdr_containment")
    except Exception:
        return False
    try:
        plan = herdr.plan_herdr_containment(
            {"mount_manifest": [], "egress_allowlist": []},
            run_id="harness-matrix-probe",
            seat_command=("true",),
        )
        launcher = herdr.HerdrContainmentLaunch(plan)
        launcher.launch()
    except herdr.HerdrContainmentNotWired:
        return False
    except Exception:
        # Any other failure also means we cannot claim a live contained launch.
        return False
    return True


# ---------------------------------------------------------------------------
# rollup
# ---------------------------------------------------------------------------


def _rollup(ring0: Cell, ring1: Cell, ring2: Cell, containment: Cell) -> Cell:
    """Roll the ring cells up into an overall status, conservatively.

    A capability that is not verified never lifts the rollup. Containment that is
    deferred caps the rollup at ``partial`` (governance rings present but the
    runtime is not yet contained).
    """
    rings_present = [
        c.verified and c.value not in (RING1_NONE, "none")
        for c in (ring0, ring1, ring2)
    ]
    containment_live = containment.verified and containment.value not in (
        "none",
        "deferred (U2 stub)",
    )

    if all(rings_present) and containment_live:
        value = STATUS_FULL
    elif any(rings_present):
        value = STATUS_PARTIAL
    else:
        value = STATUS_NONE

    note = (
        f"rollup of rings (ring0/ring1/ring2 verified+present={sum(rings_present)}/3) "
        f"+ containment live={containment_live}"
    )
    return Cell(value, note, verified=True)


# ---------------------------------------------------------------------------
# build + render
# ---------------------------------------------------------------------------


def build_matrix(repo_root: Path | str = ".") -> HarnessMatrix:
    """Build the PROBED harness-support matrix by inspecting specs/config."""
    root = Path(repo_root).resolve()
    return HarnessMatrix(
        rows=(
            _claude_row(root),
            _codex_row(root),
            _lane_row(root),
        )
    )


def render_markdown(matrix: HarnessMatrix) -> str:
    """Render the matrix + per-cell provenance as Markdown."""
    headers = ["harness", "Ring-0", "Ring-1", "Ring-2", "containment", "status"]
    lines = [
        "# CE harness-support capability matrix (ce-ops#220)",
        "",
        "DERIVED by probing the adapter specs / committed config at runtime — "
        "never hand-asserted. A `*` marks a cell asserted-but-unverifiable.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in matrix.rows:
        cells = [row.harness]
        for cap in CAPABILITIES:
            cell = row.cells[cap]
            mark = "" if cell.verified else " *"
            cells.append(f"{cell.value}{mark}")
        lines.append("| " + " | ".join(cells) + " |")

    lines += ["", "## Provenance", ""]
    for row in matrix.rows:
        lines.append(f"### {row.harness}")
        for cap in CAPABILITIES:
            cell = row.cells[cap]
            flag = "" if cell.verified else " [asserted-but-unverifiable]"
            lines.append(f"- **{cap}** = `{cell.value}`{flag} — {cell.provenance}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(matrix: HarnessMatrix) -> str:
    return json.dumps(matrix.to_dict(), indent=2, sort_keys=True) + "\n"
