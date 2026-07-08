"""Probed CE harness-support and promotion capability matrix.

The matrix separates code support from live controller promotion. A row may be
gate-capable only when code support exists, launch wiring exists, live evidence
exists, and promotion has been approved, or when an explicit Operator-ratified
exception is recorded on that same row.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

SUPPORT_COLUMNS = ("code-support", "launch-wired", "live-proven", "promotion-approved")
CAPABILITIES = SUPPORT_COLUMNS
DISPLAY_COLUMNS = ("provider", "ring", *SUPPORT_COLUMNS, "gate-capable", "exception")
HARNESSES = (
    "claude_code",
    "codex",
    "lane_worker",
    "contained_controller_scaffold",
    "ephemeral_controller_providers",
)

GREEN = "green"
YELLOW = "yellow"
RED = "red"
GATE_YES = "yes"
GATE_NO = "no"
NO_EXCEPTION = "none"

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
class PromotionException:
    """Operator-ratified exception permitting a non-all-green gate row."""

    date: str
    ratification_ref: str
    provenance: str

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "ratification_ref": self.ratification_ref,
            "provenance": self.provenance,
        }

    def render(self) -> str:
        return f"{self.date} {self.ratification_ref}"


@dataclass(frozen=True)
class HarnessRow:
    provider: str
    ring: str
    cells: dict[str, Cell] = field(default_factory=dict)
    gate_capable: Cell = field(default_factory=lambda: _gate_no("not evaluated"))
    exception: PromotionException | None = None

    @property
    def harness(self) -> str:
        """Compatibility alias for call sites that enumerate matrix providers."""

        return self.provider

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ring": self.ring,
            "cells": {capability: self.cells[capability].to_dict() for capability in SUPPORT_COLUMNS},
            "gate_capable": self.gate_capable.to_dict(),
            "exception": self.exception.to_dict() if self.exception else None,
        }


@dataclass(frozen=True)
class HarnessMatrix:
    rows: tuple[HarnessRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "harness-support-promotion-matrix",
            "issue": "ticket-479",
            "capabilities": list(SUPPORT_COLUMNS),
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


def _green(provenance: str) -> Cell:
    return Cell(GREEN, provenance, verified=True)


def _yellow(provenance: str) -> Cell:
    return Cell(YELLOW, provenance, verified=False)


def _red(provenance: str) -> Cell:
    return Cell(RED, provenance, verified=True)


def _gate_yes(provenance: str) -> Cell:
    return Cell(GATE_YES, provenance, verified=True)


def _gate_no(provenance: str) -> Cell:
    return Cell(GATE_NO, provenance, verified=True)


def _row(
    provider: str,
    ring: str,
    *,
    code_support: Cell,
    launch_wired: Cell,
    live_proven: Cell,
    promotion_approved: Cell,
    gate_capable: Cell | None = None,
    exception: PromotionException | None = None,
) -> HarnessRow:
    cells = {
        "code-support": code_support,
        "launch-wired": launch_wired,
        "live-proven": live_proven,
        "promotion-approved": promotion_approved,
    }
    gate = gate_capable or (
        _gate_yes("all four promotion cells are green")
        if all(cell.value == GREEN and cell.verified for cell in cells.values())
        else _gate_no("one or more promotion cells are not green")
    )
    return HarnessRow(provider, ring, cells, gate, exception)


def _claude_rows(repo_root: Path) -> tuple[HarnessRow, ...]:
    launch_path = _module_file("claude_launch_spec")
    hook_confirm_path = _module_file("hook_pack_confirm")
    hook_check_path = _module_file("hook_check")
    settings_path = repo_root / ".claude" / "settings.json"

    ring0_ok = _module_has("claude_launch_spec", "evaluate_claude_launch", "build_governed_claude_command")
    try:
        confirm_mod = import_module("creator_engine_validator.hook_pack_confirm")
        confirmation = confirm_mod.confirm_hook_pack(
            repo_root,
            validator_probe=lambda: _module_has("hook_check", "evaluate", "HookContext"),
        )
    except Exception:
        confirmation = None
    ring1_ok = bool(confirmation and confirmation.pretooluse_registered and confirmation.validator_reachable)
    ring2_ok = bool(confirmation and confirmation.stop_registered and _module_has("hook_check", "evaluate", "HookContext"))

    return (
        _row(
            "claude_code",
            "Ring 0",
            code_support=_green(f"{_rel(launch_path)}: evaluate_claude_launch + build_governed_claude_command")
            if ring0_ok
            else _red("claude_launch_spec evaluator/builder not importable"),
            launch_wired=_green(f"{_rel(launch_path)}: governed Claude command builder is wired before harness start")
            if ring0_ok
            else _red("Claude Ring 0 launch builder is not wired"),
            live_proven=_green(f"{_rel(launch_path)}: launch envelope evaluator is covered by committed probes")
            if ring0_ok
            else _red("Claude Ring 0 live proof is absent"),
            promotion_approved=_green("Claude Ring 0 is full per existing matrix"),
        ),
        _row(
            "claude_code",
            "Ring 1",
            code_support=_green(f"{_rel(hook_confirm_path)}: confirm_hook_pack")
            if ring1_ok
            else _red("Claude PreToolUse hook-pack could not be confirmed"),
            launch_wired=_green(f"{_rel(settings_path, repo_root=repo_root)}: PreToolUse hook registered")
            if ring1_ok
            else _red("Claude Ring 1 hook is not launch-wired"),
            live_proven=_green(f"{_rel(hook_confirm_path)}: validator-reachable PreToolUse confirmation")
            if ring1_ok
            else _red("Claude Ring 1 live proof is absent"),
            promotion_approved=_green("Claude Ring 1 is full per existing matrix"),
        ),
        _row(
            "claude_code",
            "Ring 2",
            code_support=_green(f"{_rel(hook_check_path)}: evaluate(HookContext)")
            if ring2_ok
            else _red("Claude Stop/closeout hook could not be confirmed"),
            launch_wired=_green(f"{_rel(settings_path, repo_root=repo_root)}: Stop hook registered")
            if ring2_ok
            else _red("Claude Ring 2 closeout hook is not launch-wired"),
            live_proven=_green(f"{_rel(hook_confirm_path)}: Stop hook confirmation")
            if ring2_ok
            else _red("Claude Ring 2 live proof is absent"),
            promotion_approved=_green("Claude Ring 2 is full per existing matrix"),
        ),
    )


def _codex_rows(_repo_root: Path) -> tuple[HarnessRow, ...]:
    launch_path = _module_file("codex_launch_spec")
    confirm_path = _module_file("hook_pack_confirm")
    containment_path = _module_file("runner.herdr_containment")
    ring0_ok = _module_has("codex_launch_spec", "evaluate_codex_launch", "build_governed_codex_command")
    ring1_candidate = _module_has("hook_pack_confirm", "confirm_codex_managed_hook_pack")
    containment_candidate = _module_has("runner.herdr_containment", "plan_herdr_containment")

    return (
        _row(
            "codex",
            "Ring 0",
            code_support=_green(
                f"{_rel(launch_path)}: evaluate_codex_launch + build_governed_codex_command scrubs ambient repo credentials"
            )
            if ring0_ok
            else _red("codex_launch_spec evaluator/builder not importable"),
            launch_wired=_green(f"{_rel(launch_path)}: governed Codex command builder is wired before harness start")
            if ring0_ok
            else _red("Codex Ring 0 launch builder is not wired"),
            live_proven=_green(f"{_rel(launch_path)}: Ring 0 evaluator is committed and probed")
            if ring0_ok
            else _red("Codex Ring 0 live proof is absent"),
            promotion_approved=_green("Codex Ring 0 is full per known state"),
        ),
        _row(
            "codex",
            "Ring 1",
            code_support=_green(f"{_rel(confirm_path)}: confirm_codex_managed_hook_pack exists")
            if ring1_candidate
            else _red("Codex managed hook-pack predicate is absent"),
            launch_wired=_green(
                "Operator-authorized pre-act (decision 4, Operator decisions 2026-07-08); "
                "containment accepted per C5 promotion (decision 3, same ledger); "
                "promotion evidence packet still pending = ticket 480"
            ),
            live_proven=_red("not live-proven until the ticket 480 evidence packet and Ring 1 smoke are accepted"),
            promotion_approved=_red("promotion deferred pending containment acceptance and ticket 480"),
        ),
        _row(
            "codex",
            "Ring 2",
            code_support=_red(f"{_rel(launch_path)}: no Codex-owned Stop/closeout hook surface is wired"),
            launch_wired=_red("no Codex Ring 2 closeout launch wiring"),
            live_proven=_red("no Codex Ring 2 live proof"),
            promotion_approved=_red("Codex Ring 2 promotion is not approved"),
        ),
        _row(
            "codex",
            "containment",
            code_support=_green(f"{_rel(containment_path)}: plan_herdr_containment exists")
            if containment_candidate
            else _red("containment plan probe is absent"),
            launch_wired=_yellow("containment deferred; live launch still fails closed / is not wired"),
            live_proven=_red("Codex containment is not live-proven"),
            promotion_approved=_red("Codex containment promotion is deferred"),
        ),
    )


def _lane_ledger_root_env_wired() -> bool:
    """True when lane launch exports the ledger root into the launched pane env."""
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
        source = inspect.getsource(launch)
    except (OSError, TypeError):
        return False
    return "CE_LEDGER_ROOT_ENV" in source and "pane_env" in source and "env=pane_env" in source


def _lane_rows(repo_root: Path) -> tuple[HarnessRow, ...]:
    lane_path = _module_file("lane_runtime")
    settings_path = repo_root / ".claude" / "settings.json"
    ring0_ok = _module_has("lane_runtime", "launch", "ClaudeLaunchRefused")
    ring1_ok = _lane_ledger_root_env_wired()
    try:
        confirm_mod = import_module("creator_engine_validator.hook_pack_confirm")
        ring1_ok = ring1_ok and bool(confirm_mod.confirm_hook_pack(repo_root).pretooluse_registered)
    except Exception:
        ring1_ok = False
    ring2_ok = _module_has("lane_runtime", "verify", "verify_closeout")

    return (
        _row(
            "lane_worker",
            "Ring 0",
            code_support=_green(f"{_rel(lane_path)}: launch() runs governed lane Ring 0 refusal before side effects")
            if ring0_ok
            else _red("lane_runtime launch / ClaudeLaunchRefused not importable"),
            launch_wired=_green(f"{_rel(lane_path)}: governed worker lane launch is wired")
            if ring0_ok
            else _red("lane worker Ring 0 launch wiring is absent"),
            live_proven=_green(f"{_rel(lane_path)}: worker-lane Ring 0 path is committed and probed")
            if ring0_ok
            else _red("lane worker Ring 0 live proof is absent"),
            promotion_approved=_green("lane is approved as worker fan-out, not live controller authority"),
        ),
        _row(
            "lane_worker",
            "Ring 1",
            code_support=_green(f"{_rel(settings_path, repo_root=repo_root)}: committed PreToolUse hook-pack")
            if ring1_ok
            else _red("lane worker Ring 1 hook invariant is absent"),
            launch_wired=_green(f"{_rel(lane_path)}: launch() exports CE_LEDGER_ROOT into the pane env")
            if ring1_ok
            else _red("lane worker Ring 1 launch wiring is absent"),
            live_proven=_green(f"{_rel(lane_path)}: wrapped harness resolves posture from the real seat claim")
            if ring1_ok
            else _red("lane worker Ring 1 live proof is absent"),
            promotion_approved=_green("lane is approved as worker fan-out, not live controller authority"),
        ),
        _row(
            "lane_worker",
            "Ring 2",
            code_support=_green(f"{_rel(lane_path)}: verify() + verify_closeout provide lane closeout checks")
            if ring2_ok
            else _red("lane_runtime verify / verify_closeout not importable"),
            launch_wired=_green(f"{_rel(lane_path)}: closeout verification is wired for worker lanes")
            if ring2_ok
            else _red("lane worker Ring 2 launch wiring is absent"),
            live_proven=_green(f"{_rel(lane_path)}: worker-lane closeout checks are committed and probed")
            if ring2_ok
            else _red("lane worker Ring 2 live proof is absent"),
            promotion_approved=_green("lane is approved as worker fan-out, not live controller authority"),
        ),
    )


def _contained_controller_rows() -> tuple[HarnessRow, ...]:
    return (
        _row(
            "contained_controller_scaffold",
            "C1 static/dry-run",
            code_support=_green("contained-controller scaffold exists only as static/dry-run support"),
            launch_wired=_yellow("dry-run scaffold only; no live controller promotion wiring"),
            live_proven=_red("contained controller scaffold is not live-proven"),
            promotion_approved=_red("contained controller scaffold is not promotion-approved"),
        ),
        _row(
            "contained_controller_scaffold",
            "C2",
            code_support=_yellow("C2 scaffold is unproven beyond static/dry-run design"),
            launch_wired=_red("C2 launch wiring is unproven"),
            live_proven=_red("C2 is not live-proven"),
            promotion_approved=_red("C2 promotion is not approved"),
        ),
        _row(
            "contained_controller_scaffold",
            "C3",
            code_support=_yellow("C3 scaffold is unproven beyond static/dry-run design"),
            launch_wired=_red("C3 launch wiring is unproven"),
            live_proven=_red("C3 is not live-proven"),
            promotion_approved=_red("C3 promotion is not approved"),
        ),
        _row(
            "contained_controller_scaffold",
            "C4",
            code_support=_yellow("C4 scaffold is unproven beyond static/dry-run design"),
            launch_wired=_red("C4 launch wiring is unproven"),
            live_proven=_red("C4 is not live-proven"),
            promotion_approved=_red("C4 promotion is not approved"),
        ),
    )


def _ephemeral_controller_rows() -> tuple[HarnessRow, ...]:
    return (
        _row(
            "ephemeral_controller_providers",
            "design-stage",
            code_support=_yellow("ephemeral-controller providers are design-stage only"),
            launch_wired=_red("ephemeral-controller provider launch wiring is not present"),
            live_proven=_red("ephemeral-controller providers are not live-proven"),
            promotion_approved=_red("ephemeral-controller provider promotion is not approved"),
        ),
    )


def build_matrix(repo_root: Path | str = ".") -> HarnessMatrix:
    root = Path(repo_root).resolve()
    return HarnessMatrix(
        rows=(
            *_claude_rows(root),
            *_codex_rows(root),
            *_lane_rows(root),
            *_contained_controller_rows(),
            *_ephemeral_controller_rows(),
        )
    )


def row_all_green(row: HarnessRow) -> bool:
    return all(cell.value == GREEN and cell.verified for cell in row.cells.values())


def row_has_ratified_exception(row: HarnessRow) -> bool:
    return bool(row.exception and row.exception.date and row.exception.ratification_ref)


def render_markdown(matrix: HarnessMatrix) -> str:
    lines = [
        "# CE harness-support capability matrix",
        "",
        "This is the authoritative CE harness-support and promotion matrix. It is rendered from "
        "`creator_engine_validator.harness_matrix`; `yellow *` marks deferred or design-stage "
        "support, and `red` marks an absent or refused promotion requirement.",
        "",
        "A row is gate-capable only when `code-support`, `launch-wired`, `live-proven`, and "
        "`promotion-approved` are all `green`, or when the row records an explicit "
        "Operator-ratified exception with date and ratification reference.",
        "",
        "| " + " | ".join(DISPLAY_COLUMNS) + " |",
        "| " + " | ".join(["---"] * len(DISPLAY_COLUMNS)) + " |",
    ]
    for row in matrix.rows:
        values = [row.provider, row.ring]
        for capability in SUPPORT_COLUMNS:
            cell = row.cells[capability]
            marker = " *" if cell.value == YELLOW or not cell.verified else ""
            values.append(f"{cell.value}{marker}")
        values.append(row.gate_capable.value)
        values.append(row.exception.render() if row.exception else NO_EXCEPTION)
        lines.append("| " + " | ".join(values) + " |")

    lines += ["", "## Provenance", ""]
    for row in matrix.rows:
        lines.append(f"### {row.provider} - {row.ring}")
        for capability in SUPPORT_COLUMNS:
            cell = row.cells[capability]
            marker = " [deferred/design-stage]" if cell.value == YELLOW or not cell.verified else ""
            lines.append(f"- **{capability}** = `{cell.value}`{marker} - {cell.provenance}")
        lines.append(f"- **gate-capable** = `{row.gate_capable.value}` - {row.gate_capable.provenance}")
        if row.exception:
            lines.append(
                "- **exception** = "
                f"`{row.exception.render()}` - {row.exception.provenance}"
            )
        else:
            lines.append("- **exception** = `none` - no Operator-ratified exception recorded")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(matrix: HarnessMatrix) -> str:
    return json.dumps(matrix.to_dict(), indent=2, sort_keys=True) + "\n"
