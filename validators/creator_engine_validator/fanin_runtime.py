"""Gate 7 local read-only evidence fan-in runtime (`ce fanin build` / `inspect`).

Implements the runtime named in the v1.0 traceability matrix:

* ``RV1-070`` — ``ce fanin build`` produces a **deterministic, content-hashed**
  packet under the ignored ``.hermes/fan-in/`` root, aggregating evidence
  manifests + Side-Effect Ledger references; ``ce fanin inspect`` reads it back.
  The packet is authored as deterministic stdlib ``json`` bytes (no wall-clock
  fields), so identical inputs yield byte-identical, content-addressed output.
* ``RV1-071`` — the fan-in packet carries **no authority**. Any ratify / enqueue
  / land attempt is refused; stale evidence (a manifest whose own SHA drifted
  from its ratified pin), a missing Source-ratification ref, and an evidence
  entry SHA mismatch are refused **fail-closed before any write**. The runtime
  performs NO git/GitHub/tracker/CI/deploy/provider mutation — it only reads
  local evidence and runs a read-only ``git check-ignore`` on the output root.

This module reuses the already-landed Side-Effect Ledger runtime
(``side_effect_ledger_runtime.verify``) for ledger references and the shared
``schema.validate_with_schema`` helper for packet-shape validation. It never
prints or stores secret values.

Prose contract: ``docs/operations/EVIDENCE_FAN_IN_PROTOCOL.md``.
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

from . import side_effect_ledger_runtime
from .git_worktree import find_enclosing_git_worktree
from .loader import LoaderError, load_yaml
from .schema import validate_with_schema

PACKET_KIND = "evidence-fan-in-packet"
REQUEST_KIND = "evidence-fan-in-request"
SCHEMA_VERSION = "1"

# The packet schema lives at the repo root, resolved package-relatively so that
# ``inspect`` works regardless of the caller's working directory.
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "evidence-fan-in-packet.schema.yaml"
PROSE_CONTRACT = "docs/operations/EVIDENCE_FAN_IN_PROTOCOL.md"

GitRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FaninError(Exception):
    """Base class for fan-in runtime errors. Carries a ``code``."""

    code = "G7-FANIN-ERROR"


class FaninBuildError(FaninError):
    code = "G7-BUILD-ERROR"


class RequestError(FaninBuildError):
    code = "G7-REQUEST-ERROR"


class AuthorityRefused(FaninBuildError):
    code = "G7-AUTHORITY-REFUSED"


class MissingSourceRatification(FaninBuildError):
    code = "G7-MISSING-RATIFICATION"


class StaleEvidence(FaninBuildError):
    code = "G7-STALE-EVIDENCE"


class EvidenceShaMismatch(FaninBuildError):
    code = "G7-SHA-MISMATCH"


class LedgerEvidenceError(FaninBuildError):
    code = "G7-LEDGER-EVIDENCE"


class PacketRootNotIgnored(FaninBuildError):
    code = "G7-PACKET-ROOT-NOT-IGNORED"


class FaninInspectError(FaninError):
    code = "G7-INSPECT-ERROR"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildResult:
    packet_path: Path
    content_hash: str
    packet: dict[str, Any]
    evidence_count: int
    ledger_chain_count: int


@dataclass(frozen=True)
class InspectResult:
    ok: bool
    packet_path: Path
    content_hash: str
    packet: dict[str, Any]
    issues: tuple[str, ...]


# ---------------------------------------------------------------------------
# Canonical serialization + hashing (deterministic stdlib JSON)
# ---------------------------------------------------------------------------


def _canonical_bytes(obj: Any) -> str:
    """Deterministic packet serialization: sorted keys, newline-terminated."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _content_hash(payload_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload_without_hash).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _require_ignored_packet_root(packet_root: Path, repo_root: Path | None, runner: GitRunner) -> None:
    enclosing = repo_root if repo_root is not None else _detect_repo_root(packet_root)
    if enclosing is None or not _is_inside(packet_root, enclosing):
        return
    proc = runner(["git", "-C", str(enclosing), "check-ignore", "-q", "--", str(packet_root)])
    if proc.returncode != 0:
        raise PacketRootNotIgnored(
            f"packet root {packet_root} is inside repo {enclosing} but is not git-ignored; "
            "fan-in packets must live under an ignored path (e.g. .hermes/fan-in/)"
        )


