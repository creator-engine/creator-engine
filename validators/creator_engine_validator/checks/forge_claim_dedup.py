"""Forge-claim + dedup validation (v3.5-C A-C4 — design §A.4).

Validates **forge-projected claim records** (`kind: forge-claim`) against
`schemas/forge-claim.schema.yaml` plus the governance invariants:

- **Idempotency key integrity:** the record's `idempotency_key` MUST equal
  the SHA256 over the canonical `(repo, item_id, claimant_instance,
  lease_window)` tuple — a retry inside the lease window is the SAME claim.
  The derivation is RE-IMPLEMENTED here (`shared` check; the v3
  `forge.backlog` twin is drift-guarded by the unit tests, which may import
  both).
- **Escalation, never silent overwrite:** a second live claimant on a held
  item surfaces as an **escalation** (`contention.surfaced_as: escalation`,
  with the earlier-`claimed_at`-wins winner as a *proposal*). A record
  claiming `silent-overwrite` — or a `contended` status with no contention
  block — is rejected.
- **Deterministic dedup:** a dedup link binds only on deterministic
  evidence — an `embedding_similarity` entry with `score >= threshold` and a
  pinned `model_ref` suffices; `title_token_overlap` + `cross_reference` are
  additive corroboration (sufficient TOGETHER, not alone). A dedup proposal
  without that bar is rejected.

**Advisory-lock honesty:** nothing here (or in `forge.backlog`) is a hard
lock — assignee + Status are advisory and two seats can interleave between
read and write (claim-side TOCTOU, §11.1). This check guarantees the RECORD
cannot misrepresent a collision as resolved; it cannot prevent the collision.

This is a **shared** check: it imports only the shared engine; it MUST NOT
import the v3 `forge.backlog` module (the `version_boundary` CODE_UNALLOWED
ratchet) — hence the re-implemented key derivation.

See:
  - `docs/contracts/forge-claim.md`
  - `schemas/forge-claim.schema.yaml`
  - `creator_engine_validator/forge/backlog.py` (the live projection adapter)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "forge_claim_dedup"
CONTRACT = "docs/contracts/forge-claim.md"
SCHEMA = "schemas/forge-claim.schema.yaml"
KIND_VALUE = "forge-claim"

# Failure codes (explicit error classes).
CODE_SCHEMA = "VAL-FC-SCHEMA"
CODE_INVALID = "VAL-FC-INVALID"
CODE_IDEMPOTENCY = "VAL-FC-IDEMPOTENCY"
CODE_SILENT_OVERWRITE = "VAL-FC-SILENT-OVERWRITE"
CODE_DEDUP_NONDETERMINISTIC = "VAL-FC-DEDUP-NONDETERMINISTIC"


def derive_idempotency_key(
    repo: str, item_id: str, claimant_instance: str, lease_window: str
) -> str:
    """The canonical claim idempotency key (re-implemented; see module doc)."""
    canon = "\n".join((repo, item_id, claimant_instance, lease_window)) + "\n"
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def iter_claim_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate forge-claim files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p) and not _is_under_excluded(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if isinstance(data, dict) and data.get("kind") == KIND_VALUE:
                seen.add(resolved)
                records.append(candidate)
    return records


def _check_idempotency_key(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """The recorded key must equal the canonical derivation over the claim tuple."""
    parts = (
        record.get("repo"), record.get("item_id"),
        record.get("claimant_instance"), record.get("lease_window"),
    )
    if not all(isinstance(p, str) and p for p in parts):
        return []  # the schema already rejects the missing tuple members
    expected = derive_idempotency_key(*parts)  # type: ignore[arg-type]
    actual = record.get("idempotency_key")
    if actual == expected:
        return []
    return [make_error(
        CODE_IDEMPOTENCY, path, "idempotency_key",
        "idempotency_key does not equal the canonical SHA256 over "
        "(repo, item_id, claimant_instance, lease_window); a retry in the "
        "lease window must be the SAME claim",
        CONTRACT,
    )]


def _check_contention(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """A collision surfaces as an escalation — never a silent overwrite."""
    errors: list[ValidationError] = []
    contention = record.get("contention")
    if record.get("status") == "contended" and not isinstance(contention, dict):
        errors.append(make_error(
            CODE_SILENT_OVERWRITE, path, "contention",
            "status: contended requires the contention block (the observed "
            "competing claimant(s) surfaced as an escalation)",
            CONTRACT,
        ))
    if isinstance(contention, dict) and contention.get("surfaced_as") != "escalation":
        errors.append(make_error(
            CODE_SILENT_OVERWRITE, path, "contention/surfaced_as",
            f"a second claimant on a held item surfaces as an ESCALATION, never "
            f"{contention.get('surfaced_as')!r}; the advisory lock has no "
            "overwrite semantics",
            CONTRACT,
        ))
    return errors


def _deterministic_dedup_evidence(evidence: list[Any]) -> bool:
    """The deterministic-evidence bar (design §A.4, gitcrawl semantics).

    Sufficient: an embedding-similarity measurement at/over its pinned
    threshold with a pinned model; OR shared-title-token overlap PLUS a
    cross-reference (additive corroboration — neither suffices alone).
    """
    has_overlap = False
    has_crossref = False
    for entry in evidence:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        if kind == "embedding_similarity":
            score, threshold = entry.get("score"), entry.get("threshold")
            if (
                isinstance(score, (int, float)) and isinstance(threshold, (int, float))
                and not isinstance(score, bool) and not isinstance(threshold, bool)
                and score >= threshold
                and isinstance(entry.get("model_ref"), str) and entry.get("model_ref")
            ):
                return True
        elif kind == "title_token_overlap":
            tokens = entry.get("shared_tokens")
            if isinstance(tokens, list) and tokens:
                has_overlap = True
        elif kind == "cross_reference":
            if isinstance(entry.get("ref"), str) and entry.get("ref"):
                has_crossref = True
    return has_overlap and has_crossref


def _check_dedup(record: dict[str, Any], path: Path) -> list[ValidationError]:
    dedup = record.get("dedup")
    if not isinstance(dedup, dict):
        return []
    evidence = dedup.get("evidence")
    if isinstance(evidence, list) and _deterministic_dedup_evidence(evidence):
        return []
    return [make_error(
        CODE_DEDUP_NONDETERMINISTIC, path, "dedup/evidence",
        "a dedup link requires deterministic evidence: embedding similarity at/"
        "over its pinned threshold with a pinned model, or title-token overlap "
        "PLUS a cross-reference (additive corroboration); this proposal carries "
        "neither",
        CONTRACT,
    )]


def validate_claim(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one forge-claim record against the schema + invariants."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_idempotency_key(record, path))
    errors.extend(_check_contention(record, path))
    errors.extend(_check_dedup(record, path))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_IDEMPOTENCY, CODE_SILENT_OVERWRITE,
     CODE_DEDUP_NONDETERMINISTIC],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_claim_records([Path(p) for p in paths]):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(validate_claim(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
