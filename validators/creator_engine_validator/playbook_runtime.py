"""Public PLAYBOOK.md runtime projection for ce-ops#248.

The public playbook format is a human-facing authoring layer. This module keeps
the internal workflow descriptor schema as the dispatch SSOT by validating the
public frontmatter, projecting it into ``schemas/playbook.schema.yaml``, and
validating that projection with the existing schema helper.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Iterable, Mapping

import yaml

from .reporting import ValidationError
from .schema import validate_with_schema


CONTRACT = "docs/contracts/playbook-format.md"
INTERNAL_CONTRACT = "docs/contracts/playbook-format.md"
SCHEMA_PATH = "schemas/playbook.schema.yaml"
CODE_PUBLIC = "PLAYBOOK-PUBLIC-FORMAT"
CODE_SCHEMA = "PLAYBOOK-INTERNAL-SCHEMA"
PLAYBOOK_FILE = "PLAYBOOK.md"
WORKFLOW_FILE = "workflow.ce.yml"
GOVERNED_COMMAND_DENY_EXIT = 121

STATUS_VALUES = {"active", "draft", "deprecated"}
MODE_VALUES = {"ceo", "dev"}
GATE_VALUES = ("plan", "author", "review", "merge")
WORK_CLASS_VALUES = {"tiny", "story", "feature", "epic"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,96}$")

_SPINE_DIRS = {"plan", "author", "review", "merge", "operate", "ceo-mode"}

_GATE_MAP: dict[str, tuple[str, str]] = {
    "plan": ("dor", "Plan gate: problem, scope, and definition of done are ready before dispatch."),
    "author": ("dod", "Author gate: governed author output exists and is ready for review."),
    "review": ("review", "Review gate: a distinct governed reviewer evaluates the current head."),
    "merge": ("ratification", "Merge gate: human ratification and landing criteria are satisfied."),
}

_DISPATCH_TARGETS = {
    "plan": "controller-seat",
    "author": "author-seat",
    "review": "reviewer-seat",
    "merge": "controller-seat",
}


class PlaybookError(Exception):
    """Fail-closed playbook refusal carrying structured validation errors."""

    def __init__(self, message: str, errors: Iterable[ValidationError] = ()):
        super().__init__(message)
        self.errors = tuple(errors)


@dataclass(frozen=True)
class PublicPlaybook:
    path: Path
    frontmatter: dict[str, Any]
    body: str
    descriptor: dict[str, Any]
    source_format: str = "public-frontmatter"

    @property
    def id(self) -> str:
        playbook = self.descriptor.get("playbook")
        if isinstance(playbook, dict) and playbook.get("name"):
            return str(playbook["name"])
        return str(self.frontmatter["id"])

    def summary(self) -> dict[str, Any]:
        playbook = self.descriptor["playbook"]
        metadata = self.descriptor.get("metadata") if isinstance(self.descriptor.get("metadata"), dict) else {}
        return {
            "id": self.id,
            "title": playbook["title"],
            "mode": metadata.get("mode", "dev"),
            "work_class": metadata.get("work_class", "story"),
            "status": playbook["status"],
            "path": str(self.path),
            "source_format": self.source_format,
        }


@dataclass(frozen=True)
class StepExecution:
    id: str
    title: str
    action: str
    command: str | None
    expected_result: str | None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    governance_decision: dict[str, Any] | None = None


StepExecutor = Callable[[StepExecution, Path], StepExecution]


def _error(path: Path, field: str, message: str, *, code: str = CODE_PUBLIC) -> ValidationError:
    return ValidationError(code=code, path=f"{path}:{field}", message=message, contract=CONTRACT)


def _split_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlaybookError(f"cannot read playbook {path}: {exc}") from exc

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise PlaybookError(
            f"{path} is missing YAML frontmatter",
            [_error(path, "/", "PLAYBOOK.md must start with YAML frontmatter delimited by ---")],
        )
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        raise PlaybookError(
            f"{path} frontmatter is not closed",
            [_error(path, "/", "YAML frontmatter must be closed by ---")],
        )

    raw_frontmatter = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as exc:
        raise PlaybookError(
            f"{path} frontmatter is not valid YAML",
            [_error(path, "/", f"frontmatter YAML parse failed: {exc}")],
        ) from exc
    if not isinstance(data, dict):
        raise PlaybookError(
            f"{path} frontmatter must be a mapping",
            [_error(path, "/", "frontmatter must parse to a YAML mapping")],
        )
    return data, "\n".join(lines[end + 1 :])


def _validate_required_string(
    errors: list[ValidationError], path: Path, data: dict[str, Any], key: str
) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(_error(path, f"/{key}", f"{key} is required and must be a non-empty string"))


def _validate_step_list(
    errors: list[ValidationError],
    path: Path,
    data: dict[str, Any],
    key: str,
    required_text_key: str,
) -> None:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(_error(path, f"/{key}", f"{key} is required and must be a non-empty list"))
        return
    seen: set[str] = set()
    for index, item in enumerate(value):
        pointer = f"/{key}/{index}"
        if not isinstance(item, dict):
            errors.append(_error(path, pointer, f"{key} entries must be mappings"))
            continue
        item_id = item.get("id")
        text = item.get(required_text_key)
        if not isinstance(item_id, str) or not SLUG_RE.match(item_id):
            errors.append(_error(path, f"{pointer}/id", "entry id must be a valid slug"))
        elif item_id in seen:
            errors.append(_error(path, f"{pointer}/id", f"duplicate entry id {item_id!r}"))
        else:
            seen.add(item_id)
        if not isinstance(text, str) or not text.strip():
            errors.append(
                _error(path, f"{pointer}/{required_text_key}", f"{required_text_key} must be a non-empty string")
            )
        command = item.get("command")
        if command is not None and (not isinstance(command, str) or not command.strip()):
            errors.append(_error(path, f"{pointer}/command", "command must be a non-empty string when present"))
        expected_result = item.get("expected_result")
        if expected_result is not None and (
            not isinstance(expected_result, str) or not expected_result.strip()
        ):
            errors.append(
                _error(path, f"{pointer}/expected_result", "expected_result must be a non-empty string when present")
            )


def _validate_public_frontmatter(path: Path, data: dict[str, Any], body: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for key in ("id", "title", "goal", "status", "mode", "work_class"):
        _validate_required_string(errors, path, data, key)

    playbook_id = data.get("id")
    if isinstance(playbook_id, str):
        if not SLUG_RE.match(playbook_id):
            errors.append(_error(path, "/id", "id must match ^[a-z0-9][a-z0-9-]{1,96}$"))
        if path.name == PLAYBOOK_FILE and path.parent.name in _SPINE_DIRS:
            errors.append(_error(path, "/id", "PLAYBOOK.md must be inside an id-named folder"))
        elif path.name == PLAYBOOK_FILE and path.parent.name != playbook_id:
            errors.append(_error(path, "/id", f"id must match folder name {path.parent.name!r}"))

    if data.get("status") not in STATUS_VALUES:
        errors.append(_error(path, "/status", f"status must be one of {sorted(STATUS_VALUES)}"))
    if data.get("mode") not in MODE_VALUES:
        errors.append(_error(path, "/mode", f"mode must be one of {sorted(MODE_VALUES)}"))
    if data.get("work_class") not in WORK_CLASS_VALUES:
        errors.append(_error(path, "/work_class", f"work_class must be one of {sorted(WORK_CLASS_VALUES)}"))

    gates = data.get("gates")
    if not isinstance(gates, list) or not gates:
        errors.append(_error(path, "/gates", "gates is required and must be a non-empty list"))
    else:
        seen_gates: set[str] = set()
        for index, gate in enumerate(gates):
            if gate not in GATE_VALUES:
                errors.append(_error(path, f"/gates/{index}", f"gate must be one of {list(GATE_VALUES)}"))
            elif gate in seen_gates:
                errors.append(_error(path, f"/gates/{index}", f"duplicate gate {gate!r}"))
            else:
                seen_gates.add(gate)

    _validate_step_list(errors, path, data, "prerequisites", "description")
    _validate_step_list(errors, path, data, "steps", "action")
    _validate_step_list(errors, path, data, "expected_outcome", "description")

    triggers = data.get("triggers")
    if triggers is not None and (
        not isinstance(triggers, list)
        or any(not isinstance(item, str) or not item.strip() for item in triggers)
    ):
        errors.append(_error(path, "/triggers", "triggers must be a list of non-empty strings when present"))

    related = data.get("related")
    if related is not None and (
        not isinstance(related, list)
        or any(not isinstance(item, str) or not item.strip() for item in related)
    ):
        errors.append(_error(path, "/related", "related must be a list of non-empty strings when present"))

    headings = _markdown_headings(body)
    required_sections = {
        "overview": {"overview"},
        "prerequisites": {"prerequisites", "what you need"},
        "steps": {"steps"},
        "customization": {"customization"},
        "related": {"related", "what's next", "whats next"},
    }
    for label, aliases in required_sections.items():
        if not headings.intersection(aliases):
            errors.append(_error(path, f"/body/{label}", f"human prose must include a {label} section"))

    return errors


def _markdown_headings(body: str) -> set[str]:
    headings: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip().lower()
        title = re.sub(r"[^\w\s'-]", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        if title:
            headings.add(title)
    return headings


def _human_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _stage_gate_refs(stage_id: str, gates: list[str]) -> list[str]:
    if stage_id in gates:
        return [stage_id]
    return list(gates)


def project_public_playbook(data: dict[str, Any], *, source_path: Path | None = None) -> dict[str, Any]:
    gates = [str(gate) for gate in data["gates"]]
    steps = data["steps"]
    playbook_type = "workflow"
    descriptor: dict[str, Any] = {
        "kind": "ce-playbook",
        "schema_version": "1",
        "playbook": {
            "name": data["id"],
            "title": data["title"],
            "type": playbook_type,
            "owner_issue": "ce-ops#248",
            "status": data["status"],
            "summary": data["goal"],
        },
        "preconditions": [
            {"id": item["id"], "description": item["description"]} for item in data["prerequisites"]
        ],
        "outputs": [
            {"id": item["id"], "description": item["description"]} for item in data["expected_outcome"]
        ],
        "dispatch": {
            "default_target": "governed-seat",
            "authority_envelope": "envelope.template.yml",
            "work_claim_required": True,
            "review_required": "review" in gates,
        },
        "gates": [
            {
                "id": gate,
                "type": _GATE_MAP[gate][0],
                "description": _GATE_MAP[gate][1],
                "required": True,
            }
            for gate in gates
        ],
        "stages": [
            _stage_from_public_step(step, gates)
            for step in steps
        ],
        "references": list(data.get("related") or []),
        "metadata": {
            "public_playbook": True,
            "mode": data["mode"],
            "work_class": data["work_class"],
        },
    }
    if source_path is not None:
        descriptor["metadata"]["source_path"] = str(source_path)
    if data.get("triggers"):
        descriptor["metadata"]["triggers"] = list(data["triggers"])
    if not descriptor["references"]:
        descriptor.pop("references")
    return descriptor


def _stage_from_public_step(step: dict[str, Any], gates: list[str]) -> dict[str, Any]:
    stage = {
        "id": step["id"],
        "title": _human_title(step["id"]),
        "brief": f"briefs/{step['id']}.md",
        "dispatch_target": _DISPATCH_TARGETS.get(step["id"], "governed-seat"),
        "gates": _stage_gate_refs(step["id"], gates),
    }
    if step.get("description"):
        stage["description"] = step["description"]
    if step.get("action"):
        stage["action"] = step["action"]
    if step.get("command"):
        stage["command"] = step["command"]
    if step.get("expected_result"):
        stage["expected_result"] = step["expected_result"]
    return stage


def _validate_descriptor(path: Path, descriptor: dict[str, Any]) -> list[ValidationError]:
    errors = validate_with_schema(
        descriptor,
        SCHEMA_PATH,
        path,
        code=CODE_SCHEMA,
        contract=INTERNAL_CONTRACT,
    )
    declared_gates = {gate["id"] for gate in descriptor.get("gates", []) if isinstance(gate, dict)}
    for index, stage in enumerate(descriptor.get("stages", [])):
        if not isinstance(stage, dict):
            continue
        for gate in stage.get("gates", []):
            if gate not in declared_gates:
                errors.append(
                    ValidationError(
                        code=CODE_SCHEMA,
                        path=f"{path}:/stages/{index}/gates",
                        message=f"stage {stage.get('id')!r} references undeclared gate {gate!r}",
                        contract=INTERNAL_CONTRACT,
                    )
                )
    return errors


def load_playbook(path: str | Path) -> PublicPlaybook:
    resolved = _resolve_playbook_path(Path(path))
    if resolved.name == WORKFLOW_FILE:
        return load_workflow_playbook(resolved)
    frontmatter, body = _split_frontmatter(resolved)
    public_errors = _validate_public_frontmatter(resolved, frontmatter, body)
    if public_errors:
        raise PlaybookError(f"{resolved} is not a valid public playbook", public_errors)
    descriptor = project_public_playbook(frontmatter, source_path=resolved)
    descriptor_errors = _validate_descriptor(resolved, descriptor)
    if descriptor_errors:
        raise PlaybookError(f"{resolved} does not project to a valid internal descriptor", descriptor_errors)
    return PublicPlaybook(path=resolved, frontmatter=frontmatter, body=body, descriptor=descriptor)


def load_workflow_playbook(path: str | Path) -> PublicPlaybook:
    resolved = Path(path)
    try:
        data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PlaybookError(f"cannot read playbook {resolved}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise PlaybookError(
            f"{resolved} is not valid YAML",
            [_error(resolved, "/", f"workflow YAML parse failed: {exc}", code=CODE_SCHEMA)],
        ) from exc
    if not isinstance(data, dict):
        raise PlaybookError(
            f"{resolved} must parse to a mapping",
            [_error(resolved, "/", "workflow.ce.yml must parse to a YAML mapping", code=CODE_SCHEMA)],
        )
    descriptor_errors = _validate_descriptor(resolved, data)
    if descriptor_errors:
        raise PlaybookError(f"{resolved} is not a valid playbook workflow", descriptor_errors)
    playbook = data["playbook"]
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    frontmatter = {
        "id": playbook["name"],
        "title": playbook["title"],
        "goal": playbook.get("summary", ""),
        "status": playbook["status"],
        "mode": metadata.get("mode", "dev"),
        "work_class": metadata.get("work_class", "story"),
    }
    return PublicPlaybook(
        path=resolved,
        frontmatter=frontmatter,
        body="",
        descriptor=data,
        source_format="workflow",
    )


def _resolve_playbook_path(path: Path) -> Path:
    if path.is_dir():
        candidate = path / PLAYBOOK_FILE
        if candidate.is_file():
            return candidate
        workflow = path / WORKFLOW_FILE
        if workflow.is_file():
            return workflow
    if path.is_file():
        return path
    raise PlaybookError(f"no {PLAYBOOK_FILE} or {WORKFLOW_FILE} at {path}")


def discover_playbooks(root: str | Path = ".") -> list[PublicPlaybook]:
    root_path = Path(root)
    if root_path.is_dir():
        candidates = sorted({*root_path.rglob(PLAYBOOK_FILE), *root_path.rglob(WORKFLOW_FILE)})
    else:
        candidates = [_resolve_playbook_path(root_path)]
    return [load_playbook(candidate) for candidate in candidates]


def resolve_playbook(ref: str | Path, *, root: str | Path = ".") -> PublicPlaybook:
    ref_path = Path(ref)
    if ref_path.exists() or str(ref).endswith(PLAYBOOK_FILE):
        return load_playbook(ref_path)
    ref_text = str(ref)
    if not SLUG_RE.match(ref_text):
        raise PlaybookError(f"playbook id {ref_text!r} is not a valid slug")
    matches = [
        candidate
        for candidate in sorted({*Path(root).rglob(PLAYBOOK_FILE), *Path(root).rglob(WORKFLOW_FILE)})
        if _candidate_id(candidate) == ref_text
    ]
    if not matches:
        raise PlaybookError(f"playbook {ref_text!r} not found under {root}")
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise PlaybookError(f"playbook id {ref_text!r} is ambiguous under {root}: {rendered}")
    return load_playbook(matches[0])


def _candidate_id(path: Path) -> str:
    if path.name == PLAYBOOK_FILE:
        return path.parent.name
    if path.name == WORKFLOW_FILE:
        return path.parent.name
    return path.stem


def dry_run_plan(playbook: PublicPlaybook) -> dict[str, Any]:
    descriptor = playbook.descriptor
    metadata = descriptor.get("metadata") if isinstance(descriptor.get("metadata"), dict) else {}
    return {
        "dry_run": True,
        "id": playbook.id,
        "title": descriptor["playbook"]["title"],
        "mode": metadata.get("mode", "dev"),
        "work_class": metadata.get("work_class", "story"),
        "status": descriptor["playbook"]["status"],
        "gates": descriptor["gates"],
        "stages": _step_plan(playbook),
        "descriptor": descriptor,
    }


def _step_plan(playbook: PublicPlaybook) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for stage in playbook.descriptor.get("stages", []):
        if not isinstance(stage, dict):
            continue
        command = stage.get("command")
        action = stage.get("action") or stage.get("description") or f"Run stage {stage.get('id')}"
        item: dict[str, Any] = {
            "id": stage["id"],
            "title": stage["title"],
            "action": action,
            "command": command if isinstance(command, str) and command.strip() else None,
            "expected_result": stage.get("expected_result"),
            "dispatch_target": stage.get("dispatch_target"),
            "gates": list(stage.get("gates") or []),
        }
        item["execution"] = "command" if item["command"] else "action"
        steps.append(item)
    return steps


def _step_execution(step: Mapping[str, Any]) -> StepExecution:
    command = step.get("command")
    return StepExecution(
        id=str(step["id"]),
        title=str(step["title"]),
        action=str(step.get("action") or ""),
        command=str(command) if isinstance(command, str) and command.strip() else None,
        expected_result=str(step["expected_result"]) if isinstance(step.get("expected_result"), str) else None,
    )


def _hook_check_command(command: str, cwd: Path, *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "ce": {
            "posture": "governed",
            "evidence_root": ".ce/state/playbook",
        },
    }
    argv = [
        sys.executable,
        "-m",
        "creator_engine_validator",
        "hook-check",
        "--stdin",
        "--format",
        "raw",
        "--posture",
        "governed",
        "--posture-root",
        str(cwd),
        "--evidence-root",
        ".ce/state/playbook",
    ]
    ledger_root = (env or os.environ).get("CE_LEDGER_ROOT")
    if ledger_root:
        argv.extend(["--ledger-root", ledger_root])
    completed = subprocess.run(
        argv,
        input=json.dumps(event),
        cwd=cwd,
        env=dict(os.environ, **dict(env or {})),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "decision": "deny",
            "reason": f"hook-check invocation failed: {completed.stderr.strip() or completed.stdout.strip()}",
        }
    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {"decision": "deny", "reason": f"hook-check returned invalid JSON: {exc}"}
    if not isinstance(payload, dict):
        return {"decision": "deny", "reason": "hook-check returned a non-object decision"}
    return payload


def default_step_executor(step: StepExecution, cwd: Path) -> StepExecution:
    if not step.command:
        return StepExecution(
            id=step.id,
            title=step.title,
            action=step.action,
            command=None,
            expected_result=step.expected_result,
            returncode=0,
            stdout="",
            stderr="action step acknowledged; no shell command declared",
        )
    decision = _hook_check_command(step.command, cwd)
    if decision.get("decision") == "deny":
        return StepExecution(
            id=step.id,
            title=step.title,
            action=step.action,
            command=step.command,
            expected_result=step.expected_result,
            returncode=GOVERNED_COMMAND_DENY_EXIT,
            stderr=str(decision.get("reason") or "governance denied command"),
            governance_decision=decision,
        )
    completed = subprocess.run(
        step.command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return StepExecution(
        id=step.id,
        title=step.title,
        action=step.action,
        command=step.command,
        expected_result=step.expected_result,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        governance_decision=decision,
    )


def run_playbook(
    playbook: PublicPlaybook,
    *,
    dry_run: bool = False,
    cwd: str | Path = ".",
    executor: StepExecutor | None = None,
) -> dict[str, Any]:
    plan = dry_run_plan(playbook)
    if dry_run:
        return {
            "ok": True,
            "action": "playbook_run_planned",
            "dry_run": True,
            "has_authority": False,
            "mode": plan["mode"],
            "work_class": plan["work_class"],
            "gates": plan["gates"],
            "stages": plan["stages"],
            "plan": plan,
        }

    runner = executor or default_step_executor
    results: list[dict[str, Any]] = []
    final_status = "PASS"
    run_cwd = Path(cwd)
    for step in plan["stages"]:
        execution = runner(_step_execution(step), run_cwd)
        status = "PASS" if execution.returncode == 0 else "FAIL"
        if status == "FAIL":
            final_status = "FAIL"
        results.append(
            {
                "id": execution.id,
                "title": execution.title,
                "status": status,
                "returncode": execution.returncode,
                "action": execution.action,
                "command": execution.command,
                "expected_result": execution.expected_result,
                "stdout": execution.stdout,
                "stderr": execution.stderr,
                "governance_decision": execution.governance_decision,
            }
        )
        if status == "FAIL":
            break
    return {
        "ok": final_status == "PASS",
        "action": "playbook_run_completed",
        "dry_run": False,
        "has_authority": True,
        "mode": plan["mode"],
        "work_class": plan["work_class"],
        "playbook": playbook.summary(),
        "steps": results,
        "final_status": final_status,
    }


def _emit_error(command: str, exc: PlaybookError, *, json_output: bool) -> int:
    payload = {
        "ok": False,
        "error": str(exc),
        "errors": [error.to_dict() for error in exc.errors],
    }
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ERROR: ce playbook {command} refused: {exc}", file=sys.stderr)
        for error in exc.errors:
            print(f"  {error.format()}", file=sys.stderr)
    return 1


def run_cli(args: Any) -> int:
    command = getattr(args, "playbook_cmd", None)
    root = getattr(args, "playbooks_root", ".")
    json_output = bool(getattr(args, "json_output", False))
    try:
        if command == "list":
            playbooks = discover_playbooks(root)
            payload = {"ok": True, "playbooks": [playbook.summary() for playbook in playbooks]}
            if json_output:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                for item in payload["playbooks"]:
                    print(
                        f"{item['id']}\t{item['title']}\t{item['mode']}\t"
                        f"{item['work_class']}\t{item['status']}"
                    )
            return 0
        if command == "show":
            playbook = resolve_playbook(getattr(args, "ref"), root=root)
            payload = {
                "ok": True,
                "playbook": playbook.summary(),
                "frontmatter": playbook.frontmatter,
                "descriptor": playbook.descriptor,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if command == "run":
            playbook = resolve_playbook(getattr(args, "ref"), root=root)
            payload = run_playbook(playbook, dry_run=bool(getattr(args, "dry_run", False)))
            if json_output:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                if payload["dry_run"]:
                    print(f"PLAN {playbook.id}: {payload['mode']} / {payload['work_class']}")
                    for step in payload["stages"]:
                        detail = step["command"] or step["action"]
                        print(f"STEP {step['id']}: {detail}")
                else:
                    for step in payload["steps"]:
                        print(f"STEP {step['id']}: {step['status']}")
                    print(f"RESULT: {payload['final_status']}")
            return 0 if payload["ok"] else 1
    except PlaybookError as exc:
        return _emit_error(str(command or "unknown"), exc, json_output=json_output)
    return 2
