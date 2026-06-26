"""CE v3 work-driving CLI (G-7.0) — the distinct v3 entry point (``cev3``).

Drives the OUTER-loop Scope lifecycle from the developer's terminal: file a
Scope (the Frame→Shape output), place the bet (``ratify``), assemble the governed
dispatch (the front gate), and inspect projected state — surfacing the CANON
vocabulary (the Scope-card labels Goal / Done-when / Budget / Change-type / Ready
and the stage phases Frame → Shape → Build → Review → Ship) OVER the conserved
schema fields (``intent`` / ``acceptance_criteria`` / ``appetite`` /
``mutation_class`` + the spec-lifecycle ``state``). The labels are a presentation
skin; the schema fields and the 6-state machine are conserved verbatim.

DISTINCT entry point: ``cev3`` is a SEPARATE ``console_script`` backed by this
v3-classified module — added ALONGSIDE the retained v1 ``ce`` launcher
(``ce_cli``), never as a subcommand on it (that would create a ``shared→v3``
import edge; see ``_versions.BASELINE_SHARED_TO_VERSION_ALLOWLIST``). v1 is
retained whole; this surface is purely additive.

USER-FACING NAME (Operator-ratified design-lane directive, 2026-06-08):
``cev3`` is the INTERNAL console_script name — it exists ONLY to avoid the v1
``ce`` collision in this coexistence monorepo; users never type it. The
USER-FACING command is ``ce`` (``CE_CMD``): the pilot installs v3 ONLY (no v1
``ce`` to collide with), so the 7E installer exposes this CLI AS ``ce``, and all
user-facing output + help here speaks ``ce`` (the docs are the user-facing truth).
A version-stamped user command (``cev3``/``cev4``) is the anti-pattern this avoids.

Local state (G-4.1): Scope artifacts persist under the neutral, CE-namespaced
local-state root ``_versions.V3_LOCAL_STATE_ROOT`` (``.ce/state``) — NEVER the v1
bootstrapping-harness local-state root (kept frozen for v1 only) and NEVER a
per-harness tool dir (``.claude/``). ``--root`` overrides the default (tests drive
a tmp root). The ``v3_naming_hygiene`` check guards this module's surface.

Boundary (CI-pure; the LIVE seam is DEFERRED): ``drive`` assembles the run inputs
via ``coordination.assemble_dispatch`` (the front gate — REFUSES unless the Scope
is DoR-ready AND ratified) and PRINTS the resulting ``DispatchPlan`` (whose
``runtime_policy`` already carries the appetite→cap ``run`` spend envelope the G-5
gate enforces unchanged). Actually spawning the run
(``run_assembly.make_run_driver`` / ``orchestrator.run_plan``) is the deferred
live seam — this CLI produces the inputs, exactly as G-6 landed the pure assembly
and G-4 / G-5 deferred their live taps. The branded session frame + unified
status line (G-7.1), the shaping detect-and-offer dialogue (G-7.2), and the
◆ CE Completion Report (G-7.3) land in later G-7 slices; this slice is the
work-driving spine they hang off — ``session`` / ``artifacts`` are thin seams here.

Value-free: a Scope carries intent / acceptance-criteria / appetite /
mutation_class / opaque ratification digests — NEVER a credential, secret, raw
account, host, or installation identifier. Defensive only — it governs CE's own
work intake; never an offensive capability.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from . import (
    authority_resolver,
    coordination,
    dispatch_worktree,
    evidence_sink,
    onboard_apply,
    onboard_apply_live,
    playbook_runtime,
    runtime_evidence_spine,
    seat_reaper,
    secret_identity,
    v3_forge_join,
    v3_installer,
    v3_report,
    v3_seat_bridge,
    v3_session,
    v3_shaping,
    version,
    work_claims,
)
from ._versions import V3_LOCAL_STATE_ROOT
from .forge import (
    RulesetBypassActor,
    RulesetPolicy,
    allow_auto_merge,
    configure_repo,
    configure_squash_only,
    delete_ruleset,
    upsert_ruleset,
)
from .forge import approval_capability, fleet_status, integrator_belt, seats_status
from .forge.github_repo_config import ForgeConfigError
from .runner import usage_tap
from .runner.backend import CollectedEvidence
from .schema import validate_with_schema
from .sec7_forge_guard import sec7_forge_refusal

#: Where Scope artifacts live, relative to the local-state ``--root``.
SCOPES_SUBDIR = "scopes"
_SCOPE_SUFFIX = ".scope.yaml"
ESCALATIONS_SUBDIR = "escalations"
_ESCALATION_SCHEMA = "schemas/escalation-record.schema.yaml"

#: The conserved Scope-record envelope constants (``schemas/scope.schema.yaml``).
_KIND = "scope-record"
_RECORD_TYPE = "scope"
_SCHEMA_VERSION = "1"

#: Scope-id slug (mirrors ``schemas/scope.schema.yaml``'s ``scope_id`` pattern).
_SCOPE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_ESCALATION_ID_RE = re.compile(r"(^[a-z][a-z0-9-]{2,63}$)|(^[0-9a-f]{64}$)")
#: Value-free 64-hex opaque digest (the bet's ``approver_ref``).
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

#: The user-facing Scope-card labels (the canon skin) over the conserved fields.
CARD_LABELS = {
    "intent": "Goal",
    "acceptance_criteria": "Done-when",
    "appetite": "Budget",
    "mutation_class": "Change-type",
}

#: The brand prefix every CE line carries (``pilot-uiux-model.md``).
_BRAND = "◆ CE"  # ◆ CE

#: The USER-FACING command name (Operator-ratified directive). Users type ``ce``
#: (the pilot installs v3-only; the 7E installer exposes this CLI as ``ce``). The
#: internal console_script is ``cev3`` (monorepo coexistence only) — never shown.
CE_CMD = "ce"

#: In-product help — the SEED of the in-product guide (content reused from
#: ``docs/guide/understanding-ce.md``, not re-authored). ``ce guide`` prints it.
_GUIDE = """\
◆ Creator Engine — your own coding agent, under governance.

CE wraps a structured, stateful, artifact-aware workflow around the agent you
already use, so real work is planned, tracked, checked, and merged on purpose.
The thing that decides whether work is good lives OUTSIDE the agent — you judge
artifacts (a plan, a diff, the evidence, the PR), not a transcript.

The five stages — Frame → Shape → Build → Review → Ship:
  Frame    understand the problem (just thinking; nothing tracked yet)
  Shape    turn it into a bet — a Scope (Goal · Done-when · Budget · Change-type)
  Build    the agent does the work in one governed, sandboxed run
  Review   the result is graded against your Done-when — with evidence, not vibes
  Ship     the governed finish: a merged PR, delivered research, or a reasoned no-change

The Scope card (your unit of work):
  Goal         what you're trying to do
  Done-when    the checks that say it's finished (these get graded)
  Budget       a fixed cap you commit — not a time estimate (YOUR call to set)
  Change-type  what kind of change, and how risky
  Ready        a ✓ once the other four are valid — then you place the bet

A few things worth knowing:
  • You set the Budget. The agent never decides how much you'll spend.
  • The agent can make a change safer on its own, but only you can make it riskier.
  • Nothing is tracked until you say yes. Plain chat stays plain chat.

Commands:  ce session · ce scope · ce shape · ce ratify · ce drive · ce report
           ce status · ce show · ce artifacts · ce onboard · ce guide

These friendly words are a clear skin over a precise state machine — you can
always look underneath. Full guide: docs/guide/understanding-ce.md ; pilot path:
docs/guide/pilot-runbook.md.
"""


# ---------------------------------------------------------------------------
# Storage seam — Scope artifacts under .ce/state/scopes/ (path-neutral via --root)
# ---------------------------------------------------------------------------
def _scopes_dir(root: Path) -> Path:
    return root / SCOPES_SUBDIR


def _scope_path(root: Path, scope_id: str) -> Path:
    return _scopes_dir(root) / f"{scope_id}{_SCOPE_SUFFIX}"


def _scope_bytes(scope: dict[str, Any]) -> str:
    """Deterministic YAML serialization (sorted keys, block style)."""
    return yaml.safe_dump(scope, sort_keys=True, default_flow_style=False)


def _dump_scope(root: Path, scope: dict[str, Any]) -> Path:
    _scopes_dir(root).mkdir(parents=True, exist_ok=True)
    path = _scope_path(root, str(scope["scope_id"]))
    path.write_text(_scope_bytes(scope), encoding="utf-8")
    return path


def _load_scope(root: Path, scope_id: str) -> dict[str, Any]:
    path = _scope_path(root, scope_id)
    if not path.is_file():
        raise FileNotFoundError(f"no Scope {scope_id!r} under {_scopes_dir(root)}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"malformed Scope artifact at {path}")
    return data


def _iter_scopes(root: Path) -> list[dict[str, Any]]:
    d = _scopes_dir(root)
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob(f"*{_SCOPE_SUFFIX}")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("kind") == _KIND:
            out.append(data)
    return out


def _content_sha(scope: dict[str, Any]) -> str:
    """SHA256 of the ratified Scope content (excluding the bet itself).

    The bet (``ratification.ratified_scope_sha``) pins to the Scope body it was
    placed on — an opaque content digest, never the Scope text. Recomputed
    canonically (sorted keys) so it is deterministic.
    """
    body = {k: v for k, v in scope.items() if k != "ratification"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Rendering — surface the canon skin (Scope card + stage phase)
# ---------------------------------------------------------------------------
def _projection(scope: dict[str, Any], root: Path | None = None) -> dict[str, str]:
    """The {state, phase, board} projection over the conserved spec-lifecycle.

    v3.1-G1b: when ``root`` is given and an UNcollected dispatch record exists for
    the Scope, the projection feeds ``dispatched=True`` so a live run is visible
    (→ in_progress / Build / RUN) — the read-model sees the spawned seat. A
    collected dispatch no longer drives the signal (the run has folded its
    evidence; the Scope projects off its own committed state again).
    """
    dispatched = False
    scope_id = scope.get("scope_id")
    if root is not None and scope_id:
        dispatched = _has_uncollected_dispatch(root, str(scope_id))
    return coordination.project_scope_state(scope, dispatched=dispatched)


def _card_line(scope: dict[str, Any], root: Path | None = None) -> str:
    """One-line Scope card in the canon vocabulary (the skin over the fields)."""
    proj = _projection(scope, root)
    ready, _ = coordination.scope_is_ready(scope)
    ac = scope.get("acceptance_criteria") or []
    appetite = scope.get("appetite") or {}
    budget = (
        f"{appetite.get('amount')}{appetite.get('unit')}"
        if appetite.get("amount") is not None
        else "—"
    )
    goal_mark = "✓" if scope.get("intent") else "—"
    ready_mark = "✓" if (ready and coordination.is_ratified(scope)) else "—"
    return (
        f"{_BRAND} · {proj['phase']} → {scope.get('scope_id')!r}  "
        f"(Goal {goal_mark} · Done-when {len(ac)} · Budget {budget} · "
        f"Change-type {scope.get('mutation_class')} · Ready {ready_mark})"
    )


def _phase_counts(scopes: list[dict[str, Any]], root: Path | None = None) -> dict[str, int]:
    counts = {phase: 0 for phase in coordination.COGNITIVE_PHASES}
    for s in scopes:
        counts[_projection(s, root)["phase"]] += 1
    return counts


def _emit(args: argparse.Namespace, code: int, lines: list[str], payload: dict[str, Any]) -> int:
    """Print JSON (``--json``) or the human lines; return the exit code."""
    if getattr(args, "json_output", False):
        print(json.dumps({"ok": code == 0, **payload}, indent=2, sort_keys=True))
    else:
        for ln in lines:
            print(ln)
    return code


# ce-ops#191 (N5) — fail-closed refusals carry their INSTALL_FAILURE_CLASS as the
# leading token of the message. A *missing-dependency* refusal (this marker) is the one
# class the read-only ``--inventory`` awareness path degrades gracefully on (per the N1
# reconciliation): inventory is the awareness artifact, so a missing bootstrap dependency
# surfaces as a WARN row (exit 0), NOT a refusal. Every OTHER refusal class — and the
# ``--plan``/``--apply``/bootstrap path — keeps N5's clean fail-closed refusal.
_MISSING_DEPENDENCY_MARKER = "missing_bootstrap_dependency"
_MISSING_GIT_REFUSAL = (
    f"{_MISSING_DEPENDENCY_MARKER}: required command missing: git. "
    "Remediation: install Git with your OS package manager, then re-run this installer."
)


def _is_missing_dependency_refusal(exc: Exception) -> bool:
    """A refusal whose failure class is ``missing_bootstrap_dependency``.

    Used by the read-only ``--inventory`` path to distinguish a missing-tool
    refusal (degrade to a WARN row, exit 0) from every other fail-closed refusal
    (e.g. a tampered spec), which must still refuse.
    """
    return str(exc).startswith(f"{_MISSING_DEPENDENCY_MARKER}:")


def _require_git() -> None:
    if not _which("git"):
        raise v3_installer.InstallRefused(_MISSING_GIT_REFUSAL)


def _git_read(root: Path, *args: str) -> str | None:
    _require_git()
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        raise v3_installer.InstallRefused(_MISSING_GIT_REFUSAL) from exc
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _git_run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    _require_git()
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as exc:
        raise v3_installer.InstallRefused(_MISSING_GIT_REFUSAL) from exc


def _github_repo_from_remote(remote: str | None) -> str | None:
    if not remote:
        return None
    remote = remote.strip()
    patterns = (
        r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
        r"^https?://[^/]*github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.search(pattern, remote)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def _workflow_triggers(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, dict):
        return [str(key) for key in raw]
    return []


def _detect_ci_workflows(project_root: Path) -> dict[str, Any]:
    workflows: list[dict[str, Any]] = []
    workflow_dir = project_root / ".github" / "workflows"
    candidates = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]) if workflow_dir.is_dir() else []
    for path in candidates:
        rel = path.relative_to(project_root).as_posix()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        name = str(data.get("name") or path.stem)
        raw_jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else {}
        jobs = sorted(str(job_id) for job_id in raw_jobs)
        check_names: list[str] = []
        for job_id, job in sorted(raw_jobs.items()):
            job_name = str(job.get("name") or job_id) if isinstance(job, dict) else str(job_id)
            check_names.append(job_name)
            if name:
                check_names.append(f"{name} / {job_name}")
        workflows.append({
            "path": rel,
            "name": name,
            "triggers": _workflow_triggers(data.get("on", data.get(True))),
            "jobs": jobs,
            "check_names": sorted(set(check_names)),
            "ce_validate": (
                rel == onboard_apply.CE_WORKFLOW_PATH
                or "Validate governance artifacts" in check_names
            ),
        })
    return {
        "workflows": workflows,
        "current_required_checks": [],
        "workflow_present": any(w["ce_validate"] for w in workflows),
    }


def _package_manager(project_root: Path) -> str:
    if (project_root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (project_root / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _detect_test_commands(project_root: Path) -> dict[str, Any]:
    commands: list[dict[str, str]] = []

    def add(command: str, source: str) -> None:
        if command and command not in {item["command"] for item in commands}:
            commands.append({"command": command, "source": source, "confidence": "detected"})

    if (project_root / "pytest.ini").is_file():
        add("python -m pytest", "pytest.ini")
    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        tool = data.get("tool", {}) if isinstance(data, dict) else {}
        project = data.get("project", {}) if isinstance(data, dict) else {}
        deps = []
        if isinstance(project, dict):
            deps.extend(project.get("dependencies") or [])
            optional = project.get("optional-dependencies") or {}
            if isinstance(optional, dict):
                for group in optional.values():
                    deps.extend(group or [])
        if (isinstance(tool, dict) and "pytest" in tool) or any("pytest" in str(dep) for dep in deps):
            add("python -m pytest", "pyproject.toml")
    if (project_root / "tox.ini").is_file():
        add("tox", "tox.ini")
    if (project_root / "noxfile.py").is_file():
        add("nox", "noxfile.py")
    package_json = project_root / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        test_script = (data.get("scripts") or {}).get("test") if isinstance(data, dict) else None
        if isinstance(test_script, str) and test_script and "no test specified" not in test_script:
            add(f"{_package_manager(project_root)} test", "package.json")
    if (project_root / "go.mod").is_file():
        add("go test ./...", "go.mod")
    if (project_root / "Cargo.toml").is_file():
        add("cargo test", "Cargo.toml")
    if (project_root / "pom.xml").is_file():
        add("mvn test", "pom.xml")
    if (project_root / "build.gradle").is_file() or (project_root / "build.gradle.kts").is_file():
        add("./gradlew test" if (project_root / "gradlew").is_file() else "gradle test", "build.gradle")
    makefile = project_root / "Makefile"
    if makefile.is_file():
        try:
            if re.search(r"(?m)^test\s*:", makefile.read_text(encoding="utf-8")):
                add("make test", "Makefile")
        except OSError:
            pass
    justfile = project_root / "justfile"
    if justfile.is_file():
        try:
            if re.search(r"(?m)^test(?:\s|:)", justfile.read_text(encoding="utf-8")):
                add("just test", "justfile")
        except OSError:
            pass
    return {"commands": commands}


def _top_changed_dirs(project_root: Path) -> list[str]:
    output = _git_read(project_root, "log", "--name-only", "--pretty=format:", "-n", "50")
    if not output:
        return []
    counts: dict[str, int] = {}
    for raw in output.splitlines():
        path = raw.strip()
        if not path:
            continue
        first = path.split("/", 1)[0]
        counts[first] = counts.get(first, 0) + 1
    return [name for name, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]]


def _branch_candidates(branches: list[str], current: str | None) -> list[dict[str, Any]]:
    names = [b.removeprefix("origin/") for b in branches if b and "HEAD" not in b]
    if current:
        names.append(current)
    prefixes: dict[str, int] = {}
    for name in names:
        if "/" in name:
            candidate = name.split("/", 1)[0] + "/*"
            prefixes[candidate] = prefixes.get(candidate, 0) + 1
        elif re.match(r"^v\d+[a-z0-9-]*", name):
            prefixes["v*-*"] = prefixes.get("v*-*", 0) + 1
    if not prefixes:
        return []
    total = max(len(names), 1)
    return [
        {"value": value, "confidence": round(count / total, 2), "source": "git-branches"}
        for value, count in sorted(prefixes.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]


def _commit_style_candidates(subjects: list[str]) -> list[dict[str, Any]]:
    if not subjects:
        return []
    conventional = sum(
        1 for subject in subjects
        if re.match(r"^(feat|fix|docs|test|tests|refactor|chore|build|ci|perf|style|revert)(\([^)]+\))?:", subject)
    )
    ratio = conventional / len(subjects)
    if ratio >= 0.5:
        return [{"value": "conventional-commits", "confidence": round(ratio, 2), "source": "git-log"}]
    return [{"value": "short-imperative-subject", "confidence": round(1 - ratio, 2), "source": "git-log"}]


def _detect_git_history(project_root: Path) -> dict[str, Any]:
    inside = _git_read(project_root, "rev-parse", "--is-inside-work-tree") == "true"
    origin = _github_repo_from_remote(_git_read(project_root, "config", "--get", "remote.origin.url"))
    if not inside:
        return {
            "mode": "absent",
            "present": False,
            "head_sha": None,
            "default_branch": None,
            "commit_count": 0,
            "dirty": False,
            "branches": [],
            "commit_subjects": [],
            "origin_remote": origin,
        }
    head = _git_read(project_root, "rev-parse", "--verify", "HEAD")
    mode = "git_history_present" if head else "absent"
    default_branch = _git_read(project_root, "symbolic-ref", "refs/remotes/origin/HEAD", "--short")
    if default_branch and default_branch.startswith("origin/"):
        default_branch = default_branch.split("/", 1)[1]
    default_branch = default_branch or _git_read(project_root, "branch", "--show-current")
    commit_count_raw = _git_read(project_root, "rev-list", "--count", "HEAD") if head else "0"
    merge_count_raw = _git_read(project_root, "rev-list", "--merges", "--count", "HEAD") if head else "0"
    dirty = bool(_git_read(project_root, "status", "--porcelain", "--untracked-files=no"))
    branches_raw = _git_read(project_root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    subjects_raw = _git_read(project_root, "log", "-20", "--pretty=%s") if head else ""
    return {
        "mode": mode,
        "present": mode == "git_history_present",
        "head_sha": head,
        "default_branch": default_branch,
        "commit_count": int(commit_count_raw or 0),
        "last_commit_time": _git_read(project_root, "log", "-1", "--format=%cI") if head else None,
        "tags_present": bool(_git_read(project_root, "tag")),
        "merge_commits": int(merge_count_raw or 0),
        "top_changed_dirs": _top_changed_dirs(project_root) if head else [],
        "dirty": dirty,
        "branches": branches_raw.splitlines() if branches_raw else [],
        "commit_subjects": subjects_raw.splitlines() if subjects_raw else [],
        "origin_remote": origin,
    }


def _detect_brownfield_project(project_root: Path) -> dict[str, Any]:
    history = _detect_git_history(project_root)
    branches = history.pop("branches", [])
    subjects = history.pop("commit_subjects", [])
    return {
        "enabled": True,
        "project_root": ".",
        "history": history,
        "github": {"origin_remote": history.get("origin_remote")},
        "ci": _detect_ci_workflows(project_root),
        "tests": _detect_test_commands(project_root),
        "conventions": {
            "branch_patterns": _branch_candidates(branches, history.get("default_branch")),
            "commit_styles": _commit_style_candidates(subjects),
        },
        "secrets": {
            "preflight": "required",
            "status": "not_run",
            "scanner_available": None,
            "findings": [],
        },
    }


# ---------------------------------------------------------------------------
# ce-ops#38 work-claim hook (shared runtime; forge-native; advisory)
# ---------------------------------------------------------------------------
def _make_gh_runner():
    """Factory for the work-claim gh runner (monkeypatchable in tests)."""
    return work_claims.default_gh_runner


def _acquire_dispatch_claim(ticket: str, reason: str):
    """Acquire + verify the work claim for a v3 spawn. Returns ``(ok, ctx_or_payload)``.

    ``ok`` True → ``ctx`` is ``(key, runner, claim_id)`` for best-effort release on a
    later refusal. ``ok`` False → the second element is ``(exit_code, lines, payload)``
    ready for :func:`_emit`.
    """
    try:
        key = work_claims.parse_ticket(ticket)
        runner = _make_gh_runner()
        result = work_claims.acquire(key, runner, reason=reason)
    except work_claims.WorkClaimError as exc:
        return False, (2, [f"{_BRAND} · spawn refused: --ticket {exc}"],
                       {"action": "spawn_refused", "reason": "claim_input", "detail": str(exc)})
    if not result.ok:
        return False, (1, [f"{_BRAND} · spawn refused: work claim {result.refusal_reason} — {result.note}"],
                       {"action": "spawn_refused", "reason": f"claim_{result.refusal_reason}",
                        "work_key": result.work_key, "active_claim":
                        result.state.active.to_dict() if result.state.active else None})
    return True, (key, runner, result.claim_id)


def _release_dispatch_claim(ctx, reason: str) -> None:
    """Best-effort structured release of a claim acquired before a refused spawn leg."""
    if ctx is None:
        return
    key, runner, claim_id = ctx
    work_claims.best_effort_release(
        key, runner, claim_id,
        holder=work_claims.resolve_holder(), host=work_claims.resolve_host(),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# dispatch worktree command
# ---------------------------------------------------------------------------
def _dispatch_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _dispatch_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dispatch_jsonable(v) for v in value]
    return value


def _emit_dispatch_worktree_json(code: int, payload: Mapping[str, Any]) -> int:
    print(json.dumps(_dispatch_jsonable(payload), indent=2, sort_keys=True))
    return code


def _dispatch_brief_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"--brief must be an existing file path, got {raw!r}")
    return path


def _dispatch_harness_cmd(raw: str | None, brief_path: Path) -> list[str]:
    if raw is None:
        return ["codex", "exec", str(brief_path)]
    argv = shlex.split(raw)
    if not argv:
        raise ValueError("--harness-cmd must contain at least one argv token")
    return argv


def _dispatch_outcome_payload(outcome: dispatch_worktree.DispatchOutcome) -> dict[str, Any]:
    return {
        "dispatched": bool(outcome.dispatched),
        "stage": outcome.stage,
        "reason": outcome.reason,
        "branch": outcome.branch,
        "worktree_path": outcome.worktree_path,
        "pushed": bool(outcome.pushed),
        "exec_returncode": outcome.exec_returncode,
        "lane_id": outcome.lane_id,
        "claim_id": outcome.claim_id,
    }


def _cmd_dispatch_worktree(args: argparse.Namespace) -> int:
    try:
        work_key = work_claims.parse_ticket(args.work_key)
    except work_claims.WorkClaimError as exc:
        return _emit_dispatch_worktree_json(
            2,
            {"ok": False, "error": "work_key_input", "detail": str(exc)},
        )

    try:
        brief_path = _dispatch_brief_path(args.brief)
        harness_cmd = _dispatch_harness_cmd(args.harness_cmd, brief_path)
    except (OSError, ValueError) as exc:
        return _emit_dispatch_worktree_json(
            1,
            {
                "ok": False,
                "error": "dispatch_input_failed",
                "detail": str(exc),
                "work_key": work_key.work_key,
            },
        )

    spec = dispatch_worktree.DispatchSpec(
        repo_root=Path(args.repo_root),
        ledger_root=Path(args.ledger_root),
        worktree_root=Path(args.worktree_root),
        work_key=work_key,
        branch=args.branch,
        brief_path=brief_path,
        harness_cmd=harness_cmd,
        controller_id=args.controller_id,
    )
    primitives = v3_seat_bridge.SubprocessDispatchWorktreeBridge()
    try:
        outcome = dispatch_worktree.dispatch(spec, primitives=primitives)
    except Exception as exc:  # pragma: no cover - runtime owns exact failures
        return _emit_dispatch_worktree_json(
            1,
            {
                "ok": False,
                "error": "dispatch_worktree_failed",
                "detail": str(exc),
                "work_key": work_key.work_key,
            },
        )
    payload = _dispatch_outcome_payload(outcome)
    return _emit_dispatch_worktree_json(0 if payload["dispatched"] else 1, payload)


def _cmd_dispatch(args: argparse.Namespace) -> int:
    if args.dispatch_command == "worktree":
        return _cmd_dispatch_worktree(args)
    return _emit_dispatch_worktree_json(
        2,
        {"ok": False, "error": "unknown_dispatch_command", "command": args.dispatch_command},
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def _cmd_scope(args: argparse.Namespace) -> int:
    """File (draft) a Scope from the Scope-card flags. The Frame→Shape output."""
    if not _SCOPE_ID_RE.match(args.scope_id or ""):
        return _emit(
            args, 2,
            [f"{_BRAND} · refused: --id must match ^[a-z][a-z0-9-]{{2,63}}$"],
            {"error": "invalid scope_id"},
        )
    scope: dict[str, Any] = {
        "kind": _KIND,
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "scope_id": args.scope_id,
        "intent": args.goal,            # Goal → intent
        "mutation_class": args.change_type,  # Change-type → mutation_class
    }
    if args.done_when:
        scope["acceptance_criteria"] = list(args.done_when)  # Done-when → acceptance_criteria
    if args.budget is not None:
        appetite: dict[str, Any] = {"amount": args.budget, "unit": args.budget_unit}  # Budget → appetite
        if args.budget_window:
            appetite["window"] = args.budget_window
        scope["appetite"] = appetite
    if args.note:
        scope["note"] = args.note
    path = _dump_scope(Path(args.root), scope)
    ready, reasons = coordination.scope_is_ready(scope)
    lines = [
        f"{_BRAND} · filed Scope {args.scope_id!r} → {path}",
        _card_line(scope),
    ]
    if not ready:
        lines.append(f"{_BRAND} · not yet Ready: {'; '.join(reasons)}")
    return _emit(
        args, 0, lines,
        {"action": "filed", "scope_id": args.scope_id, "path": str(path),
         "projection": _projection(scope), "ready": ready, "reasons": reasons},
    )


def _cmd_ratify(args: argparse.Namespace) -> int:
    """Place the bet (the human-only front-gate ratification) on a Ready Scope."""
    root = Path(args.root)
    try:
        scope = _load_scope(root, args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · ratify refused: {exc}"], {"error": str(exc)})
    if not _HEX64_RE.match(args.approver_ref or ""):
        return _emit(
            args, 2,
            [f"{_BRAND} · ratify refused: --approver-ref must be a 64-hex opaque digest "
             "(value-free; never a raw account)"],
            {"error": "invalid approver_ref"},
        )
    ready, reasons = coordination.scope_is_ready(scope)
    if not ready:
        # The bet is placed at Shape→Build, only once the Scope is Ready.
        return _emit(
            args, 1,
            [f"{_BRAND} · ratify refused: Scope is not Ready — {'; '.join(reasons)}"],
            {"error": "not_ready", "reasons": reasons},
        )
    scope.pop("ratification", None)
    scope["ratification"] = {
        "approver_ref": args.approver_ref,
        "ratified_scope_sha": _content_sha(scope),
    }
    path = _dump_scope(root, scope)
    lines = [
        f"{_BRAND} · bet placed on Scope {args.scope_id!r} → {path}",
        _card_line(scope),
    ]
    return _emit(
        args, 0, lines,
        {"action": "ratified", "scope_id": args.scope_id, "path": str(path),
         "projection": _projection(scope)},
    )


def _cmd_drive(args: argparse.Namespace) -> int:
    """Assemble the governed dispatch (the front gate) — the LIVE spawn is deferred."""
    root = Path(args.root)
    try:
        scope = _load_scope(root, args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · drive refused: {exc}"], {"error": str(exc)})
    runtime_policy: dict[str, Any] = {}
    if args.policy:
        policy_path = Path(args.policy)
        if not policy_path.is_file():
            # Fail closed: never dispatch silently dropping an operator's intended
            # spend ceiling / runtime policy.
            return _emit(
                args, 2,
                [f"{_BRAND} · drive refused: --policy file not found: {policy_path}"],
                {"error": "policy_not_found", "policy": str(policy_path)},
            )
        loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return _emit(
                args, 2,
                [f"{_BRAND} · drive refused: --policy must be a YAML mapping "
                 f"(got {type(loaded).__name__}); refusing rather than drop your spend policy"],
                {"error": "policy_malformed", "policy": str(policy_path)},
            )
        runtime_policy = loaded
    verdict = authority_resolver.DEV_AUTHORITY_RESOLVER.resolve(
        authority_resolver.ScopeRatifyDecision(scope=scope, runtime_policy=runtime_policy)
    )
    result = verdict.value
    if isinstance(result, coordination.DispatchRefusal):
        lines = [
            f"{_BRAND} · drive REFUSED ({result.reason}) — the front gate held",
            *(f"    - {d}" for d in result.detail),
        ]
        return _emit(
            args, 1, lines,
            {"action": "refused", "reason": result.reason, "detail": list(result.detail)},
        )
    envelopes = result.runtime_policy.get("spend_envelopes", [])
    if getattr(args, "spawn", False):
        return _drive_spawn(args, root, result, envelopes)
    lines = [
        f"{_BRAND} · BUILD dispatch assembled for Scope {result.scope_id!r} "
        f"(class {result.mutation_class})",
        f"    spend_envelopes: {json.dumps(envelopes, sort_keys=True)}",
        f"{_BRAND} · (assemble-only — pass --spawn to launch the governed seat)",
    ]
    return _emit(
        args, 0, lines,
        {"action": "dispatch_assembled", "scope_id": result.scope_id,
         "mutation_class": result.mutation_class, "runtime_policy": result.runtime_policy,
         "live_spawn": "available_via_--spawn"},
    )


CODEX_LOW_RISK_CLASSES = frozenset({"none", "docs", "code"})


def _valid_hex64(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[0-9a-fA-F]{64}", value))


def _drive_spawn(
    args: argparse.Namespace,
    root: Path,
    plan: coordination.DispatchPlan,
    envelopes: list[Any],
) -> int:
    """`--spawn`: materialize the dispatch → spawn the governed seat → seed the brief.

    The front gate already held (caller has a DispatchPlan). Harness selection is
    explicit: Claude is the default stronger Ring-1 path; Codex is accepted only
    under the G1-codex low-risk guard or a value-free override digest.
    """
    if args.harness not in v3_seat_bridge.HARNESS_BRIDGES:
        return _emit(
            args, 2,
            [f"{_BRAND} · drive --spawn refused: harness {args.harness!r} is not bridged "
             f"(available: {', '.join(sorted(v3_seat_bridge.HARNESS_BRIDGES))})"],
            {"action": "spawn_refused", "reason": "harness_not_supported",
             "harness": args.harness},
        )
    codex_risk_override = getattr(args, "codex_risk_override", None)
    if args.harness == v3_seat_bridge.CODEX_BRIDGE_HARNESS:
        if plan.mutation_class not in CODEX_LOW_RISK_CLASSES:
            if not _valid_hex64(codex_risk_override):
                return _emit(
                    args, 2,
                    [f"{_BRAND} · drive --spawn refused: Codex is managed-PreToolUse gated "
                     f"and may not drive mutation class {plan.mutation_class!r} without "
                     "--codex-risk-override <HEX64>"],
                    {"action": "spawn_refused", "reason": "codex_risk_refused",
                     "harness": args.harness, "mutation_class": plan.mutation_class},
                )
        elif codex_risk_override and not _valid_hex64(codex_risk_override):
            return _emit(
                args, 2,
                [f"{_BRAND} · drive --spawn refused: --codex-risk-override must be a "
                 "value-free 64-hex digest"],
                {"action": "spawn_refused", "reason": "codex_risk_override_malformed",
                 "harness": args.harness},
            )
    elif codex_risk_override:
        return _emit(
            args, 2,
            [f"{_BRAND} · drive --spawn refused: --codex-risk-override applies only to "
             "the codex harness"],
            {"action": "spawn_refused", "reason": "codex_risk_override_wrong_harness",
             "harness": args.harness},
        )
    # ce-ops#38: when a --ticket is supplied, acquire + verify the work claim
    # BEFORE any dispatch side effect (no dispatch.yaml / runtime-policy / brief /
    # pane until the claim is held). --ticket is OPTIONAL on the spawn path: the
    # spec ratified it as REQUIRED, but the closed 15-path manifest excludes
    # test_v3_cli.py, whose existing --spawn tests (and the pr/review/merge/e2e
    # fixtures built on them) call --spawn without a ticket. Honoring both
    # acceptance criteria (zero out-of-manifest diff + full suite green) forces
    # the optional posture here, mirroring the v1 `--claim-ticket` mitigation and
    # the spec's own "manual-dispatch gap" language. DECLARED deviation.
    claim_ctx = None
    if getattr(args, "ticket", None):
        ok, claim = _acquire_dispatch_claim(args.ticket, reason="implement")
        if not ok:
            code, lines, payload = claim
            return _emit(args, code, lines, payload)
        claim_ctx = claim
    unattended = not args.no_unattended
    record = v3_seat_bridge.materialize_dispatch(
        plan,
        root,
        harness=args.harness,
        unattended=unattended,
        codex_risk_override=codex_risk_override if args.harness == v3_seat_bridge.CODEX_BRIDGE_HARNESS else None,
    )
    codex_before: set[Path] | None = None
    launched_cwd = Path.cwd().resolve()
    if args.harness == v3_seat_bridge.CODEX_BRIDGE_HARNESS:
        codex_before = v3_seat_bridge.snapshot_codex_transcripts()
    try:
        spawn = v3_seat_bridge.spawn_seat(record)
        v3_seat_bridge.seed_brief(record)
        if args.harness == v3_seat_bridge.CODEX_BRIDGE_HARNESS:
            v3_seat_bridge.stamp_codex_transcript_locator(
                record,
                before=codex_before or set(),
                launched_cwd=launched_cwd,
            )
    except v3_seat_bridge.SeatBridgeError as exc:
        # Fail-closed: the dispatch was materialized before the v1 launch leg, so a
        # refused spawn would otherwise sit on disk with terminal/spawned_at unset —
        # which the read-model would have mistaken for a live Build/RUN run. Stamp
        # the failure (value-free) so it projects as neither pending nor live; the
        # attempt is conserved, not deleted.
        v3_seat_bridge.mark_spawn_failed(record, exc)
        # The seat never materialized — release the work claim we just acquired.
        _release_dispatch_claim(claim_ctx, "spawn-refused-before-side-effect")
        return _emit(
            args, 1,
            [f"{_BRAND} · drive --spawn refused: {exc}"],
            {"action": "spawn_refused", "reason": "launch_refused",
             "run_id": record.run_id, "detail": str(exc),
             "dispatch_path": str(record.dispatch_path)},
        )
    pane = spawn.terminal.get("pane_id")
    lines = [
        f"{_BRAND} · SPAWNED governed seat for Scope {plan.scope_id!r} "
        f"(class {plan.mutation_class}, harness {args.harness}, run {record.run_id})",
        f"    spend_envelopes: {json.dumps(envelopes, sort_keys=True)}",
        f"    dispatch: {record.dispatch_path}",
        f"    pane: {pane}"
        + ("  [unattended]" if unattended else "  [interactive]"),
    ]
    return _emit(
        args, 0, lines,
        {"action": "spawned", "scope_id": plan.scope_id, "run_id": record.run_id,
         "mutation_class": plan.mutation_class, "harness": args.harness,
         "unattended": unattended,
         "dispatch_path": str(record.dispatch_path), "pane_id": pane,
         "terminal": spawn.terminal, "resource_bound": spawn.resource_bound},
    )


# ---------------------------------------------------------------------------
# Dispatch-record storage seam + run evidence (G1b — .ce/state/dispatches, runs)
# ---------------------------------------------------------------------------
DISPATCHES_SUBDIR = "dispatches"
RUNS_SUBDIR = "runs"


def _dispatch_path(root: Path, run_id: str) -> Path:
    return root / DISPATCHES_SUBDIR / run_id / "dispatch.yaml"


def _run_evidence_path(root: Path, run_id: str) -> Path:
    return root / RUNS_SUBDIR / f"{run_id}.runtime-evidence.yaml"


def _load_dispatch(root: Path, run_id: str) -> dict[str, Any]:
    path = _dispatch_path(root, run_id)
    if not path.is_file():
        raise FileNotFoundError(f"no dispatch record for run {run_id!r} under {root / DISPATCHES_SUBDIR}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"malformed dispatch record at {path}")
    return data


def _find_dispatch_for_scope(root: Path, scope_id: str) -> dict[str, Any] | None:
    """The newest dispatch record for ``scope_id`` (run_id sorts lexically by utcstamp), or None."""
    ddir = root / DISPATCHES_SUBDIR
    if not ddir.is_dir():
        return None
    found: list[dict[str, Any]] = []
    for child in sorted(ddir.iterdir()):
        drec = child / "dispatch.yaml"
        if not drec.is_file():
            continue
        data = yaml.safe_load(drec.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("scope_id") == scope_id:
            found.append(data)
    if not found:
        return None
    return sorted(found, key=lambda d: str(d.get("run_id")))[-1]


def _has_uncollected_dispatch(root: Path, scope_id: str) -> bool:
    """True iff a LIVE dispatched run exists for ``scope_id`` (drives Build/RUN).

    A dispatch projects Build/RUN ONLY when it was ACTUALLY spawned (``spawned_at``
    / ``terminal`` stamped) and is neither collected nor spawn-failure-stamped. A
    materialized-but-refused/half spawn (terminal/spawned_at unset, or
    ``spawn_failed_at`` set) is NOT a live run — fail-closed, so a stale dispatch is
    never mistaken for an active one.
    """
    drec = _find_dispatch_for_scope(root, scope_id)
    if not drec:
        return False
    spawned = bool(drec.get("spawned_at") or drec.get("terminal"))
    return bool(spawned and not drec.get("collected_at") and not drec.get("spawn_failed_at"))


def _collected_run_evidence(root: Path, scope_id: str) -> Path | None:
    """The evidence chain path of ``scope_id``'s newest COLLECTED dispatch, if any."""
    drec = _find_dispatch_for_scope(root, scope_id)
    if not drec or not drec.get("collected_at"):
        return None
    chain = _run_evidence_path(root, str(drec.get("run_id")))
    return chain if chain.is_file() else None


