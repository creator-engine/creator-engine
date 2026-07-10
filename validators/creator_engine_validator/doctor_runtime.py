"""RV1-061 — ``ce doctor`` runtime: host detection + guard reporting.

``ce doctor`` is the operator preflight. It resolves a host-posture snapshot
(:class:`~creator_engine_validator.environment_guard.EnvironmentFacts`),
evaluates the governed-environment guard predicate, and surfaces missing
prerequisites by name with a deterministic non-zero exit on any refusal.

Detection is deliberately bounded and side-effect-free: ``tmux -V`` /
``podman info`` are local probes, ``git check-ignore`` is local, and the
packaging contract is read from tracked files. When tenant brain recall is
configured, doctor also runs a bounded 1s endpoint reachability probe. The
detection seam (:func:`detect_environment`) is monkeypatchable so the CLI
branches can be tested without a real host.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from . import bootstrap_runtime
from . import environment_guard as guard
from . import launch_runtime
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


# --- ce-ops#197 PR-4: onboard phase-1 probes ---------------------------------
# The low-TMPDIR + PATH-gap probes `ce onboard` consumes. Both are pure, offline,
# side-effect-free, and injectable, mirroring the rest of doctor_runtime.

#: Free-space floor below which a tmpfs $TMPDIR risks exhausting mid-wheelhouse
#: build (friction #3). The published install.sh stages ~hundreds of MB; 512 MiB
#: is a conservative margin. Onboard only SURFACES this; install.sh owns the
#: home-staging fallback (PR-2).
LOW_TMPDIR_FLOOR_BYTES = 512 * 1024 * 1024


def probe_low_tmpdir(
    tmpdir: str | None = None,
    *,
    floor_bytes: int = LOW_TMPDIR_FLOOR_BYTES,
    disk_usage: Any | None = None,
) -> bool:
    """True when $TMPDIR free space is below the wheelhouse-build floor (#3).

    Offline + best-effort: an unreadable / missing path returns ``False`` (the
    probe never refuses on its own — it surfaces a hint for onboard).
    """
    path = tmpdir if tmpdir is not None else (os.environ.get("TMPDIR") or "/tmp")
    usage = disk_usage if disk_usage is not None else shutil.disk_usage
    try:
        return usage(path).free < floor_bytes
    except (OSError, ValueError):
        return False


def probe_path_gap(
    *,
    path_value: str | None = None,
    home: str | None = None,
) -> bool:
    """True when ``~/.local/bin`` is absent from PATH (#2 / #212).

    The governed launcher resolves the harness on the seat's actual launch PATH;
    a missing ``~/.local/bin`` is the precise drift that yields exit-127. Onboard
    surfaces this so the profile-PATH writer (phase 4) is run.
    """
    resolved_home = home if home is not None else os.environ.get("HOME")
    if not resolved_home:
        return False
    local_bin = str(Path(resolved_home) / ".local" / "bin")
    raw = path_value if path_value is not None else os.environ.get("PATH", "")
    entries = {p for p in raw.split(os.pathsep) if p}
    return local_bin not in entries


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


def detect_ce_dogfood_posture(
    repo_root: Path | str,
    *,
    argv0: str | None = None,
    module_file: Path | str | None = None,
) -> dict[str, Any]:
    """Classify whether this process is dogfooding installed CE.

    ``source_checkout`` means the imported package bytes resolve under this
    checkout's ``validators/`` tree. ``installed`` means they do not. A true
    dogfood posture requires both installed package bytes and a console-script
    invocation (``ce``/``cev3``), not ``python -m`` from a checkout.
    """
    root = Path(repo_root).resolve()
    module_path = Path(module_file) if module_file is not None else Path(__file__)
    try:
        resolved_module = module_path.resolve()
    except OSError:
        resolved_module = module_path.absolute()
    source_pkg = root / "validators" / "creator_engine_validator"
    try:
        resolved_module.relative_to(source_pkg.resolve())
        package_origin = "source_checkout"
    except ValueError:
        package_origin = "installed"

    raw_argv0 = argv0 if argv0 is not None else sys.argv[0]
    argv_name = Path(raw_argv0).name
    if argv_name in {"ce", "cev3", "creator-engine-validator"}:
        invocation = "console_script"
    elif argv_name in {"ce_cli.py", "v3_cli.py", "__main__.py"}:
        invocation = "python_module"
    elif raw_argv0.endswith("creator_engine_validator.ce_cli") or raw_argv0.endswith(
        "creator_engine_validator.v3_cli"
    ):
        invocation = "python_module"
    else:
        invocation = "unknown"

    return {
        "invocation": invocation,
        "argv0": raw_argv0,
        "package_origin": package_origin,
        "installed_ce": invocation == "console_script" and package_origin == "installed",
    }


_CE_SOURCE_TREE_MARKERS = (
    Path("validators") / "creator_engine_validator" / "__init__.py",
    Path("validators") / "creator_engine_validator" / "doctor_runtime.py",
    Path("validators") / "creator_engine_validator" / "packaging_runtime.py",
    Path("validators") / "tests" / "conftest.py",
    Path("docs") / "governance" / "V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md",
)


def is_ce_source_tree_context(repo_root: Path | str) -> bool:
    """True when ``repo_root`` is the Creator Engine source checkout.

    RED-G-6 is a CE developer/source-tree packaging contract. The signal avoids
    the packaging files under test (``validators/pyproject.toml``,
    ``validators/wheelhouse``, ``validators/uv.lock``) so real packaging drift
    still refuses inside the CE checkout.
    """
    root = Path(repo_root)
    return all((root / marker).is_file() for marker in _CE_SOURCE_TREE_MARKERS)


def detect_environment(
    repo_root: Path | str,
    *,
    version_info: Sequence[int] | None = None,
    tmux_adapter: Any | None = None,
    podman_runner: Any | None = None,
    hidden_continuation: bool = False,
    argv0: str | None = None,
) -> guard.EnvironmentFacts:
    """Resolve the host-posture snapshot the guard reasons over (offline)."""
    root = Path(repo_root)
    vi = tuple(version_info) if version_info is not None else tuple(sys.version_info[:3])
    adapter = tmux_adapter if tmux_adapter is not None else TmuxAdapter()
    tmux_available = adapter.is_available()
    podman_available, podman_rootless = _podman_status(podman_runner)
    is_git = _git_tracks_repo(root)
    ce_source_tree = is_ce_source_tree_context(root)
    packaging = verify_packaging_contract(root) if ce_source_tree else None
    awl_root = root / ".hermes" / "active-work-ledger"
    dogfood = detect_ce_dogfood_posture(root, argv0=argv0)
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
        ce_invocation=str(dogfood["invocation"]),
        ce_package_origin=str(dogfood["package_origin"]),
        ce_dogfood_installed=bool(dogfood["installed_ce"]),
        ce_source_tree_context=ce_source_tree,
    )


def run_doctor(
    repo_root: Path | str,
    *,
    require_visible_launch: bool = False,
    require_worker: bool = False,
    check_packaging: bool = True,
    require_installed_ce: bool = False,
    target_python: Path | str | None = None,
    check_seat_env: bool = False,
    version_info: Sequence[int] | None = None,
    facts: guard.EnvironmentFacts | None = None,
    tmux_adapter: Any | None = None,
    podman_runner: Any | None = None,
    hidden_continuation: bool = False,
    mem_total_bytes: int | None = None,
    argv0: str | None = None,
    harness: str = launch_runtime.DEFAULT_HARNESS,
    which: Any | None = None,
) -> DoctorReport:
    """Evaluate the guard and assemble a deterministic, JSON-safe report."""
    if facts is None:
        facts = detect_environment(
            repo_root,
            version_info=version_info,
            tmux_adapter=tmux_adapter,
            podman_runner=podman_runner,
            hidden_continuation=hidden_continuation,
            argv0=argv0,
        )
    result = guard.evaluate(
        facts,
        require_visible_launch=require_visible_launch,
        require_worker=require_worker,
        check_packaging=check_packaging,
        require_installed_ce=require_installed_ce,
    )
    payload = result.to_dict()
    payload["repo_root"] = str(Path(repo_root))
    resolved_target_python = (
        Path(target_python)
        if target_python is not None
        else bootstrap_runtime.default_target_python(Path(repo_root))
    )
    seat_env_applicable = (
        check_seat_env
        or target_python is not None
        or resolved_target_python.is_file()
    )
    seat_env_check = bootstrap_runtime.doctor_check(
        resolved_target_python,
        applicable=seat_env_applicable,
    )
    payload["checks"].append(seat_env_check)
    if seat_env_check["applicable"] and not seat_env_check["ok"]:
        payload["refused_clauses"].append(seat_env_check["clause"])
    payload["ok"] = payload["ok"] and not (
        seat_env_check["applicable"] and not seat_env_check["ok"]
    )
    recall_status = launch_runtime.probe_controller_recall_endpoint(repo_root)
    payload["checks"].append(
        {
            "clause": "CE-BRAIN-RECALL",
            "name": "brain recall endpoint",
            "applicable": recall_status.get("state") != "unconfigured",
            "ok": recall_status.get("state") != "unavailable",
            "detail": recall_status.get("line") or str(recall_status.get("reason", "")),
            "status": recall_status,
        }
    )
    harness_check = launch_runtime.harness_binary_check(harness, which=which)
    if not require_visible_launch and not harness_check["ok"]:
        harness_check = {
            **harness_check,
            "severity": "warning",
            "detail": (
                f"{harness_check['detail']}; advisory in default doctor mode "
                "and required when --require-visible-launch is set"
            ),
        }
    payload["checks"].append(harness_check)
    if require_visible_launch and harness_check["applicable"] and not harness_check["ok"]:
        payload["refused_clauses"].append(harness_check["clause"])
        payload["ok"] = False
    # ce-ops#25: surface the derived CE version identity beside the packaging
    # health line (local preflight telemetry, Open-Q3 — never attestation).
    payload["ce_version"] = ce_version(repo_root)
    dependency_wheelhouse_ok = None
    dependency_wheelhouse_violations: list[str] = []
    if facts.packaging:
        dependency_wheelhouse_ok = bool(
            facts.packaging.details.get("dependency_wheelhouse_ok", facts.packaging.ok)
        )
        dependency_wheelhouse_violations = list(
            facts.packaging.details.get("dependency_wheelhouse_violations", [])
        )
    wheelhouse_wheels = (
        list(facts.packaging.details.get("wheelhouse_wheels", []))
        if facts.packaging
        else []
    )
    first_party_app_wheel_committed = False
    if facts.packaging:
        first_party_app_wheel_committed = bool(
            facts.packaging.details.get(
                "first_party_app_wheel_committed",
                any(
                    name.startswith("creator_engine_validator-") and name.endswith(".whl")
                    for name in wheelhouse_wheels
                ),
            )
        )
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
        "wheelhouse_offline": dependency_wheelhouse_ok,
        "dependency_wheelhouse_offline": dependency_wheelhouse_ok,
        "dependency_wheelhouse_violations": dependency_wheelhouse_violations,
        "first_party_app_wheel_committed": first_party_app_wheel_committed,
        "ce_dogfood_invocation": facts.ce_invocation,
        "ce_package_origin": facts.ce_package_origin,
        "ce_dogfood_installed": facts.ce_dogfood_installed,
        "ce_source_tree_context": facts.ce_source_tree_context,
        "target_python": str(resolved_target_python),
        "target_python_exists": resolved_target_python.is_file(),
        "controller_seat_app_installed": (
            bool(seat_env_check["ok"]) if seat_env_check["applicable"] else None
        ),
        "configured_harness": harness,
        "configured_harness_binary": harness_check["binary"],
        "configured_harness_binary_resolved": harness_check["resolved"],
    }
    payload["requested"] = {
        "require_visible_launch": require_visible_launch,
        "require_worker": require_worker,
        "check_packaging": check_packaging,
        "require_installed_ce": require_installed_ce,
        "check_seat_env": check_seat_env,
        "target_python": str(resolved_target_python),
        "harness": harness,
    }
    # ce-ops#197 PR-4: the onboard phase-1 probes. Advisory-only (never refuse on
    # their own) — `ce onboard` reads these to surface friction #3 (low /tmp) and
    # to decide whether the profile-PATH writer (phase 4) is warranted (#2/#212).
    payload["onboard_probes"] = {
        "low_tmpdir": probe_low_tmpdir(),
        "path_gap": probe_path_gap(),
    }
    # v3.5-F: the §4.4 host-class default materialization. Doctor EMITS the
    # resource policy fragment for the Operator to ratify INTO the policy file
    # — launch never computes bounds silently; absent MemTotal -> None (never
    # fabricated).
    mem_total = mem_total_bytes if mem_total_bytes is not None else _mem_total_bytes()
    payload["resource_policy_recommendation"] = (
        resource_bound_spec.host_class_defaults(mem_total) if mem_total else None
    )
    return DoctorReport(ok=bool(payload["ok"]), payload=payload)


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
        elif (
            check.get("clause") == "CE-BRAIN-RECALL"
            or check.get("clause") not in report.payload["refused_clauses"]
        ):
            mark = "WARN"
        else:
            mark = "FAIL"
        lines.append(f"  [{mark}] {check['clause']} {check['name']}: {check['detail']}")
    if not report.ok:
        refused = ", ".join(report.payload["refused_clauses"])
        lines.append(f"  refused clauses: {refused}")
    return "\n".join(lines)
