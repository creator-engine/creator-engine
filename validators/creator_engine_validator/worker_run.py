"""One-call governed worker role run surface (ce-ops#259).

This module resolves the checked-in CE role definitions under
``.claude/agents/<role>.md``, composes the existing ``worker_spawn`` launch
primitive, seeds a pointer-only prompt/findings instruction into the launched
pane, and collects a structured findings artifact through injectable seams. It
does not introduce a new launcher or harness path.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import worker_spawn


ROLE_DEFS_REL = Path(".claude/agents")
RUNS_REL = Path(".ce/state/worker-runs")
ROLE_LANE_BINDINGS: dict[str, str] = {
    "architect_research": "read-only",
    "implementer": "implementation",
    "reviewer": "review",
    "verification": "audit",
}


class WorkerRunError(Exception):
    code = "CE259-WORKER-RUN-ERROR"


class MissingWorkerRunRole(WorkerRunError):
    code = "CE259-WORKER-RUN-ROLE-MISSING"


class UnknownWorkerRunRole(WorkerRunError):
    code = "CE259-WORKER-RUN-ROLE-UNKNOWN"


class InvalidWorkerRunBrief(WorkerRunError):
    code = "CE259-WORKER-RUN-BRIEF"


class WorkerRunLaunchFailed(WorkerRunError):
    code = "CE259-WORKER-RUN-LAUNCH"


class WorkerRunSeedFailed(WorkerRunError):
    code = "CE259-WORKER-RUN-SEED"


class WorkerRunFindingsUnavailable(WorkerRunError):
    code = "CE259-WORKER-RUN-FINDINGS"


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    path: Path
    sha256: str
    description: str | None
    tools: tuple[str, ...]
    body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "sha256": self.sha256,
            "description": self.description,
            "tools": list(self.tools),
        }


@dataclass(frozen=True)
class WorkerRunResult:
    run_id: str
    role: RoleDefinition
    brief_path: Path
    prompt_path: Path
    findings_path: Path
    spawn: worker_spawn.WorkerSpawnResult
    findings: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "role": self.role.to_dict(),
            "brief_path": str(self.brief_path),
            "prompt_path": str(self.prompt_path),
            "findings_path": str(self.findings_path),
            "spawn": self.spawn.to_dict(),
            "findings": self.findings,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _slug_token(value: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.strip().lower())
    out = "-".join(part for part in out.split("-") if part)
    return out


def _split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    raw = text[4:end]
    body = text[end + 4 :].lstrip("\r\n")
    loaded = yaml.safe_load(raw) if raw.strip() else {}
    return (loaded if isinstance(loaded, dict) else {}), body


def _tools_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, list):
        return tuple(str(part).strip() for part in value if str(part).strip())
    return (str(value).strip(),) if str(value).strip() else ()


def resolve_role_definition(role: str | None, *, repo_root: Path | str = ".") -> RoleDefinition:
    raw = (role or "").strip()
    if not raw:
        raise MissingWorkerRunRole("--role is required")
    role_name = _slug_token(raw).replace("-", "_")
    if not role_name:
        raise MissingWorkerRunRole("--role is required")
    if role_name not in ROLE_LANE_BINDINGS:
        raise UnknownWorkerRunRole(
            f"role {raw!r} is not a sanctioned worker-run role; expected one of: "
            f"{', '.join(sorted(ROLE_LANE_BINDINGS))}"
        )
    path = Path(repo_root) / ROLE_DEFS_REL / f"{role_name}.md"
    if not path.is_file():
        raise UnknownWorkerRunRole(f"role definition not found: {path}")
    data = path.read_bytes()
    text = data.decode("utf-8")
    meta, body = _split_front_matter(text)
    declared = str(meta.get("name") or role_name).strip()
    if declared != role_name:
        raise UnknownWorkerRunRole(
            f"role definition {path} declares name {declared!r}, expected {role_name!r}"
        )
    return RoleDefinition(
        name=role_name,
        path=path,
        sha256=_sha256_bytes(data),
        description=str(meta["description"]) if meta.get("description") is not None else None,
        tools=_tools_tuple(meta.get("tools")),
        body=body,
    )


def resolve_brief_path(brief: Path | str) -> Path:
    path = Path(brief)
    if not path.is_file():
        raise InvalidWorkerRunBrief(f"brief file {str(path)!r} does not exist")
    return path


def _run_id(role: str, brief_sha: str, supplied: str | None) -> str:
    if supplied:
        slug = _slug_token(supplied)
        if slug:
            return slug
    return f"worker-run-{role.replace('_', '-')}-{brief_sha[:8]}-{uuid.uuid4().hex[:8]}"


def _render_prompt(
    *,
    role: RoleDefinition,
    brief_path: Path,
    brief_sha: str,
    findings_path: Path,
) -> str:
    brief_text = brief_path.read_text(encoding="utf-8")
    tools = ", ".join(role.tools) if role.tools else "unspecified"
    return (
        "# CE Governed Worker Run\n\n"
        f"Role: `{role.name}`\n"
        f"Role definition: `{role.path}`\n"
        f"Role definition SHA256: `{role.sha256}`\n"
        f"Declared tools: {tools}\n"
        f"Brief: `{brief_path}`\n"
        f"Brief SHA256: `{brief_sha}`\n"
        f"Findings artifact: `{findings_path}`\n\n"
        "You are running under the role definition below. Execute the brief within "
        "that role boundary and return structured findings only. Write the final "
        "findings artifact as YAML or JSON with at least `status`, `summary`, and "
        "`findings` fields.\n\n"
        "## Role Definition\n\n"
        f"{role.body.rstrip()}\n\n"
        "## Brief\n\n"
        f"{brief_text.rstrip()}\n"
    )


class FileFindingsCollector:
    """Collect findings from the declared worker-run artifact path."""

    def __init__(self, *, timeout_seconds: float = 300.0, poll_interval_seconds: float = 1.0):
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def collect(self, *, findings_path: Path, **_: Any) -> dict[str, Any]:
        deadline = time.monotonic() + max(0.0, self.timeout_seconds)
        while True:
            if findings_path.is_file():
                return normalize_findings(findings_path)
            if time.monotonic() >= deadline:
                raise WorkerRunFindingsUnavailable(
                    f"findings artifact was not produced: {findings_path}"
                )
            time.sleep(max(0.05, self.poll_interval_seconds))


def render_seed_instruction(*, prompt_path: Path, findings_path: Path) -> str:
    return (
        f"Read {prompt_path} and execute under it. "
        f"Write final YAML or JSON findings to {findings_path}."
    )


class TmuxPromptSeeder:
    """Deliver the pointer-only worker-run instruction to a launched tmux pane."""

    def __init__(self, *, runner: Any = subprocess.run):
        self.runner = runner

    def seed(
        self,
        *,
        prompt_path: Path,
        findings_path: Path,
        spawn: worker_spawn.WorkerSpawnResult,
        **_: Any,
    ) -> str:
        terminal = _spawn_terminal(spawn)
        pane = terminal.get("pane_id") or terminal.get("pane")
        if not pane:
            raise WorkerRunSeedFailed("worker launch did not return an addressable pane_id")
        line = render_seed_instruction(prompt_path=prompt_path, findings_path=findings_path)
        literal = self.runner(
            ["tmux", "send-keys", "-t", str(pane), "-l", line],
            capture_output=True,
            text=True,
        )
        if getattr(literal, "returncode", 1) != 0:
            reason = (getattr(literal, "stderr", "") or "").strip() or "(no stderr)"
            raise WorkerRunSeedFailed(f"tmux send-keys seed failed: {reason}")
        enter = self.runner(
            ["tmux", "send-keys", "-t", str(pane), "Enter"],
            capture_output=True,
            text=True,
        )
        if getattr(enter, "returncode", 1) != 0:
            reason = (getattr(enter, "stderr", "") or "").strip() or "(no stderr)"
            raise WorkerRunSeedFailed(f"tmux send-keys enter failed: {reason}")
        return line


def _spawn_terminal(spawn: worker_spawn.WorkerSpawnResult) -> dict[str, Any]:
    if spawn.launch_outcome and spawn.launch_outcome.terminal:
        return dict(spawn.launch_outcome.terminal)
    seat_refs = spawn.record.get("seat_refs") if isinstance(spawn.record, dict) else None
    terminal = seat_refs.get("terminal") if isinstance(seat_refs, dict) else None
    return dict(terminal) if isinstance(terminal, dict) else {}


def normalize_findings(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = yaml.safe_load(text)
    if isinstance(parsed, dict):
        findings = parsed.get("findings")
        if findings is None:
            findings = []
        if not isinstance(findings, list):
            findings = [findings]
        return {
            "status": str(parsed.get("status") or "completed"),
            "summary": parsed.get("summary"),
            "findings": findings,
            "raw": parsed,
        }
    if isinstance(parsed, list):
        return {"status": "completed", "summary": None, "findings": parsed, "raw": parsed}
    return {
        "status": "completed",
        "summary": text.strip() or None,
        "findings": [{"kind": "text", "body": text}],
        "raw": text,
    }


def run_worker_role(
    *,
    role: str | None,
    brief: Path | str,
    repo_root: Path | str = ".",
    worktree: Path | str | None = None,
    harness: str = "claude",
    run_id: str | None = None,
    parent_id: str | None = None,
    worker_id: str | None = None,
    environ: Mapping[str, str] | None = None,
    launcher: Any | None = None,
    seeder: Any | None = None,
    collector: Any | None = None,
) -> WorkerRunResult:
    root = Path(repo_root).resolve()
    role_def = resolve_role_definition(role, repo_root=root)
    brief_path = resolve_brief_path(brief)
    brief_data = brief_path.read_bytes()
    brief_sha = _sha256_bytes(brief_data)
    resolved_run_id = _run_id(role_def.name, brief_sha, run_id)
    run_root = root / RUNS_REL / resolved_run_id
    prompt_path = run_root / "prompt.md"
    findings_path = run_root / "findings.yaml"
    prompt_text = _render_prompt(
        role=role_def,
        brief_path=brief_path,
        brief_sha=brief_sha,
        findings_path=findings_path,
    )
    run_root.mkdir(parents=True, exist_ok=False)
    prompt_path.write_text(prompt_text, encoding="utf-8")

    spawn_role = role_def.name
    try:
        spawn = worker_spawn.spawn_worker(
            role=spawn_role,
            harness=harness,
            worktree=worktree or root,
            scope_id=resolved_run_id,
            prompt_file=prompt_path,
            parent_id=parent_id,
            worker_id=worker_id,
            environ=environ,
            launcher=launcher,
        )
    except worker_spawn.WorkerSpawnError as exc:
        raise WorkerRunLaunchFailed(f"worker spawn refused [{exc.code}]: {exc}") from exc

    live_seeder = seeder or TmuxPromptSeeder()
    try:
        live_seeder.seed(
            run_id=resolved_run_id,
            role=role_def,
            brief_path=brief_path,
            prompt_path=prompt_path,
            findings_path=findings_path,
            spawn=spawn,
        )
    except WorkerRunError:
        raise
    except Exception as exc:
        raise WorkerRunSeedFailed(f"worker prompt seed failed: {exc}") from exc

    live_collector = collector or FileFindingsCollector()
    try:
        findings = live_collector.collect(
            run_id=resolved_run_id,
            role=role_def,
            brief_path=brief_path,
            prompt_path=prompt_path,
            findings_path=findings_path,
            spawn=spawn,
        )
    except WorkerRunError:
        raise
    except Exception as exc:
        raise WorkerRunFindingsUnavailable(f"findings collection failed: {exc}") from exc

    return WorkerRunResult(
        run_id=resolved_run_id,
        role=role_def,
        brief_path=brief_path,
        prompt_path=prompt_path,
        findings_path=findings_path,
        spawn=spawn,
        findings=findings,
    )
