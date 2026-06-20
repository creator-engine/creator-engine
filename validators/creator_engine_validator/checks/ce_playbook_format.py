"""CE playbook library scaffold validator (ce-ops#145).

The playbook format is intentionally repo-native: each playbook is a directory
under ``playbooks/`` with human docs, a machine-checkable ``workflow.ce.yml``,
briefs referenced by stage id, an authority envelope template, and a harness
contract. This check validates the file scaffold, schema, stage brief
references, folder/name binding, and top-level index coverage.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "ce_playbook_format"
CONTRACT = "docs/contracts/playbook-format.md"
SCHEMA_PATH = "schemas/playbook.schema.yaml"

CODE_REQUIRED_FILE = "VAL-PLAYBOOK-REQUIRED-FILE"
CODE_SCHEMA = "VAL-PLAYBOOK-SCHEMA"
CODE_NAME = "VAL-PLAYBOOK-NAME"
CODE_BRIEF_REF = "VAL-PLAYBOOK-BRIEF"
CODE_INDEX = "VAL-PLAYBOOK-INDEX"

REQUIRED_FILES = ("README.md", "workflow.ce.yml", "envelope.template.yml", "harness.md")
PLAYBOOKS_DIRNAME = "playbooks"
WORKFLOW_FILE = "workflow.ce.yml"

_INDEX_LINK_PATTERNS = (
    r"\[[^\]]*{name}[^\]]*\]\((?:\./)?{name}/(?:README\.md)?\)",
    r"\bplaybooks/{name}/\b",
)


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _is_playbook_dir(path: Path) -> bool:
    return path.is_dir() and (path / WORKFLOW_FILE).is_file()


def _playbook_dirs_under(playbooks_root: Path) -> list[Path]:
    if not playbooks_root.is_dir():
        return []
    return sorted(
        child
        for child in playbooks_root.iterdir()
        if child.is_dir() and not child.name.startswith(".") and not _is_tmp_artifact(child)
    )


def _discover_playbook_dirs(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        candidates: list[Path] = []
        if _is_playbook_dir(path):
            candidates = [path]
        elif path.is_file() and path.name == WORKFLOW_FILE:
            candidates = [path.parent]
        elif path.is_dir() and path.name == PLAYBOOKS_DIRNAME:
            candidates = _playbook_dirs_under(path)
        elif path.is_dir() and (path / PLAYBOOKS_DIRNAME).is_dir():
            candidates = _playbook_dirs_under(path / PLAYBOOKS_DIRNAME)
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _pointer(parts: Iterable[str | int]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _load_workflow(path: Path) -> tuple[Any | None, list[ValidationError]]:
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return None, [make_error(CODE_SCHEMA, path, "", str(exc), SCHEMA_PATH)]
    errors = validate_with_schema(data, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=CONTRACT)
    return data, errors


def _validate_required_files(playbook_dir: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for rel in REQUIRED_FILES:
        p = playbook_dir / rel
        if not p.is_file():
            errors.append(
                make_error(
                    CODE_REQUIRED_FILE,
                    p,
                    "",
                    f"playbook {playbook_dir.name!r} must include {rel}",
                    CONTRACT,
                )
            )
    briefs = playbook_dir / "briefs"
    if not briefs.is_dir():
        errors.append(
            make_error(
                CODE_REQUIRED_FILE,
                briefs,
                "",
                f"playbook {playbook_dir.name!r} must include a briefs/ directory",
                CONTRACT,
            )
        )
    return errors


def _validate_workflow_semantics(playbook_dir: Path, data: Any) -> list[ValidationError]:
    if not isinstance(data, dict):
        return []
    errors: list[ValidationError] = []
    playbook = data.get("playbook")
    if isinstance(playbook, dict):
        name = playbook.get("name")
        if name != playbook_dir.name:
            errors.append(
                make_error(
                    CODE_NAME,
                    playbook_dir / WORKFLOW_FILE,
                    _pointer(("playbook", "name")),
                    f"playbook.name must match folder name {playbook_dir.name!r}",
                    CONTRACT,
                )
            )

    dispatch = data.get("dispatch")
    if isinstance(dispatch, dict) and dispatch.get("authority_envelope") != "envelope.template.yml":
        errors.append(
            make_error(
                CODE_REQUIRED_FILE,
                playbook_dir / WORKFLOW_FILE,
                _pointer(("dispatch", "authority_envelope")),
                "dispatch.authority_envelope must reference envelope.template.yml",
                CONTRACT,
            )
        )

    gates = data.get("gates")
    gate_ids = {gate.get("id") for gate in gates if isinstance(gate, dict)} if isinstance(gates, list) else set()
    stages = data.get("stages")
    if not isinstance(stages, list):
        return errors
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        stage_id = stage.get("id")
        brief = stage.get("brief")
        if isinstance(brief, str):
            brief_path = Path(brief)
            if (
                brief_path.is_absolute()
                or len(brief_path.parts) != 2
                or brief_path.parts[0] != "briefs"
                or brief_path.suffix != ".md"
            ):
                errors.append(
                    make_error(
                        CODE_BRIEF_REF,
                        playbook_dir / WORKFLOW_FILE,
                        _pointer(("stages", index, "brief")),
                        "stage brief must be a relative briefs/<stage>.md path",
                        CONTRACT,
                    )
                )
            elif isinstance(stage_id, str) and brief != f"briefs/{stage_id}.md":
                expected = f"briefs/{stage_id}.md"
                errors.append(
                    make_error(
                        CODE_BRIEF_REF,
                        playbook_dir / WORKFLOW_FILE,
                        _pointer(("stages", index, "brief")),
                        f"stage {stage_id!r} brief must be {expected}; got {brief}",
                        CONTRACT,
                    )
                )
            elif not (playbook_dir / brief_path).is_file():
                errors.append(
                    make_error(
                        CODE_BRIEF_REF,
                        playbook_dir / brief,
                        "",
                        f"stage {stage.get('id', index)!r} references a missing brief",
                        CONTRACT,
                    )
                )
        stage_gate_refs = stage.get("gates")
        if isinstance(stage_gate_refs, list):
            for gate_index, gate_ref in enumerate(stage_gate_refs):
                if gate_ref not in gate_ids:
                    errors.append(
                        make_error(
                            CODE_SCHEMA,
                            playbook_dir / WORKFLOW_FILE,
                            _pointer(("stages", index, "gates", gate_index)),
                            f"stage gate {gate_ref!r} is not declared in gates[]",
                            CONTRACT,
                        )
                    )
    return errors


def _index_mentions_playbook(index_text: str, name: str) -> bool:
    escaped = re.escape(name)
    return any(re.search(pattern.format(name=escaped), index_text) for pattern in _INDEX_LINK_PATTERNS)


def _validate_index(playbooks_root: Path, playbook_dirs: list[Path]) -> list[ValidationError]:
    index_path = playbooks_root / "README.md"
    if not index_path.is_file():
        return [
            make_error(
                CODE_INDEX,
                index_path,
                "",
                "playbooks/README.md must index every playbook directory",
                CONTRACT,
            )
        ]
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [make_error(CODE_INDEX, index_path, "", f"failed to read index: {exc}", CONTRACT)]
    errors: list[ValidationError] = []
    for playbook_dir in playbook_dirs:
        if not _index_mentions_playbook(text, playbook_dir.name):
            errors.append(
                make_error(
                    CODE_INDEX,
                    index_path,
                    "",
                    f"playbooks/README.md must list playbook {playbook_dir.name!r}",
                    CONTRACT,
                )
            )
    return errors


def validate_playbook_dir(playbook_dir: Path) -> list[ValidationError]:
    errors = _validate_required_files(playbook_dir)
    workflow_path = playbook_dir / WORKFLOW_FILE
    if workflow_path.is_file():
        data, workflow_errors = _load_workflow(workflow_path)
        errors.extend(workflow_errors)
        errors.extend(_validate_workflow_semantics(playbook_dir, data))
    return errors


@register(
    CHECK_NAME,
    [CODE_REQUIRED_FILE, CODE_SCHEMA, CODE_NAME, CODE_BRIEF_REF, CODE_INDEX],
)
def run(paths: Iterable[Path]) -> CheckResult:
    playbook_dirs = _discover_playbook_dirs(paths)
    errors: list[ValidationError] = []
    for playbook_dir in playbook_dirs:
        errors.extend(validate_playbook_dir(playbook_dir))

    by_root: dict[Path, list[Path]] = {}
    for playbook_dir in playbook_dirs:
        by_root.setdefault(playbook_dir.parent, []).append(playbook_dir)
    for playbooks_root, dirs in by_root.items():
        errors.extend(_validate_index(playbooks_root, dirs))

    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
