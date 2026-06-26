"""ce-ops#220 - probed CE harness-support capability matrix.

The matrix is the single source of truth for which external agent harnesses CE
supports, and to what governance extent. It is deliberately derived from
committed wiring and importable validator modules where CE has wiring; rows that
are not actor harnesses, or whose support is not yet verified, are marked as
such instead of being promoted by prose.

Columns:

* ring0 - launch envelope / credential scrub before the harness starts.
* ring1 - per-tool-call hook surface.
* ring2 - Stop / closeout surface.
* containment - sandbox / PTY containment.
* native_fanout - whether the harness or surface can fan out natively.
* status - full / partial / deferred / none rollup.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

CAPABILITIES = ("ring0", "ring1", "ring2", "containment", "native_fanout", "status")
HARNESSES = (
    "claude_code",
    "codex",
    "hermes",
    "opencode",
    "copilot_cli",
    "nanoclaw",
    "discord",
    "slack",
)

STATUS_FULL = "full"
STATUS_PARTIAL = "partial"
STATUS_DEFERRED = "deferred"
STATUS_NONE = "none"

DOC_PATH = Path("docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md")


@dataclass(frozen=True)
class Cell:
    """One matrix cell plus the file-backed reason for that value."""

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
            "cells": {capability: self.cells[capability].to_dict() for capability in CAPABILITIES},
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


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _repo_root_from_package() -> Path:
    return _package_root().parent.parent


def _module_file(dotted: str) -> Path | None:
    try:
        module = import_module(f"creator_engine_validator.{dotted}")
    except Exception:
        fallback = _package_root().joinpath(*dotted.split(".")).with_suffix(".py")
        return fallback.resolve() if fallback.is_file() else None
    raw = getattr(module, "__file__", None)
    return Path(raw).resolve() if raw else None


def _rel(path: Path | None, *, repo_root: Path | None = None) -> str:
    if path is None:
        return "<not found>"
    root = repo_root or _repo_root_from_package()
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _module_has(dotted: str, *symbols: str) -> bool:
    try:
        module = import_module(f"creator_engine_validator.{dotted}")
    except Exception:
        path = _module_file(dotted)
        if path is None:
            return False
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return False
        needles = tuple(
            (
                f"def {symbol}",
                f"class {symbol}",
                f"{symbol} =",
                f"{symbol}:",
            )
            for symbol in symbols
        )
        return all(any(needle in text for needle in options) for options in needles)
    return all(hasattr(module, symbol) for symbol in symbols)


def _full(provenance: str) -> Cell:
    return Cell(STATUS_FULL, provenance, verified=True)


def _partial(provenance: str, *, verified: bool = True) -> Cell:
    return Cell(STATUS_PARTIAL, provenance, verified=verified)


def _deferred(provenance: str, *, verified: bool = False) -> Cell:
    return Cell(STATUS_DEFERRED, provenance, verified=verified)


def _none(provenance: str, *, verified: bool = True) -> Cell:
    return Cell(STATUS_NONE, provenance, verified=verified)


def _claude_row(repo_root: Path) -> HarnessRow:
    launch_path = _module_file("claude_launch_spec")
    hook_confirm_path = _module_file("hook_pack_confirm")
    hook_check_path = _module_file("hook_check")

    ring0_ok = _module_has("claude_launch_spec", "evaluate_claude_launch", "build_governed_claude_command")
    ring0 = (
        _full(f"{_rel(launch_path)}: evaluate_claude_launch + build_governed_claude_command")
        if ring0_ok
        else _none("claude_launch_spec evaluator/builder not importable", verified=False)
    )

    try:
        confirm_mod = import_module("creator_engine_validator.hook_pack_confirm")
        confirmation = confirm_mod.confirm_hook_pack(
            repo_root,
            validator_probe=lambda: _module_has("hook_check", "evaluate", "HookContext"),
        )
    except Exception:
        confirmation = None
    ring1_ok = bool(confirmation and confirmation.pretooluse_registered and confirmation.validator_reachable)
    ring1 = (
        _full(
            f"{_rel(repo_root / '.claude/settings.json', repo_root=repo_root)}: PreToolUse hook-pack "
            f"confirmed via {_rel(hook_confirm_path)}"
        )
        if ring1_ok
        else _none(".claude PreToolUse hook-pack could not be confirmed", verified=False)
    )

    ring2_ok = bool(confirmation and confirmation.stop_registered and _module_has("hook_check", "evaluate", "HookContext"))
    ring2 = (
        _full(
            f"{_rel(repo_root / '.claude/settings.json', repo_root=repo_root)}: Stop hook + "
            f"{_rel(hook_check_path)}: evaluate(HookContext)"
        )
        if ring2_ok
        else _none("Claude Stop/closeout hook could not be confirmed", verified=False)
    )

    containment = _containment_cell()
    native_fanout = _partial(
        "CE fan-out is provided by worker_spawn / lane launch rather than Claude Code native background agents, "
        "which Ring 0 refuses for governed seats"
    )
    status = _status_from_cells(ring0, ring1, ring2)
    return HarnessRow(
        "claude_code",
        {
            "ring0": ring0,
            "ring1": ring1,
            "ring2": ring2,
            "containment": containment,
            "native_fanout": native_fanout,
            "status": status,
        },
    )


def _codex_row(repo_root: Path) -> HarnessRow:
    launch_path = _module_file("codex_launch_spec")
    confirm_path = _module_file("hook_pack_confirm")

    ring0_ok = _module_has("codex_launch_spec", "evaluate_codex_launch", "build_governed_codex_command")
    ring0 = (
        _full(f"{_rel(launch_path)}: evaluate_codex_launch + build_governed_codex_command scrubs ambient repo credentials")
        if ring0_ok
        else _none("codex_launch_spec evaluator/builder not importable", verified=False)
    )

    # ce-ops#220's SSOT truth is intentionally conservative: Codex is supported
    # at Ring 0 today; Codex Ring 1 remains the ce-ops#219 follow-on capability.
    # The probe cites any candidate managed-hook predicate but does not promote
    # the support cell until that follow-on is accepted as the support boundary.
    if _module_has("hook_pack_confirm", "confirm_codex_managed_hook_pack"):
        provenance = (
            f"{_rel(confirm_path)}: confirm_codex_managed_hook_pack exists, but the matrix records "
            "Codex Ring 1 support as deferred pending containment acceptance"
        )
    else:
        provenance = "no Codex per-tool-call hook confirmation predicate is importable; deferred pending containment acceptance"
    ring1 = _deferred(provenance)

    ring2 = _none(f"{_rel(launch_path)}: no Codex-owned Stop/closeout hook surface is wired")
    containment = _containment_cell()
    native_fanout = _none("no Codex native governed fan-out wiring is present in CE")
    status = _status_from_cells(ring0, ring1, ring2)
    return HarnessRow(
        "codex",
        {
            "ring0": ring0,
            "ring1": ring1,
            "ring2": ring2,
            "containment": containment,
            "native_fanout": native_fanout,
            "status": status,
        },
    )


def _hermes_row(_repo_root: Path) -> HarnessRow:
    launch_path = _module_file("hermes_launch_spec")
    ring0_candidate = _module_has("hermes_launch_spec", "evaluate_hermes_launch", "build_governed_hermes_command")
    ring0 = (
        _partial(
            f"{_rel(launch_path)}: Hermes launch evaluator/builder exists, but the matrix classifies "
            "Hermes governance extent as unverified until a harness audit promotes it",
            verified=False,
        )
        if ring0_candidate
        else _deferred("Hermes support is unverified; no launch-spec probe found")
    )
    ring1 = _deferred("Hermes per-tool-call hook support is unverified")
    ring2 = _deferred("Hermes Stop/final-answer hook support is unverified")
    containment = _containment_cell()
    native_fanout = _deferred("Hermes native fan-out support is unverified")
    status = _deferred("Hermes support is explicitly unverified in this matrix")
    return HarnessRow(
        "hermes",
        {
            "ring0": ring0,
            "ring1": ring1,
            "ring2": ring2,
            "containment": containment,
            "native_fanout": native_fanout,
            "status": status,
        },
    )


def _unverified_actor_row(harness: str, label: str) -> HarnessRow:
    status = _deferred(f"{label} support is unverified; no CE harness adapter wiring is probed")
    return HarnessRow(
        harness,
        {
            "ring0": _deferred(f"{label} launch envelope / cred-scrub support is unverified"),
            "ring1": _deferred(f"{label} per-tool-call hook support is unverified"),
            "ring2": _deferred(f"{label} Stop/closeout support is unverified"),
            "containment": _deferred(f"{label} sandbox / PTY containment support is unverified"),
            "native_fanout": _deferred(f"{label} native fan-out support is unverified"),
            "status": status,
        },
    )


def _emission_only_row(surface: str) -> HarnessRow:
    notify_path = _module_file("runner.notify_feed")
    webhook_ok = _module_has("runner.notify_feed", "SINK_WEBHOOK", "parse_notify_config", "SinkConfig")
    fanout = (
        _full(f"{_rel(notify_path)}: first-class webhook sink covers {surface} emission")
        if webhook_ok
        else _none("notify_feed webhook sink is not importable", verified=False)
    )
    status = _none(f"{surface} is an emission-only non-actor surface; there is no Ring 1 actor to gate")
    return HarnessRow(
        surface,
        {
            "ring0": _none(f"{surface} is not an actor harness; no launch envelope applies"),
            "ring1": _none(f"{surface} is not an actor harness; no per-tool-call hook applies"),
            "ring2": _none(f"{surface} is not an actor harness; no Stop/closeout applies"),
            "containment": _none(f"{surface} is not an actor harness; no sandbox / PTY applies"),
            "native_fanout": fanout,
            "status": status,
        },
    )


def _containment_cell() -> Cell:
    herdr_path = _module_file("runner.herdr_containment")
    if not _module_has("runner.herdr_containment", "plan_herdr_containment"):
        return _none("runner.herdr_containment plan probe is not importable", verified=False)
    if _herdr_launch_is_wired():
        return _full(f"{_rel(herdr_path)}: HerdrContainmentLaunch.launch is wired")
    return _deferred(
        f"{_rel(herdr_path)}: containment plan exists, but live launch still fails closed / is not wired"
    )


def _herdr_launch_is_wired() -> bool:
    try:
        herdr = import_module("creator_engine_validator.runner.herdr_containment")
        plan = herdr.plan_herdr_containment(
            {"mount_manifest": [], "egress_allowlist": []},
            run_id="harness-matrix-probe",
            seat_command=("true",),
        )
        launcher = herdr.HerdrContainmentLaunch(plan)
        launcher.launch()
    except Exception:
        return False
    return True


def _status_from_cells(ring0: Cell, ring1: Cell, ring2: Cell) -> Cell:
    present = sum(1 for cell in (ring0, ring1, ring2) if cell.verified and cell.value in {STATUS_FULL, STATUS_PARTIAL})
    if present == 3:
        value = STATUS_FULL
    elif present:
        value = STATUS_PARTIAL
    else:
        value = STATUS_NONE
    return Cell(value, f"rollup of verified Ring 0/1/2 support: {present}/3", verified=True)


def build_matrix(repo_root: Path | str = ".") -> HarnessMatrix:
    root = Path(repo_root).resolve()
    return HarnessMatrix(
        rows=(
            _claude_row(root),
            _codex_row(root),
            _hermes_row(root),
            _unverified_actor_row("opencode", "OpenCode"),
            _unverified_actor_row("copilot_cli", "Copilot CLI"),
            _emission_only_row("nanoclaw"),
            _emission_only_row("discord"),
            _emission_only_row("slack"),
        )
    )


def render_markdown(matrix: HarnessMatrix) -> str:
    headers = ["harness", "Ring 0", "Ring 1", "Ring 2", "containment", "native fan-out", "status"]
    lines = [
        "# CE harness-support capability matrix",
        "",
        "This is the authoritative CE harness-support matrix. It is rendered from "
        "`creator_engine_validator.harness_matrix`; `*` marks a cell whose support "
        "is deferred or otherwise not verified by committed wiring.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in matrix.rows:
        values = [row.harness]
        for capability in CAPABILITIES:
            cell = row.cells[capability]
            marker = "" if cell.verified else " *"
            values.append(f"{cell.value}{marker}")
        lines.append("| " + " | ".join(values) + " |")

    lines += ["", "## Provenance", ""]
    for row in matrix.rows:
        lines.append(f"### {row.harness}")
        for capability in CAPABILITIES:
            cell = row.cells[capability]
            marker = "" if cell.verified else " [unverified/deferred]"
            lines.append(f"- **{capability}** = `{cell.value}`{marker} - {cell.provenance}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(matrix: HarnessMatrix) -> str:
    return json.dumps(matrix.to_dict(), indent=2, sort_keys=True) + "\n"