# ---------------------------------------------------------------------------
# Request parsing + evidence aggregation
# ---------------------------------------------------------------------------


def _load_request(request: Path) -> dict[str, Any]:
    if not request.is_file():
        raise RequestError(f"fan-in request not found: {request}")
    try:
        data = load_yaml(request)
    except LoaderError as exc:
        raise RequestError(f"fan-in request is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise RequestError(f"fan-in request at {request} is not a mapping")
    if data.get("kind") not in (REQUEST_KIND, None):
        raise RequestError(
            f"fan-in request kind {data.get('kind')!r} != {REQUEST_KIND!r}"
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


def _parse_manifest_entries(manifest_path: Path) -> list[dict[str, str]]:
    """Parse a ``sha256sum``-style manifest into sorted {path, sha256} entries."""
    entries: list[dict[str, str]] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise EvidenceShaMismatch(f"malformed manifest line in {manifest_path}: {raw!r}")
        sha, path_token = parts[0], parts[1].lstrip("*").strip()
        entries.append({"path": path_token, "sha256": sha})
    return sorted(entries, key=lambda item: item["path"])


def _verify_entry(manifest_path: Path, entry: dict[str, str]) -> None:
    listed = Path(entry["path"])
    resolved = listed if listed.is_absolute() else (manifest_path.parent / listed)
    if not resolved.is_file():
        raise EvidenceShaMismatch(
            f"evidence file referenced by {manifest_path} is missing: {entry['path']}"
        )
    actual = _sha256_file(resolved)
    if actual != entry["sha256"]:
        raise EvidenceShaMismatch(
            f"evidence SHA mismatch for {entry['path']}: manifest={entry['sha256']} actual={actual}"
        )


def _aggregate_evidence(request: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    manifests = data.get("evidence_manifests")
    if not isinstance(manifests, list) or not manifests:
        raise RequestError("request must list at least one evidence_manifests entry")

    evidence: list[dict[str, Any]] = []
    for raw in manifests:
        if not isinstance(raw, dict):
            raise RequestError("each evidence_manifests entry must be a mapping")
        manifest_ref = raw.get("manifest_ref")
        pinned_sha = raw.get("manifest_sha256")
        if not manifest_ref:
            raise RequestError("evidence_manifests entry is missing manifest_ref")
        if not pinned_sha:
            raise RequestError(f"evidence_manifests entry {manifest_ref} is missing manifest_sha256")

        listed = Path(manifest_ref)
        manifest_path = listed if listed.is_absolute() else (request.parent / listed)
        if not manifest_path.is_file():
            raise StaleEvidence(f"evidence manifest not found: {manifest_ref}")

        actual_sha = _sha256_file(manifest_path)
        if actual_sha != pinned_sha:
            raise StaleEvidence(
                f"stale evidence manifest {manifest_ref}: pinned={pinned_sha} actual={actual_sha} "
                "(manifest changed since Source ratification)"
            )

        entries = _parse_manifest_entries(manifest_path)
        for entry in entries:
            _verify_entry(manifest_path, entry)

        evidence.append(
            {
                "manifest_ref": str(manifest_ref),
                "manifest_sha256": str(pinned_sha),
                "entry_count": len(entries),
                "entries": entries,
            }
        )
    return sorted(evidence, key=lambda item: item["manifest_ref"])


def _aggregate_ledger(data: dict[str, Any]) -> dict[str, Any]:
    section = data.get("side_effect_ledger")
    if not isinstance(section, dict) or not section.get("root_ref"):
        return {"root_ref": None, "verified": False, "chains": []}

    root_ref = str(section["root_ref"])
    result = side_effect_ledger_runtime.verify(side_effect_ledger_root=root_ref)
    if not result.ok:
        raise LedgerEvidenceError(
            "referenced Side-Effect Ledger fails verification; refusing to aggregate tampered "
            "evidence: " + "; ".join(result.errors)
        )
    chains = [
        {
            "controller_id": chain["controller_id"],
            "lane_id": chain["lane_id"],
            "record_count": chain["record_count"],
            "head_sha256": chain["head_sha256"],
            "last_record_ref": chain["last_record_ref"],
        }
        for chain in result.summary["chains"]
    ]
    return {"root_ref": root_ref, "verified": True, "chains": chains}


# ---------------------------------------------------------------------------
# ce fanin build
# ---------------------------------------------------------------------------


def build(
    *,
    request: Path | str,
    packet_root: Path | str,
    repo_root: Path | str | None = None,
    packet_id: str | None = None,
    authority_action: str | None = None,
    git_runner: GitRunner | None = None,
) -> BuildResult:
    """Aggregate local evidence into a deterministic content-hashed fan-in packet.

    Every refusal (authority attempt, malformed request, missing ratification,
    stale evidence, entry SHA mismatch, tampered ledger, un-ignored root) raises
    **before any packet write**, leaving the fan-in root byte-identical.
    """
    # 1. No authority — refuse any ratify/enqueue/land attempt before reading.
    if authority_action:
        raise AuthorityRefused(
            f"fan-in packets carry no authority; refusing action {authority_action!r} "
            "(ratify/enqueue/land must happen through the governed Source pathway)"
        )

    request = Path(request)
    packet_root = Path(packet_root)
    runner = git_runner or _default_git_runner

    # 2. Parse the request + require a Source-ratification reference.
    data = _load_request(request)
    ratification = _require_source_ratification(data)
    resolved_packet_id = packet_id or data.get("packet_id")
    if not resolved_packet_id:
        raise RequestError("request is missing packet_id (and none supplied)")

    # 3. The output root must be git-ignored when inside a repository.
    _require_ignored_packet_root(packet_root, Path(repo_root) if repo_root else None, runner)

    # 4. Aggregate evidence (refuses stale / SHA-mismatch) and ledger refs.
    evidence = _aggregate_evidence(request, data)
    ledger = _aggregate_ledger(data)

    # 5. Build the deterministic payload (no wall-clock fields) and content hash.
    payload: dict[str, Any] = {
        "kind": PACKET_KIND,
        "schema_version": SCHEMA_VERSION,
        "packet_id": str(resolved_packet_id),
        "has_authority": False,
        "source_ratification": ratification,
        "evidence": evidence,
        "side_effect_ledger": ledger,
    }
    content_hash = _content_hash(payload)
    packet = {**payload, "content_hash": content_hash}

    # 6. Self-validate the produced packet against its schema before writing.
    schema_errors = validate_with_schema(
        packet, SCHEMA_PATH, "<fanin-packet>", code="RV1-070", contract=PROSE_CONTRACT
    )
    if schema_errors:
        raise FaninBuildError(
            "internal: produced packet fails its own schema: "
            + "; ".join(err.format() for err in schema_errors)
        )

    # --- Side effects begin here (content-addressed packet under the root) ---
    packet_path = packet_root / f"{resolved_packet_id}-{content_hash}.json"
    _atomic_write(packet_path, _canonical_bytes(packet))

    return BuildResult(
        packet_path=packet_path,
        content_hash=content_hash,
        packet=packet,
        evidence_count=len(evidence),
        ledger_chain_count=len(ledger["chains"]),
    )


# ---------------------------------------------------------------------------
# ce fanin inspect
# ---------------------------------------------------------------------------


def inspect(*, packet: Path | str) -> InspectResult:
    """Read an existing packet and verify its content hash + shape (read-only).

    Never mutates tracked files and grants no authority. Returns ``ok=False``
    with populated ``issues`` for a schema or hash failure; raises only when the
    packet file itself cannot be read.
    """
    packet_path = Path(packet)
    if not packet_path.is_file():
        raise FaninInspectError(f"fan-in packet not found: {packet_path}")
    try:
        data = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FaninInspectError(f"fan-in packet is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise FaninInspectError(f"fan-in packet at {packet_path} is not a JSON object")

    issues: list[str] = []

    # Shape: validate against the packet schema.
    schema_errors = validate_with_schema(
        data, SCHEMA_PATH, str(packet_path), code="RV1-070", contract=PROSE_CONTRACT
    )
    issues.extend(err.message for err in schema_errors)

    # Deterministic content hash: recompute over the payload sans content_hash.
    payload = dict(data)
    stored_hash = payload.pop("content_hash", None)
    recomputed = _content_hash(payload)
    if stored_hash != recomputed:
        issues.append(
            f"content_hash mismatch: stored={stored_hash} recomputed={recomputed} "
            "(packet tampered or not canonically serialized)"
        )

    return InspectResult(
        ok=not issues,
        packet_path=packet_path,
        content_hash=recomputed,
        packet=data,
        issues=tuple(issues),
    )