def _forge_surface_for_scope(root: Path, scope_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The newest author ``change`` block + the newest live reviewer dispatch for a Scope (G2c).

    Returns ``(change_block, review_dispatch)`` — either may be ``None``. The author change block is
    the value-free PR pointer a ``cev3 pr --apply`` stamped; the review dispatch is a ``role:
    reviewer`` dispatch that was spawned and not failure-stamped (a LIVE venue).
    """
    ddir = root / DISPATCHES_SUBDIR
    if not ddir.is_dir():
        return None, None
    authors: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    for child in sorted(ddir.iterdir()):
        drec = child / "dispatch.yaml"
        if not drec.is_file():
            continue
        data = yaml.safe_load(drec.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("scope_id") != scope_id:
            continue
        if data.get("role") == "reviewer":
            if data.get("spawned_at") and not data.get("spawn_failed_at"):
                reviews.append(data)
        elif data.get("change"):
            authors.append(data)
    change_block = (
        sorted(authors, key=lambda d: str(d.get("run_id")))[-1].get("change") if authors else None
    )
    review = sorted(reviews, key=lambda d: str(d.get("run_id")))[-1] if reviews else None
    return change_block, review


def _resolve_run_evidence(args: argparse.Namespace, root: Path) -> tuple[str | None, str | None]:
    """Resolve (evidence-path, run_id) for report/artifacts.

    An explicit ``--evidence`` always wins; otherwise, when the Scope has a
    COLLECTED dispatch, default to its persisted chain
    (``<root>/runs/<run_id>.runtime-evidence.yaml``) so the read-model surfaces a
    finished run with zero extra flags.
    """
    evidence = getattr(args, "evidence", None)
    run_id = getattr(args, "run_id", None)
    if not evidence:
        drec = _find_dispatch_for_scope(root, args.scope_id)
        if drec and drec.get("collected_at"):
            chain = _run_evidence_path(root, str(drec.get("run_id")))
            if chain.is_file():
                evidence = str(chain)
                run_id = run_id or str(drec.get("run_id"))
    return evidence, run_id


def _policy_sha(policy: dict[str, Any]) -> str:
    """The 64-hex policy binding for the run's records.

    Delegates to the canonical derivation (``v3_forge_join.policy_sha``) so the ``cev3 collect``
    fold and the ``cev3 pr`` forge-join bind a run's records under the SAME policy digest — the
    derivation lives in exactly one place (extracted, not duplicated).
    """
    return v3_forge_join.policy_sha(policy)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EscalationSyncRefused(Exception):
    """Fail-closed refusal for `ce escalation sync`."""


def _escalations_dir(root: Path) -> Path:
    return root / ESCALATIONS_SUBDIR


def _escalation_path(root: Path, escalation_id: str) -> Path:
    return _escalations_dir(root) / f"{escalation_id}.yaml"


def _escalation_bytes(record: dict[str, Any]) -> str:
    return yaml.safe_dump(record, sort_keys=True, default_flow_style=False)


def _escalation_schema_errors(record: dict[str, Any], path: Path) -> list[str]:
    return [
        e.format()
        for e in validate_with_schema(
            record,
            _ESCALATION_SCHEMA,
            path,
            code="VAL-ESCALATION-RECORD-SCHEMA",
            contract=_ESCALATION_SCHEMA,
        )
    ]


def _write_escalation(root: Path, record: dict[str, Any]) -> Path:
    path = _escalation_path(root, str(record["escalation_id"]))
    _escalations_dir(root).mkdir(parents=True, exist_ok=True)
    path.write_text(_escalation_bytes(record), encoding="utf-8")
    return path


def _load_escalation(root: Path, escalation_id: str) -> dict[str, Any]:
    path = _escalation_path(root, escalation_id)
    if not path.is_file():
        raise FileNotFoundError(f"no escalation {escalation_id!r} under {_escalations_dir(root)}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != "escalation-record":
        raise ValueError(f"malformed escalation record at {path}")
    return data


def _iter_escalations(root: Path) -> list[dict[str, Any]]:
    d = _escalations_dir(root)
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(d.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict) and data.get("kind") == "escalation-record":
            out.append(data)
    return out


def _require_valid_escalation_id(args: argparse.Namespace, escalation_id: str) -> int | None:
    if _ESCALATION_ID_RE.match(escalation_id or ""):
        return None
    return _emit(
        args,
        2,
        [f"{_BRAND} · escalation refused: id must be a slug or 64-hex digest"],
        {"error": "invalid_escalation_id"},
    )


def _cmd_escalation_open(args: argparse.Namespace) -> int:
    root = Path(args.root)
    invalid = _require_valid_escalation_id(args, args.escalation_id)
    if invalid is not None:
        return invalid
    path = _escalation_path(root, args.escalation_id)
    if path.exists():
        return _emit(
            args,
            2,
            [f"{_BRAND} · escalation open refused: {args.escalation_id!r} already exists"],
            {"error": "duplicate_escalation_id", "path": str(path)},
        )
    record: dict[str, Any] = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": args.escalation_id,
        "title": args.title,
        "decision_needed": args.decision,
        "recommendation": args.recommend,
        "created_at": _utc_now_iso(),
    }
    if args.source_ref:
        record["source_ref"] = args.source_ref
    errors = _escalation_schema_errors(record, path)
    if errors:
        return _emit(
            args,
            2,
            [f"{_BRAND} · escalation open refused: schema-invalid", *errors],
            {"error": "schema_invalid", "detail": errors},
        )
    written = _write_escalation(root, record)
    return _emit(
        args,
        0,
        [f"{_BRAND} · opened AWAITING-OPERATOR escalation {args.escalation_id!r} → {written}"],
        {"action": "escalation_opened", "escalation_id": args.escalation_id, "path": str(written)},
    )


def _cmd_escalation_resolve(args: argparse.Namespace) -> int:
    root = Path(args.root)
    invalid = _require_valid_escalation_id(args, args.escalation_id)
    if invalid is not None:
        return invalid
    try:
        record = _load_escalation(root, args.escalation_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · escalation resolve refused: {exc}"], {"error": str(exc)})
    record["resolved_at"] = _utc_now_iso()
    if args.resolution:
        record["resolution"] = args.resolution
    path = _escalation_path(root, args.escalation_id)
    errors = _escalation_schema_errors(record, path)
    if errors:
        return _emit(
            args,
            2,
            [f"{_BRAND} · escalation resolve refused: schema-invalid", *errors],
            {"error": "schema_invalid", "detail": errors},
        )
    written = _write_escalation(root, record)
    return _emit(
        args,
        0,
        [f"{_BRAND} · resolved escalation {args.escalation_id!r} → {written}"],
        {"action": "escalation_resolved", "escalation_id": args.escalation_id, "path": str(written)},
    )


def _extract_issue_field(body: Any, *labels: str) -> str | None:
    text = str(body or "")
    wanted = {label.lower().replace("_", " ") for label in labels}
    for line in text.splitlines():
        clean = line.strip().strip("*").strip()
        if ":" not in clean:
            continue
        name, value = clean.split(":", 1)
        normalized = name.strip().lower().replace("_", " ")
        if normalized in wanted and value.strip():
            return value.strip()
    return None


def _issue_escalation_id(issue: dict[str, Any]) -> str:
    number = issue.get("number")
    if isinstance(number, int) or (isinstance(number, str) and number.isdigit()):
        return f"awaiting-operator-{number}"
    source = str(issue.get("url") or issue.get("title") or "awaiting-operator")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _project_issue_to_escalation(
    issue: dict[str, Any],
    *,
    existing_by_source: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_ref = str(issue.get("url") or "")
    if not source_ref:
        raise EscalationSyncRefused("gh issue payload missing url")
    title = str(issue.get("title") or "").strip()
    created_at = str(issue.get("createdAt") or "").strip()
    if not title or not created_at:
        raise EscalationSyncRefused(f"gh issue payload for {source_ref} missing title/createdAt")
    decision = _extract_issue_field(issue.get("body"), "decision needed", "decision_needed", "decision")
    recommendation = _extract_issue_field(issue.get("body"), "recommendation", "recommended")
    if not decision or not recommendation:
        raise EscalationSyncRefused(
            f"gh issue {source_ref} must contain 'Decision needed:' and 'Recommendation:' lines"
        )

    existing = existing_by_source.get(source_ref) or {}
    record = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": existing.get("escalation_id") or _issue_escalation_id(issue),
        "title": title,
        "decision_needed": decision,
        "recommendation": recommendation,
        "created_at": created_at,
        "source_ref": source_ref,
    }
    state = str(issue.get("state") or "").lower()
    if state == "closed":
        closed_at = str(issue.get("closedAt") or "").strip()
        if not closed_at:
            raise EscalationSyncRefused(f"closed gh issue {source_ref} missing closedAt")
        record["resolved_at"] = closed_at
        record["resolution"] = "closed on forge"
    return record


def project_escalation_sync(
    issues: list[Any],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """PURE gh-issue JSON payload -> escalation-record bodies."""
    existing_by_source = {
        str(record.get("source_ref")): record
        for record in existing
        if isinstance(record, Mapping) and record.get("source_ref")
    }
    planned: dict[str, dict[str, Any]] = {}
    for issue in issues:
        if not isinstance(issue, dict):
            raise EscalationSyncRefused("gh issue payload must be a list of objects")
        record = _project_issue_to_escalation(issue, existing_by_source=existing_by_source)
        planned[str(record["source_ref"])] = record
    return [planned[k] for k in sorted(planned)]


def _load_gh_issues(
    repo: str,
    label: str,
    *,
    runner: Any | None = None,
) -> list[Any]:
    if runner is None:
        runner = subprocess.run
    argv = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--label",
        label,
        "--state",
        "all",
        "--json",
        "number,title,url,body,createdAt,closedAt,state",
    ]
    completed = runner(argv, capture_output=True, text=True)
    if getattr(completed, "returncode", 1) != 0:
        stderr = getattr(completed, "stderr", "") or ""
        raise EscalationSyncRefused(stderr.strip() or "gh issue list failed")
    try:
        payload = json.loads(getattr(completed, "stdout", "") or "")
    except (TypeError, json.JSONDecodeError) as exc:
        raise EscalationSyncRefused(f"gh issue list returned unparsable JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise EscalationSyncRefused("gh issue list JSON must be a list")
    return payload


def _cmd_escalation_sync(args: argparse.Namespace) -> int:
    root = Path(args.root)
    try:
        payload = _load_gh_issues(args.repo, args.label)
        planned = project_escalation_sync(payload, _iter_escalations(root))
    except EscalationSyncRefused as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · escalation sync REFUSED: {exc}"],
            {"error": "sync_refused", "detail": str(exc), "written": 0},
        )

    all_errors: list[str] = []
    for record in planned:
        all_errors.extend(_escalation_schema_errors(record, _escalation_path(root, str(record["escalation_id"]))))
    if all_errors:
        return _emit(
            args,
            1,
            [f"{_BRAND} · escalation sync REFUSED: schema-invalid payload", *all_errors],
            {"error": "schema_invalid", "detail": all_errors, "written": 0},
        )

    written = [_write_escalation(root, record) for record in planned]
    return _emit(
        args,
        0,
        [f"{_BRAND} · synced {len(written)} escalation record(s) from {args.repo} label {args.label!r}"],
        {"action": "escalation_synced", "count": len(written), "paths": [str(p) for p in written]},
    )


def _cmd_escalation(args: argparse.Namespace) -> int:
    if args.escalation_command == "open":
        return _cmd_escalation_open(args)
    if args.escalation_command == "resolve":
        return _cmd_escalation_resolve(args)
    if args.escalation_command == "sync":
        return _cmd_escalation_sync(args)
    return 2


# ---------------------------------------------------------------------------
# notify — the v3.1-B.8 Operator-notify feed (once | watch | status)
# ---------------------------------------------------------------------------
def _notify_sync_tick(
    root: Path, repo: str, label: str, *, runner: Any | None = None
) -> dict[str, Any]:
    """Mirror forge awaiting-operator issues into local records BEFORE the fold (reuse).

    Cross-host fan-in (Fork 4): the existing ``_load_gh_issues`` + pure
    ``project_escalation_sync`` legs, run each poll tick. **Tolerant** — forge
    downtime must never block local alerting, so a refusal is returned (logged by the
    caller) and the fold over local records proceeds.
    """
    try:
        payload = _load_gh_issues(repo, label, runner=runner)
        planned = project_escalation_sync(payload, _iter_escalations(root))
    except EscalationSyncRefused as exc:
        return {"ok": False, "error": str(exc), "written": 0}
    written = 0
    for record in planned:
        errs = _escalation_schema_errors(record, _escalation_path(root, str(record["escalation_id"])))
        if errs:
            continue
        _write_escalation(root, record)
        written += 1
    return {"ok": True, "written": written}


def _cmd_notify_once(args: argparse.Namespace, *, runner: Any | None = None) -> int:
    from .runner import notify_feed

    root = Path(args.root)
    sync_note: dict[str, Any] | None = None
    if getattr(args, "sync_repo", None):
        sync_note = _notify_sync_tick(root, args.sync_repo, args.sync_label, runner=runner)
    try:
        summary = notify_feed.run_once(root, runner=runner)
    except notify_feed.NotifyConfigError as exc:
        return _emit(
            args, 2,
            [f"{_BRAND} · notify once REFUSED: malformed notify config — {exc}"],
            {"error": "notify_config_invalid", "detail": str(exc)},
        )
    lines = [
        f"{_BRAND} · notify once — dispatched {summary['dispatched']} "
        f"({summary['ok']} ok · {summary['failed']} failed) over sinks "
        f"{', '.join(summary['sinks']) or '—'}"
    ]
    payload: dict[str, Any] = {"action": "notify_once", **summary}
    if sync_note is not None:
        state = "ok" if sync_note["ok"] else f"FAILED (tolerated): {sync_note.get('error')}"
        lines.append(f"    sync · {args.sync_repo} {state} ({sync_note.get('written', 0)} mirrored)")
        payload["sync"] = sync_note
    return _emit(args, 0, lines, payload)


def _cmd_notify_status(args: argparse.Namespace) -> int:
    from .runner import notify_feed

    root = Path(args.root)
    try:
        config = notify_feed.load_config(root)
    except notify_feed.NotifyConfigError as exc:
        return _emit(
            args, 2,
            [f"{_BRAND} · notify status REFUSED: malformed notify config — {exc}"],
            {"error": "notify_config_invalid", "detail": str(exc)},
        )
    escalations = notify_feed.load_escalations(root) or []
    ledger = notify_feed.load_ledger(root)
    fold = notify_feed.fold_notify_feed(escalations, ledger, config)
    counts = fold["counts"]
    lines = [
        f"{_BRAND} · notify status — open {counts['open_count']} · resolved "
        f"{counts['resolved_count']} · pending entry {counts['pending_entry']} / exit "
        f"{counts['pending_exit']} · delivered {counts['delivered']} · failed {counts['failed']}",
        f"    sinks · {', '.join(fold['sinks']) or '—'}",
    ]
    return _emit(args, 0, lines, {"action": "notify_status", "counts": counts, "sinks": fold["sinks"]})


def _cmd_notify_watch(args: argparse.Namespace, *, runner: Any | None = None) -> int:
    import time

    from .runner import notify_feed

    root = Path(args.root)
    interval = max(1, int(args.interval))
    # Validate the config LOUDLY up front (exit 2) before entering the loop.
    try:
        notify_feed.load_config(root)
    except notify_feed.NotifyConfigError as exc:
        return _emit(
            args, 2,
            [f"{_BRAND} · notify watch REFUSED: malformed notify config — {exc}"],
            {"error": "notify_config_invalid", "detail": str(exc)},
        )
    print(
        f"{_BRAND} · notify watch — root {root} · interval {interval}s · "
        f"sync {args.sync_repo or 'off'} (Ctrl-C to stop)",
        flush=True,
    )
    try:
        while True:
            if getattr(args, "sync_repo", None):
                note = _notify_sync_tick(root, args.sync_repo, args.sync_label, runner=runner)
                if not note["ok"]:
                    print(
                        f"{_BRAND} · notify watch — forge sync FAILED (tolerated, "
                        f"local fold proceeds): {note.get('error')}",
                        flush=True,
                    )
            try:
                summary = notify_feed.run_once(root, runner=runner)
                if summary["dispatched"]:
                    print(
                        f"{_BRAND} · notify watch — dispatched {summary['dispatched']} "
                        f"({summary['failed']} failed)",
                        flush=True,
                    )
            except notify_feed.NotifyConfigError as exc:
                # The daemon must not die on a mid-flight bad edit; surface it loudly.
                print(
                    f"{_BRAND} · notify watch — config became invalid (alerting PAUSED "
                    f"until fixed): {exc}",
                    flush=True,
                )
            time.sleep(interval)
    except KeyboardInterrupt:  # pragma: no cover - interactive stop
        return 0


def _cmd_notify(args: argparse.Namespace) -> int:
    if args.notify_command == "once":
        return _cmd_notify_once(args)
    if args.notify_command == "watch":
        return _cmd_notify_watch(args)
    if args.notify_command == "status":
        return _cmd_notify_status(args)
    return 2


# ---------------------------------------------------------------------------
# reap — the ce-ops#43 seat/venue retirement reaper (once | watch | status)
#
# Mirrors the notify I/O-edge daemon house style: a pure fold over local state
# first, a narrow I/O edge for irreversible work, a durable private ledger for
# attempted actions; `once` = one fold + one bounded action pass, `watch` repeats
# `once` at an interval, `status` is a no-mutation read model.
# ---------------------------------------------------------------------------
def _reaper_executor_for(args: argparse.Namespace):
    """Build the substrate→executor factory the reaper delegates to (live wiring).

    The tmux executor crosses to ``ce lane archive --json`` and
    ``creator-engine-validator pco-release`` as subprocess+DATA; the transcript is
    resolved by exact ``harness_session_id`` under the harness projects dir.
    """
    from . import reaper_executors

    search_root = _claude_config_dir(args) / "projects"
    ce_exe = getattr(args, "ce_exe", None) or "ce"
    validator_exe = getattr(args, "validator_exe", None) or "creator-engine-validator"

    def factory(terminal_kind: str | None):
        base = reaper_executors.default_executor_for(terminal_kind)
        if base is None:
            return None
        return reaper_executors.TmuxExecutor(
            ce_exe=ce_exe,
            validator_exe=validator_exe,
            transcript_search_root=search_root,
        )

    return factory


def _reaper_ledger_root(args: argparse.Namespace) -> Path | None:
    """Resolve the active-work-ledger root from the flag or CE_LEDGER_ROOT (no baked literal)."""
    explicit = getattr(args, "ledger_root", None)
    if explicit:
        return Path(explicit)
    env = os.environ.get(seat_reaper.LEDGER_ROOT_ENV)
    return Path(env) if env else None


def _reaper_archive_root(args: argparse.Namespace) -> Path | None:
    """Resolve the transcript-archive root from the flag or CE_TRANSCRIPT_ARCHIVE_ROOT."""
    explicit = getattr(args, "archive_root", None)
    if explicit:
        return Path(explicit)
    env = os.environ.get(seat_reaper.ARCHIVE_ROOT_ENV)
    return Path(env) if env else None


def _reaper_common_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "ledger_root": _reaper_ledger_root(args),
        "archive_root": _reaper_archive_root(args),
        "executor_for": _reaper_executor_for(args),
        "grace_seconds": int(getattr(args, "grace_seconds", seat_reaper.DEFAULT_GRACE_SECONDS)),
        "stale_seconds": int(getattr(args, "stale_seconds", seat_reaper.DEFAULT_STALE_SECONDS)),
    }


def _reaper_summary_line(action: str, payload: dict[str, Any]) -> str:
    if action == "reap_status":
        return (
            f"{_BRAND} · reap status — observed {payload['observed_dispatches']} · "
            f"eligible {payload['eligible']} · conserved {payload['conserved']} · "
            f"would-escalate {payload['would_escalate']} · retired {payload['already_retired']} · "
            f"active/unknown {payload['active_or_unknown']}"
        )
    return (
        f"{_BRAND} · {action.replace('_', ' ')} — observed {payload['observed_dispatches']} · "
        f"reaped {payload['reaped']} · conserved {payload['conserved']} · "
        f"escalated {payload['escalated']} · skipped {payload['skipped_active_or_unknown']} · "
        f"retired {payload['already_retired']} · failed {payload['failed']}"
    )


def _cmd_reap_status(args: argparse.Namespace) -> int:
    root = Path(args.root)
    payload = seat_reaper.reap_status(
        root,
        ledger_root=_reaper_ledger_root(args),
        executor_for=_reaper_executor_for(args),
        grace_seconds=int(getattr(args, "grace_seconds", seat_reaper.DEFAULT_GRACE_SECONDS)),
        stale_seconds=int(getattr(args, "stale_seconds", seat_reaper.DEFAULT_STALE_SECONDS)),
    )
    return _emit(args, 0, [_reaper_summary_line("reap_status", payload)], payload)


def _cmd_reap_once(args: argparse.Namespace) -> int:
    root = Path(args.root)
    repo_root = Path(getattr(args, "repo_root", None) or Path.cwd())
    payload = seat_reaper.reap_once(root, repo_root=repo_root, **_reaper_common_kwargs(args))
    return _emit(args, 0, [_reaper_summary_line("reap_once", payload)], payload)


def _cmd_reap_watch(args: argparse.Namespace) -> int:
    import signal
    import time

    root = Path(args.root)
    repo_root = Path(getattr(args, "repo_root", None) or Path.cwd())
    interval = int(args.interval)
    if interval < 1:
        return _emit(
            args, 2,
            [f"{_BRAND} · reap watch REFUSED: --interval must be >= 1 (got {interval})"],
            {"error": "reap_invalid_interval", "interval": interval},
        )

    stop = {"flag": False}

    def _on_signal(signum, _frame):  # pragma: no cover - signal delivery is environmental
        stop["flag"] = True

    # SIGINT/SIGTERM stop the loop CLEANLY after the current pass (exceeds the
    # notify precedent, which handles only KeyboardInterrupt).
    previous: dict[int, Any] = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            previous[sig] = signal.signal(sig, _on_signal)
        except (ValueError, OSError):  # pragma: no cover - non-main-thread / unsupported
            pass
    print(
        f"{_BRAND} · reap watch — root {root} · interval {interval}s (Ctrl-C / SIGTERM to stop)",
        flush=True,
    )
    try:
        while not stop["flag"]:
            payload = seat_reaper.reap_once(
                root, repo_root=repo_root, action="reap_watch_tick", **_reaper_common_kwargs(args)
            )
            print(_reaper_summary_line("reap_watch_tick", payload), flush=True)
            if stop["flag"]:
                break
            # sleep in short slices so a signal stops promptly after the pass
            slept = 0
            while slept < interval and not stop["flag"]:
                time.sleep(1)
                slept += 1
    except KeyboardInterrupt:  # pragma: no cover - interactive stop
        pass
    finally:
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):  # pragma: no cover
                pass
    return 0


def _cmd_reap(args: argparse.Namespace) -> int:
    if args.reap_command == "once":
        return _cmd_reap_once(args)
    if args.reap_command == "watch":
        return _cmd_reap_watch(args)
    if args.reap_command == "status":
        return _cmd_reap_status(args)
    return 2


def _claude_config_dir(args: argparse.Namespace) -> Path:
    """Resolve the harness config dir for stamped-id transcript lookup (D6/F9).

    Precedence: ``--claude-config-dir`` → ``$CLAUDE_CONFIG_DIR`` → ``~/.claude``.
    """
    explicit = getattr(args, "claude_config_dir", None)
    if explicit:
        return Path(explicit)
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env) if env else Path.home() / ".claude"


def _resolve_collect_transcript(
    args: argparse.Namespace, dispatch: dict[str, Any], run_id: str
) -> tuple[Path | None, str, tuple[int, list[str], dict[str, Any]] | None]:
    """D6/F9 transcript resolution: the dispatch NAMES its transcript, collect never guesses.

    Returns ``(transcript_path | None, transcript_source, refusal | None)`` where ``refusal``
    is an ``(exit_code, lines, payload)`` triple for :func:`_emit`. Resolution order:

    * ``--transcript-override`` given → fold it, ``operator_override`` (the loud salvage hatch);
    * a stamped ``harness_session_id`` present:
        - explicit ``--transcript`` → fold ONLY if its stem equals the stamped id, else REFUSE
          (the #14/#21 mis-fold, machine-blocked);
        - no ``--transcript`` → resolve by EXACT KEY ``<config>/projects/*/<id>.jsonl``: one hit →
          fold (``stamped``); zero or many → REFUSE;
    * no stamped id (pre-F9 record) → today's behavior conserved (optional ``--transcript``),
      ``unstamped``.
    """
    override = getattr(args, "transcript_override", None)
    explicit = getattr(args, "transcript", None)
    harness = str(dispatch.get("harness") or v3_seat_bridge.DEFAULT_BRIDGE_HARNESS)
    session_id = dispatch.get("harness_session_id")
    sid = str(session_id) if session_id else ""

    def _not_found(path: Path, kind: str) -> tuple[int, list[str], dict[str, Any]]:
        return (
            2,
            [f"{_BRAND} · collect refused: {kind} not found: {path}"],
            {"error": "transcript_not_found", "transcript": str(path)},
        )

    if override:
        tp = Path(override)
        if not tp.is_file():
            return None, "", _not_found(tp, "transcript-override")
        return tp, "operator_override", None

    if harness == v3_seat_bridge.CODEX_BRIDGE_HARNESS:
        transcript_ref = str(dispatch.get("transcript_ref") or "")

        def _codex_meta_id(path: Path) -> str:
            meta = v3_seat_bridge._read_codex_session_meta(path)
            return str((meta or {}).get("id") or "")

        if explicit:
            tp = Path(explicit)
            if not tp.is_file():
                return None, "", _not_found(tp, "transcript")
            if sid and _codex_meta_id(tp) != sid:
                return None, "", (
                    2,
                    [f"{_BRAND} · collect refused: --transcript {tp.name!r} does not match the "
                     f"Codex run's stamped session id {sid!r} — refusing the mis-fold "
                     f"(pass --transcript-override to fold a salvaged transcript anyway)"],
                    {"error": "transcript_id_mismatch", "run_id": run_id,
                     "stamped_session_id": sid, "given_session_id": _codex_meta_id(tp)},
                )
            return tp, "stamped", None

        if transcript_ref:
            tp = Path(transcript_ref)
            if tp.is_file() and (not sid or _codex_meta_id(tp) == sid):
                return tp, "stamped", None
            if tp.is_file() and sid:
                return None, "", (
                    2,
                    [f"{_BRAND} · collect refused: stamped Codex transcript_ref {tp} no longer "
                     f"matches session id {sid!r}"],
                    {"error": "transcript_id_mismatch", "run_id": run_id,
                     "stamped_session_id": sid, "transcript_ref": str(tp)},
                )
        if sid:
            hits = v3_seat_bridge._find_codex_transcripts(session_id=sid)
            if not hits:
                return None, "", (
                    2,
                    [f"{_BRAND} · collect refused: no Codex transcript for stamped session id "
                     f"{sid!r} under {Path.home() / '.codex' / 'sessions'} — a spawned Codex "
                     "seat must have a transcript (pass --transcript-override to fold a salvaged one)"],
                    {"error": "stamped_transcript_missing", "run_id": run_id,
                     "harness_session_id": sid,
                     "sessions_dir": str(Path.home() / ".codex" / "sessions")},
                )
            if len(hits) > 1:
                return None, "", (
                    2,
                    [f"{_BRAND} · collect refused: {len(hits)} Codex transcripts match stamped "
                     f"session id {sid!r} — refusing an ambiguous fold"],
                    {"error": "stamped_transcript_ambiguous", "run_id": run_id,
                     "harness_session_id": sid, "matches": [str(path) for path, _meta in hits]},
                )
            return hits[0][0], "stamped", None
        return None, "", (
            2,
            [f"{_BRAND} · collect refused: Codex dispatch has no stamped transcript_ref or "
             "harness_session_id (pass --transcript-override only for salvage)"],
            {"error": "stamped_transcript_missing", "run_id": run_id},
        )

    if sid:
        if explicit:
            tp = Path(explicit)
            if not tp.is_file():
                return None, "", _not_found(tp, "transcript")
            if tp.stem != sid:
                return None, "", (
                    2,
                    [f"{_BRAND} · collect refused: --transcript {tp.name!r} does not match the "
                     f"run's stamped harness session id {sid!r} — refusing the mis-fold "
                     f"(pass --transcript-override to fold a salvaged transcript anyway)"],
                    {"error": "transcript_id_mismatch", "run_id": run_id,
                     "stamped_session_id": sid, "given_stem": tp.stem},
                )
            return tp, "stamped", None
        cfg = _claude_config_dir(args)
        hits = sorted((cfg / "projects").glob(f"*/{sid}.jsonl"))
        if not hits:
            return None, "", (
                2,
                [f"{_BRAND} · collect refused: no harness transcript for stamped session id "
                 f"{sid!r} under {cfg / 'projects'}/*/ — a spawned seat must have a transcript "
                 f"(pass --transcript-override to fold a salvaged one)"],
                {"error": "stamped_transcript_missing", "run_id": run_id,
                 "harness_session_id": sid, "config_dir": str(cfg)},
            )
        if len(hits) > 1:
            return None, "", (
                2,
                [f"{_BRAND} · collect refused: {len(hits)} transcripts match stamped session id "
                 f"{sid!r} — refusing an ambiguous fold (chain integrity over convenience)"],
                {"error": "stamped_transcript_ambiguous", "run_id": run_id,
                 "harness_session_id": sid, "matches": [str(h) for h in hits]},
            )
        return hits[0], "stamped", None

    # pre-F9 record: no stamped id — conserve today's behavior.
    if explicit:
        tp = Path(explicit)
        if not tp.is_file():
            return None, "", _not_found(tp, "transcript")
        return tp, "unstamped", None
    return None, "unstamped", None


def _cmd_collect(args: argparse.Namespace) -> int:
    """Fold a finished seat run into a conserved evidence chain (G1b run→evidence).

    Reads the dispatch record, folds the harness transcript into
    ``runtime_spend_ledger`` leaves (the live per-turn tap stays the declared
    deferred seam — this is post-hoc metering), appends the typed terminal
    ``runtime_run_outcome``, hash-chains them, and persists
    ``<root>/runs/<run_id>.runtime-evidence.yaml`` (refusing to overwrite an
    existing chain). Marks the dispatch ``collected_at``.
    """
    root = Path(args.root)
    run_id = args.run_id
    try:
        dispatch = _load_dispatch(root, run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · collect refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · collect refused: run {run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    chain_path = _run_evidence_path(root, run_id)
    if chain_path.exists():
        # Conserved evidence is append-only; never silently re-fold a collected run.
        return _emit(
            args, 2,
            [f"{_BRAND} · collect refused: run {run_id!r} already collected at {chain_path}"],
            {"error": "already_collected", "run_id": run_id, "evidence": str(chain_path)},
        )

    # The merged runtime policy the seat ran under — read AS DATA for the rates + binding.
    policy: dict[str, Any] = {}
    policy_ref = dispatch.get("runtime_policy_ref")
    if policy_ref and Path(policy_ref).is_file():
        loaded = yaml.safe_load(Path(policy_ref).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            policy = loaded
    policy_sha = _policy_sha(policy)
    model_rates = policy.get("model_rates") or []

    # 1) The typed terminal outcome + its value-free change_set pointer (determined FIRST so a
    #    missing-outcome refusal is independent of transcript resolution).
    #    v3.1-G2a: when the dispatch carries a forge-stamped `change` block (a `cev3 pr --apply`
    #    opened a real PR), derive the change_set FROM IT — closing G1's "head_sha defaults to the
    #    run id" honesty gap with a forge-derived fact — and default --outcome to pr_opened. Explicit
    #    flags still win; the operator-typed fallback is byte-conserved for runs that opened no PR.
    change_block = dispatch.get("change") or {}
    outcome = args.outcome or ("pr_opened" if change_block else None)
    if outcome is None:
        return _emit(
            args, 2,
            [f"{_BRAND} · collect refused: --outcome is required "
             f"(run {run_id!r} carries no stamped change block to derive it from)"],
            {"error": "outcome_required", "run_id": run_id},
        )

    # 2) Resolve the harness transcript by the stamped session id — never by guess (D6/F9).
    #    The mis-fold that metered the orchestrator on the #14/#21 chains is machine-blocked.
    tpath, transcript_source, refusal = _resolve_collect_transcript(args, dispatch, run_id)
    if refusal is not None:
        code, lines, payload = refusal
        return _emit(args, code, lines, payload)

    # 3) Spend ledger leaves — fold the RESOLVED transcript by REUSING the usage tap
    #    (compute_cost + meter_record_body); unpriced turns are surfaced, never $0.
    ledger_bodies: list[dict[str, Any]] = []
    unpriced = 0
    if tpath is not None:
        turns = usage_tap.tap_transcript_file(tpath)
        ledger_bodies, unpriced_turns = usage_tap.usage_turns_to_ledger(
            turns, model_rates=model_rates, fleet_id=run_id,
            policy_sha=policy_sha, run_id_of=lambda _t: run_id,
        )
        unpriced = len(unpriced_turns)
    change_set: dict[str, Any] = {
        "branch": args.branch or change_block.get("branch") or run_id,
        "base": args.base or change_block.get("base") or "main",
        "manifest_paths": list(args.manifest_paths or change_block.get("manifest_paths") or []),
        "head_sha": args.head_sha or change_block.get("head_sha") or run_id,
    }
    pr_number = args.pr if args.pr is not None else change_block.get("pr_number")
    if pr_number is not None:
        change_set["pr_number"] = pr_number
    # F6: propagate the value-free base-only re-stamp anchor so `cev3 merge` can machine-prove a
    # later base-only motion. A chain without `base_sha` is legacy-unprovable, never overridden.
    base_sha = change_block.get("base_sha")
    if base_sha:
        change_set["base_sha"] = base_sha
    outcome_body = {
        "kind": runtime_evidence_spine.RUN_OUTCOME_RECORD_KIND,
        "record_type": runtime_evidence_spine.RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": policy_sha,
        "run_id": run_id,
        "recorded_at": _utc_now_iso(),
        "outcome": outcome,
        "change_set": change_set,
    }

    # 4) Hash-chain the leaves then the terminal outcome; persist via the existing
    #    sink (refuses empty / non-uniform run_id / hash-broken / schema-invalid).
    chain: list[dict[str, Any]] = []
    for body in [*ledger_bodies, outcome_body]:
        chain.append(runtime_evidence_spine.append(chain, body))
    sink = evidence_sink.file_evidence_sink(_run_evidence_path(root, run_id).parent)
    try:
        receipt = sink(CollectedEvidence(
            handle_ref=run_id,
            records=tuple(chain),
            note=f"v3.1-G1 collect: run {run_id} folded {len(ledger_bodies)} spend leaf(s) "
                 f"+ outcome {outcome} (transcript_source: {transcript_source})",
        ))
    except evidence_sink.EvidencePersistRefused as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · collect refused: {exc}"],
            {"error": "persist_refused", "detail": str(exc), "run_id": run_id},
        )

    # 4) Mark the dispatch collected (an uncollected dispatch projects Build/RUN) + stamp the
    #    D6/F9 transcript-source honesty marker (the schema'd spend leaves stay untouched).
    dispatch["collected_at"] = _utc_now_iso()
    dispatch["transcript_source"] = transcript_source
    _dispatch_path(root, run_id).write_text(
        yaml.safe_dump(dispatch, sort_keys=True, default_flow_style=False), encoding="utf-8"
    )

    lines = [
        f"{_BRAND} · COLLECTED run {run_id!r} for Scope {args.scope_id!r} "
        f"(outcome {outcome}, {len(ledger_bodies)} spend leaf(s)"
        + (f", {unpriced} unpriced" if unpriced else "") + ")",
        f"    evidence: {receipt.path}",
    ]
    return _emit(
        args, 0, lines,
        {"action": "collected", "scope_id": args.scope_id, "run_id": run_id,
         "outcome": outcome, "pr": pr_number, "evidence": str(receipt.path),
         "spend_leaves": len(ledger_bodies), "unpriced_turns": unpriced,
         "transcript_source": transcript_source,
         "record_count": receipt.record_count},
    )


def _cmd_pr(args: argparse.Namespace) -> int:
    """Push the seat's authored branch + open its PR through the v3 forge (G2a, plan-by-default).

    Plan-by-default: without ``--apply`` it prints the would-push/would-open plan and mutates
    nothing. With ``--apply`` it drives ``v3_forge_join.open_change_for_run``
    (mint→push→open under a JIT least-privilege token, revoked in a finally) and stamps the
    value-free ``change`` block onto the dispatch. The ORCHESTRATOR/Operator session invokes this —
    a §7-governed seat is hook-denied the underlying push anyway (the authority model is conserved,
    now with the mechanical push automated v3-side).
    """
    root = Path(args.root)
    run_id = args.run_id
    # Precondition: the run must belong to the named Scope (the collect discipline).
    try:
        dispatch = _load_dispatch(root, run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · pr refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · pr refused: run {run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    try:
        app_config = v3_forge_join.load_app_config(args.app_config)
        ref = v3_forge_join.open_change_for_run(
            root, run_id, app_config=app_config, branch=args.branch,
            manifest_paths=args.manifest_paths, base=args.base,
            source_dir=args.source_dir, apply=args.apply,
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · pr refused: {exc}"],
            {"action": "pr_refused", "run_id": run_id, "detail": str(exc)},
        )
    opened = bool(args.apply) and ref.pr_number is not None
    if opened:
        lines = [
            f"{_BRAND} · OPENED PR #{ref.pr_number} for Scope {args.scope_id!r} (run {run_id})",
            f"    branch {ref.branch} → {ref.base} · head {ref.head_sha}",
            f"    dispatch: {_dispatch_path(root, run_id)}",
            f"    next: {CE_CMD} review {args.scope_id} --run {run_id} --spawn",
        ]
    else:
        lines = [
            f"{_BRAND} · PR PLAN for Scope {args.scope_id!r} (run {run_id}) — nothing mutated",
            f"    would push branch {ref.branch} → {ref.base} on {ref.repo}",
            f"{_BRAND} · (plan-only — pass --apply to push + open the PR)",
        ]
    return _emit(
        args, 0, lines,
        {"action": "pr_opened" if opened else "pr_planned",
         "scope_id": args.scope_id, "run_id": run_id, "apply": bool(args.apply),
         "pr_number": ref.pr_number, "branch": ref.branch, "base": ref.base,
         "head_sha": ref.head_sha, "repo": ref.repo,
         "dispatch_path": str(_dispatch_path(root, run_id))},
    )


def _operation_policy_sha(action: str, repo: str, payload: Mapping[str, Any]) -> str:
    body = {"action": action, "repo": repo, **dict(payload)}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _run_scoped_cli_op(
    *,
    app_config: v3_forge_join.AppConfig,
    action: str,
    payload: Mapping[str, Any],
    permissions: Mapping[str, str],
    secret_name: str,
    ttl_seconds: int,
    escalation_authority: tuple[tuple[str, str], ...],
    op,
):
    refusal = sec7_forge_refusal(action)
    if refusal is not None:
        raise v3_forge_join.ForgeJoinRefused(refusal)
    token = v3_forge_join.mint_operation_token(
        app_config,
        run_id=action,
        policy_sha_value=_operation_policy_sha(action, app_config.repo, payload),
        permissions=permissions,
        secret_name=secret_name,
        requested_ttl_seconds=ttl_seconds,
        escalation_authority=escalation_authority,
    )
    try:
        runner = v3_forge_join.authenticated_gh_runner(token)
        return op(runner)
    finally:
        v3_forge_join._revoke_best_effort(token)  # best-effort cleanup mirrors forge join apply legs


def _cmd_configure_repo(args: argparse.Namespace) -> int:
    """Plan/apply repo-level GitHub configuration through a scoped admin token."""
    try:
        app_config = v3_forge_join.load_app_config(args.app_config)

        def op(runner):
            if args.allow_auto_merge:
                return allow_auto_merge(app_config.repo, apply=args.apply, gh_runner=runner)
            if args.squash_only:
                return configure_squash_only(app_config.repo, apply=args.apply, gh_runner=runner)
            return configure_repo(app_config.repo, branch=args.branch, apply=args.apply, gh_runner=runner)

        result = _run_scoped_cli_op(
            app_config=app_config,
            action="configure_repo",
            payload={
                "branch": args.branch,
                "apply": bool(args.apply),
                "allow_auto_merge": bool(args.allow_auto_merge),
                "squash_only": bool(args.squash_only),
            },
            permissions=v3_forge_join.REPO_ADMIN_TOKEN_PERMISSIONS,
            secret_name=v3_forge_join.REPO_ADMIN_SECRET_NAME,
            ttl_seconds=v3_forge_join.REPO_ADMIN_TOKEN_TTL_SECONDS,
            escalation_authority=v3_forge_join.REPO_ADMIN_TOKEN_ESCALATION_AUTHORITY,
            op=op,
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · configure-repo refused: {exc}"],
            {"action": "configure_repo_refused", "detail": str(exc)},
        )
    planned = not bool(args.apply)
    action = "repo_config_planned" if planned else "repo_config_applied"
    lines = [
        f"{_BRAND} · {'REPO CONFIG PLAN' if planned else 'REPO CONFIG APPLIED'} for {app_config.repo}",
        f"    operation: {result.operation} · changed={result.changed} · verified={result.verified}",
    ]
    return _emit(args, 0, lines, {"action": action, **result.to_dict()})


def _cmd_ruleset(args: argparse.Namespace) -> int:
    """Plan/apply a repo ruleset through a scoped admin token."""
    try:
        app_config = v3_forge_join.load_app_config(args.app_config)
        actor = RulesetBypassActor(
            actor_id=args.bypass_integration_id,
            actor_type="Integration",
            bypass_mode="pull_request",
        )
        policy = RulesetPolicy(
            name=args.name,
            branch=args.branch,
            required_approving_review_count=args.required_approvals,
            bypass_actors=(actor,),
        )

        def op(runner):
            if args.delete:
                return delete_ruleset(app_config.repo, args.name, apply=args.apply, gh_runner=runner)
            return upsert_ruleset(app_config.repo, policy, apply=args.apply, gh_runner=runner)

        result = _run_scoped_cli_op(
            app_config=app_config,
            action="ruleset",
            payload={
                "name": args.name,
                "branch": args.branch,
                "apply": bool(args.apply),
                "delete": bool(args.delete),
                "bypass_integration_id": args.bypass_integration_id,
            },
            permissions=v3_forge_join.REPO_ADMIN_TOKEN_PERMISSIONS,
            secret_name=v3_forge_join.REPO_ADMIN_SECRET_NAME,
            ttl_seconds=v3_forge_join.REPO_ADMIN_TOKEN_TTL_SECONDS,
            escalation_authority=v3_forge_join.REPO_ADMIN_TOKEN_ESCALATION_AUTHORITY,
            op=op,
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · ruleset refused: {exc}"],
            {"action": "ruleset_refused", "detail": str(exc)},
        )
    planned = not bool(args.apply)
    action = "ruleset_planned" if planned else "ruleset_applied"
    lines = [
        f"{_BRAND} · {'RULESET PLAN' if planned else 'RULESET APPLIED'} for {app_config.repo}",
        f"    {result.operation}: {result.name} · changed={result.changed} · verified={result.verified}",
    ]
    return _emit(args, 0, lines, {"action": action, **result.to_dict()})


def _cmd_review_submit(args: argparse.Namespace) -> int:
    """Submit the separate reviewer App's APPROVE for a run's opened PR."""
    root = Path(args.root)
    try:
        dispatch = _load_dispatch(root, args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · review-submit refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · review-submit refused: run {args.run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": args.run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    try:
        reviewer = v3_forge_join.load_reviewer_app_config(args.reviewer_app_config)
        result = v3_forge_join.submit_review_for_run(
            root, args.run_id, reviewer_app_config=reviewer, apply=args.apply, body=args.body or "",
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · review-submit refused: {exc}"],
            {"action": "review_submit_refused", "run_id": args.run_id, "detail": str(exc)},
        )
    planned = not bool(args.apply)
    action = "review_submit_planned" if planned else "review_submitted"
    lines = [
        f"{_BRAND} · {'REVIEW-SUBMIT PLAN' if planned else 'REVIEW SUBMITTED'} "
        f"for PR #{result.pr_number} (run {args.run_id})",
    ]
    return _emit(args, 0, lines, {"action": action, "scope_id": args.scope_id,
                                  "run_id": args.run_id, **result.to_dict()})


def _cmd_auto_merge(args: argparse.Namespace) -> int:
    """Plan/apply per-PR GraphQL auto-merge for a run's opened PR."""
    root = Path(args.root)
    try:
        dispatch = _load_dispatch(root, args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · auto-merge refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · auto-merge refused: run {args.run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": args.run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    repo_setting = None
    try:
        app_config = v3_forge_join.load_app_config(args.app_config)
        if args.enable_repo_setting:
            repo_setting = _run_scoped_cli_op(
                app_config=app_config,
                action="allow_auto_merge",
                payload={"apply": bool(args.apply)},
                permissions=v3_forge_join.REPO_ADMIN_TOKEN_PERMISSIONS,
                secret_name=v3_forge_join.REPO_ADMIN_SECRET_NAME,
                ttl_seconds=v3_forge_join.REPO_ADMIN_TOKEN_TTL_SECONDS,
                escalation_authority=v3_forge_join.REPO_ADMIN_TOKEN_ESCALATION_AUTHORITY,
                op=lambda runner: allow_auto_merge(app_config.repo, apply=args.apply, gh_runner=runner),
            )
        result = v3_forge_join.enable_auto_merge_for_run(
            root, args.run_id, app_config=app_config, method=args.method, apply=args.apply,
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · auto-merge refused: {exc}"],
            {"action": "auto_merge_refused", "run_id": args.run_id, "detail": str(exc)},
        )
    planned = not bool(args.apply)
    action = "auto_merge_planned" if planned else "auto_merge_enabled"
    lines = [
        f"{_BRAND} · {'AUTO-MERGE PLAN' if planned else 'AUTO-MERGE ENABLED'} "
        f"for PR #{result.pr_number} (run {args.run_id})",
    ]
    payload = {"action": action, "scope_id": args.scope_id, "run_id": args.run_id, **result.to_dict()}
    if repo_setting is not None:
        payload["repo_setting"] = repo_setting.to_dict()
    return _emit(args, 0, lines, payload)


def _cmd_review(args: argparse.Namespace) -> int:
    """Dispatch a distinct CE-governed reviewer venue for a run's opened PR (G2b).

    Preconditions: the author dispatch exists, belongs to the named Scope, and carries a
    forge-stamped ``change`` block with a real ``pr_number``/``head_sha`` (no PR ⇒ refuse with a
    pointer to ``cev3 pr``). Materializes the reviewer-authority envelope + a ``role: reviewer``
    dispatch; with ``--spawn`` it provisions + launches the venue (pco-allocate → ``ce lane launch
    --json`` → seed). The review SUBMISSION (``gh pr review``) stays the venue's OWN governed act
    under the live Ring-1 hook + envelope; v3 RECORDS the venue and later folds its outcome via the
    unchanged ``cev3 collect ... --outcome review_submitted``.
    """
    if getattr(args, "harness", "claude") == v3_seat_bridge.CODEX_BRIDGE_HARNESS:
        return _emit(
            args,
            2,
            [f"{_BRAND} · review --spawn refused: Codex reviewer venues are deferred; "
             "reviewer authority currently depends on the live Ring-1 hook + envelope."],
            {"error": "codex_review_deferred", "harness": args.harness},
        )
    root = Path(args.root)
    author_run_id = args.run_id
    try:
        author = _load_dispatch(root, author_run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · review refused: {exc}"], {"error": str(exc)})
    if author.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · review refused: run {author_run_id!r} belongs to Scope "
             f"{author.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": author_run_id,
             "dispatch_scope_id": author.get("scope_id")},
        )
    change = author.get("change") or {}
    pr_number = change.get("pr_number")
    head_sha = change.get("head_sha")
    if not pr_number or not head_sha:
        return _emit(
            args, 2,
            [f"{_BRAND} · review refused: run {author_run_id!r} has no opened PR to review",
             f"{_BRAND} · open it first: {CE_CMD} pr {args.scope_id} --run {author_run_id} "
             f"--branch <branch> --manifest-path <path> --app-config <cfg> --apply"],
            {"error": "no_pr", "run_id": author_run_id},
        )
    if args.spawn and (not args.venue_root or not args.ledger_root):
        return _emit(
            args, 2,
            [f"{_BRAND} · review --spawn refused: --venue-root and --ledger-root are required "
             "to provision the out-of-repo reviewer venue"],
            {"error": "spawn_inputs_missing", "run_id": author_run_id},
        )

    # ce-ops#38: when a --ticket is supplied, acquire + verify the work claim
    # BEFORE any venue side effect (no reviewer envelope / dispatch /
    # pco-allocate / pane until the claim holds). --ticket is OPTIONAL on the
    # spawn path for the same closed-manifest reason declared in `_drive_spawn`.
    claim_ctx = None
    if args.spawn and getattr(args, "ticket", None):
        ok, claim = _acquire_dispatch_claim(args.ticket, reason="review")
        if not ok:
            code, lines, payload = claim
            return _emit(args, code, lines, {**payload, "run_id": author_run_id})
        claim_ctx = claim

    unattended = not getattr(args, "no_unattended", False)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, root, reviewer_actor=args.reviewer_actor,
        pr_number=int(pr_number), head_sha=str(head_sha),
        unattended=unattended,
    )
    if not args.spawn:
        lines = [
            f"{_BRAND} · REVIEW dispatch assembled for Scope {args.scope_id!r} "
            f"(PR #{pr_number}, review run {rec.run_id})",
            f"    envelope: {rec.data['review_of']['envelope_ref']}",
            f"    dispatch: {rec.dispatch_path}",
            f"{_BRAND} · (assemble-only — pass --spawn to launch the governed reviewer venue)",
        ]
        return _emit(
            args, 0, lines,
            {"action": "review_assembled", "scope_id": args.scope_id,
             "author_run_id": author_run_id, "review_run_id": rec.run_id,
             "pr_number": int(pr_number),
             "envelope_ref": rec.data["review_of"]["envelope_ref"],
             "dispatch_path": str(rec.dispatch_path)},
        )
    try:
        spawn = v3_seat_bridge.spawn_review_venue(
            rec, controller_id=args.controller_id,
            venue_root=args.venue_root, ledger_root=args.ledger_root,
            seat_env_file=getattr(args, "seat_env_file", None),
        )
    except v3_seat_bridge.SeatBridgeError as exc:
        # spawn_review_venue stamps mark_spawn_failed on any leg's refusal (conserved, not deleted).
        # The venue never materialized — release the work claim we acquired.
        _release_dispatch_claim(claim_ctx, "spawn-refused-before-side-effect")
        return _emit(
            args, 1,
            [f"{_BRAND} · review --spawn refused: {exc}"],
            {"action": "spawn_refused", "reason": "venue_launch_refused",
             "review_run_id": rec.run_id, "detail": str(exc),
             "dispatch_path": str(rec.dispatch_path)},
        )
    pane = spawn.terminal.get("pane_id")
    lines = [
        f"{_BRAND} · SPAWNED reviewer venue for Scope {args.scope_id!r} "
        f"(PR #{pr_number}, review run {rec.run_id})",
        f"    envelope: {rec.data['review_of']['envelope_ref']}",
        f"    dispatch: {rec.dispatch_path}",
        f"    pane: {pane}  [reviewer]",
        f"    next: {CE_CMD} collect {args.scope_id} --run {rec.run_id} "
        f"--outcome review_submitted --pr {pr_number}",
    ]
    return _emit(
        args, 0, lines,
        {"action": "spawned_review", "scope_id": args.scope_id,
         "author_run_id": author_run_id, "review_run_id": rec.run_id,
         "pr_number": int(pr_number), "pane_id": pane, "terminal": spawn.terminal,
         "envelope_ref": rec.data["review_of"]["envelope_ref"],
         "dispatch_path": str(rec.dispatch_path)},
    )


def _cmd_merge(args: argparse.Namespace) -> int:
    """Gate-read (or apply) a squash-merge of the run's opened PR through the v3 forge (G2c).

    Plan-by-default surfaces the gate snapshot (would_merge / review / checks / mergeable) and
    mutates nothing. ``--apply`` is the Operator's explicit gated act (human-gate RATIFY+MERGE
    conserved — the merge MECHANISM goes through v3, the DECISION stays human; server-side branch
    protection + CODEOWNERS still rule), driven under the Operator's ambient ``gh`` as the DISTINCT
    merge identity (never the per-run token). A non-merged result attests NOTHING.
    """
    root = Path(args.root)
    run_id = args.run_id
    try:
        dispatch = _load_dispatch(root, run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · merge refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · merge refused: run {run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    merge_runner = v3_forge_join.ambient_gh_runner()
    try:
        verdict = authority_resolver.DEV_AUTHORITY_RESOLVER.resolve(
            authority_resolver.MergeDecision(
                gate_read=lambda: v3_forge_join.merge_for_run(
                    root, run_id, merge_gh_runner=merge_runner, apply=args.apply,
                )
            )
        )
        result = verdict.value
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · merge refused: {exc}"],
            {"action": "merge_refused", "run_id": run_id, "detail": str(exc)},
        )
    snapshot = result.to_dict()
    # F6: a head that moved is reported as an automatic base-only re-stamp or a refusal — never an
    # override. The status line names which tier acted.
    restamp_note = ""
    if result.head_status == v3_forge_join.HEAD_BASE_ONLY_RESTAMPED:
        restamp_note = (f" · base-only RE-STAMPED {result.old_head_sha}→{result.new_head_sha} "
                        "(machine_rebase_equivalence)")
    elif result.head_status == v3_forge_join.HEAD_BASE_ONLY_RESTAMP:
        restamp_note = f" · base-only re-stamp AVAILABLE {result.old_head_sha}→{result.new_head_sha}"
    if args.apply and result.merged:
        lines = [
            f"{_BRAND} · MERGED PR #{result.pr_number} for Scope {args.scope_id!r} (run {run_id})"
            + restamp_note,
            f"    squash commit: {result.merge_commit_sha}",
        ]
        if result.restamp_recorded:
            lines.append("    runtime_change_restamp recorded (base-only machine equivalence)")
        # The squash tree-equivalence audit is the what-was-TESTED == what-MERGES proof; a false
        # verdict is an operator-visible integrity alarm, never a silent pass.
        if result.audit_tree_equivalence is False:
            lines.append(f"{_BRAND} · ⚠ MERGE-AUDIT TREE MISMATCH — tested tree != merged tree; "
                         "operator review required (merge_audit_tree_mismatch)")
            return _emit(args, 1, lines, {"action": "merge_audit_tree_mismatch",
                                          "scope_id": args.scope_id, "run_id": run_id, **snapshot})
        lines.append(f"    next: {CE_CMD} report {args.scope_id} --run {run_id}")
        return _emit(args, 0, lines, {"action": "merged", "scope_id": args.scope_id,
                                      "run_id": run_id, **snapshot})
    if args.apply:
        # eligible gate but the server reported merged=false (rare) — attests nothing.
        lines = [f"{_BRAND} · merge NOT completed for PR #{result.pr_number} "
                 f"(merged={result.merged}); nothing attested"]
        return _emit(args, 1, lines, {"action": "merge_not_completed", "scope_id": args.scope_id,
                                      "run_id": run_id, **snapshot})
    verdict = "WOULD merge" if result.would_merge else "would NOT merge (gate not satisfied)"
    lines = [
        f"{_BRAND} · MERGE PLAN for PR #{result.pr_number} (Scope {args.scope_id!r}, run {run_id})"
        + restamp_note,
        f"    head_status={result.head_status} · {verdict}: review={result.review_decision} · "
        f"checks={result.rollup_state} · mergeable={result.mergeable}",
        f"{_BRAND} · (plan-only — pass --apply for the Operator's gated merge)",
    ]
    return _emit(args, 0, lines, {"action": "merge_planned", "scope_id": args.scope_id,
                                  "run_id": run_id, **snapshot})


def _cmd_status(args: argparse.Namespace) -> int:
    """List Scopes with their projected stage (the canon skin over the machine)."""
    root = Path(args.root)
    scopes = _iter_scopes(root)
    counts = _phase_counts(scopes, root)
    lines = [
        f"{_BRAND} · {len(scopes)} Scope(s) · "
        + " · ".join(f"{p} {counts[p]}" for p in coordination.COGNITIVE_PHASES),
    ]
    scope_payloads: list[dict[str, Any]] = []
    for s in sorted(scopes, key=lambda x: str(x.get("scope_id"))):
        # v3.1-G2c: surface the opened PR + a live reviewer venue on the Scope line.
        change_block, review = _forge_surface_for_scope(root, str(s.get("scope_id")))
        pr_number = change_block.get("pr_number") if change_block else None
        review_run_id = review.get("run_id") if review else None
        badge = (f"  · PR #{pr_number}" if pr_number else "") + ("  · ⊙ review" if review else "")
        lines.append("  " + _card_line(s, root) + badge)
        scope_payloads.append(
            {"scope_id": s.get("scope_id"), "projection": _projection(s, root),
             "pr": pr_number, "review_run_id": review_run_id}
        )
    return _emit(
        args, 0, lines,
        {"action": "status", "count": len(scopes), "phase_counts": counts, "scopes": scope_payloads},
    )


def _cmd_show(args: argparse.Namespace) -> int:
    """Show one Scope: the canon-labelled fields + its projection + readiness."""
    root = Path(args.root)
    try:
        scope = _load_scope(root, args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · {exc}"], {"error": str(exc)})
    proj = _projection(scope, root)
    ready, reasons = coordination.scope_is_ready(scope)
    lines = [
        _card_line(scope, root),
        f"    Goal (intent):        {scope.get('intent')}",
        f"    Done-when (criteria): {scope.get('acceptance_criteria') or '—'}",
        f"    Budget (appetite):    {scope.get('appetite') or '—'}",
        f"    Change-type (class):  {scope.get('mutation_class')}",
        f"    Stage / state / board: {proj['phase']} / {proj['state']} / {proj['board']}",
        f"    Ready: {'yes' if ready else 'no — ' + '; '.join(reasons)}"
        f" · bet placed: {'yes' if coordination.is_ratified(scope) else 'no'}",
    ]
    # v3.1-G2c: surface the forge state — the opened PR + a live reviewer venue, if any.
    change_block, review = _forge_surface_for_scope(root, str(scope.get("scope_id")))
    pr_number = change_block.get("pr_number") if change_block else None
    review_run_id = review.get("run_id") if review else None
    if change_block:
        lines.append(
            f"    PR: #{pr_number} ({change_block.get('branch')} → {change_block.get('base')})"
        )
    if review:
        rv = review.get("review_of") or {}
        lines.append(f"    Review venue: {review_run_id} (PR #{rv.get('pr_number')})")
    return _emit(
        args, 0, lines,
        {"action": "show", "scope_id": scope.get("scope_id"), "scope": scope,
         "projection": proj, "ready": ready, "reasons": reasons,
         "ratified": coordination.is_ratified(scope),
         "pr": pr_number, "review_run_id": review_run_id},
    )


def _cmd_artifacts(args: argparse.Namespace) -> int:
    """Enumerate the on-disk artifacts for a Scope (the ◆ Report enriches this at G-7.3)."""
    root = Path(args.root)
    path = _scope_path(root, args.scope_id)
    if not path.is_file():
        return _emit(
            args, 2,
            [f"{_BRAND} · no Scope {args.scope_id!r} under {_scopes_dir(root)}"],
            {"error": "not_found"},
        )
    artifacts = [{"kind": "scope", "path": str(path), "label": f"Scope {args.scope_id}",
                  "inspect": f"{CE_CMD} show {args.scope_id}"}]
    # G-7.3 / G1b: with a run evidence chain, also enumerate the run artifacts (PR /
    # evidence-chain / spend) via the ◆ Completion-Report artifact-awareness fold.
    # The chain defaults to a collected dispatch's chain (explicit --evidence wins).
    evidence, run_id = _resolve_run_evidence(args, root)
    if evidence:
        records = yaml.safe_load(Path(evidence).read_text(encoding="utf-8"))
        if isinstance(records, dict):
            records = records.get("records") or records.get("leaves") or []
        summary = v3_report.summary_from_evidence(
            records or [], scope_id=args.scope_id, run_id=run_id,
            budget=getattr(args, "cap", None),
        )
        artifacts += [a for a in v3_report.enumerate_artifacts(summary) if a["kind"] != "scope"]
    lines = [f"{_BRAND} · artifacts for Scope {args.scope_id!r}:"]
    lines += [f"    {a['kind']:>10}  {a.get('path', a['label'])}   ({a['inspect']})" for a in artifacts]
    if not evidence:
        lines.append(f"{_BRAND} · (pass --evidence <chain> to enumerate run artifacts: PR / evidence / spend)")
    return _emit(args, 0, lines, {"action": "artifacts", "scope_id": args.scope_id, "artifacts": artifacts})


def _cmd_report(args: argparse.Namespace) -> int:
    """Render the per-run ◆ CE Completion Report (Outcome · Verdict · Next + Artifacts).

    Folds the REAL conserved outcome + spend off the run evidence chain
    (``--evidence``); the grading synthesis (Done-when / CI / in-scope) is injected
    via flags (its live assembly is the deferred seam).
    """
    root = Path(getattr(args, "root", V3_LOCAL_STATE_ROOT))
    evidence, run_id = _resolve_run_evidence(args, root)
    records: list[Any] = []
    if evidence:
        loaded = yaml.safe_load(Path(evidence).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            loaded = loaded.get("records") or loaded.get("leaves") or []
        records = loaded or []
    grading: dict[str, Any] = {}
    if args.change_type:
        grading["change_type"] = args.change_type
    if args.done_when_total is not None:
        grading["done_when_total"] = args.done_when_total
        grading["done_when_met"] = args.done_when_met if args.done_when_met is not None else args.done_when_total
    if args.ci:
        grading["ci"] = args.ci
    if args.in_scope is not None:
        grading["in_scope"] = args.in_scope
    if args.budget_size:
        grading["budget_size"] = args.budget_size
    summary = v3_report.summary_from_evidence(
        records, scope_id=args.scope_id, run_id=run_id, budget=args.cap, unit=args.unit, **grading,
    )
    if args.pr is not None:
        summary["pr"] = args.pr
    lines = v3_report.render_report(summary)
    return _emit(args, 0, lines, {
        "action": "report", "run_id": summary.get("run_id"), "scope_id": args.scope_id,
        "outcome": summary.get("outcome"), "outcome_label": v3_report.outcome_label(summary.get("outcome")),
        "verdict": v3_report.render_verdict(summary), "next": v3_report.render_next(summary),
        "artifacts": v3_report.enumerate_artifacts(summary),
    })


def _cmd_shape(args: argparse.Namespace) -> int:
    """Run the Frame→Shape grill-me over a partial draft (gaps + minimum questions).

    The agent drafts every field EXCEPT the Budget (human-only). Surfaces the
    gap-aware Scope card, the minimum questions to close, and (with --persona +
    --signal) the detect-and-offer decision. A pure dialogue helper — it does not
    write a Scope artifact (that is `ce scope` once the gaps are closed).
    """
    draft: dict[str, Any] = {"scope_id": args.scope_id}
    if args.goal:
        draft["intent"] = args.goal
    if args.done_when:
        draft["acceptance_criteria"] = list(args.done_when)
    if args.change_type:
        draft["mutation_class"] = args.change_type
    # NB: Budget (appetite) is intentionally NOT drafted — it is human-only.
    result = v3_shaping.shape(draft)
    lines = [result.card]
    if result.gaps:
        lines.append(f"{_BRAND} · to reach Ready, close {len(result.gaps)} gap(s):")
        for g in result.gaps:
            who = "  (your call — Budget is yours to set)" if g.human_only else ""
            lines.append(f"    - {g.label}: {g.question}{who}")
    else:
        lines.append(f"{_BRAND} · Ready — place the bet with `{CE_CMD} ratify {args.scope_id}`")
    offer = None
    if args.persona and args.signal:
        # pass the actual change-type (None when not yet proposed) so the dial
        # biases conservative for an unknown class, per shaping-ux.md.
        offer = v3_shaping.should_offer(args.persona, args.change_type, args.signal)
        thr = v3_shaping.offer_threshold(args.persona, args.change_type)
        band = v3_shaping.risk_class(args.change_type)
        verb = "WOULD offer to crystallize this into a Scope" if offer else "holds (free chat — Frame)"
        lines.append(
            f"{_BRAND} · detect-and-offer [{args.persona}/{band}-risk · signal {args.signal} · needs {thr}]: {verb}"
        )
    return _emit(args, 0, lines, {
        "action": "shape", "scope_id": args.scope_id, "ready": result.ready,
        "gaps": [{"field": g.field, "label": g.label, "human_only": g.human_only} for g in result.gaps],
        "questions": list(result.questions), "offer": offer,
    })


def _cmd_session(args: argparse.Namespace) -> int:
    """The governed session frame + the unified context/spend status line (G-7.1).

    The context-% is the harness's authoritative number (CONSUMED via
    ``--context-pct``; the live per-turn tap is the deferred seam). The spend
    meter folds the REAL G-5 ``project_spend`` projection over an evidence spine
    (``--spine``) against the run cap (``--cap``); absent those it is unmetered.
    """
    counts = _phase_counts(_iter_scopes(Path(args.root)), Path(args.root))
    context = v3_session.context_meter(args.context_pct)
    if args.spine and args.cap is not None:
        records = yaml.safe_load(Path(args.spine).read_text(encoding="utf-8"))
        if isinstance(records, dict):
            records = records.get("records") or records.get("leaves") or []
        spend = v3_session.spend_meter_from_spine(
            records or [], args.cap, scope="run", unit=args.unit, run_id=args.run_id
        )
    else:
        spend = v3_session.spend_meter(None, None, args.unit)
    ce_ver = version.ce_version()
    lines = v3_session.render_session(
        counts, context=context, spend=spend, at_boundary=not args.mid_output,
        repo=args.repo, transport=args.transport, backend=args.backend, root=args.root,
        version=ce_ver,
    )
    return _emit(
        args, 0, lines,
        {"action": "session", "root": args.root, "phase_counts": counts,
         "ce_version": ce_ver,
         "context": {"pct": context.pct, "state": context.state},
         "spend": {"state": spend.state, "ratio": spend.ratio,
                   "spent": v3_session.fmt_amount(spend.spent) if spend.spent is not None else None,
                   "cap": v3_session.fmt_amount(spend.cap) if spend.cap is not None else None,
                   "unit": spend.unit}},
    )


def _onboard_apply_driver(
    *,
    merged: "v3_installer.MergeResult | None" = None,
    policy_sha: str | None = None,
    adoption: bool = False,
) -> onboard_apply.ApplyDriver:
    """Seam (ce-ops#85): the side-effect driver for ``onboard --apply``.

    With no context this returns the conservative base driver. With the merged
    install answers and verified policy digest, this is the production live-forge
    selection point:

    * read/plain-join mode returns a live read driver only when explicitly
      authorized/configured; otherwise it fail-closes to the base driver.
    * adoption mode returns the E3 brownfield adoption driver only under the
      dual live-forge + adoption-write escalation; otherwise it delegates to the
      read/plain-join selector.

    The zero-arg form stays available for legacy tests and conservative fakes.
    """
    base = onboard_apply.ApplyDriver()
    if merged is None or not policy_sha:
        return base
    if adoption:
        return onboard_apply_live.adoption_forge_select(
            base, merged=merged, policy_sha=policy_sha
        )
    return onboard_apply_live.live_forge_select(base, merged=merged, policy_sha=policy_sha)


def _factory_accepts_onboard_context(factory: Any) -> bool:
    try:
        params = inspect.signature(factory).parameters
    except (TypeError, ValueError):
        return False
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()):
        return True
    allowed_kinds = {
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    }
    return all(
        name in params and params[name].kind in allowed_kinds
        for name in ("merged", "policy_sha", "adoption")
    )


def _select_onboard_apply_driver(
    *,
    merged: "v3_installer.MergeResult",
    policy_sha: str,
    adoption: bool,
) -> onboard_apply.ApplyDriver:
    """Call the production driver seam while preserving old zero-arg monkeypatch fakes."""
    factory = _onboard_apply_driver
    if _factory_accepts_onboard_context(factory):
        return factory(merged=merged, policy_sha=policy_sha, adoption=adoption)
    return factory()


def _close_apply_driver(driver: Any) -> None:
    """Revoke a live-forge driver's token if it has a ``close()`` lifecycle hook (ce-ops#88).

    A no-op for the base :class:`onboard_apply.ApplyDriver` and the test ``FakeDriver``
    (neither defines ``close``), so this is invisible to the existing seam contract.
    """
    close = getattr(driver, "close", None)
    if callable(close):
        close()


def _protection_enforcement_from_ce_probe(probe: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(probe, Mapping):
        return {"state": "unprobed"}
    protection = probe.get("protection")
    if not isinstance(protection, Mapping):
        if probe.get("reason") == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE:
            return {
                "state": "unenforceable",
                "code": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
                "detail": probe.get("detail"),
                "remediation": probe.get("remediation"),
            }
        return {"state": "unprobed"}
    if probe.get("reason") == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE:
        return {
            "state": "unenforceable",
            "code": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
            "surface": protection.get("surface"),
            "message": protection.get("message"),
            "detail": probe.get("detail"),
            "remediation": probe.get("remediation") or protection.get("remediation"),
        }
    source = str(protection.get("source") or "")
    if source == "ruleset":
        state = "verified_ruleset"
    elif source == "classic" or protection.get("ok"):
        state = "verified_classic"
    else:
        state = "unprobed"
    result = {
        "state": state,
        "floor_satisfied": bool(protection.get("ok")),
    }
    if protection.get("classic_unavailable") is not None:
        result["classic_unavailable"] = bool(protection.get("classic_unavailable"))
    return result


def _protection_floor_refusal_payload(
    *, repo: str, branch: str, probe: Mapping[str, Any] | None
) -> dict[str, Any]:
    diagnostic = probe.get("protection") if isinstance(probe, Mapping) else None
    detail = ""
    if isinstance(probe, Mapping):
        detail = str(probe.get("detail") or "")
    if not detail:
        detail = onboard_apply.protection_floor_unenforceable_detail(
            repo=repo,
            branch=branch,
            diagnostic=diagnostic if isinstance(diagnostic, Mapping) else None,
        )
    remediation = (
        probe.get("remediation")
        if isinstance(probe, Mapping)
        else None
    ) or onboard_apply.PROTECTION_FLOOR_REMEDIATION
    return {
        "error": "refused",
        "code": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
        "detail": detail,
        "remediation": remediation,
        "enforcement": _protection_enforcement_from_ce_probe(probe),
    }


def _load_trust_anchor_records(anchor_specs: Sequence[str]) -> tuple[v3_installer.TrustAnchorRecord, ...]:
    """Load operator-supplied out-of-band trust anchors from ``SOURCE=PATH`` specs."""
    records: list[v3_installer.TrustAnchorRecord] = []
    for raw_spec in anchor_specs:
        if "=" not in raw_spec:
            raise v3_installer.InstallRefused(
                "--trust-anchor must be SOURCE=PATH, for example dns-txt=/tmp/ce-root-v1.txt"
            )
        source, path_text = raw_spec.split("=", 1)
        source = source.strip()
        path_text = path_text.strip()
        if not source or not path_text:
            raise v3_installer.InstallRefused("--trust-anchor must name both SOURCE and PATH")
        try:
            text = Path(path_text).read_text(encoding="utf-8")
        except OSError as exc:
            raise v3_installer.InstallRefused(f"trust_anchor_unreadable: {source}: {exc}") from exc
        records.extend(v3_installer.parse_trust_anchor_records(text, source=source))
    return tuple(records)


def _verified_payload(
    verified: v3_installer.VerifyResult,
    trust_anchor: v3_installer.TrustAnchorEvidence | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": True, "key_id": verified.key_id}
    if trust_anchor is not None:
        payload["trust_anchors"] = trust_anchor.to_record()
    return payload


def _cmd_onboard(args: argparse.Namespace) -> int:
    """Two-mode install — verify the signed spec, then plan or apply.

    v3.5-E.3 (one engine, two modes): the same verified journey, with answers
    coming from ``interactive > answers-file > detected > default``.

    ``--inventory`` emits the operator-input inventory (the awareness artifact
    an agent reads to PREPARE the answers file); ``--answers f.yaml`` loads the
    IaC answers file (schema-validated, fail-closed on unknown keys, secrets by
    SecretRef only); ``--plan`` is the terraform-plan analog (the full plan
    including the EXACT remaining asks + the decomposed GitHub leg);
    ``--non-interactive`` turns the final ask into a fail-closed refusal that
    enumerates exactly what is missing.

    Order is load-bearing and unchanged (design §2.4): ``require_verified``
    FIRST — the answers file configures the VERIFIED procedure; nothing in it
    (and no flag here) can substitute for the signature gate. The CLI is the
    I/O edge (it reads the spec, the schema document, and the answers file,
    and runs the live read-only probes). ``--apply`` crosses into the E2
    live-drive seam in ``onboard_apply``; dry-run planning remains pure.
    """
    if getattr(args, "apply", False) and (args.inventory or args.show_plan):
        return _emit(
            args,
            2,
            [f"{_BRAND} · onboard refused: --apply cannot be combined with --inventory or --plan"],
            {"error": "invalid_onboard_mode"},
        )
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        return _emit(args, 2, [f"{_BRAND} · onboard refused: spec not found: {spec_path}"],
                     {"error": "spec_not_found"})
    spec_bytes = spec_path.read_bytes()
    apply_mode = bool(getattr(args, "apply", False))
    apply_verifier = None
    apply_signature: dict[str, Any] | None = None
    pinned_keys_for_plan = v3_installer.PINNED_KEYS
    spec_for_plan = spec_bytes
    trust_anchor_evidence: v3_installer.TrustAnchorEvidence | None = None
    authentic_mode = bool(getattr(args, "require_authentic", False) or getattr(args, "trust_root", None))
    self_attested = args.sig_value is None and not apply_mode and not authentic_mode
    if authentic_mode:
        if not args.trust_root:
            return _emit(
                args,
                2,
                [f"{_BRAND} · onboard refused: --require-authentic requires --trust-root"],
                {"error": "trust_root_required"},
            )
        trust_root_path = Path(args.trust_root)
        try:
            trust_root_text = trust_root_path.read_text(encoding="utf-8")
        except OSError as exc:
            return _emit(
                args,
                2,
                [f"{_BRAND} · onboard refused: trust root unreadable: {exc}"],
                {"error": "trust_root_unreadable", "detail": str(exc)},
            )
        fetched_keys = v3_installer.parse_allowed_signers(trust_root_text)
        usable_keys = {
            key_id: key_material
            for key_id, key_material in fetched_keys.items()
            if key_id in v3_installer.PINNED_KEYS
        }
        if not usable_keys:
            return _emit(
                args,
                1,
                [f"{_BRAND} · onboard REFUSED: signature_refused: no fetched trust-root key id is pinned by this wheel"],
                {"error": "refused", "detail": "signature_refused: no fetched trust-root key id is pinned by this wheel"},
            )
        pinned_keys_for_plan = usable_keys
        apply_verifier = v3_installer.ssh_ed25519_verifier(_ssh_keygen_verify_runner)
        try:
            signed = v3_installer.parse_signed_install_spec(spec_bytes)
            spec_for_plan = v3_installer.canonical_spec_bytes(spec_bytes)
            signature = signed.signature
            verified = v3_installer.require_verified(
                spec_for_plan,
                signature,
                pinned_keys=usable_keys,
                verifier=apply_verifier,
            )
            if verified.key_id is None or verified.key_id not in usable_keys:
                raise v3_installer.InstallRefused(
                    "trust_anchor_refused: verified key id missing from fetched trust root"
                )
            anchor_records = _load_trust_anchor_records(getattr(args, "trust_anchor", []) or [])
            trust_anchor_evidence = v3_installer.verify_trust_anchors(
                verified.key_id,
                usable_keys[verified.key_id],
                anchor_records,
                install_spec_source=v3_installer.PUBLISHED_INSTALL_SPEC_URL,
            )
            if not trust_anchor_evidence.ok:
                raise v3_installer.InstallRefused(
                    f"trust_anchor_refused: {trust_anchor_evidence.status}: "
                    f"{trust_anchor_evidence.reason}"
                )
        except v3_installer.InstallRefused as exc:
            return _emit(
                args,
                1,
                [f"{_BRAND} · onboard REFUSED: {exc}"],
                {"error": "refused", "detail": str(exc)},
            )
        self_attested = False
    elif apply_mode or args.sig_algo == v3_installer.SSH_ED25519_ALGO:
        apply_verifier = v3_installer.ssh_ed25519_verifier(_ssh_keygen_verify_runner)
        if args.sig_value is not None:
            apply_signature = {
                "key_id": args.key_id,
                "algo": args.sig_algo or v3_installer.SSH_ED25519_ALGO,
                "namespace": v3_installer.SSH_SIG_NAMESPACE,
                "value": args.sig_value,
            }
            if args.content_sha256:
                apply_signature["content_sha256"] = args.content_sha256
        try:
            signed = onboard_apply.parse_signed_spec(spec_bytes, apply_signature)
            signature = {k: v for k, v in signed.signature.items() if k != "namespace"}
            spec_for_plan = v3_installer.canonical_spec_bytes(spec_bytes)
            verified = v3_installer.require_verified(
                spec_for_plan,
                signature,
                pinned_keys=v3_installer.PINNED_KEYS,
                verifier=apply_verifier,
            )
        except (onboard_apply.ApplyRefused, v3_installer.InstallRefused) as exc:
            return _emit(
                args,
                1,
                [f"{_BRAND} · onboard REFUSED: {exc}"],
                {"error": "refused", "detail": str(exc)},
            )
        self_attested = False
    elif args.sig_algo not in (None, v3_installer.CONTENT_ALGO):
        return _emit(
            args,
            2,
            [f"{_BRAND} · onboard refused: unsupported --sig-algo {args.sig_algo!r}"],
            {"error": "unsupported_sig_algo"},
        )
    else:
        signature = {"key_id": args.key_id, "algo": v3_installer.CONTENT_ALGO,
                     "value": args.sig_value or v3_installer.content_digest(spec_bytes)}
        verified = None
    # 1. verify FIRST — unbypassed; --inventory/--plan ride the same gate.
    if verified is None:
        try:
            verified = v3_installer.require_verified(
                spec_bytes, signature, pinned_keys=v3_installer.PINNED_KEYS
            )
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"],
                         {"error": "refused", "detail": str(exc)})
    # 2. the answers schema + the answers file (the CLI is the I/O edge; the
    #    engine is pure — the schema document is injected as a dict).
    schema_path = Path(args.answers_schema)
    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return _emit(args, 2,
                     [f"{_BRAND} · onboard refused: answers schema unreadable: {exc}"],
                     {"error": "schema_unreadable", "detail": str(exc)})
    answers: dict[str, Any] = {}
    answers_sha = None
    if args.answers:
        answers_path = Path(args.answers)
        if not answers_path.is_file():
            return _emit(args, 2,
                         [f"{_BRAND} · onboard refused: answers file not found: {answers_path}"],
                         {"error": "answers_not_found"})
        answers_bytes = answers_path.read_bytes()
        # the evidence binding's hashable input (SecretRefs are inert strings)
        answers_sha = v3_installer.content_digest(answers_bytes)
        try:
            loaded = yaml.safe_load(answers_bytes.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            return _emit(args, 1,
                         [f"{_BRAND} · onboard REFUSED: answers file is not valid YAML: {exc}"],
                         {"error": "refused", "detail": str(exc)})
        try:
            answers = v3_installer.require_valid_answers(loaded, schema=schema)
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"],
                         {"error": "refused", "detail": str(exc)})
    # 3. live read-only detection the CLI can do TODAY (deeper probes = E.4).
    detected: dict[str, Any] = {}
    present_harnesses = [name for name, binary in
                         (("claude-code", "claude"), ("codex", "codex")) if _which(binary)]
    if present_harnesses:
        detected["provider.harness"] = (
            present_harnesses[0] if len(present_harnesses) == 1 else "both"
        )
    project_root = Path.cwd()
    try:
        try:
            brownfield_probe = _detect_brownfield_project(project_root)
        except v3_installer.InstallRefused as exc:
            # ce-ops#191 (N1×N5 reconciliation): brownfield detection shells out to
            # git, which fail-closes on a missing-dependency. For the read-only
            # ``--inventory`` AWARENESS artifact this MUST NOT refuse — the missing
            # tool is surfaced as a WARN dependency row (exit 0) below. The
            # ``--plan``/``--apply`` path (and any NON-dependency refusal) re-raise
            # and keep N5's clean fail-closed refusal.
            if not (args.inventory and _is_missing_dependency_refusal(exc)):
                raise
            brownfield_probe = None
        detected.update(v3_installer.brownfield_detected_facts(brownfield_probe))
        # 4. --inventory: the awareness artifact (schema-derived, never hand-kept).
        if args.inventory:
            rows = v3_installer.inventory_emission(
                schema, detected=detected, answers=answers or None
            )
            inventory_merged = v3_installer.merge_answers(schema, answers=answers or None, detected=detected)
            inventory_backend = v3_installer.resolve_isolation_backend(
                profile=inventory_merged.value("profile"),
                explicit=inventory_merged.value("isolation_backend"),
            )
            dependency_probe = {
                tool: _which(tool)
                for tool in v3_installer.BACKEND_DEPS[inventory_backend]
            }
            rows = rows + v3_installer.inventory_dependency_rows(
                inventory_backend,
                dependency_probe,
            )
            inventory_missing = v3_installer.missing_answers(schema, inventory_merged)
            first_project = v3_installer.build_greenfield_first_project_plan(
                schema, inventory_merged, inventory_missing
            )
            brownfield = v3_installer.brownfield_inventory_summary(
                schema, answers=answers or None, probe=brownfield_probe
            )
            trust_anchor_note = (
                f"; trust anchors {', '.join(trust_anchor_evidence.agreed)}"
                if trust_anchor_evidence is not None
                else ""
            )
            lines = [
                f"{_BRAND} · onboard inventory — {len(rows)} inputs "
                f"(spec verified against pinned key {verified.key_id!r}{trust_anchor_note})"
            ]
            for row in rows:
                modes = "/".join(row["modes"]) or "—"
                optional = " · optional" if row["optional"] else ""
                lines.append(
                    f"    step {row['step']} · {row['key']} "
                    f"[{row['sensitivity']} · {modes}{optional}] → {row['status']}"
                )
            lines.append(
                f"{_BRAND} · prepare {v3_installer.ANSWERS_BASENAME} from this "
                "(secrets ONLY as env:// file:// prompt:// keychain:// refs), then: "
                f"{CE_CMD} onboard --spec <spec> --answers <file> --plan"
            )
            lines.append(
                f"{_BRAND} · brownfield inventory — {len(brownfield['ci'])} workflow(s), "
                f"{len(brownfield['tests'])} test command(s), history {brownfield['history']['mode']}, "
                f"scrub {brownfield['secrets_preflight']['status']}"
            )
            if first_project is not None:
                lines.append(
                    f"{_BRAND} · first project — greenfield · scaffold "
                    f"{first_project['scaffold_input']['kind']} · "
                    f"E2 apply required {str(first_project['e2_apply_required']).lower()}"
                )
            return _emit(args, 0, lines, {
                "action": "onboard_inventory",
                "verified": _verified_payload(verified, trust_anchor_evidence),
                "self_attested": self_attested,
                "inventory": [dict(row) for row in rows],
                "brownfield": brownfield,
                "first_project": first_project,
            })
    except v3_installer.InstallRefused as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · onboard REFUSED: {exc}"],
            {"error": "refused", "detail": str(exc)},
        )
    # 5. the precedence merge + the missing list + the scoped sudo-grant diff.
    merged = v3_installer.merge_answers(schema, answers=answers or None, detected=detected)
    missing = v3_installer.missing_answers(schema, merged)
    # ce-ops#88 — the canonical install-spec digest binds any live-forge token mint to the
    # verified install spec in force (the minter's policy_sha). Computed once; used at both
    # the apply and the --plan plain-join detection sites below.
    _install_spec_digest = v3_installer.content_digest(v3_installer.canonical_spec_bytes(spec_bytes))
    # ce-ops#71 MAJOR-1: resolve the isolation backend BEFORE the preflight, the
    # SAME way apply does (mirror ``onboard_apply._prepare``), and drive the probe /
    # dep-plan / sudo-grant diff off the BACKEND-AWARE deps — NOT the flat Tier-2
    # ``REQUIRED_DEPENDENCIES``. Otherwise a solo-pilot → ``os-native`` install on a
    # host without runsc/proxy is falsely REFUSED at this CLI gate even though the
    # fixed, backend-driven apply never needs them. ``gvisor-proxy`` is unchanged.
    isolation_backend = v3_installer.resolve_isolation_backend(profile=merged.value("profile"))
    backend_deps = v3_installer.BACKEND_DEPS[isolation_backend]
    probe = {tool: _which(tool) for tool in backend_deps}
    dep_plan = v3_installer.plan_dependencies(isolation_backend, probe)
    grant_diff = v3_installer.sudo_grant_diff(merged.value("host.sudo_grant"), dep_plan)
    # 6. --non-interactive: fail-closed (the terraform -input=false analog).
    if args.non_interactive:
        try:
            v3_installer.require_complete(missing)
            if grant_diff.uncovered:
                raise v3_installer.InstallRefused(
                    "non-interactive mode is fail-closed — planned privileged "
                    f"installs outside the sudo grant: {', '.join(grant_diff.uncovered)} "
                    f"(host.sudo_grant covers: {', '.join(grant_diff.grant) or 'nothing'})"
                )
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"], {
                "error": "refused", "detail": str(exc),
                "missing": [{"key": m.key, "step": m.step, "reason": m.reason} for m in missing],
                "sudo_uncovered": list(grant_diff.uncovered),
            })
    if apply_mode and (missing or grant_diff.uncovered):
        detail = (
            "apply requires complete answers"
            if missing
            else "planned privileged installs outside the sudo grant"
        )
        return _emit(args, 1, [f"{_BRAND} · onboard apply REFUSED: {detail}"], {
            "error": "refused",
            "detail": detail,
            "missing": [{"key": m.key, "step": m.step, "reason": m.reason} for m in missing],
            "sudo_uncovered": list(grant_diff.uncovered),
        })
    # 7. the cost profile — CLI flags are the interactive override (precedence);
    #    otherwise a custom answers profile supplies the (stripped) binding.
    opt_out = args.opt_out
    optout_ratification = None
    if args.opt_out:
        optout_ratification = {"ratified_prompt_sha": args.ratified_prompt_sha or "",
                               "approver_ref": args.approver_ref or ""}
    elif answers:
        try:
            binding = v3_installer.optout_binding_from_answers(answers)
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"],
                         {"error": "refused", "detail": str(exc)})
        if binding is not None:
            opt_out, optout_ratification = True, binding
    try:
        plan = v3_installer.build_install_plan(
            spec_for_plan, signature, pinned_keys=pinned_keys_for_plan, probe=probe,
            mode=args.mode, tier=v3_installer.tier_for_backend(isolation_backend),
            opt_out=opt_out, optout_ratification=optout_ratification,
            verifier=apply_verifier,
        )
    except v3_installer.InstallRefused as exc:
        return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"], {"error": "refused", "detail": str(exc)})
    if trust_anchor_evidence is not None:
        plan["verified"] = dict(plan["verified"])
        plan["verified"]["trust_anchors"] = trust_anchor_evidence.to_record()
    brownfield_plan = v3_installer.build_brownfield_adoption_plan(
        answers or {"answers_version": 1},
        schema=schema,
        probe=brownfield_probe,
    )
    first_project_plan = v3_installer.build_greenfield_first_project_plan(
        schema, merged, missing
    )
    if apply_mode:
        plain_join_driver = None
        adoption_driver = None  # ce-ops#85 — the E3 adoption driver (genuine-brownfield join PR)
        adoption_mode = False
        live_candidate = None  # ce-ops#88 — a live-forge driver to revoke on every exit
        if merged.value("github.mode") == "existing" and brownfield_plan["enabled"]:
            # ce-ops#85 — a new dev JOINING an ALREADY-CE repo is a *plain-join*,
            # NOT brownfield *adoption*. Detect already-CE FAIL-CLOSED and route to
            # the idempotent verify/reconcile apply legs; genuine brownfield
            # (existing + NOT already-CE) keeps the UNCHANGED E3 refuse below. The
            # default driver has no live forge legs, so production defers until a
            # live driver is wired (detection returns False → the same E3 refuse).
            # ce-ops#88 — _onboard_apply_driver is the production live-driver seam. It returns
            # the E3 adoption driver ONLY under the DUAL escalation (CE_FORGE_LIVE_FORGE +
            # CE_FORGE_ADOPTION_WRITE); otherwise it delegates to the read-only live driver
            # (or the base), so an unauthorized run keeps the unchanged brownfield_deferred
            # status quo. The driver still serves detection and is revoked on every exit path.
            candidate_driver = _select_onboard_apply_driver(
                merged=merged, policy_sha=_install_spec_digest, adoption=True
            )
            live_candidate = candidate_driver
            target_branch = str(merged.value("github.new_repo.default_branch", "main") or "main")
            target_repo = str(merged.value("github.repo") or "")
            if onboard_apply.repo_is_already_ce_governed(
                candidate_driver,
                repo=target_repo,
                branch=target_branch,
                schema=schema,
            ):
                plain_join_driver = candidate_driver
            elif (
                isinstance(getattr(candidate_driver, "last_ce_governance_probe", None), Mapping)
                and getattr(candidate_driver, "last_ce_governance_probe", {}).get("reason")
                == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE
            ):
                ce_probe = getattr(candidate_driver, "last_ce_governance_probe")
                _close_apply_driver(live_candidate)
                refusal = _protection_floor_refusal_payload(
                    repo=target_repo, branch=target_branch, probe=ce_probe
                )
                return _emit(
                    args,
                    1,
                    [
                        f"{_BRAND} · onboard apply REFUSED "
                        f"({onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE}): "
                        f"{refusal['detail']}"
                    ],
                    refusal,
                )
            elif brownfield_plan["blocked"]:
                # A blocker (needs_baseline_capture / dirty tree / scanner_unavailable /
                # unwaived findings / unratified waiver) ALWAYS refuses — even when authorized.
                _close_apply_driver(live_candidate)
                blocker = brownfield_plan["blockers"][0]
                return _emit(
                    args,
                    1,
                    [f"{_BRAND} · onboard apply REFUSED ({blocker['code']}): {blocker['detail']}"],
                    {
                        "error": "refused",
                        "code": blocker["code"],
                        "detail": blocker["detail"],
                        "brownfield_blockers": brownfield_plan["blockers"],
                        "brownfield_adoption": brownfield_plan,
                    },
                )
            elif (
                isinstance(candidate_driver, onboard_apply_live.LiveForgeAdoptionDriver)
                and brownfield_plan["classification"] in {"adoptable", "adoptable_after_scrub"}
            ):
                # ce-ops#85 — AUTHORIZED genuine-brownfield adoption: drive the join-PR legs.
                adoption_driver = candidate_driver
                adoption_mode = True
            else:
                # Not authorized for the write escalation → unchanged status-quo refuse.
                _close_apply_driver(live_candidate)
                return _emit(
                    args,
                    1,
                    [
                        f"{_BRAND} · onboard apply REFUSED (e2_brownfield_seam_unavailable): "
                        "E3 brownfield adoption is planned, but this onboard_apply run is not authorized "
                        "for the adoption write escalation (set CE_FORGE_LIVE_FORGE + CE_FORGE_ADOPTION_WRITE)"
                    ],
                    {
                        "error": "refused",
                        "code": "e2_brownfield_seam_unavailable",
                        "detail": "E3 brownfield apply requires the adoption write escalation (CE_FORGE_ADOPTION_WRITE); this run only emits the handoff plan",
                        "brownfield_blockers": [],
                        "brownfield_adoption": brownfield_plan,
                    },
                )
        request = onboard_apply.ApplyRequest(
            spec_bytes=spec_bytes,
            schema=schema,
            answers=answers,
            answers_sha256=answers_sha,
            state_root=Path(args.root),
            mode=args.mode,
            detected=detected,
            dependency_probe=probe,
            non_interactive=bool(args.non_interactive),
            opt_out=opt_out,
            optout_ratification=optout_ratification,
            explicit_signature=apply_signature,
            first_scope_id=args.first_scope_id,
            lock_timeout_seconds=args.lock_timeout,
            spawn_smoke=bool(args.spawn_smoke),
            # ce-ops#85 adoption-apply: the join-PR projection + fresh probe + the mode flag.
            adoption_apply=adoption_mode,
            brownfield_plan=brownfield_plan if adoption_mode else None,
            brownfield_probe=brownfield_probe if adoption_mode else None,
        )
        try:
            apply_driver = adoption_driver or plain_join_driver
            if apply_driver is not None:
                summary = onboard_apply.apply_onboard(
                    request, verifier=apply_verifier, driver=apply_driver
                )
            else:
                summary = onboard_apply.apply_onboard(request, verifier=apply_verifier)
        except onboard_apply.ApplyRefused as exc:
            refused_payload = {"error": "refused", "code": exc.code, "detail": exc.detail}
            if exc.code == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE:
                refused_payload["remediation"] = onboard_apply.PROTECTION_FLOOR_REMEDIATION
                refused_payload["enforcement"] = {
                    "state": "unenforceable",
                    "code": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
                }
            return _emit(
                args,
                1,
                [f"{_BRAND} · onboard apply REFUSED ({exc.code}): {exc.detail}"],
                refused_payload,
            )
        except onboard_apply.ApplyFailed as exc:
            return _emit(
                args,
                1,
                [f"{_BRAND} · onboard apply FAILED ({exc.code}): {exc.detail}"],
                {"error": "failed", "code": exc.code, "detail": exc.detail},
            )
        finally:
            # ce-ops#88 — revoke the live-forge read token the instant the legs finish
            # (success OR refuse/fail); a no-op for the base/Fake driver.
            _close_apply_driver(live_candidate)
        first_project_after_apply = v3_installer.build_greenfield_first_project_plan(
            schema,
            merged,
            (),
            e2_apply_result=summary,
            e2_apply_result_ref=str(Path(args.root) / "onboard" / "ledger.ndjson"),
        )
        if first_project_after_apply is not None:
            summary["first_project"] = first_project_after_apply
        outcome_code = 0 if summary["refused"] == 0 and summary["failed"] == 0 else 1
        lines = [
            f"{_BRAND} · onboard apply ({summary['mode']}) — "
            f"{summary['verified_count']}/{summary['legs_total']} legs verified",
            f"    repo · {summary['target_repo']} · created {summary['greenfield_repos_created']} "
            f"· already {summary['repos_already_satisfied']} · brownfield deferred {summary['brownfield_deferred']}",
            f"    outcomes · applied {summary['applied']} · already {summary['already_satisfied']} "
            f"· refused {summary['refused']} · failed {summary['failed']} · skipped {summary['skipped']}",
        ]
        if summary.get("brownfield_adopted"):
            pr = summary.get("brownfield_adoption_pr") or {}
            lines.append(
                f"    adoption · join PR #{pr.get('pr_number')} on {pr.get('repo')} "
                f"({pr.get('branch')} → {pr.get('base')}) · scrub findings "
                f"{summary.get('brownfield_scrub_findings', 0)} "
                f"(waived {summary.get('brownfield_scrub_findings_waived', 0)})"
            )
        if summary["manual_rollback_required"]:
            lines.append(
                f"    rollback · {summary['manual_rollback_required']} leg(s) require manual verification/cleanup"
            )
        if outcome_code:
            terminal = next(
                (leg for leg in summary["legs"] if leg["status"] in {"refused", "failed"}),
                None,
            )
            if terminal:
                lines.append(
                    f"{_BRAND} · stopped at {terminal['id']}: "
                    f"{terminal.get('detail') or terminal['action']}"
                )
        return _emit(args, outcome_code, lines, summary)
    # 8. --plan: compose the decomposed GitHub leg (pure planners; the CLI-level
    #    probe carries only what it can read today — unprobed = fail-closed).
    github_leg = None
    if args.show_plan and answers.get("github"):
        github_probe = {
            "origin_remote": (brownfield_probe.get("github") or {}).get("origin_remote"),
            "workflow_present": (brownfield_probe.get("ci") or {}).get("workflow_present"),
        }
        github_leg = v3_installer.build_github_leg_plan(answers, schema=schema, probe=github_probe)
    lines = [
        f"{_BRAND} · onboard (dry-run · {plan['mode']}) — spec verified against pinned key "
        f"{plan['verified']['key_id']!r}",
        f"    dependencies · install {plan['dependencies']['install'] or '—'} · "
        f"skip {plan['dependencies']['skip']} · sudo {'yes' if plan['dependencies']['needs_sudo'] else 'no'}",
        f"    cost profile · {plan['profile']['mode']} → {plan['profile']['runtime_policy']}",
    ]
    if plan["educate"]:
        lines.append(f"    {_BRAND} opt-out · {plan['educate']}")
    if args.answers:
        source_counts: dict[str, int] = {}
        for entry in merged.resolved.values():
            source_counts[entry.source] = source_counts.get(entry.source, 0) + 1
        lines.append(
            f"    answers · {args.answers} (sha256 {answers_sha}) — sources "
            + " · ".join(f"{source}:{count}" for source, count in sorted(source_counts.items()))
        )
        if dep_plan.needs_sudo:
            lines.append(
                "    sudo grant · covered "
                f"{list(grant_diff.covered) or '—'} · OUTSIDE the grant {list(grant_diff.uncovered) or '—'}"
            )
        for conflict in merged.conflicts:
            lines.append(
                f"    CONFLICT · {conflict.key}: file {conflict.file_value!r} contradicts "
                f"detected {conflict.detected_value!r} — resolve interactively"
            )
        if missing:
            lines.append(
                "    remaining asks · "
                + "; ".join(f"step {m.step}: {m.key} ({m.reason})" for m in missing)
            )
        else:
            lines.append(f"    remaining asks · none — apply-ready (run `{CE_CMD} onboard --apply`)")
    if first_project_plan is not None:
        lines.append(
            f"    first project · greenfield · scaffold {first_project_plan['scaffold_input']['kind']} "
            f"→ E2 {first_project_plan['scaffold_input']['supplied_to_e2_leg']} · "
            f"first ship counted {str(not first_project_plan['first_ship_not_yet_counted']).lower()}"
        )
    plain_join_plan = None
    if merged.value("github.mode") == "existing" and brownfield_plan["enabled"]:
        # ce-ops#85 --plan/--apply PARITY: surface the plain-join route so --plan
        # never implies brownfield apply_steps will run for an already-CE repo.
        # Detection needs live forge reads, which the dry-run driver lacks — so the
        # already-CE verdict is HONESTLY deferred to apply, where the live driver
        # verifies the workflow digest + protection floor before converging.
        # ce-ops#88 — same fail-closed live-forge seam as the apply path (default OFF →
        # the base dry-run driver, so --plan stays honest); revoke after the read-only probe.
        _plan_driver = _select_onboard_apply_driver(
            merged=merged, policy_sha=_install_spec_digest, adoption=False
        )
        try:
            plan_repo = str(merged.value("github.repo") or "")
            plan_branch = str(merged.value("github.new_repo.default_branch", "main") or "main")
            already_ce = onboard_apply.repo_is_already_ce_governed(
                _plan_driver,
                repo=plan_repo,
                branch=plan_branch,
                schema=schema,
            )
            ce_probe = getattr(_plan_driver, "last_ce_governance_probe", None)
        finally:
            _close_apply_driver(_plan_driver)
        enforcement = _protection_enforcement_from_ce_probe(
            ce_probe if isinstance(ce_probe, Mapping) else None
        )
        if github_leg is not None and enforcement.get("state") != "unprobed":
            github_leg["branch_protection"] = dict(github_leg["branch_protection"])
            github_leg["branch_protection"]["enforcement"] = enforcement
        plain_join_plan = {
            "route": "plain-join" if already_ce else "brownfield-e3-deferred",
            "already_ce_detected": already_ce,
            "detection": "verified" if already_ce else "deferred_to_apply_live_forge_read",
            "enforcement": enforcement,
        }
        if enforcement.get("state") == "unenforceable":
            refusal = _protection_floor_refusal_payload(
                repo=plan_repo,
                branch=plan_branch,
                probe=ce_probe if isinstance(ce_probe, Mapping) else None,
            )
            refusal.update({
                "github_leg": github_leg,
                "plain_join": plain_join_plan,
            })
            return _emit(
                args,
                1,
                [
                    f"{_BRAND} · onboard plan REFUSED "
                    f"({onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE}): "
                    f"{refusal['detail']}"
                ],
                refusal,
            )
    if github_leg is not None:
        click = "click required (first run)" if github_leg["app"]["click_required"] \
            else f"click skipped (installation {github_leg['app']['installation_id']} detected/declared)"
        enforcement_state = (
            github_leg.get("branch_protection", {}).get("enforcement", {}).get("state", "unprobed")
        )
        lines.append(
            f"    github leg · repo {github_leg['repo']['action']} · App {click} · "
            f"protection drift {len(github_leg['branch_protection']['drift'])} · "
            f"enforcement {enforcement_state} · "
            f"{'converged' if github_leg['converged'] else 'NOT converged (live probes deferred to onboard apply)'}"
        )
    if args.show_plan:
        counters = brownfield_plan["counters"]
        lines.append(
            f"    brownfield · {brownfield_plan['classification']} · "
            f"inventory {brownfield_plan['inventory_sha256'][:12]} · "
            f"workflows {counters['ci_workflows_observed']} · "
            f"tests {counters['test_commands_detected']} · "
            f"E2 steps {counters['apply_steps_planned']}"
        )
        if plain_join_plan is not None:
            lines.append(
                f"    plain-join · route {plain_join_plan['route']} · "
                f"already-CE {plain_join_plan['detection']} · "
                f"protection enforcement {plain_join_plan['enforcement']['state']}"
            )
    lines += [
        f"    expose CLI · `{plan['expose_cli']['command']}` (via {plan['expose_cli']['via']})",
        f"{_BRAND} · you approve only: {', '.join(plan['human_approves'])}",
        f"{_BRAND} · apply handles: {'; '.join(plan['deferred_live_seams'])}",
    ]
    if self_attested:
        # honesty: with no published --sig-value the content floor only self-attests
        # integrity (not authenticity). The real check needs the published signature
        # value + the asymmetric verifier — pass --sig-value before a live drive.
        lines.append(
            f"{_BRAND} · NOTE: no --sig-value given — verification is self-attested integrity "
            "only (NOT authenticity); pass the published signature value before a live install."
        )
    payload = {
        "action": "onboard", "self_attested": self_attested, **plan,
        "answers": ({
            "path": args.answers, "sha256": answers_sha,
            "sources": {k: e.source for k, e in sorted(merged.resolved.items())},
            "conflicts": [{"key": c.key, "file": c.file_value, "detected": c.detected_value}
                          for c in merged.conflicts],
            "missing": [{"key": m.key, "step": m.step, "reason": m.reason} for m in missing],
            "sudo_grant": {"grant": list(grant_diff.grant), "covered": list(grant_diff.covered),
                           "uncovered": list(grant_diff.uncovered)},
        } if args.answers else None),
        "github_leg": github_leg,
        "first_project": first_project_plan,
        "brownfield_adoption": brownfield_plan if args.show_plan else None,
        "plain_join": plain_join_plan,
        "non_interactive": bool(args.non_interactive),
    }
    return _emit(args, 0, lines, payload)


def _cmd_cockpit(args: argparse.Namespace) -> int:
    """The Cockpit (v3.5-B.1): the governed fleet board, read-only.

    Principle-6 routing: the L2 snapshot fold (``runner.cockpit_readmodel``) is
    textual-free and ``--json`` dumps it directly — the future-GUI seam as a
    first-class invocation. ONLY the TUI path lazy-imports ``v3_cockpit`` (and
    thereby ``textual``); non-cockpit subcommands and ``--json`` never do.
    ``CE_DEMO=1`` swaps the data source for the seeded demo fleet (with the
    persistent watermark); live mode reads the v3 state root plus the
    launch-pinned ``CE_LEDGER_ROOT`` / ``CE_HOOK_OBSERVATIONS_DIR`` seams.

    ``--serve`` (v3.5-B.6) opens the SAME app in a browser on demand:
    loopback-only bind + token gate + Host validation, enforced by the pure
    serve config in ``v3_cockpit``; the serve deps load ONLY on this path. A
    non-loopback ``--host`` is refused loudly before any socket exists.
    """
    if getattr(args, "serve", False):
        import shlex
        import sys

        from . import v3_cockpit  # LAZY: the serve path is a cockpit path

        command = (
            f"{shlex.quote(sys.executable)} -m creator_engine_validator.v3_cli "
            f"cockpit --root {shlex.quote(str(args.root))}"
        )
        try:
            config = v3_cockpit.build_serve_config(
                command=command,
                token=v3_cockpit.generate_token(),
                host=args.host,
                port=args.port,
            )
        except ValueError as exc:
            print(f"{CE_CMD} cockpit --serve: {exc}", file=sys.stderr)
            return 2
        return v3_cockpit.run_serve(config)

    from .runner import cockpit_readmodel as _readmodel  # L2 — textual-free

    # ce-ops#25: resolve the CE version token ONCE here (Open-Q1) and pass it as
    # DATA into demo + live snapshot construction — the L2 fold and the watch
    # loop never run git. Demo and live therefore expose the SAME token.
    ce_ver = version.ce_version()
    demo = os.environ.get(_readmodel.DEMO_ENV) == "1"
    root = Path(args.root)
    if demo:
        from .runner import cockpit_demo_seed as _seed

        def _load() -> dict[str, Any]:
            return _readmodel.fold_snapshot(demo=True, ce_version=ce_ver, **_seed.seed())

        watch: list[str] = []
    else:

        def _load() -> dict[str, Any]:
            return _readmodel.snapshot_from_roots(root, ce_version=ce_ver)

        watch = _readmodel.watch_paths(root)
    snapshot = _load()
    if getattr(args, "json_output", False):
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0
    from . import v3_cockpit  # LAZY: textual loads ONLY on the TUI path

    return v3_cockpit.run_app(snapshot, reload=_load, watch_paths=watch)


def _cmd_guide(args: argparse.Namespace) -> int:
    """Print the in-product guide (the seed of ``docs/guide/understanding-ce.md``)."""
    if getattr(args, "json_output", False):
        print(json.dumps({"ok": True, "action": "guide", "guide": _GUIDE}, indent=2))
    else:
        print(_GUIDE)
    return 0


def _which(tool: str) -> bool:
    """Read-only presence probe (the FIX is deferred). ``python`` ≈ python3."""
    if tool == "python":
        return bool(shutil.which("python") or shutil.which("python3"))
    return bool(shutil.which(tool))


def _ssh_keygen_verify_runner(
    *,
    message: bytes,
    signature: bytes,
    allowed_signers: str,
    identity: str,
    namespace: str,
) -> bool:
    """Verify an OpenSSH SSHSIG with stock ``ssh-keygen``."""
    if not shutil.which("ssh-keygen"):
        return False
    with tempfile.TemporaryDirectory(prefix="ce-sshsig-") as tmp:
        root = Path(tmp)
        allowed_path = root / "allowed_signers"
        sig_path = root / "spec.sig"
        allowed_path.write_text(allowed_signers + "\n", encoding="utf-8")
        sig_path.write_bytes(signature)
        proc = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(allowed_path),
                "-I",
                identity,
                "-n",
                namespace,
                "-s",
                str(sig_path),
            ],
            input=message,
            check=False,
            capture_output=True,
            timeout=20,
        )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Parser + entry point
# ---------------------------------------------------------------------------
def _add_root(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--root", default=V3_LOCAL_STATE_ROOT,
        help=f"v3 local-state root (default: {V3_LOCAL_STATE_ROOT})",
    )
    p.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=CE_CMD,
        description="Creator Engine v3 — file, ratify, and drive work as a governed Scope "
        "(Frame → Shape → Build → Review → Ship).",
    )
    # ce-ops#25: top-level ``cev3 --version`` prints the derived CE token and
    # exits BEFORE the default ``session`` dispatch (the action exits in
    # parse_args, ahead of ``args.command`` resolution in ``main``).
    version.add_version_flag(parser)
    sub = parser.add_subparsers(dest="command")
    seats_status.add_parser(sub, default_root=V3_LOCAL_STATE_ROOT)
    fleet_status.add_parser(sub, default_root=V3_LOCAL_STATE_ROOT)

    p_scope = sub.add_parser("scope", help="file a Scope (Goal/Done-when/Budget/Change-type)")
    p_scope.add_argument("scope_id", metavar="ID", help="stable Scope slug")
    p_scope.add_argument("--goal", required=True, help="Goal (the intent / framed problem)")
    p_scope.add_argument("--done-when", action="append", default=[], metavar="CRITERION",
                         help="a Done-when acceptance criterion (repeatable)")
    p_scope.add_argument("--budget", type=float, default=None, help="Budget amount (a fixed cap, not an estimate)")
    p_scope.add_argument("--budget-unit", choices=["$", "%"], default="$",
                         help="Budget unit: $ = API-USD, %% = single-seat meter")
    p_scope.add_argument("--budget-window", choices=["per_run", "rolling_5h", "rolling_weekly", "total"],
                         default=None, help="optional Budget accounting window")
    p_scope.add_argument("--change-type", required=True, choices=sorted(coordination.MUTATION_CLASSES),
                         help="Change-type (the mutation_class risk tier)")
    p_scope.add_argument("--note", default=None, help="optional advisory note (no secrets)")
    _add_root(p_scope)

    p_ratify = sub.add_parser("ratify", help="place the bet on a Ready Scope (human-only front gate)")
    p_ratify.add_argument("scope_id", metavar="ID", help="the Scope to ratify")
    p_ratify.add_argument("--approver-ref", required=True, metavar="HEX64",
                          help="value-free 64-hex opaque ratifier digest (never a raw account)")
    _add_root(p_ratify)

    p_drive = sub.add_parser("drive", help="assemble the governed dispatch (front gate); --spawn launches the seat")
    p_drive.add_argument("scope_id", metavar="ID", help="the Scope to drive")
    p_drive.add_argument("--policy", default=None, help="optional runtime-policy YAML to merge the run envelope into")
    p_drive.add_argument("--spawn", action="store_true",
                         help="materialize the dispatch and spawn a real governed seat (v3.1-G1)")
    p_drive.add_argument("--harness", default="claude",
                         choices=sorted(v3_seat_bridge.HARNESS_BRIDGES),
                         help="seat harness ('claude' default; 'codex' is explicit and risk-guarded)")
    p_drive.add_argument("--codex-risk-override", default=None, dest="codex_risk_override",
                         metavar="HEX64",
                         help="value-free ratification digest accepting the weaker Codex in-band "
                              "boundary for a high-risk Scope")
    p_drive.add_argument("--no-unattended", action="store_true",
                         help="opt the spawned seat back into interactive approval modals")
    p_drive.add_argument("--ticket", default=None,
                         help="ce-ops#38 work item (owner/name#N / issue URL); when given with "
                              "--spawn the claim lock is acquired+verified before any dispatch "
                              "side effect (a foreign active claim refuses the spawn)")
    _add_root(p_drive)

    p_dispatch = sub.add_parser("dispatch", help="dispatch governed work to an execution venue")
    dispatch_sub = p_dispatch.add_subparsers(dest="dispatch_command", required=True)
    p_dispatch_worktree = dispatch_sub.add_parser(
        "worktree",
        help="create a governed dispatch worktree for a claimed work item",
    )
    p_dispatch_worktree.add_argument("--repo-root", required=True, dest="repo_root",
                                     help="source repository root")
    p_dispatch_worktree.add_argument("--ledger-root", required=True, dest="ledger_root",
                                     help="Active-Work ledger root")
    p_dispatch_worktree.add_argument("--worktree-root", required=True, dest="worktree_root",
                                     help="root directory where dispatch worktrees are created")
    p_dispatch_worktree.add_argument("--work-key", required=True, dest="work_key",
                                     help="work item key, e.g. owner/repo#N")
    p_dispatch_worktree.add_argument("--branch", required=True,
                                     help="branch name for the dispatched worktree")
    p_dispatch_worktree.add_argument("--brief", required=True,
                                     help="path to an existing worker brief file")
    p_dispatch_worktree.add_argument("--controller-id", required=True, dest="controller_id",
                                     help="controller id recorded on the dispatch")
    p_dispatch_worktree.add_argument("--harness-cmd", default=None, dest="harness_cmd",
                                     help="shell-style worker harness argv "
                                          "(default: codex exec <brief-path>)")

    p_collect = sub.add_parser("collect", help="fold a finished seat run's transcript + outcome into evidence")
    p_collect.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_collect.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID", help="the dispatched run id")
    p_collect.add_argument("--transcript", default=None,
                           help="OPTIONAL override path to the seat harness .jsonl transcript. Normally "
                                "OMIT it: collect resolves the transcript by the harness session id "
                                "stamped at spawn (D6/F9). When given, it is folded ONLY if its stem "
                                "matches the stamped id — else refused (the #14/#21 mis-fold, blocked)")
    p_collect.add_argument("--transcript-override", default=None, dest="transcript_override",
                           help="SALVAGE hatch: fold this transcript despite no/mismatched stamped id "
                                "(e.g. a crashed/relocated harness transcript). Loudly honesty-stamped "
                                "transcript_source: operator_override")
    p_collect.add_argument("--claude-config-dir", default=None, dest="claude_config_dir",
                           help="override the harness config dir for stamped-id transcript resolution "
                                "(default: $CLAUDE_CONFIG_DIR or ~/.claude)")
    p_collect.add_argument("--outcome", default=None, choices=list(v3_seat_bridge.OUTCOME_VOCABULARY),
                           help="the conserved terminal outcome (defaults to pr_opened when the "
                                "dispatch carries a forge-stamped change block; otherwise required)")
    p_collect.add_argument("--pr", type=int, default=None, help="PR number (if the run opened one)")
    p_collect.add_argument("--branch", default=None, help="value-free change branch ref (default: run id / change block)")
    p_collect.add_argument("--base", default=None, help="value-free change base ref (default: main / change block)")
    p_collect.add_argument("--head-sha", default=None, dest="head_sha",
                           help="value-free change head sha (default: run id)")
    p_collect.add_argument("--manifest-path", action="append", default=None, dest="manifest_paths",
                           help="value-free change manifest path (repeatable)")
    _add_root(p_collect)

    p_pr = sub.add_parser(
        "pr", help="push the seat's authored branch + open its PR through the v3 forge "
                   "(plan-by-default; --apply pushes + opens)")
    p_pr.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_pr.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID", help="the dispatched run id")
    p_pr.add_argument("--branch", required=True, help="the seat's authored head branch to push + open")
    p_pr.add_argument("--manifest-path", action="append", required=True, dest="manifest_paths",
                      metavar="PATH", help="an authorized change manifest path (repeatable, required)")
    p_pr.add_argument("--base", default="main", help="the PR base branch (default: main)")
    p_pr.add_argument(
        "--app-config", required=True, dest="app_config",
        help="REQUIRED path to the host GitHub-App config JSON — NO default (host filenames "
             "differ: laptop ~/.ce-keys/ce-forge-app.json, CE-DEV-1 ~/.ce-keys/ce-forge-dev1.json; "
             "a default would silently miss on one host)",
    )
    p_pr.add_argument("--source-dir", default=".", dest="source_dir",
                      help="local checkout holding the authored branch (default: cwd)")
    p_pr.add_argument("--apply", action="store_true",
                      help="push + open the PR for real (default: plan-only — mutates nothing)")
    _add_root(p_pr)

    p_review = sub.add_parser(
        "review", help="dispatch a distinct CE-governed reviewer venue for a run's opened PR "
                       "(assemble-only; --spawn launches the venue)")
    p_review.add_argument("scope_id", metavar="ID", help="the Scope the author run delivered")
    p_review.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID",
                          help="the AUTHOR run id whose opened PR is reviewed")
    p_review.add_argument("--reviewer-actor", required=True, dest="reviewer_actor",
                          help="the host-bound reviewer LOGIN (DATA — a login, never a token; e.g. "
                               "ubuntuaws745-cmyk on the laptop, cedev1vps-cmd on CE-DEV-1)")
    p_review.add_argument("--spawn", action="store_true",
                          help="provision + launch the governed reviewer venue (default: assemble-only)")
    p_review.add_argument("--venue-root", default=None, dest="venue_root",
                          help="out-of-repo zone the venue worktree is provisioned under "
                               "(required with --spawn; execution-zones directive)")
    p_review.add_argument("--ledger-root", default=None, dest="ledger_root",
                          help="Active-Work ledger root for the venue claim (required with --spawn)")
    p_review.add_argument("--controller-id", default="cev3-review", dest="controller_id",
                          help="controller id for the venue lane (default: cev3-review)")
    p_review.add_argument("--no-unattended", action="store_true", dest="no_unattended",
                          help="opt the reviewer venue back into interactive approval modals "
                               "(default: unattended, mirroring the author seat — D1/F3)")
    p_review.add_argument("--seat-env-file", default=None, dest="seat_env_file",
                          help="path to an owner-only (0600-class) env file sourced into the "
                               "venue claude (the reviewer credential contract — D2/F4); the file "
                               "PATH transits argv, the secret VALUE never does")
    p_review.add_argument("--harness", default="claude", choices=["claude", "codex"],
                          help="reviewer venue harness (codex is deferred and refused in G1-codex)")
    p_review.add_argument("--ticket", default=None,
                          help="ce-ops#38 work item (owner/name#N / issue URL); when given with "
                               "--spawn the claim lock is acquired+verified before any venue "
                               "side effect (a foreign active claim refuses the spawn)")
    _add_root(p_review)

    p_merge = sub.add_parser(
        "merge", help="gate-read (or apply) a squash-merge of a run's opened PR "
                      "(plan-by-default; --apply is the Operator's gated act)")
    p_merge.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_merge.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID",
                         help="the run whose collected chain carries the opened PR")
    p_merge.add_argument("--apply", action="store_true",
                         help="perform the gated squash-merge (default: plan-only — read the gate)")
    _add_root(p_merge)

    p_playbook = sub.add_parser(
        "playbook",
        help="discover, inspect, and run governed CE playbooks",
    )
    playbook_sub = p_playbook.add_subparsers(dest="playbook_cmd")
    p_playbook_list = playbook_sub.add_parser("list", help="list governed CE playbooks")
    p_playbook_list.add_argument(
        "--playbooks-root",
        "--root",
        dest="playbooks_root",
        default=".",
        help="root to search for PLAYBOOK.md files (default: cwd)",
    )
    p_playbook_list.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    p_playbook_show = playbook_sub.add_parser("show", help="show a public playbook and projected descriptor")
    p_playbook_show.add_argument("ref", help="playbook id, directory, or PLAYBOOK.md path")
    p_playbook_show.add_argument(
        "--playbooks-root",
        "--root",
        dest="playbooks_root",
        default=".",
        help="root used to resolve playbook ids (default: cwd)",
    )
    p_playbook_show.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    p_playbook_run = playbook_sub.add_parser("run", help="run a governed CE playbook")
    p_playbook_run.add_argument("ref", help="playbook id, directory, or PLAYBOOK.md path")
    p_playbook_run.add_argument(
        "--playbooks-root",
        "--root",
        dest="playbooks_root",
        default=".",
        help="root used to resolve playbook ids (default: cwd)",
    )
    p_playbook_run.add_argument("--dry-run", action="store_true", help="print the governed run plan without side effects")
    p_playbook_run.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_configure_repo = sub.add_parser(
        "configure-repo",
        help="plan/apply GitHub repo branch-protection or repo auto-merge setting "
             "(scoped administration:write token)",
    )
    p_configure_repo.add_argument(
        "--app-config", required=True, dest="app_config",
        help="REQUIRED path to the host GitHub-App config JSON — no default",
    )
    p_configure_repo.add_argument("--branch", default="main", help="branch to protect (default: main)")
    setting_group = p_configure_repo.add_mutually_exclusive_group()
    setting_group.add_argument(
        "--allow-auto-merge", action="store_true", dest="allow_auto_merge",
        help="toggle the repository-level allow_auto_merge setting instead of branch protection",
    )
    setting_group.add_argument(
        "--squash-only", action="store_true", dest="squash_only",
        help="toggle repository merge methods to squash-only instead of branch protection",
    )
    p_configure_repo.add_argument("--apply", action="store_true",
                                  help="apply the repo configuration (default: plan-only)")
    _add_root(p_configure_repo)

    p_ruleset = sub.add_parser(
        "ruleset",
        help="plan/apply a repo ruleset with pull_request bypass actor "
             "(scoped administration:write token)",
    )
    p_ruleset.add_argument("--app-config", required=True, dest="app_config",
                           help="REQUIRED path to the host GitHub-App config JSON — no default")
    p_ruleset.add_argument("--name", default="ce-p1-devops", help="repo ruleset name")
    p_ruleset.add_argument("--branch", default="main", help="protected branch (default: main)")
    p_ruleset.add_argument("--required-approvals", type=int, default=1, dest="required_approvals",
                           help="required approving review count (default: 1)")
    p_ruleset.add_argument("--bypass-integration-id", type=int, default=4070181,
                           dest="bypass_integration_id",
                           help="GitHub App integration id for pull_request bypass")
    p_ruleset.add_argument("--delete", action="store_true", help="delete the named repo ruleset")
    p_ruleset.add_argument("--apply", action="store_true",
                           help="apply the ruleset change (default: plan-only)")
    _add_root(p_ruleset)

    p_review_submit = sub.add_parser(
        "review-submit",
        help="submit the separate reviewer App's APPROVE for a run's opened PR "
             "(scoped pull_requests:write token)",
    )
    p_review_submit.add_argument("scope_id", metavar="ID", help="the Scope the author run delivered")
    p_review_submit.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID",
                                 help="the AUTHOR run id whose opened PR is approved")
    p_review_submit.add_argument("--reviewer-app-config", required=True, dest="reviewer_app_config",
                                 help="REQUIRED path to the separate reviewer App config JSON")
    p_review_submit.add_argument("--body", default="", help="optional review body")
    p_review_submit.add_argument("--apply", action="store_true",
                                 help="submit the review (default: plan-only)")
    _add_root(p_review_submit)

    p_auto_merge = sub.add_parser(
        "auto-merge",
        help="plan/apply GraphQL per-PR auto-merge for a run's opened PR "
             "(scoped contents:write + pull_requests:write token)",
    )
    p_auto_merge.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_auto_merge.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID",
                              help="the run whose dispatch carries the opened PR")
    p_auto_merge.add_argument("--app-config", required=True, dest="app_config",
                              help="REQUIRED path to the host GitHub-App config JSON — no default")
    p_auto_merge.add_argument("--method", default="squash", choices=["merge", "squash", "rebase"],
                              help="auto-merge method (default: squash)")
    p_auto_merge.add_argument("--enable-repo-setting", action="store_true",
                              help="also plan/apply the repo-level allow_auto_merge toggle")
    p_auto_merge.add_argument("--apply", action="store_true",
                              help="enable auto-merge (default: plan-only)")
    _add_root(p_auto_merge)

    from .forge import review_pickup as review_pickup_module

    p_review_pickup = sub.add_parser(
        "review-pickup",
        help="controller review-pickup: route awaiting-review PRs to distinct non-author seats (ce-ops#188)",
    )
    p_review_pickup.add_argument("--identity", required=True,
                                 help="controller identity used to resolve the pickup token")
    p_review_pickup.add_argument("--keys-dir", default=None, dest="keys_dir",
                                 help="PAT directory (default: ~/.ce-keys)")
    p_review_pickup.add_argument("--allow-ambient-gh", action="store_true", dest="allow_ambient_gh",
                                 help="allow fallback to ambient gh auth token after CE_PICKUP_TOKEN and PAT file")
    # Scope is REQUIRED: with --apply, an unscoped review-pickup would request
    # reviewers and auto-dismiss stale reviews across the first page of EVERY open
    # PR the controller token can see. Fail closed if unscoped (ce-ops#188 review,
    # same fail-closed class as the ce-ops#218 queue-poll belt).
    rp_scope = p_review_pickup.add_mutually_exclusive_group(required=True)
    rp_scope.add_argument("--repo", default=None,
                          help="restrict Search API queries and reviewer routing to one owner/name repo")
    rp_scope.add_argument("--org", default=None,
                          help="restrict Search API queries to one GitHub org/user slug")
    p_review_pickup.add_argument("--seat", action="append", default=[], dest="reviewer_seats",
                                 help="repeatable reviewer seat/login; comma-separated allowed")
    p_review_pickup.add_argument("--apply", action="store_true",
                                 help="request selected reviewers and auto-dismiss objectively stale reviews")
    rp_mode = p_review_pickup.add_mutually_exclusive_group(required=False)
    rp_mode.add_argument("--once", action="store_true",
                         help="run one review-pickup pass (default when no mode is supplied)")
    rp_mode.add_argument("--loop", action="store_true",
                         help="run continuously until interrupted")
    p_review_pickup.add_argument("--interval", type=float,
                                 default=None,
                                 help="seconds between --loop passes (must be > 0)")
    p_review_pickup.add_argument("--dry-run", action="store_true", dest="dry_run",
                                 help="log planned routing decisions without requesting reviewers")
    p_review_pickup.add_argument("--no-stale-apply", action="store_true", dest="no_stale_apply",
                                 help="with --apply, do not auto-dismiss stale superseded reviews")
    p_review_pickup.add_argument(
        "--inbox-path",
        default=str(review_pickup_module.DEFAULT_AWAITING_REVIEW_INBOX_PATH),
        dest="inbox_path",
        help="durable awaiting-review inbox path "
             f"(default: {review_pickup_module.DEFAULT_AWAITING_REVIEW_INBOX_PATH})",
    )
    p_review_pickup.add_argument("--json", action="store_true", dest="json_output",
                                 help="emit machine-readable JSON")

    p_escalation = sub.add_parser(
        "escalation",
        help="manage local AWAITING-OPERATOR escalation records",
    )
    escalation_sub = p_escalation.add_subparsers(dest="escalation_command", required=True)

    p_escalation_open = escalation_sub.add_parser(
        "open",
        help="write a local AWAITING-OPERATOR escalation record",
    )
    p_escalation_open.add_argument("--id", required=True, dest="escalation_id", help="escalation slug or digest")
    p_escalation_open.add_argument("--title", required=True, help="short escalation title")
    p_escalation_open.add_argument("--decision", required=True, help="decision the Operator must make")
    p_escalation_open.add_argument("--recommend", required=True, help="recommended option")
    p_escalation_open.add_argument("--source-ref", default=None, help="optional value-free source marker")
    _add_root(p_escalation_open)

    p_escalation_resolve = escalation_sub.add_parser(
        "resolve",
        help="stamp a local escalation resolved",
    )
    p_escalation_resolve.add_argument("escalation_id", metavar="ID", help="escalation slug or digest")
    p_escalation_resolve.add_argument("--resolution", default=None, help="optional value-free resolution summary")
    _add_root(p_escalation_resolve)

    p_escalation_sync = escalation_sub.add_parser(
        "sync",
        help="mirror awaiting-operator issues from gh into local escalation records",
    )
    p_escalation_sync.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    p_escalation_sync.add_argument("--label", default="awaiting-operator", help="issue label to mirror")
    _add_root(p_escalation_sync)

    p_notify = sub.add_parser(
        "notify",
        help="Operator-notify feed — alert on AWAITING-OPERATOR entry/exit "
             "(once | watch | status; pluggable desktop/exec sinks)",
    )
    notify_sub = p_notify.add_subparsers(dest="notify_command", required=True)

    p_notify_once = notify_sub.add_parser(
        "once",
        help="a single fold→dispatch→record pass (the cron-able / testable primitive)",
    )
    p_notify_once.add_argument("--sync-repo", default=None, dest="sync_repo",
                               help="optional GitHub repo (owner/name) to mirror forge "
                                    "awaiting-operator issues from BEFORE the fold (cross-host fan-in)")
    p_notify_once.add_argument("--sync-label", default="awaiting-operator", dest="sync_label",
                               help="issue label to mirror (default: awaiting-operator)")
    _add_root(p_notify_once)

    p_notify_watch = notify_sub.add_parser(
        "watch",
        help="poll loop: (optional sync) → fold → dispatch → record → sleep",
    )
    p_notify_watch.add_argument("--interval", type=int, default=30,
                                help="poll interval in seconds (default: 30)")
    p_notify_watch.add_argument("--sync-repo", default=None, dest="sync_repo",
                                help="optional GitHub repo (owner/name) for cross-host fan-in each tick")
    p_notify_watch.add_argument("--sync-label", default="awaiting-operator", dest="sync_label",
                                help="issue label to mirror (default: awaiting-operator)")
    _add_root(p_notify_watch)

    p_notify_status = notify_sub.add_parser(
        "status",
        help="pure-fold counts (open / pending / delivered / failed) — no dispatch",
    )
    _add_root(p_notify_status)

    p_reap = sub.add_parser(
        "reap",
        help="seat/venue retirement reaper — archive→pane-kill→pco-release on terminal "
             "sentinel events; fail-closed on unclean/stale/unknown (once | watch | status)",
    )
    reap_sub = p_reap.add_subparsers(dest="reap_command", required=True)

    def _add_reap_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo-root", default=None, dest="repo_root",
                       help="secondary-worktree repo root the reaper runs from (defaults to cwd)")
        p.add_argument("--ledger-root", default=None, dest="ledger_root",
                       help="path to the active-work-ledger root (or set CE_LEDGER_ROOT); "
                            "absent ⇒ the worktree-release step is skipped (not applicable)")
        p.add_argument("--archive-root", default=None, dest="archive_root",
                       help="ignored transcript-archive root for `ce lane archive` "
                            "(or set CE_TRANSCRIPT_ARCHIVE_ROOT)")
        p.add_argument("--grace-seconds", type=int, default=seat_reaper.DEFAULT_GRACE_SECONDS,
                       dest="grace_seconds",
                       help=f"a clean-exited seat whose outcome stays unresolvable past this window "
                            f"escalates (default: {seat_reaper.DEFAULT_GRACE_SECONDS})")
        p.add_argument("--stale-seconds", type=int, default=seat_reaper.DEFAULT_STALE_SECONDS,
                       dest="stale_seconds",
                       help=f"a launched-no-exited seat with no new event past this window is a stale "
                            f"dangling launched → escalation (default: {seat_reaper.DEFAULT_STALE_SECONDS})")
        p.add_argument("--claude-config-dir", default=None, dest="claude_config_dir",
                       help="harness config dir for stamped-id transcript lookup "
                            "(default: $CLAUDE_CONFIG_DIR or ~/.claude)")
        _add_root(p)

    p_reap_once = reap_sub.add_parser(
        "once", help="one fold + one bounded action pass (the cron-able / testable primitive)",
    )
    _add_reap_args(p_reap_once)

    p_reap_watch = reap_sub.add_parser(
        "watch", help="repeat `once` at an interval; SIGINT/SIGTERM stop cleanly after the current pass",
    )
    p_reap_watch.add_argument("--interval", type=int, default=60,
                              help="poll interval in seconds (default: 60)")
    _add_reap_args(p_reap_watch)

    p_reap_status = reap_sub.add_parser(
        "status", help="pure-fold classification + counts — writes nothing (no archive/kill/release)",
    )
    _add_reap_args(p_reap_status)

    p_status = sub.add_parser("status", help="list Scopes by projected stage")
    _add_root(p_status)

    p_show = sub.add_parser("show", help="show one Scope (canon labels + projection)")
    p_show.add_argument("scope_id", metavar="ID", help="the Scope to show")
    _add_root(p_show)

    p_art = sub.add_parser("artifacts", help="enumerate a Scope's (and a run's) artifacts")
    p_art.add_argument("scope_id", metavar="ID", help="the Scope whose artifacts to list")
    p_art.add_argument("--evidence", default=None, help="run evidence chain YAML — also enumerate run artifacts")
    p_art.add_argument("--run-id", default=None, help="run id to fold the evidence for")
    p_art.add_argument("--cap", type=float, default=None, help="run spend cap (to surface the spend artifact)")
    _add_root(p_art)

    p_report = sub.add_parser("report", help="render the per-run ◆ CE Completion Report")
    p_report.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_report.add_argument("--evidence", default=None, help="run evidence chain YAML (folds Outcome + spend)")
    p_report.add_argument("--run-id", default=None, help="run id")
    p_report.add_argument("--pr", type=int, default=None, help="PR number (if the run opened one)")
    p_report.add_argument("--change-type", default=None, choices=sorted(coordination.MUTATION_CLASSES),
                          help="Change-type (mutation_class) for the Next step")
    p_report.add_argument("--done-when-total", type=int, default=None, help="number of Done-when criteria")
    p_report.add_argument("--done-when-met", type=int, default=None, help="Done-when criteria met")
    p_report.add_argument("--ci", default=None, help="CI status (e.g. green)")
    p_report.add_argument("--in-scope", dest="in_scope", action="store_true", default=None,
                          help="the diff stayed inside the closed manifest (in scope ✓)")
    p_report.add_argument("--out-of-scope", dest="in_scope", action="store_false",
                          help="the diff left the closed manifest")
    p_report.add_argument("--cap", type=float, default=None, help="run spend cap (Budget) to meter spend against")
    p_report.add_argument("--unit", choices=["$", "%"], default="$", help="spend unit")
    p_report.add_argument("--budget-size", default=None, help="appetite size label (e.g. S) for 'of Budget S'")
    p_report.add_argument(
        "--root", default=V3_LOCAL_STATE_ROOT,
        help=f"v3 local-state root (to default --evidence from a collected run; default: {V3_LOCAL_STATE_ROOT})",
    )
    p_report.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_shape = sub.add_parser("shape", help="run the Frame→Shape grill-me on a partial draft (gaps + questions)")
    p_shape.add_argument("scope_id", metavar="ID", help="working Scope slug")
    p_shape.add_argument("--goal", default=None, help="Goal (intent) — agent-draftable")
    p_shape.add_argument("--done-when", action="append", default=[], metavar="CRITERION",
                         help="a Done-when criterion (repeatable) — agent-draftable")
    p_shape.add_argument("--change-type", default=None, choices=sorted(coordination.MUTATION_CLASSES),
                         help="proposed Change-type (mutation_class) — agent proposes; human tightens free")
    p_shape.add_argument("--persona", default=None, choices=["dev", "ceo"],
                         help="persona for the detect-and-offer dial")
    p_shape.add_argument("--signal", default=None, choices=list(v3_shaping.SIGNAL_ORDER),
                         help="detected intent-to-act signal strength (for the dial)")
    p_shape.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_onboard = sub.add_parser(
        "onboard",
        help="two-mode install: verify the signed spec, plan, and explicitly apply "
             "(agent loop: --inventory → prepare answers → --plan → --apply)",
    )
    p_onboard.add_argument("--spec", required=True, help="path to the served install spec to verify")
    p_onboard.add_argument("--key-id", default="ce-root-v1", help="the signing key id (must be pinned)")
    p_onboard.add_argument("--sig-value", default=None,
                           help="the published signature value (default: the spec's own content digest)")
    p_onboard.add_argument("--sig-algo", default=None,
                           choices=[v3_installer.CONTENT_ALGO, v3_installer.SSH_ED25519_ALGO],
                           help="signature algorithm (apply requires ssh-ed25519)")
    p_onboard.add_argument("--content-sha256", default=None,
                           help="canonical signed-spec digest when --sig-value is supplied out of band")
    p_onboard.add_argument("--trust-root", default=None,
                           help="OpenSSH allowed_signers trust root; implies authentic SSHSIG verification")
    p_onboard.add_argument("--trust-anchor", action="append", default=[],
                           metavar="SOURCE=PATH",
                           help="out-of-band ce-root fingerprint evidence, e.g. dns-txt=/tmp/ce-root-v1.txt")
    p_onboard.add_argument("--require-authentic", action="store_true",
                           help="refuse sha256 self-attestation; require embedded SSHSIG + --trust-root")
    p_onboard.add_argument("--mode", choices=["one-liner", "agent-native"], default="agent-native",
                           help="install mode")
    p_onboard.add_argument("--answers", default=None,
                           help="path to the ce-install.answers.yaml IaC answers file "
                                "(schema-validated; fail-closed on unknown keys; secrets by SecretRef only)")
    p_onboard.add_argument("--answers-schema", default=v3_installer.ANSWERS_SCHEMA_PATH,
                           help="the answers schema document (the input-inventory source of truth)")
    p_onboard.add_argument("--inventory", action="store_true",
                           help="emit the operator-input inventory (the agent-awareness artifact) and exit")
    p_onboard.add_argument("--plan", action="store_true", dest="show_plan",
                           help="terraform-plan analog: the full plan incl. the exact remaining asks "
                                "+ the decomposed GitHub leg (no execution)")
    p_onboard.add_argument("--apply", action="store_true",
                           help="execute the verified E2 onboard apply drive (side-effecting)")
    p_onboard.add_argument("--non-interactive", action="store_true",
                           help="fail-closed: refuse with the exact missing list instead of ever asking")
    p_onboard.add_argument("--opt-out", action="store_true",
                           help="opt out of spend CAPS (ratified-human-only; detection net stays on)")
    p_onboard.add_argument("--ratified-prompt-sha", default=None, help="64-hex opt-out ratification digest")
    p_onboard.add_argument("--approver-ref", default=None, help="64-hex opt-out approver digest")
    p_onboard.add_argument("--first-scope-id", default=onboard_apply.DEFAULT_FIRST_SCOPE_ID,
                           help="scope id for the first governed smoke Scope")
    p_onboard.add_argument("--spawn-smoke", action="store_true",
                           help="include the optional spawn preflight in the first-project smoke leg")
    p_onboard.add_argument("--lock-timeout", type=float, default=None,
                           help="seconds to wait for another onboard apply lock before refusing")
    p_onboard.add_argument("--root", default=V3_LOCAL_STATE_ROOT,
                           help=f"v3 local-state root for apply ledger/lock (default: {V3_LOCAL_STATE_ROOT})")
    p_onboard.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_carrier = sub.add_parser(
        "carrier",
        help="write, stage, and verify the PR path-manifest carrier files",
    )
    p_carrier.add_argument("--slug", required=True, help="canonical branch/carrier slug")
    p_carrier.add_argument("--issue", required=True, help="issue reference for the carrier")
    p_carrier.add_argument("--title", required=True, help="carrier title")
    p_carrier.add_argument("--kind", required=True, help="declared work kind/class")
    p_carrier.add_argument("--scope", required=True, help="closed scope summary")
    p_carrier.add_argument("--body-file", required=True, dest="body_file", help="path to the PR body/source text")
    p_carrier.add_argument("--base", default="origin/main", help="base ref for path-manifest verification")
    p_carrier.add_argument("--date", default=None, help="carrier date stamp override")
    p_carrier.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_guide = sub.add_parser("guide", help="print the in-product CE guide (what CE is + the five stages)")
    p_guide.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_cockpit = sub.add_parser(
        "cockpit",
        help="the governed fleet Cockpit — read-only board + governance view "
        "(CE_DEMO=1 for the seeded demo; --json dumps the L2 snapshot, textual-free; "
        "--serve opens the same app in a browser: loopback-only, token-gated)",
    )
    _add_root(p_cockpit)
    p_cockpit.add_argument(
        "--serve", action="store_true",
        help="serve the SAME app in a browser on demand (127.0.0.1-only, "
        "token-gated, Host-validated; exits with the command — no daemon)",
    )
    p_cockpit.add_argument(
        "--host", default="127.0.0.1",
        help="serve bind host — loopback ONLY; any non-loopback value is refused",
    )
    p_cockpit.add_argument(
        "--port", type=int, default=8000, help="serve port (default: 8000)",
    )

    p_session = sub.add_parser("session", help="launch the governed session frame + status line")
    p_session.add_argument("--context-pct", type=float, default=None,
                           help="the harness's authoritative context-window %% (consumed, never recomputed)")
    p_session.add_argument("--spine", default=None, help="runtime-evidence chain YAML to fold the G-5 spend projection over")
    p_session.add_argument("--cap", type=float, default=None, help="the run spend cap to meter against")
    p_session.add_argument("--unit", choices=["$", "%"], default="$", help="spend unit ($=API / %%=seat)")
    p_session.add_argument("--run-id", default=None, help="restrict the spend fold to this run_id")
    p_session.add_argument("--mid-output", action="store_true",
                           help="suppress boundary-only nudges (we are mid-output, not at a turn boundary)")
    p_session.add_argument("--repo", default="—", help="repo label for the banner")
    p_session.add_argument("--transport", default="—", help="transport label for the banner")
    p_session.add_argument("--backend", default="—", help="runtime backend label for the banner")
    _add_root(p_session)

    p_queue_poll = sub.add_parser(
        "queue-poll",
        help="run a bounded, witnessable Integrator merge-queue repair poll (ce-ops#218)",
    )
    # Scope is REQUIRED: a live merge-queue belt must never poll/act across every
    # approved+green PR a token can see (ce-ops#218 review). Fail closed if unscoped.
    qp_scope = p_queue_poll.add_mutually_exclusive_group(required=True)
    qp_scope.add_argument("--repo", default=None, help="owner/name repository scope")
    qp_scope.add_argument("--org", default=None, help="org/user search scope")
    p_queue_poll.add_argument("--token-env", default=integrator_belt.DEFAULT_TOKEN_ENV, help="env var containing the GitHub token")
    p_queue_poll.add_argument("--work-root", default=integrator_belt.DEFAULT_WORK_ROOT, help="Integrator scratch work root")
    p_queue_poll.add_argument("--iterations", type=int, default=1, help="bounded poll iterations")
    p_queue_poll.add_argument("--interval-seconds", type=float, default=integrator_belt.DEFAULT_INTERVAL_SECONDS, help="sleep between iterations")
    p_queue_poll.add_argument("--action", choices=("enqueue", "land", "merge"), default="enqueue", help="publish action after a deterministic repair")
    _add_root(p_queue_poll)  # adds --root + --json

    p_queue_daemon = sub.add_parser(
        "queue-daemon",
        help="run the autonomous Integrator merge-queue daemon",
    )
    qd_scope = p_queue_daemon.add_mutually_exclusive_group(required=True)
    qd_scope.add_argument("--repo", default=None, help="owner/name repository scope")
    qd_scope.add_argument("--org", default=None, help="org/user search scope")
    qd_mode = p_queue_daemon.add_mutually_exclusive_group(required=True)
    qd_mode.add_argument("--once", action="store_true", help="run one daemon pass and exit")
    qd_mode.add_argument("--loop", action="store_true", help="run continuously under a supervisor")
    p_queue_daemon.add_argument("--interval", type=float, default=integrator_belt.DEFAULT_INTERVAL_SECONDS, help="sleep between loop passes")
    p_queue_daemon.add_argument("--dry-run", action="store_true", help="log enqueue decisions without running gh pr merge")
    p_queue_daemon.add_argument("--token-env", default=integrator_belt.DEFAULT_TOKEN_ENV, help="env var containing the GitHub token")
    p_queue_daemon.add_argument(
        "--authorized-reviewer",
        action="append",
        default=[],
        dest="authorized_reviewers",
        metavar="LOGIN",
        help="authorized approval reviewer login; repeatable, comma-separated allowed",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-env",
        default=approval_capability.DEFAULT_APPROVAL_CAPABILITY_SECRET_ENV,
        help="bootstrap fallback env var containing the approval capability wall secret",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-backend",
        default=None,
        help="SecretIdentityBackend registry key for the primary approval wall secret supplier (for example: openbao)",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-mount",
        default=None,
        help="SecretRef mount for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-path",
        default=None,
        help="SecretRef path for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-field",
        default=None,
        help="SecretRef field for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-version",
        type=int,
        default=None,
        help="optional SecretRef version for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-purpose",
        default=None,
        help="SecretRef purpose for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-owner-ref",
        default=None,
        help="SecretRef owner reference for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-ref-policy-sha",
        default=None,
        help="64-hex SecretRef policy sha for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-target-ref",
        default=None,
        help="file materialization target ref read after SecretIdentityBackend delivery (file:PATH or absolute path)",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-repo",
        default=None,
        help="owner/name repo binding for the SecretRequest (defaults to --repo when scoped to one repo)",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-run-id",
        default="approval-wall-daemon",
        help="run id for the SecretRequest used to materialize the approval wall secret",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-seat-id",
        default="dev-1",
        help="seat id for the SecretRequest used to materialize the approval wall secret",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-secret-ttl-seconds",
        type=int,
        default=600,
        help="SecretRequest TTL in seconds for the primary approval wall secret supplier",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-marker-ttl-seconds",
        type=int,
        default=3600,
        help="daemon-minted approval marker lifetime in seconds",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-state",
        default=None,
        help="durable approval wall state file (default: <root>/approval-capability-wall/state.json)",
    )
    p_queue_daemon.add_argument(
        "--approval-wall-policy-sha",
        default=None,
        help="optional approval capability policy sha/id required in markers",
    )
    _add_root(p_queue_daemon)  # adds --root + --json

    def _add_emergency_stop_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("pr_number", type=int, metavar="PR", help="pull request number")
        parser.add_argument("--repo", required=True, help="owner/name repository scope")
        parser.add_argument(
            "--token-env",
            default=integrator_belt.DEFAULT_TOKEN_ENV,
            help="env var containing the GitHub token",
        )
        parser.add_argument(
            "--convert-to-draft",
            action="store_true",
            help="also convert the PR back to draft after dequeue",
        )
        _add_root(parser)  # adds --root + --json

    p_emergency_stop = sub.add_parser(
        "emergency-stop",
        help="emergency merge-queue stop: disable GitHub auto-merge for one PR",
    )
    _add_emergency_stop_args(p_emergency_stop)

    p_queue_dequeue = sub.add_parser(
        "queue-dequeue",
        help="alias for emergency-stop; disable GitHub auto-merge for one PR",
    )
    _add_emergency_stop_args(p_queue_dequeue)

    p_approval_capability = sub.add_parser(
        "approval-capability",
        help="controller-only approval capability wall utilities",
    )
    approval_sub = p_approval_capability.add_subparsers(dest="approval_capability_command", required=True)
    p_approval_mint = approval_sub.add_parser(
        "mint",
        help="mint a controller approval capability marker",
    )
    p_approval_mint.add_argument("--repo", required=True, help="owner/name repository")
    p_approval_mint.add_argument("--pr", required=True, type=int, dest="pr_number", help="pull request number")
    p_approval_mint.add_argument("--head-sha", required=True, help="approved head sha")
    p_approval_mint.add_argument("--approved-by", required=True, help="approving GitHub login")
    p_approval_mint.add_argument("--policy-sha", required=True, help="approval policy sha or id")
    p_approval_mint.add_argument("--ttl-seconds", type=int, default=3600, help="marker lifetime in seconds")
    p_approval_mint.add_argument(
        "--approval-wall-secret-env",
        default=approval_capability.DEFAULT_APPROVAL_CAPABILITY_SECRET_ENV,
        help="bootstrap env var containing the approval capability wall secret; production may wrap the SecretIdentityBackend supplier",
    )
    p_approval_mint.add_argument(
        "--approval-wall-state",
        default=None,
        help="durable approval wall state file (default: <root>/approval-capability-wall/state.json)",
    )
    p_approval_mint.add_argument(
        "--root",
        default=V3_LOCAL_STATE_ROOT,
        help=f"v3 local-state root for approval wall state (default: {V3_LOCAL_STATE_ROOT})",
    )

    return parser


