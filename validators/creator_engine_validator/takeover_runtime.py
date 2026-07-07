"""Read-only ``ce takeover`` continuity planner.

Slice B intentionally stops at detect/select/verify/hydrate planning.  It does
not start a controller, re-arm watchers, sign, or mutate live state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import brain_runtime, launch_runtime
from .loader import LoaderError, load_yaml

INITIAL_STATE = "AWAITING-OPERATOR"
TAKEOVER_KIND = "ce-takeover-evidence-packet"
SUPPORTED_HARNESSES = frozenset({"claude", "codex"})
_MAX_MATCH_BYTES = 128_000
FORGE_HOUSEKEEPING_RUNBOOK = "docs/operations/FORGE_HOUSEKEEPING_RUNBOOK.md"


class TakeoverError(Exception):
    code = "CE-TAKEOVER-ERROR"


class UnsupportedHarness(TakeoverError):
    code = "CE-TAKEOVER-UNSUPPORTED-HARNESS"


class LiveTakeoverNotImplemented(TakeoverError):
    code = "CE-TAKEOVER-LIVE-DEFERRED"


class DutyManifestError(TakeoverError):
    code = "CE-TAKEOVER-DUTY-MANIFEST"


@dataclass(frozen=True)
class EvidenceSource:
    name: str
    path: str
    status: str
    detail: str
    count: int | None = None
    newest_mtime: float | None = None
    matches_predecessor: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "path": self.path,
            "status": self.status,
            "detail": self.detail,
        }
        if self.count is not None:
            payload["count"] = self.count
        if self.newest_mtime is not None:
            payload["newest_mtime"] = self.newest_mtime
        if self.matches_predecessor:
            payload["matches_predecessor"] = list(self.matches_predecessor)
        return payload


@dataclass(frozen=True)
class ReArmAction:
    duty_id: str
    duty_type: str
    command: tuple[str, ...]
    source: str
    enabled: bool = True

    @property
    def action(self) -> str:
        return f"re-arm-{self.duty_type}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "duty_id": self.duty_id,
            "duty_type": self.duty_type,
            "execute": False,
            "enabled": self.enabled,
            "command": list(self.command),
            "source": self.source,
            "detail": f"would run: {' '.join(self.command)}",
        }


@dataclass(frozen=True)
class ReArmPlan:
    manifest_path: str
    status: str
    detail: str
    actions: tuple[ReArmAction, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "status": self.status,
            "detail": self.detail,
            "dry_run": True,
            "actions": [action.to_dict() for action in self.actions],
        }


@dataclass(frozen=True)
class TakeoverPlan:
    predecessor: str
    harness: str
    repo_root: Path
    dry_run: bool
    initial_state: str
    evidence_sources: tuple[EvidenceSource, ...]
    ring0_report: launch_runtime.LaunchPreflightReport
    hydration_actions: tuple[dict[str, Any], ...]
    rearm_plan: ReArmPlan

    @property
    def predecessor_detected(self) -> bool:
        return any(source.matches_predecessor for source in self.evidence_sources)

    @property
    def evidence_gaps(self) -> tuple[dict[str, str], ...]:
        return tuple(
            {"name": source.name, "path": source.path, "detail": source.detail}
            for source in self.evidence_sources
            if source.status in {"missing", "unreadable"}
        )

    @property
    def ring0_ok(self) -> bool:
        ring0_gate_names = {
            "plan",
            "foreman-dispatch-contract",
            "harness-governance",
            "harness-binary",
        }
        return all(
            gate.status != "WOULD-REFUSE"
            for gate in self.ring0_report.gates
            if gate.name in ring0_gate_names
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": TAKEOVER_KIND,
            "schema_version": 1,
            "generated_at": launch_runtime.takeover_evidence_generated_at(),
            "host_id": launch_runtime.takeover_evidence_host_id(),
            "predecessor": {
                "requested": self.predecessor,
                "detected": self.predecessor_detected,
            },
            "selected_harness": self.harness,
            "repo_root": str(self.repo_root),
            "dry_run": self.dry_run,
            "ring0_verify": {
                "ok": self.ring0_ok,
                "launch_runtime_report": self.ring0_report.to_dict(),
            },
            "evidence_sources": [source.to_dict() for source in self.evidence_sources],
            "evidence_gaps": list(self.evidence_gaps),
            "hydration_plan": list(self.hydration_actions),
            "re_arm_plan": self.rearm_plan.to_dict(),
            "raw_controller_launch_refusal": (
                launch_runtime.raw_controller_launch_refusal_evidence(
                    harness=self.harness,
                    repo_root=self.repo_root,
                    predecessor=self.predecessor,
                )
            ),
            "initial_state": self.initial_state,
        }

    def format_lines(self) -> list[str]:
        lines = [
            "ce takeover (dry-run): no state will be mutated",
            f"predecessor: {self.predecessor} "
            f"({'detected' if self.predecessor_detected else 'not detected; evidence gaps retained'})",
            f"selected harness: {self.harness}",
            f"Ring-0 verify: {'PASS' if self.ring0_ok else 'WOULD-REFUSE'}",
            f"initial state: {self.initial_state}",
            "would take actions:",
        ]
        for action in self.hydration_actions:
            lines.append(f"  - {action['action']}: {action['detail']}")
        lines.append(f"duty manifest: {self.rearm_plan.status} ({self.rearm_plan.detail})")
        if self.rearm_plan.actions:
            lines.append("would re-arm duties:")
            for action in self.rearm_plan.actions:
                lines.append(
                    f"  - {action.action} {action.duty_id}: {' '.join(action.command)}"
                )
        if self.evidence_gaps:
            lines.append("evidence gaps:")
            for gap in self.evidence_gaps:
                lines.append(f"  - {gap['name']}: {gap['detail']} ({gap['path']})")
        return lines


class _ReadOnlyTmuxProbe:
    """Launch preflight adapter that cannot spawn and reports no live session."""

    kind = "takeover-dry-run"

    def is_available(self) -> bool:
        return True

    def session_exists(self, session: str) -> bool:
        del session
        return False

    def ensure_pane(self, **_kwargs: Any) -> None:
        raise AssertionError("ce takeover dry-run must not spawn tmux")


def build_plan(
    *,
    predecessor: str,
    harness: str,
    repo_root: Path | str,
    dry_run: bool,
    duty_manifest: Path | str | None = None,
    which: Any | None = None,
) -> TakeoverPlan:
    if harness not in SUPPORTED_HARNESSES:
        raise UnsupportedHarness(
            f"harness {harness!r} is not supported for takeover "
            f"({', '.join(sorted(SUPPORTED_HARNESSES))})"
        )
    if not dry_run:
        raise LiveTakeoverNotImplemented(
            "live takeover execution is deferred; rerun with --dry-run for the Slice B evidence packet"
        )

    root = Path(repo_root).resolve()
    evidence = _detect_predecessor_state(root, predecessor)
    ring0 = launch_runtime.preflight_launch(
        harness=harness,
        repo_root=root,
        backend=launch_runtime.HOST_BACKEND_OPT_OUT,
        tmux_adapter=_ReadOnlyTmuxProbe(),
        which=which,
    )
    actions = _hydration_actions(evidence)
    rearm_plan = _plan_rearm_actions(root, duty_manifest=duty_manifest)
    return TakeoverPlan(
        predecessor=predecessor,
        harness=harness,
        repo_root=root,
        dry_run=dry_run,
        initial_state=INITIAL_STATE,
        evidence_sources=evidence,
        ring0_report=ring0,
        hydration_actions=actions,
        rearm_plan=rearm_plan,
    )


def _detect_predecessor_state(repo_root: Path, predecessor: str) -> tuple[EvidenceSource, ...]:
    state_root = repo_root / ".ce" / "state"
    sources: list[EvidenceSource] = [
        _path_source("ce_state_root", state_root, predecessor=predecessor),
        _glob_source(
            "lifecycle_records",
            state_root,
            ("seats/*/*.yaml", "dispatches/*/events.jsonl"),
            predecessor=predecessor,
        ),
        _glob_source(
            "controller_evidence",
            state_root,
            ("controller-evidence/*.json",),
            predecessor=predecessor,
        ),
        _newest_source(
            "resume_state",
            state_root,
            ("**/*resume*", "**/*session*"),
            predecessor=predecessor,
        ),
        _path_source(
            "brain_bootstrap",
            brain_runtime.ledger_path(state_root),
            predecessor=predecessor,
        ),
        _first_existing_source(
            "active_work_ledger",
            (state_root / "active-work-ledger", repo_root / ".hermes" / "active-work-ledger"),
            predecessor=predecessor,
        ),
        _first_existing_source(
            "merge_queue",
            (
                state_root / "merge-queue",
                state_root / "queue",
                state_root / "integration-queue",
                state_root / "conveyor",
            ),
            predecessor=predecessor,
        ),
        _first_existing_source(
            "approval_wall",
            (
                state_root / "approval-wall",
                state_root / "approval_wall",
                state_root / "automerge" / "kill-switch.json",
            ),
            predecessor=predecessor,
        ),
        _first_existing_source(
            "watcher_manifest",
            (
                state_root / "watchers" / "duty-manifest.yaml",
                state_root / "duty-manifest.yaml",
                repo_root / ".ce" / "duty-manifest.yaml",
                state_root / "watchers" / "manifest.yaml",
                state_root / "watcher-manifest.yaml",
                repo_root / ".ce" / "watcher-manifest.yaml",
            ),
            predecessor=predecessor,
        ),
    ]
    return tuple(sources)


def _default_duty_manifest_paths(repo_root: Path) -> tuple[Path, ...]:
    state_root = repo_root / ".ce" / "state"
    return (
        state_root / "watchers" / "duty-manifest.yaml",
        state_root / "duty-manifest.yaml",
        repo_root / ".ce" / "duty-manifest.yaml",
        state_root / "watchers" / "manifest.yaml",
        state_root / "watcher-manifest.yaml",
        repo_root / ".ce" / "watcher-manifest.yaml",
    )


def _resolve_duty_manifest(repo_root: Path, duty_manifest: Path | str | None) -> Path:
    if duty_manifest is not None:
        return Path(duty_manifest)
    for candidate in _default_duty_manifest_paths(repo_root):
        if candidate.exists():
            return candidate
    return _default_duty_manifest_paths(repo_root)[0]


def _plan_rearm_actions(
    repo_root: Path,
    *,
    duty_manifest: Path | str | None,
) -> ReArmPlan:
    manifest_path = _resolve_duty_manifest(repo_root, duty_manifest)
    if not manifest_path.exists():
        return ReArmPlan(
            str(manifest_path),
            "missing",
            "no machine-readable duty manifest found",
        )
    try:
        raw = load_yaml(manifest_path)
    except LoaderError as exc:
        return ReArmPlan(str(manifest_path), "unreadable", str(exc))
    if not isinstance(raw, dict):
        return ReArmPlan(
            str(manifest_path),
            "invalid",
            "duty manifest must be a YAML mapping",
        )
    actions: list[ReArmAction] = []
    errors: list[str] = []
    for duty in _iter_manifest_duties(raw):
        try:
            action = _parse_rearm_duty(duty, source=str(manifest_path))
        except DutyManifestError as exc:
            errors.append(str(exc))
            continue
        if action.enabled:
            actions.append(action)
    if errors:
        return ReArmPlan(str(manifest_path), "invalid", "; ".join(errors))
    return ReArmPlan(
        str(manifest_path),
        "found",
        f"planned {len(actions)} re-arm action(s) from duty manifest",
        tuple(actions),
    )


def _iter_manifest_duties(raw: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    duties: list[dict[str, Any]] = []
    top_level = raw.get("duties")
    if isinstance(top_level, list):
        duties.extend(duty for duty in top_level if isinstance(duty, dict))
    for duty_type in ("watcher", "daemon"):
        entries = raw.get(f"{duty_type}s")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    item = dict(entry)
                    item.setdefault("type", duty_type)
                    duties.append(item)
    return tuple(duties)


def _parse_rearm_duty(raw: dict[str, Any], *, source: str) -> ReArmAction:
    duty_id = str(raw.get("id") or raw.get("name") or "").strip()
    if not duty_id:
        raise DutyManifestError("duty entry is missing id")
    duty_type = str(raw.get("type") or raw.get("kind") or "").strip().lower()
    if duty_type not in {"watcher", "daemon"}:
        raise DutyManifestError(f"duty {duty_id!r} has unsupported type {duty_type!r}")
    command = raw.get("rearm_command", raw.get("command"))
    argv = _normalize_command(command)
    if not argv:
        raise DutyManifestError(f"duty {duty_id!r} is missing rearm_command")
    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise DutyManifestError(f"duty {duty_id!r} enabled must be boolean")
    return ReArmAction(
        duty_id=duty_id,
        duty_type=duty_type,
        command=argv,
        source=source,
        enabled=enabled,
    )


def _normalize_command(command: Any) -> tuple[str, ...]:
    if isinstance(command, list):
        return tuple(str(part) for part in command if str(part).strip())
    if isinstance(command, str):
        return tuple(part for part in command.split() if part)
    return ()


def _path_source(name: str, path: Path, *, predecessor: str) -> EvidenceSource:
    if not path.exists():
        return EvidenceSource(name, str(path), "missing", "input not present")
    try:
        if path.is_dir():
            children = tuple(sorted(p for p in path.iterdir()))
            newest = _newest_mtime(children)
            matches = _matches_predecessor(children, predecessor)
            return EvidenceSource(
                name,
                str(path),
                "found",
                "directory present",
                count=len(children),
                newest_mtime=newest,
                matches_predecessor=matches,
            )
        matches = _matches_predecessor((path,), predecessor)
        return EvidenceSource(
            name,
            str(path),
            "found",
            "file present",
            count=1,
            newest_mtime=path.stat().st_mtime,
            matches_predecessor=matches,
        )
    except OSError as exc:
        return EvidenceSource(name, str(path), "unreadable", str(exc))


def _glob_source(
    name: str,
    root: Path,
    patterns: Sequence[str],
    *,
    predecessor: str,
) -> EvidenceSource:
    if not root.exists():
        return EvidenceSource(name, str(root), "missing", "state root not present")
    try:
        paths = _collect_globs(root, patterns)
        if not paths:
            return EvidenceSource(name, str(root), "missing", "no matching records present")
        return EvidenceSource(
            name,
            str(root),
            "found",
            "matching records present",
            count=len(paths),
            newest_mtime=_newest_mtime(paths),
            matches_predecessor=_matches_predecessor(paths, predecessor),
        )
    except OSError as exc:
        return EvidenceSource(name, str(root), "unreadable", str(exc))


def _newest_source(
    name: str,
    root: Path,
    patterns: Sequence[str],
    *,
    predecessor: str,
) -> EvidenceSource:
    if not root.exists():
        return EvidenceSource(name, str(root), "missing", "state root not present")
    try:
        paths = _collect_globs(root, patterns)
        if not paths:
            return EvidenceSource(name, str(root), "missing", "no resume/session records present")
        newest = max(paths, key=lambda p: p.stat().st_mtime)
        return EvidenceSource(
            name,
            str(newest),
            "found",
            "newest resume/session record selected by mtime",
            count=len(paths),
            newest_mtime=newest.stat().st_mtime,
            matches_predecessor=_matches_predecessor((newest,), predecessor),
        )
    except OSError as exc:
        return EvidenceSource(name, str(root), "unreadable", str(exc))


def _first_existing_source(
    name: str,
    paths: Sequence[Path],
    *,
    predecessor: str,
) -> EvidenceSource:
    for path in paths:
        if path.exists():
            return _path_source(name, path, predecessor=predecessor)
    return EvidenceSource(
        name,
        str(paths[0]),
        "missing",
        "none of the known input locations are present",
    )


def _collect_globs(root: Path, patterns: Sequence[str]) -> tuple[Path, ...]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(p for p in root.glob(pattern) if p.exists())
    return tuple(sorted(found))


def _newest_mtime(paths: Iterable[Path]) -> float | None:
    mtimes: list[float] = []
    for path in paths:
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(mtimes) if mtimes else None


def _matches_predecessor(paths: Iterable[Path], predecessor: str) -> tuple[str, ...]:
    needle = predecessor.strip()
    if not needle:
        return ()
    matches: list[str] = []
    for path in paths:
        if needle in path.name or _file_contains(path, needle):
            matches.append(str(path))
    return tuple(matches)


def _file_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            data = handle.read(_MAX_MATCH_BYTES)
    except OSError:
        return False
    return needle.encode("utf-8", errors="ignore") in data


def _hydration_actions(evidence: Sequence[EvidenceSource]) -> tuple[dict[str, Any], ...]:
    source_names = [source.name for source in evidence if source.status == "found"]
    gap_names = [source.name for source in evidence if source.status != "found"]
    return (
        {
            "action": "detect-predecessor-state",
            "execute": False,
            "detail": f"read evidence from {len(source_names)} source(s); retain {len(gap_names)} gap(s)",
            "sources": source_names,
            "gaps": gap_names,
        },
        {
            "action": "verify-ring0-harness",
            "execute": False,
            "detail": "reuse launch_runtime preflight and launch-spec gates",
        },
        {
            "action": "hydrate-continuity-packet",
            "execute": False,
            "detail": "assemble predecessor, launch, brain, ledger, queue, approval-wall, and watcher evidence",
        },
        {
            "action": "read-forge-housekeeping-runbook",
            "execute": False,
            "detail": "read the forge housekeeping runbook before harvest, review, gate, or closeout work",
            "document_ref": FORGE_HOUSEKEEPING_RUNBOOK,
        },
        {
            "action": "enter-awaiting-operator",
            "execute": False,
            "detail": f"start takeover in {INITIAL_STATE} pending Operator review",
        },
    )


def render_json(plan: TakeoverPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n"
