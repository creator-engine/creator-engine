"""Local-only, redaction-safe runtime for the ``ce checkpoint`` handoff verb.

The checkpoint is deliberately a *recording* primitive.  It consumes only the
facts document supplied by its caller; it never discovers controller state,
contacts a forge, or turns recorded evidence into authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import validate_with_schema

SCHEMA = "schemas/checkpoint-input.schema.yaml"
STATE_RELATIVE = Path(".ce/state/research")
FACT_SECTIONS = (
    "objective_and_boundary",
    "lanes_and_seats",
    "claims_and_territory",
    "heads_and_bases",
    "durable_paths_and_sha256s",
    "validation_review_and_gates",
    "blockers_and_awaiting_operator",
    "authority_boundaries_and_next_safe_act",
    "arc_rung_stamp",
)
_SECRET_KEY = re.compile(r"(?:secret|token|credential|password|private[_-]?key|api[_-]?key)", re.I)
_SECRET_VALUE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{8,}|github_pat_|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:token|password|secret)\s*[:=])", re.I)
_UNSAFE_KEY = re.compile(r"(?:transcript|raw[_-]?(?:log|output|transcript))", re.I)


class CheckpointError(ValueError):
    """A caller-supplied checkpoint contract is invalid or unsafe."""


@dataclass(frozen=True)
class CheckpointResult:
    path: Path
    sha256: str
    idempotent: bool
    complete: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "ce-checkpoint-result",
            "schema_version": 1,
            "status": "green",
            "complete": self.complete,
            "path": str(self.path),
            "sha256": self.sha256,
            "idempotent": self.idempotent,
            "clear": "not-claimed",
        }


def _read_document(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"facts document must be readable JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise CheckpointError("facts document must be a JSON object")
    return loaded


def _walk_safe(value: Any, *, trail: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CheckpointError(f"facts key at {trail} must be text")
            if _SECRET_KEY.search(key) or _UNSAFE_KEY.search(key):
                raise CheckpointError(f"unsafe secret or transcript-shaped field refused at {trail}.{key}")
            _walk_safe(child, trail=f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_safe(child, trail=f"{trail}[{index}]")
    elif isinstance(value, str) and _SECRET_VALUE.search(value):
        raise CheckpointError(f"secret-shaped value refused at {trail}")


def _validate(document: dict[str, Any], facts_path: Path) -> None:
    _walk_safe(document)
    errors = validate_with_schema(document, SCHEMA, facts_path, code="CE-CHECKPOINT-INPUT", contract=SCHEMA)
    if errors:
        raise CheckpointError("invalid checkpoint facts: " + "; ".join(error.message for error in errors))


def _timestamp(value: str | None) -> tuple[datetime, str]:
    if value is None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        if not value.endswith("Z"):
            raise CheckpointError("--as-of must be a UTC RFC3339 value ending in Z")
        try:
            now = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CheckpointError("--as-of must be a UTC RFC3339 timestamp") from exc
        if now.tzinfo is None or now.utcoffset() != timezone.utc.utcoffset(now):
            raise CheckpointError("--as-of must be UTC")
        now = now.replace(microsecond=0)
    rendered = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return now, rendered


def _fact_line(value: Mapping[str, Any]) -> str:
    return f"- [{value['label']}] {value['fact']} — source: {value['source']}"


def render(document: Mapping[str, Any], *, timestamp: str, prior_checkpoint: str | None, clean_boundary: str) -> str:
    """Render canonical resume Markdown from already validated supplied facts."""
    facts = document["facts"]
    delta: Sequence[Mapping[str, Any]] = document.get("delta", ())
    lines = [
        f"# Resume state — {timestamp}",
        "",
        f"Prior checkpoint: {prior_checkpoint or 'none'}",
        f"Boundary: {clean_boundary}",
        "",
        "## Delta",
        *(_fact_line(item) for item in delta),
        "",
        "## Work state",
        f"- Objective: {facts['objective_and_boundary']['fact']}",
        f"- Lanes and seats: {facts['lanes_and_seats']['fact']}",
        f"- Claims and territory: {facts['claims_and_territory']['fact']}",
        f"- Heads and bases: {facts['heads_and_bases']['fact']}",
        "",
        "## Evidence and decisions",
        f"- Durable paths and SHA-256s: {facts['durable_paths_and_sha256s']['fact']}",
        f"- Validation, review, and gates: {facts['validation_review_and_gates']['fact']}",
        f"- Blockers and AWAITING-OPERATOR: {facts['blockers_and_awaiting_operator']['fact']}",
        f"- Authority boundaries: {facts['authority_boundaries_and_next_safe_act']['fact']}",
        f"- Arc/rung stamp: {facts['arc_rung_stamp']['fact']}",
        "",
        "## Resume",
        f"Next safe act: {document['next_safe_act']}",
        "Named durable sources to reload:",
        *(f"- {path}" for path in document["reload_sources"]),
        "",
    ]
    return "\n".join(lines)


def _safe_target(repo_root: Path, timestamp: str) -> Path:
    root = repo_root.resolve()
    state_root = (root / STATE_RELATIVE).resolve()
    if state_root != root / STATE_RELATIVE or not state_root.is_relative_to(root):
        raise CheckpointError("checkpoint state root is unsafe")
    target = state_root / f"RESUME_STATE_{timestamp.replace(':', '').replace('-', '')}.md"
    if not target.is_relative_to(state_root):  # defensive for future naming changes
        raise CheckpointError("checkpoint target escapes the local research root")
    return target


def _ensure_untracked(repo_root: Path, target: Path) -> None:
    """Reject a tracked target without consulting any controller runtime state."""
    git_index = repo_root / ".git"
    if not git_index.exists():
        raise CheckpointError("repo root must be a Git worktree")
    # A tracked resume record is an unsafe authority-looking artifact.  Reading
    # the local index is narrowly scoped to target safety, not state discovery.
    import subprocess
    relative = target.relative_to(repo_root).as_posix()
    result = subprocess.run(["git", "ls-files", "--error-unmatch", "--", relative], cwd=repo_root, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        raise CheckpointError("checkpoint target is tracked; refusing to write")


def create_checkpoint(
    *, repo_root: str | Path, facts_path: str | Path, prior_checkpoint: str | None = None,
    clean_boundary: str, as_of: str | None = None,
) -> CheckpointResult:
    """Validate, render and atomically persist an owner-only local checkpoint."""
    root = Path(repo_root).resolve()
    source = Path(facts_path).resolve()
    document = _read_document(source)
    _validate(document, source)
    if not clean_boundary or not clean_boundary.strip():
        raise CheckpointError("clean boundary description is required")
    if prior_checkpoint is not None and not prior_checkpoint.strip():
        raise CheckpointError("prior checkpoint must be a path or omitted")
    _now, timestamp = _timestamp(as_of)
    target = _safe_target(root, timestamp)
    _ensure_untracked(root, target)
    payload = render(document, timestamp=timestamp, prior_checkpoint=prior_checkpoint, clean_boundary=clean_boundary.strip()).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        current = target.read_bytes()
        if current == payload:
            if target.stat().st_mode & 0o077:
                raise CheckpointError("existing checkpoint is not owner-only")
            return CheckpointResult(target, digest, idempotent=True)
        raise CheckpointError("checkpoint collision: existing target contains different bytes")
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return CheckpointResult(target, digest, idempotent=False)