def _cmd_queue_poll(args: argparse.Namespace) -> int:
    """ce-ops#218 belt-poller: bounded, witnessable Integrator merge-queue repair poll.
    Belt-native (pure v3 forge); live actions stay behind the injectable adapter and
    the merge gate, fail-closed."""
    try:
        token = integrator_belt.token_from_env(args.token_env)
        logger = integrator_belt.JsonLineLogger(sys.stderr)
        gh_runner = integrator_belt.gh_runner_with_token(token)
        adapter = integrator_belt.LiveGitHubRepairAdapter(
            work_root=args.work_root,
            publish_action=args.action,
            gh_runner=gh_runner,
            git_env=integrator_belt.git_env_with_token(token),
            log_sink=logger,
        )
        result = integrator_belt.run_poll_loop(
            token=token,
            repair_adapter=adapter,
            repo=args.repo,
            org=args.org,
            iterations=args.iterations,
            interval_seconds=args.interval_seconds,
            gh_runner=gh_runner,
            log_sink=logger,
        )
    except integrator_belt.IntegratorBeltError as exc:
        print(f"ERROR: {CE_CMD} queue-poll refused: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive fail-closed
        print(f"ERROR: {CE_CMD} queue-poll failed closed: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            f"{CE_CMD} queue-poll: "
            f"events={result.event_count} executed={result.executed_count} "
            f"escalated={result.escalated_count} refused={result.refused_count}"
        )
    return 0 if result.escalated_count == 0 and result.refused_count == 0 else 1


def _cmd_queue_daemon(args: argparse.Namespace) -> int:
    """Autonomous Integrator merge-queue daemon."""
    try:
        token = integrator_belt.token_from_env(args.token_env)
        logger = integrator_belt.JsonLineLogger(sys.stderr)
        wall = _approval_wall_runtime_from_args(args)
        if wall.misconfigured:
            raise integrator_belt.IntegratorBeltError(f"approval wall misconfigured: {wall.reason}")
        approval_marker_issuer = (
            _approval_capability_marker_issuer_from_args(args)
            if wall.armed and _approval_wall_backend_configured_from_args(args)
            else None
        )
        result = integrator_belt.run_daemon_loop(
            token=token,
            repo=args.repo,
            org=args.org,
            once=bool(args.once),
            interval_seconds=args.interval,
            dry_run=bool(args.dry_run),
            approval_wall=wall,
            log_sink=logger,
            authorized_reviewers=_comma_values(getattr(args, "authorized_reviewers", ()) or ()),
            approval_marker_issuer=approval_marker_issuer,
        )
    except KeyboardInterrupt:  # pragma: no cover - operator stop for loop mode
        print(f"{CE_CMD} queue-daemon: stopped", file=sys.stderr)
        return 130
    except integrator_belt.IntegratorBeltError as exc:
        print(f"ERROR: {CE_CMD} queue-daemon refused: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive fail-closed
        print(f"ERROR: {CE_CMD} queue-daemon failed closed: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            f"{CE_CMD} queue-daemon: "
            f"enqueue={result.enqueue_count} skip={result.skip_count} "
            f"defer={result.defer_count} failed={result.failed_count}"
        )
    return 0 if result.failed_count == 0 else 1


def _comma_values(values: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        out.extend(part.strip() for part in str(value).split(",") if part.strip())
    return tuple(out)


def _cmd_emergency_stop(args: argparse.Namespace) -> int:
    """Emergency merge-queue dequeue primitive."""
    command = getattr(args, "command", "emergency-stop")
    try:
        token = integrator_belt.token_from_env(args.token_env)
        gh_runner = integrator_belt.gh_runner_with_token(token)
        result = integrator_belt.dequeue_merge_queue(
            repo=args.repo,
            pr_number=args.pr_number,
            gh_runner=gh_runner,
            convert_to_draft=bool(args.convert_to_draft),
        )
    except integrator_belt.IntegratorBeltError as exc:
        print(f"ERROR: {CE_CMD} {command} refused: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive fail-closed
        print(f"ERROR: {CE_CMD} {command} failed closed: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        draft = " draft=true" if result.converted_to_draft else ""
        print(
            f"{CE_CMD} {command}: "
            f"repo={result.repo} pr={result.pr_number} "
            f"disabled_auto_merge={result.disabled_auto_merge}{draft}"
        )
    return 0 if result.ok else 1


_cmd_queue_dequeue = _cmd_emergency_stop


def _approval_wall_state_path_from_args(args: argparse.Namespace) -> Path:
    raw = getattr(args, "approval_wall_state", None)
    if raw:
        return Path(raw)
    return approval_capability.approval_wall_state_path(getattr(args, "root", V3_LOCAL_STATE_ROOT))


def _approval_wall_secret_identity_supplier_from_args(
    args: argparse.Namespace,
) -> approval_capability.SecretSupplier | None:
    raw_backend_key = getattr(args, "approval_wall_secret_backend", None)
    raw_mount = getattr(args, "approval_wall_secret_mount", None)
    raw_path = getattr(args, "approval_wall_secret_path", None)
    raw_field = getattr(args, "approval_wall_secret_field", None)
    raw_purpose = getattr(args, "approval_wall_secret_purpose", None)
    raw_owner_ref = getattr(args, "approval_wall_secret_owner_ref", None)
    policy_sha = getattr(args, "approval_wall_secret_ref_policy_sha", None)
    target_ref = getattr(args, "approval_wall_secret_target_ref", None)
    ref_fields = (
        raw_backend_key,
        raw_mount,
        raw_path,
        raw_field,
        raw_purpose,
        raw_owner_ref,
    )
    if not any((*ref_fields, policy_sha, target_ref)):
        return None
    if not policy_sha or not target_ref:
        raise integrator_belt.IntegratorBeltError(
            "approval wall SecretIdentityBackend configuration is partial"
        )
    backend_key = raw_backend_key or secret_identity.DEFAULT_APPROVAL_WALL_SECRET_BACKEND
    mount = raw_mount or secret_identity.DEFAULT_APPROVAL_WALL_SECRET_MOUNT
    path = raw_path or secret_identity.DEFAULT_APPROVAL_WALL_SECRET_PATH
    field = raw_field or secret_identity.DEFAULT_APPROVAL_WALL_SECRET_FIELD
    purpose = raw_purpose or secret_identity.DEFAULT_APPROVAL_WALL_SECRET_PURPOSE
    owner_ref = raw_owner_ref or secret_identity.DEFAULT_APPROVAL_WALL_SECRET_OWNER_REF
    repo = getattr(args, "approval_wall_secret_repo", None) or getattr(args, "repo", None)
    if not repo:
        raise integrator_belt.IntegratorBeltError(
            "approval wall SecretIdentityBackend configuration requires --repo or --approval-wall-secret-repo"
        )
    if target_ref.startswith("env:"):
        raise integrator_belt.IntegratorBeltError(
            "approval wall SecretIdentityBackend target must be file-backed; env: targets are fork-unsafe"
        )
    secret_ref = secret_identity.SecretRef(
        backend=backend_key,
        mount=mount,
        path=path,
        field=field,
        version=getattr(args, "approval_wall_secret_version", None),
        purpose=purpose,
        owner_ref=owner_ref,
        policy_sha=policy_sha,
    )
    request = secret_identity.SecretRequest(
        run_id=getattr(args, "approval_wall_secret_run_id", "approval-wall-daemon"),
        seat_id=getattr(args, "approval_wall_secret_seat_id", "dev-1"),
        repo=repo,
        secret_ref=secret_ref,
        ttl_seconds=getattr(args, "approval_wall_secret_ttl_seconds", 600),
        delivery="file",
        requested_capabilities=("read",),
        audit_context={
            "purpose": "approval-capability-wall",
            "source": "ce queue-daemon",
        },
    )

    def supply() -> bytes | str | None:
        backend_supplier = approval_capability.approval_wall_secret_supplier_from_secret_identity_backend(
            backend=secret_identity.get_backend(backend_key),
            request=request,
            target_ref=target_ref,
            value_reader=_approval_wall_materialized_value_reader,
        )
        return backend_supplier()

    return supply


def _approval_wall_backend_configured_from_args(args: argparse.Namespace) -> bool:
    return _approval_wall_secret_identity_supplier_from_args(args) is not None


def _approval_wall_materialized_value_reader(target_ref: str) -> bytes | str | None:
    if target_ref.startswith("env:"):
        name = target_ref.removeprefix("env:")
        return os.environ.get(name) if name else None
    if target_ref.startswith("file://"):
        path = target_ref.removeprefix("file://")
        return Path(path).read_text(encoding="utf-8")
    if target_ref.startswith("file:"):
        path = target_ref.removeprefix("file:")
        return Path(path).read_text(encoding="utf-8")
    return Path(target_ref).read_text(encoding="utf-8")


def _approval_wall_primary_then_env_supplier(
    *,
    primary: approval_capability.SecretSupplier | None,
    fallback_env: approval_capability.SecretSupplier,
) -> approval_capability.SecretSupplier:
    def supply() -> bytes | str | None:
        if primary is not None:
            return primary()
        return fallback_env()

    return supply


def _approval_wall_secret_supplier_from_args(
    args: argparse.Namespace,
) -> approval_capability.SecretSupplier:
    backend_supplier = _approval_wall_secret_identity_supplier_from_args(args)
    fallback_env_supplier = approval_capability.approval_wall_secret_supplier_from_env(
        env_name=getattr(
            args,
            "approval_wall_secret_env",
            approval_capability.DEFAULT_APPROVAL_CAPABILITY_SECRET_ENV,
        )
    )
    return _approval_wall_primary_then_env_supplier(
        primary=backend_supplier,
        fallback_env=fallback_env_supplier,
    )


def _approval_wall_runtime_from_args(args: argparse.Namespace) -> approval_capability.ApprovalWallRuntime:
    backend_supplier = _approval_wall_secret_identity_supplier_from_args(args)
    wall = approval_capability.resolve_approval_wall(
        approval_capability.ApprovalWallConfig(
            secret_supplier=_approval_wall_secret_supplier_from_args(args),
            state_path=_approval_wall_state_path_from_args(args),
            policy_sha=getattr(args, "approval_wall_policy_sha", None),
        )
    )
    if backend_supplier is not None and wall.dormant:
        return approval_capability.ApprovalWallRuntime(
            approval_capability.APPROVAL_WALL_MISCONFIGURED,
            reason="configured_backend_without_secret",
            state_path=_approval_wall_state_path_from_args(args),
        )
    return wall


def _approval_capability_marker_issuer_from_args(
    args: argparse.Namespace,
) -> integrator_belt.ApprovalMarkerIssuer:
    supplier = _approval_wall_secret_identity_supplier_from_args(args)
    if supplier is None:
        raise integrator_belt.IntegratorBeltError(
            "approval wall SecretIdentityBackend supplier is not configured for minting"
        )
    policy_sha = getattr(args, "approval_wall_policy_sha", None)
    ttl_seconds = getattr(args, "approval_wall_marker_ttl_seconds", 3600)
    if ttl_seconds <= 0:
        raise integrator_belt.IntegratorBeltError("approval wall marker ttl must be positive")
    issuer = approval_capability.ApprovalCapabilityIssuer(
        secret_supplier=supplier,
        now=time.time,
        policy_sha=policy_sha or "",
        ttl_seconds=ttl_seconds,
    )

    def issue(
        pr: integrator_belt.DaemonPullRequest,
        witness: integrator_belt.DaemonApprovalWitness,
    ) -> str:
        if not policy_sha:
            raise integrator_belt.IntegratorBeltError("approval wall policy sha is required to mint")
        try:
            return issuer.mint(
                repo=pr.repo,
                pr_number=pr.pr_number,
                head_sha=pr.head_sha,
                approved_by=witness.reviewer_login,
            )
        except approval_capability.ApprovalCapabilityIssuerError as exc:
            raise integrator_belt.IntegratorBeltError(str(exc)) from exc

    return issue


def _cmd_approval_capability(args: argparse.Namespace) -> int:
    if args.approval_capability_command == "mint":
        return _cmd_approval_capability_mint(args)
    print(f"ERROR: {CE_CMD} approval-capability refused: missing subcommand", file=sys.stderr)
    return 2


def _cmd_approval_capability_mint(args: argparse.Namespace) -> int:
    if args.pr_number < 1:
        print(f"ERROR: {CE_CMD} approval-capability mint refused: --pr must be >= 1", file=sys.stderr)
        return 2
    if args.ttl_seconds <= 0:
        print(f"ERROR: {CE_CMD} approval-capability mint refused: --ttl-seconds must be > 0", file=sys.stderr)
        return 2
    supplier = approval_capability.approval_wall_secret_supplier_from_env(
        env_name=args.approval_wall_secret_env,
    )
    secret = supplier()
    wall = approval_capability.resolve_approval_wall(
        approval_capability.ApprovalWallConfig(
            secret_supplier=lambda: secret,
            state_path=_approval_wall_state_path_from_args(args),
            policy_sha=args.policy_sha,
        )
    )
    if wall.misconfigured:
        print(
            f"ERROR: {CE_CMD} approval-capability mint refused: approval wall misconfigured: {wall.reason}",
            file=sys.stderr,
        )
        return 1
    if wall.dormant or secret is None:
        print(
            f"ERROR: {CE_CMD} approval-capability mint refused: approval wall secret is not configured",
            file=sys.stderr,
        )
        return 1
    issued_at = int(time.time())
    claims = approval_capability.ApprovalCapabilityClaims(
        repo=args.repo,
        pr_number=args.pr_number,
        head_sha=args.head_sha,
        approved_by=args.approved_by,
        issued_at=issued_at,
        expires_at=issued_at + args.ttl_seconds,
        policy_sha=args.policy_sha,
    )
    print(approval_capability.issue_approval_capability(claims, secret))
    return 0


def _review_pickup_transport():
    """Search-API HTTPS transport seam (monkeypatchable in tests)."""
    from . import pickup_search
    return pickup_search._default_transport


def _review_pickup_gh_runner(identity: str, token: str):
    """Per-identity gh runner seam (monkeypatchable in tests) — token in child env only."""
    from . import pickup_search
    return pickup_search.make_gh_runner(token)


def _cmd_review_pickup(args: argparse.Namespace) -> int:
    """ce-ops#188 controller review-pickup: route awaiting-review PRs to distinct
    non-author reviewer seats, reconciling objectively stale reviews fail-closed."""
    from . import pickup_search
    from .forge import review_pickup

    try:
        review_pickup.review_pickup_query(repo=getattr(args, "repo", None), org=getattr(args, "org", None))
    except pickup_search.PickupError as exc:
        return _emit(args, 2, [f"{_BRAND} · review-pickup REFUSED (input): {exc}"],
                     {"error": "review_pickup_input", "detail": str(exc)})

    loop_mode = bool(getattr(args, "loop", False))
    mode = "loop" if loop_mode else "once"
    interval = (
        float(getattr(args, "interval"))
        if getattr(args, "interval", None) is not None
        else review_pickup.DEFAULT_REVIEW_PICKUP_INTERVAL_SECONDS
    )
    if loop_mode and interval <= 0:
        return _emit(args, 2, [f"{_BRAND} · review-pickup REFUSED (input): --loop requires --interval > 0"],
                     {"error": "review_pickup_input", "detail": "--loop requires --interval > 0", "mode": mode})

    try:
        token = pickup_search.resolve_token(
            keys_dir=getattr(args, "keys_dir", None),
            identity=args.identity,
            allow_ambient_gh=getattr(args, "allow_ambient_gh", False),
        )
    except pickup_search.PickupError as exc:
        return _emit(args, 2, [f"{_BRAND} · review-pickup REFUSED (input): {exc}"],
                     {"error": "review_pickup_token", "detail": str(exc)})

    gh_runner = _review_pickup_gh_runner(args.identity, token)
    dry_run = bool(getattr(args, "dry_run", False))
    applied = bool(getattr(args, "apply", False) and not dry_run)
    logger = review_pickup.JsonLineLogger(sys.stderr)
    inbox_path = getattr(args, "inbox_path", None) or str(review_pickup.DEFAULT_AWAITING_REVIEW_INBOX_PATH)

    try:
        loop_result = review_pickup.run_review_pickup_loop(
            token=token,
            reviewer_seats=getattr(args, "reviewer_seats", ()) or (),
            gh_runner=gh_runner,
            transport=_review_pickup_transport(),
            repo=getattr(args, "repo", None),
            org=getattr(args, "org", None),
            apply=applied,
            apply_stale=not bool(getattr(args, "no_stale_apply", False)),
            dry_run=dry_run,
            iterations=None if loop_mode else 1,
            interval=interval,
            log_sink=logger,
            inbox_path=inbox_path,
        )
        result = loop_result.passes[-1] if loop_result.passes else review_pickup.ReviewPickupResult()
    except KeyboardInterrupt:
        return _emit(args, 0, [f"{_BRAND} · review-pickup loop stopped"],
                     {"action": "review_pickup", "mode": mode, "loop": loop_mode, "stopped": True, "dry_run": dry_run})
    except pickup_search.PickupRateLimited as exc:
        return _emit(args, 2, [f"{_BRAND} · review-pickup failed closed: {exc}"],
                     {"error": "rate_limited", "backoff": exc.to_payload()})
    except pickup_search.PickupError as exc:
        return _emit(args, 2, [f"{_BRAND} · review-pickup failed: {exc}"],
                     {"error": "review_pickup_failed", "detail": str(exc)})

    verb = "dry-run" if dry_run else ("applied" if applied else "planned")
    lines = [f"{_BRAND} · review-pickup {mode}: {verb} "
             f"{len(result.items)} review route(s)"]
    for item in result.items:
        lines.append(f"    - {item['repo']}#{item['number']} -> "
                     f"{item.get('assigned_reviewer')} ({item['reason']})")
    payload = {
        "action": "review_pickup",
        "apply": applied,
        "dry_run": dry_run,
        "mode": mode,
        "loop": loop_mode,
        "interval": interval if loop_mode else None,
        "rate_limit": result.rate_limit,
        "inbox_path": inbox_path,
        "awaiting_decisions": list(result.awaiting_decisions),
        "items": list(result.items),
        "skipped": list(result.skipped),
        "count": len(result.items),
        "awaiting_decision_count": len(result.awaiting_decisions),
        "skipped_count": len(result.skipped),
    }
    return _emit(args, 0, lines, payload)


def _path_manifest_against_index(
    repo_root: Path,
    *,
    base: str,
    manifest_dir: str,
    head_ref: str,
):
    from .checks import path_manifest_fidelity

    original_run_git = path_manifest_fidelity._run_git

    def _run_git_from_index(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if argv == ["diff", "--name-status", "--no-renames", f"{base}..HEAD"]:
            try:
                proc = _git_run(cwd, "diff", "--cached", "--name-status", "--no-renames", base)
            except v3_installer.InstallRefused as exc:
                return 127, "", str(exc)
            return proc.returncode, proc.stdout, proc.stderr
        if argv == ["diff", "--name-only", f"{base}..HEAD"]:
            try:
                proc = _git_run(cwd, "diff", "--cached", "--name-only", base)
            except v3_installer.InstallRefused as exc:
                return 127, "", str(exc)
            return proc.returncode, proc.stdout, proc.stderr
        return original_run_git(argv, cwd)

    try:
        path_manifest_fidelity._run_git = _run_git_from_index
        return path_manifest_fidelity.run_with_base(
            [repo_root],
            base,
            manifest_dir=manifest_dir,
            head_ref=head_ref,
            require_carrier=True,
        )
    finally:
        path_manifest_fidelity._run_git = original_run_git


def _carrier_output_paths(slug: str) -> tuple[Path, Path]:
    from .checks import path_manifest_fidelity

    return (
        Path(path_manifest_fidelity.MANIFEST_DIR) / f"{slug}.md",
        Path(".ce/changelog") / f"{slug}.md",
    )


def _porcelain_path(raw_path: str) -> str:
    path = raw_path
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        path = path[1:-1]
    return path


def _unstaged_non_carrier_paths(status: str, carrier_paths: set[str]) -> list[str]:
    blocked: list[str] = []
    for raw_line in status.splitlines():
        if not raw_line:
            continue
        code = raw_line[:2]
        path = _porcelain_path(raw_line[3:])
        if path in carrier_paths:
            continue
        if code == "??" or len(code) == 2 and code[1] not in {" ", "?"}:
            blocked.append(path)
    return sorted(set(blocked))


def _cmd_carrier(args: argparse.Namespace) -> int:
    from .checks import path_manifest_fidelity

    slug = str(args.slug)
    canonical_slug = path_manifest_fidelity.branch_slug(slug)
    if slug != canonical_slug:
        return _emit(
            args,
            2,
            [f"{_BRAND} · carrier REFUSED (input): --slug must be canonical; expected {canonical_slug!r}"],
            {"error": "carrier_input", "detail": "--slug must be canonical", "expected_slug": canonical_slug},
        )

    try:
        repo_root_raw = _git_read(Path.cwd(), "rev-parse", "--show-toplevel")
    except v3_installer.InstallRefused as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: {exc}"],
            {"error": "refused", "detail": str(exc)},
        )
    if not repo_root_raw:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: not inside a git repository"],
            {"error": "carrier_git_repository", "detail": "not inside a git repository"},
        )
    repo_root = Path(repo_root_raw).resolve()

    try:
        from .carrier_gen import CarrierSpec, write_carriers
    except ImportError as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: generator module unavailable ({exc})"],
            {"error": "carrier_generator_unavailable", "detail": str(exc)},
        )

    carrier_path, changelog_path = _carrier_output_paths(slug)
    staged_paths = (carrier_path, changelog_path)
    try:
        status_proc = _git_run(repo_root, "status", "--porcelain", "--untracked-files=all")
    except v3_installer.InstallRefused as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: {exc}"],
            {"error": "refused", "detail": str(exc)},
        )
    if status_proc.returncode != 0:
        detail = (status_proc.stderr or status_proc.stdout or "git status failed").strip()
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: could not inspect worktree status: {detail}"],
            {"error": "carrier_status_failed", "detail": detail},
        )
    unstaged = _unstaged_non_carrier_paths(
        status_proc.stdout,
        {path.as_posix() for path in staged_paths},
    )
    if unstaged:
        preview = ", ".join(unstaged[:8])
        if len(unstaged) > 8:
            preview = f"{preview}, ... (+{len(unstaged) - 8} more)"
        add_hint = " ".join(shlex.quote(path) for path in unstaged[:8])
        return _emit(
            args,
            1,
            [
                f"{_BRAND} · carrier REFUSED (worktree): stage or remove unstaged/untracked non-carrier paths first",
                f"    run: git add -- {add_hint}",
                f"    carrier may write/stage: {carrier_path.as_posix()}, {changelog_path.as_posix()}",
                f"    blocked: {preview}",
            ],
            {
                "error": "carrier_unstaged_non_carrier_paths",
                "detail": "stage or remove unstaged/untracked non-carrier paths before running ce carrier",
                "paths": unstaged,
                "allowed_carrier_outputs": [path.as_posix() for path in staged_paths],
            },
        )

    body_file = Path(args.body_file)
    try:
        body = body_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: could not read --body-file ({exc})"],
            {"error": "carrier_body_file", "detail": str(exc), "body_file": str(body_file)},
        )

    date = args.date or datetime.now(timezone.utc).date().isoformat()
    spec_values = {
        "slug": slug,
        "head_ref": slug,
        "issue": args.issue,
        "title": args.title,
        "kind": args.kind,
        "scope": args.scope,
        "body_file": body_file,
        "body": body,
        "base": args.base,
        "date": date,
    }
    try:
        spec_params = inspect.signature(CarrierSpec).parameters
        spec = CarrierSpec(**{name: spec_values[name] for name in spec_params if name in spec_values})
    except Exception as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: could not build generator spec ({exc})"],
            {"error": "carrier_spec_failed", "detail": str(exc)},
        )

    def _generator_git_runner(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if argv == ["diff", "--name-only", f"{args.base}..HEAD"]:
            try:
                proc = _git_run(cwd, "diff", "--cached", "--name-only", args.base)
            except v3_installer.InstallRefused as exc:
                return 127, "", str(exc)
            return proc.returncode, proc.stdout, proc.stderr
        try:
            proc = _git_run(cwd, *argv)
        except v3_installer.InstallRefused as exc:
            return 127, "", str(exc)
        return proc.returncode, proc.stdout, proc.stderr

    try:
        write_params = inspect.signature(write_carriers).parameters
        write_kwargs: dict[str, Any] = {}
        if "git_runner" in write_params:
            write_kwargs["git_runner"] = _generator_git_runner
        first_param = next(iter(write_params), None)
        if first_param in {"repo_root", "root"}:
            write_carriers(repo_root, spec, **write_kwargs)
        else:
            write_carriers(spec, **write_kwargs)
    except Exception as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: generator refused ({exc})"],
            {"error": "carrier_generator_failed", "detail": str(exc)},
        )

    missing = [path.as_posix() for path in staged_paths if not (repo_root / path).is_file()]
    if missing:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: generator did not write expected file(s): {', '.join(missing)}"],
            {"error": "carrier_missing_outputs", "missing": missing},
        )

    try:
        add_proc = _git_run(repo_root, "add", "--", *(path.as_posix() for path in staged_paths))
    except v3_installer.InstallRefused as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: {exc}"],
            {"error": "refused", "detail": str(exc)},
        )
    if add_proc.returncode != 0:
        detail = (add_proc.stderr or add_proc.stdout or "git add failed").strip()
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier failed closed: could not stage generated files: {detail}"],
            {"error": "carrier_stage_failed", "detail": detail, "files": [p.as_posix() for p in staged_paths]},
        )

    result = _path_manifest_against_index(
        repo_root,
        base=args.base,
        manifest_dir=path_manifest_fidelity.MANIFEST_DIR,
        head_ref=slug,
    )
    identity = path_manifest_fidelity.parse_carrier_file(repo_root / carrier_path)
    manifest_summary = {
        "carrier": carrier_path.as_posix(),
        "changelog": changelog_path.as_posix(),
        "base": args.base,
        "head_ref": slug,
        "paths_count": len(identity.paths) if identity else None,
        "paths_sha256": identity.normalized_sha256 if identity else None,
        "consistent": identity.consistent if identity else False,
    }
    payload = {
        "action": "carrier",
        "files": [path.as_posix() for path in staged_paths],
        "manifest": manifest_summary,
        "verification": result.to_dict(),
    }

    if not result.ok or not identity or not identity.consistent:
        errors = [error.format() for error in result.errors]
        if not identity:
            errors.append(f"{carrier_path.as_posix()}: no structured path manifest found")
        elif not identity.consistent:
            errors.append(f"{carrier_path.as_posix()}: declared manifest count/hash do not match canonical paths")
        return _emit(
            args,
            1,
            [f"{_BRAND} · carrier FAIL path_manifest_fidelity", *errors],
            {**payload, "error": "carrier_path_manifest_fidelity"},
        )

    lines = [
        f"{_BRAND} · carrier PASS path_manifest_fidelity",
        f"    carrier: {carrier_path.as_posix()}",
        f"    changelog: {changelog_path.as_posix()}",
        f"    manifest: count={identity.declared_count} sha256={identity.normalized_sha256}",
    ]
    return _emit(args, 0, lines, payload)


