"""RV1-061 — ``ce doctor`` runtime: host detection + guard reporting.

``ce doctor`` is the operator preflight. It resolves a host-posture snapshot
(:class:`~creator_engine_validator.environment_guard.EnvironmentFacts`),
evaluates the governed-environment guard predicate, and surfaces missing
prerequisites by name with a deterministic non-zero exit on any refusal.

Detection is deliberately offline and side-effect-free: ``tmux -V`` /
``podman info`` are local probes, ``git check-ignore`` is local, and the
packaging contract is read from tracked files. No network call is made. The
detection seam (:func:`detect_environment`) is monkeypatchable so the CLI
branches can be tested without a real host.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from . import environment_guard as guard
from . import resource_bound_spec
from .packaging_runtime import interpreter_in_contract, verify_packaging_contract
from .tmux_adapter import TmuxAdapter
from .version import ce_version


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    payload: dict


def _mem_total_bytes(meminfo_path: Path | str = "/proc/meminfo") -> int | None:
    """Read MemTotal from /proc/meminfo (kB -> bytes); None when unavailable."""
    try:
        for line in Path(meminfo_path).read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _git_tracks_repo(repo_root: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return (repo_root / ".git").exists()
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _hermes_ignored(repo_root: Path) -> bool:
    probe = ".hermes/__ce_doctor_probe__"
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", probe],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        gitignore = repo_root / ".gitignore"
        if not gitignore.is_file():
            return False
        return any(
            line.strip().rstrip("/") == ".hermes"
            for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
        )
    return proc.returncode == 0


def _podman_status(runner) -> tuple[bool, bool]:
    """Return (available, rootless). Absent Podman => (False, False)."""
    if runner is None:
        if shutil.which("podman") is None:
            return (False, False)
        runner = _default_podman_runner
    try:
        proc = runner(["podman", "info", "--format", "{{.Host.Security.Rootless}}"])
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return (False, False)
    if getattr(proc, "returncode", 1) != 0:
        return (False, False)
    rootless = (getattr(proc, "stdout", "") or "").strip().lower() == "true"
    return (True, rootless)


def _default_podman_runner(argv: Sequence[str]):
    return subprocess.run(list(argv), check=False, capture_output=True, text=True)


def detect_environment(
    repo_root: Path | str,
    *,
    version_info: Sequence[int] | None = None,
    tmux_adapter: Any | None = None,
    podman_runner: Any | None = None,
    hidden_continuation: bool = False,
) -> guard.EnvironmentFacts:
    """Resolve the host-posture snapshot the guard reasons over (offline)."""
    root = Path(repo_root)
    vi = tuple(version_info) if version_info is not None else tuple(sys.version_info[:3])
    adapter = tmux_adapter if tmux_adapter is not None else TmuxAdapter()
    tmux_available = adapter.is_available()
    podman_available, podman_rootless = _podman_status(podman_runner)
    is_git = _git_tracks_repo(root)
    packaging = verify_packaging_contract(root)
    awl_root = root / ".hermes" / "active-work-ledger"
    return guard.EnvironmentFacts(
        version_info=vi,
        repo_root_is_git=is_git,
        hermes_ignored=_hermes_ignored(root) if is_git else False,
        tmux_available=tmux_available,
        podman_available=podman_available,
        podman_rootless=podman_rootless,
        uv_available=shutil.which("uv") is not None,
        packaging=packaging,
        hidden_continuation=hidden_continuation,
        active_work_ledger_present=awl_root.is_dir(),
    )


def run_doctor(
    repo_root: Path | str,
    *,
    require_visible_launch: bool = False,
    require_worker: bool = False,
    check_packaging: bool = True,
    version_info: Sequence[int] | None = None,
    facts: guard.EnvironmentFacts | None = None,
    tmux_adapter: Any | None = None,
    podman_runner: Any | None = None,
    hidden_continuation: bool = False,
    mem_total_bytes: int | None = None,
) -> DoctorReport:
    """Evaluate the guard and assemble a deterministic, JSON-safe report."""
    if facts is None:
        facts = detect_environment(
            repo_root,
            version_info=version_info,
            tmux_adapter=tmux_adapter,
            podman_runner=podman_runner,
            hidden_continuation=hidden_continuation,
        )
    result = guard.evaluate(
        facts,
        require_visible_launch=require_visible_launch,
        require_worker=require_worker,
        check_packaging=check_packaging,
    )
    payload = result.to_dict()
    payload["repo_root"] = str(Path(repo_root))
    # ce-ops#25: surface the derived CE version identity beside the packaging
    # health line (local preflight telemetry, Open-Q3 — never attestation).
    payload["ce_version"] = ce_version(repo_root)
    payload["prerequisites"] = {
        "python_interpreter": ".".join(str(x) for x in facts.version_info),
        "python_in_contract": interpreter_in_contract(facts.version_info),
        "repo_root_is_git": facts.repo_root_is_git,
        "hermes_state_ignored": facts.hermes_ignored,
        "active_work_ledger_present": facts.active_work_ledger_present,
        "tmux_available": facts.tmux_available,
        "uv_available": facts.uv_available,
        "podman_available": facts.podman_available,
        "podman_rootless": facts.podman_rootless,
        "wheelhouse_offline": bool(facts.packaging.ok) if facts.packaging else None,
    }
    payload["requested"] = {
        "require_visible_launch": require_visible_launch,
        "require_worker": require_worker,
        "check_packaging": check_packaging,
    }
    # v3.5-F: the §4.4 host-class default materialization. Doctor EMITS the
    # resource policy fragment for the Operator to ratify INTO the policy file
    # — launch never computes bounds silently; absent MemTotal -> None (never
    # fabricated).
    mem_total = mem_total_bytes if mem_total_bytes is not None else _mem_total_bytes()
    payload["resource_policy_recommendation"] = (
        resource_bound_spec.host_class_defaults(mem_total) if mem_total else None
    )
    return DoctorReport(ok=result.ok, payload=payload)


def render_human(report: DoctorReport) -> str:
    lines = [
        f"ce doctor: {'PASS' if report.ok else 'FAIL'} "
        f"(repo_root={report.payload['repo_root']}, version={report.payload['ce_version']})"
    ]
    for check in report.payload["checks"]:
        if not check["applicable"]:
            mark = "skip"
        elif check["ok"]:
            mark = "ok"
        else:
            mark = "FAIL"
        lines.append(f"  [{mark}] {check['clause']} {check['name']}: {check['detail']}")
    if not report.ok:
        refused = ", ".join(report.payload["refused_clauses"])
        lines.append(f"  refused clauses: {refused}")
    return "\n".join(lines)
