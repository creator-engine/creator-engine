"""Gate 8 Integration Queue **dry-run** seam runtime (`ce queue dry-run` / `inspect`).

Implements RV1-082: a *local serialized landing preview only*. The Integration
Queue (Slice 6) owns serialized canonical-branch landing order across lanes; in
v1.0 it exists only as this dry-run preview, which:

* reconstructs a **deterministic, content-hashed** serialized landing order
  across lanes from **verified fan-in packet evidence** (the landed Gate 7
  ``fanin_runtime.inspect`` seam), not from lane self-report;
* carries **no authority** — ``has_authority`` is schema ``const false`` and
  ``mode`` is schema ``const dry-run``;
* refuses any live ``enqueue`` / ``land`` / ``merge`` action **fail-closed
  before any write**, leaving the output root byte-identical. No git / GitHub /
  PR / branch / remote / tracker / CI / deploy / provider / credential / package
  mutation is ever performed — the runtime only reads local evidence and runs a
  read-only ``git check-ignore`` on the output root;
* records CE-event / PCL / distributed-identity as **deferred-not-rejected**
  seam stubs, never as active integrations.

The preview body carries no wall-clock fields, so identical inputs serialize
byte-identically and the content-addressed filename ``{preview_id}-{hash}.json``
is stable (idempotent rebuild). This module reuses the shared deterministic
serialization, the ``schema.validate_with_schema`` helper, and the Gate 7
fan-in runtime; it never prints or stores secret values.

Prose contract: ``docs/operations/INTEGRATION_QUEUE_DRY_RUN.md``.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from . import fanin_runtime
from .git_worktree import find_enclosing_git_worktree
from .loader import LoaderError, load_yaml
from .schema import validate_with_schema

PREVIEW_KIND = "integration-queue-dry-run-preview"
REQUEST_KIND = "integration-queue-dry-run-request"
SCHEMA_VERSION = "1"
MODE = "dry-run"

# Live actions the dry-run seam refuses fail-closed — there is no live
# Integration Queue authority in v1.0.
LIVE_ACTIONS = ("enqueue", "land", "merge")

# Deferred-not-rejected seams recorded alongside every preview.
SEAM_DEFAULTS: dict[str, str] = {
    "ce_event": "CE-event signed-block protocol is a team-mode seam; not implemented in v1.0.",
    "pcl": "Project Coordination Ledger (PCL) is a team-mode seam; not implemented in v1.0.",
    "distributed_identity": "Distributed identity substrate is a post-v1 seam; not implemented in v1.0.",
}

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "integration-queue-dry-run.schema.yaml"
PROSE_CONTRACT = "docs/operations/INTEGRATION_QUEUE_DRY_RUN.md"

GitRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class QueueDryRunError(Exception):
    """Base class for Integration Queue dry-run errors. Carries a ``code``."""

    code = "G8-QUEUE-ERROR"


class QueueBuildError(QueueDryRunError):
    code = "G8-QUEUE-BUILD-ERROR"


class RequestError(QueueBuildError):
    code = "G8-QUEUE-REQUEST-ERROR"


class AuthorityRefused(QueueBuildError):
    code = "G8-QUEUE-AUTHORITY-REFUSED"


class MissingSourceRatification(QueueBuildError):
    code = "G8-QUEUE-MISSING-RATIFICATION"


class FaninEvidenceError(QueueBuildError):
    code = "G8-QUEUE-FANIN-EVIDENCE"


class LandingConflict(QueueBuildError):
    code = "G8-QUEUE-LANDING-CONFLICT"


class PreviewRootNotIgnored(QueueBuildError):
    code = "G8-QUEUE-PREVIEW-ROOT-NOT-IGNORED"


class QueueInspectError(QueueDryRunError):
    code = "G8-QUEUE-INSPECT-ERROR"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildResult:
    preview_path: Path
    content_hash: str
    preview: dict[str, Any]
    lane_count: int


@dataclass(frozen=True)
class InspectResult:
    ok: bool
    preview_path: Path
    content_hash: str
    preview: dict[str, Any]
    issues: tuple[str, ...]


# ---------------------------------------------------------------------------
# Canonical serialization + hashing (deterministic stdlib JSON; no wall-clock)
# ---------------------------------------------------------------------------


def _canonical_bytes(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _content_hash(payload_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload_without_hash).encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


# ---------------------------------------------------------------------------
# Read-only git-ignore guard (the output root must never reach the tracked tree)
# ---------------------------------------------------------------------------


def _default_git_runner(argv: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=False, capture_output=True, text=True)


def _detect_repo_root(path: Path) -> Path | None:
    return find_enclosing_git_worktree(path)


def _is_inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def _require_ignored_preview_root(preview_root: Path, repo_root: Path | None, runner: GitRunner) -> None:
    enclosing = repo_root if repo_root is not None else _detect_repo_root(preview_root)
    if enclosing is None or not _is_inside(preview_root, enclosing):
        return
    proc = runner(["git", "-C", str(enclosing), "check-ignore", "-q", "--", str(preview_root)])
    if proc.returncode != 0:
        raise PreviewRootNotIgnored(
            f"preview root {preview_root} is inside repo {enclosing} but is not git-ignored; "
            "integration-queue dry-run previews must live under an ignored path "
            "(e.g. .hermes/integration-queue/)"
        )


# ---------------------------------------------------------------------------
# Request parsing + serialized landing-order reconstruction
# ---------------------------------------------------------------------------


def _load_request(request: Path) -> dict[str, Any]:
    if not request.is_file():
        raise RequestError(f"integration-queue dry-run request not found: {request}")
    try:
        data = load_yaml(request)
    except LoaderError as exc:
        raise RequestError(f"integration-queue dry-run request is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise RequestError(f"integration-queue dry-run request at {request} is not a mapping")
    if data.get("kind") not in (REQUEST_KIND, None):
        raise RequestError(
            f"integration-queue dry-run request kind {data.get('kind')!r} != {REQUEST_KIND!r}"
        )
    return data


def _require_source_ratification(data: dict[str, Any]) -> dict[str, str]:
    ratification = data.get("source_ratification")
    if not isinstance(ratification, dict):
        raise MissingSourceRatification("request is missing a source_ratification mapping")
    prompt_ref = ratification.get("prompt_ref")
    sha256 = ratification.get("sha256")
    if not prompt_ref or not sha256:
        raise MissingSourceRatification(
            "source_ratification must carry both prompt_ref and sha256"
        )
    return {"prompt_ref": str(prompt_ref), "sha256": str(sha256)}


def _verify_fanin_packet(request: Path, packet_ref: str) -> str:
    """Verify a referenced fan-in packet (read-only) and return its content hash.

    Refuses (``FaninEvidenceError``) when the packet is missing, unreadable, or
    fails its own content-hash / shape check — the dry-run preview must rest on
    verified evidence, never lane self-report.
    """
    listed = Path(packet_ref)
    packet_path = listed if listed.is_absolute() else (request.parent / listed)
    try:
        result = fanin_runtime.inspect(packet=packet_path)
    except fanin_runtime.FaninInspectError as exc:
        raise FaninEvidenceError(
            f"referenced fan-in packet {packet_ref} is unreadable: {exc}"
        ) from exc
    if not result.ok:
        raise FaninEvidenceError(
            f"referenced fan-in packet {packet_ref} failed verification; refusing to preview "
            "landing over tampered/stale evidence: " + "; ".join(result.issues)
        )
    return result.content_hash


def _reconstruct_landing_order(request: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise RequestError("request must list at least one lanes entry")

    seen_orders: dict[int, str] = {}
    staged: list[tuple[int, str, str, str]] = []
    for raw in lanes:
        if not isinstance(raw, dict):
            raise RequestError("each lanes entry must be a mapping")
        lane_ref = raw.get("lane_ref")
        packet_ref = raw.get("fanin_packet_ref")
        declared_order = raw.get("declared_order")
        if not lane_ref:
            raise RequestError("lanes entry is missing lane_ref")
        if not packet_ref:
            raise RequestError(f"lanes entry {lane_ref} is missing fanin_packet_ref")
        if not isinstance(declared_order, int) or isinstance(declared_order, bool) or declared_order < 1:
            raise RequestError(f"lanes entry {lane_ref} declared_order must be an integer >= 1")
        if declared_order in seen_orders:
            raise LandingConflict(
                f"serialized landing requires a total order: declared_order {declared_order} is "
                f"claimed by both {seen_orders[declared_order]!r} and {lane_ref!r}"
            )
        seen_orders[declared_order] = str(lane_ref)
        content_hash = _verify_fanin_packet(request, str(packet_ref))
        staged.append((declared_order, str(lane_ref), str(packet_ref), content_hash))

    staged.sort(key=lambda item: (item[0], item[1]))
    return [
        {
            "position": position,
            "lane_ref": lane_ref,
            "fanin_packet_ref": packet_ref,
            "fanin_content_hash": content_hash,
        }
        for position, (_, lane_ref, packet_ref, content_hash) in enumerate(staged, start=1)
    ]


def _resolve_seam_stubs(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    requested = data.get("seam_stubs") if isinstance(data.get("seam_stubs"), dict) else {}
    stubs: dict[str, dict[str, str]] = {}
    for name, default_note in SEAM_DEFAULTS.items():
        entry = requested.get(name) if isinstance(requested.get(name), dict) else {}
        note = entry.get("note") if isinstance(entry.get("note"), str) and entry.get("note") else default_note
        stubs[name] = {"status": "deferred-not-rejected", "note": note}
    return stubs


# ---------------------------------------------------------------------------
# ce queue dry-run (build)
# ---------------------------------------------------------------------------


def build(
    *,
    request: Path | str,
    preview_root: Path | str,
    repo_root: Path | str | None = None,
    preview_id: str | None = None,
    live_action: str | None = None,
    git_runner: GitRunner | None = None,
) -> BuildResult:
    """Reconstruct a deterministic content-hashed serialized landing preview.

    Every refusal (live action, malformed request, missing ratification, tampered
    fan-in evidence, duplicate landing position, un-ignored root) raises **before
    any preview write**, leaving the output root byte-identical.
    """
    # 1. No authority — refuse any live enqueue/land/merge before reading.
    if live_action:
        raise AuthorityRefused(
            f"the Integration Queue dry-run seam carries no authority; refusing live action "
            f"{live_action!r} (live enqueue/land/merge is POST-V1 Slice 6 authority, "
            "ratified through the governed Source pathway)"
        )

    request = Path(request)
    preview_root = Path(preview_root)
    runner = git_runner or _default_git_runner

    # 2. Parse the request + require a Source-ratification reference.
    data = _load_request(request)
    ratification = _require_source_ratification(data)
    resolved_preview_id = preview_id or data.get("preview_id")
    if not resolved_preview_id:
        raise RequestError("request is missing preview_id (and none supplied)")

    # 3. The output root must be git-ignored when inside a repository.
    _require_ignored_preview_root(preview_root, Path(repo_root) if repo_root else None, runner)

    # 4. Reconstruct serialized landing order from verified fan-in evidence.
    landing_order = _reconstruct_landing_order(request, data)
    seam_stubs = _resolve_seam_stubs(data)

    # 5. Build the deterministic payload (no wall-clock fields) and content hash.
    payload: dict[str, Any] = {
        "kind": PREVIEW_KIND,
        "schema_version": SCHEMA_VERSION,
        "preview_id": str(resolved_preview_id),
        "mode": MODE,
        "has_authority": False,
        "source_ratification": ratification,
        "landing_order": landing_order,
        "seam_stubs": seam_stubs,
    }
    content_hash = _content_hash(payload)
    preview = {**payload, "content_hash": content_hash}

    # 6. Self-validate the produced preview against its schema before writing.
    schema_errors = validate_with_schema(
        preview, SCHEMA_PATH, "<integration-queue-dry-run-preview>", code="RV1-082", contract=PROSE_CONTRACT
    )
    if schema_errors:
        raise QueueBuildError(
            "internal: produced preview fails its own schema: "
            + "; ".join(err.format() for err in schema_errors)
        )

    # --- Side effects begin here (content-addressed preview under the root) ---
    preview_path = preview_root / f"{resolved_preview_id}-{content_hash}.json"
    _atomic_write(preview_path, _canonical_bytes(preview))

    return BuildResult(
        preview_path=preview_path,
        content_hash=content_hash,
        preview=preview,
        lane_count=len(landing_order),
    )


# ---------------------------------------------------------------------------
# ce queue inspect
# ---------------------------------------------------------------------------


def inspect(*, preview: Path | str) -> InspectResult:
    """Read an existing preview and verify its content hash + shape (read-only).

    Never mutates tracked files and grants no authority. Returns ``ok=False`` with
    populated ``issues`` for a schema or hash failure; raises only when the preview
    file itself cannot be read.
    """
    preview_path = Path(preview)
    if not preview_path.is_file():
        raise QueueInspectError(f"integration-queue dry-run preview not found: {preview_path}")
    try:
        data = json.loads(preview_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise QueueInspectError(f"integration-queue dry-run preview is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise QueueInspectError(f"integration-queue dry-run preview at {preview_path} is not a JSON object")

    issues: list[str] = []

    schema_errors = validate_with_schema(
        data, SCHEMA_PATH, str(preview_path), code="RV1-082", contract=PROSE_CONTRACT
    )
    issues.extend(err.message for err in schema_errors)

    payload = dict(data)
    stored_hash = payload.pop("content_hash", None)
    recomputed = _content_hash(payload)
    if stored_hash != recomputed:
        issues.append(
            f"content_hash mismatch: stored={stored_hash} recomputed={recomputed} "
            "(preview tampered or not canonically serialized)"
        )

    return InspectResult(
        ok=not issues,
        preview_path=preview_path,
        content_hash=recomputed,
        preview=data,
        issues=tuple(issues),
    )