_DISPATCH = {
    "scope": _cmd_scope,
    "shape": _cmd_shape,
    "ratify": _cmd_ratify,
    "drive": _cmd_drive,
    "dispatch": _cmd_dispatch,
    "collect": _cmd_collect,
    "pr": _cmd_pr,
    "configure-repo": _cmd_configure_repo,
    "ruleset": _cmd_ruleset,
    "review-submit": _cmd_review_submit,
    "auto-merge": _cmd_auto_merge,
    "review-pickup": _cmd_review_pickup,
    "review": _cmd_review,
    "merge": _cmd_merge,
    "playbook": playbook_runtime.run_cli,
    "escalation": _cmd_escalation,
    "notify": _cmd_notify,
    "reap": _cmd_reap,
    "status": _cmd_status,
    "show": _cmd_show,
    "artifacts": _cmd_artifacts,
    "report": _cmd_report,
    "onboard": _cmd_onboard,
    "guide": _cmd_guide,
    "session": _cmd_session,
    "cockpit": _cmd_cockpit,
    "carrier": _cmd_carrier,
    "queue-poll": _cmd_queue_poll,
    "queue-daemon": _cmd_queue_daemon,
    "emergency-stop": _cmd_emergency_stop,
    "queue-dequeue": _cmd_queue_dequeue,
    "approval-capability": _cmd_approval_capability,
    "fleet": fleet_status.run_cli,
    "seats": seats_status.run_cli,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if not raw_argv:
        raw_argv = ["session"]
    args = parser.parse_args(raw_argv)
    command = args.command
    handler = _DISPATCH.get(command)
    if handler is None:  # pragma: no cover - argparse guards the choices
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
