"""Read-only press-merge evidence bundle assembler.

The bundle produced here is data-only. It never approves, merges, enqueues,
updates PR state, writes refs, or treats its derived summary as authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from ..checks.path_manifest_fidelity import branch_slug, parse_carrier

KIND: Final[str] = "ce-press-merge-evidence-bundle"
SCHEMA_VERSION: Final[str] = "1"
ASSEMBLER_VERSION: Final[str] = "1"

STALE_CURRENT: Final[str] = "current"
STALE_STALE: Final[str] = "stale"
STALE_UNKNOWN: Final[str] = "unknown"


@dataclass(frozen=True)
class SourceProvenance:
    """Named source metadata for a bundle field or section."""

    name: str
    type: str
    artifact_name: str | None = None
    file_path: str | None = None
    file_line_range: str | None = None
    artifact_sha256: str | None = None
    run_id: str | None = None
    run_attempt: str | None = None
    created_at: str | None = None
    head_sha: str | None = None
    repo_sha: str | None = None
    producer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "artifact_name": self.artifact_name,
            "file_path": self.file_path,
            "file_line_range": self.file_line_range,
            "artifact_sha256": self.artifact_sha256,
            "run_id": self.run_id,
            "run_attempt": self.run_attempt,
            "created_at": self.created_at,
            "head_sha": self.head_sha,
            "repo_sha": self.repo_sha,
            "producer": self.producer,
        }


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return stable JSON bytes: sorted keys, compact separators, newline."""

    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def canonical_json_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def head_staleness_status(valid_for_head_sha: str, current_head_sha_observed: str | None) -> str:
    """Classify whether a bundle minted for one head is still current."""

    if not current_head_sha_observed:
        return STALE_UNKNOWN
    return STALE_CURRENT if current_head_sha_observed == valid_for_head_sha else STALE_STALE


def approval_current_for_head(
    approval_witnesses: Sequence[Mapping[str, Any]],
    head_sha: str,
) -> bool:
    """True only when an approving witness is bound to the bundle head SHA."""

    for witness in approval_witnesses:
        state = str(witness.get("state") or "").upper()
        commit_oid = str(witness.get("commit_oid") or witness.get("commitOid") or "")
        if state == "APPROVED" and commit_oid == head_sha:
            return True
    return False


def load_json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _git_blob_sha1(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _json_payload_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _source(
    name: str,
    source_type: str,
    *,
    artifact_name: str | None = None,
    file_path: str | None = None,
    file_line_range: str | None = None,
    artifact_sha256: str | None = None,
    run_id: str | None = None,
    run_attempt: str | None = None,
    created_at: str | None = None,
    head_sha: str | None = None,
    repo_sha: str | None = None,
    producer: str | None = None,
) -> SourceProvenance:
    return SourceProvenance(
        name=name,
        type=source_type,
        artifact_name=artifact_name,
        file_path=file_path,
        file_line_range=file_line_range,
        artifact_sha256=artifact_sha256,
        run_id=run_id,
        run_attempt=run_attempt,
        created_at=created_at,
        head_sha=head_sha,
        repo_sha=repo_sha,
        producer=producer,
    )


def _normalize_checks_rows(checks_payload: Any) -> list[dict[str, Any]]:
    if isinstance(checks_payload, Mapping):
        rows = checks_payload.get("checks", [])
    else:
        rows = checks_payload
    if isinstance(rows, Mapping):
        return [
            {"name": str(name), "state": str(state), "conclusion": str(state)}
            for name, state in sorted(rows.items())
        ]
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _subject_from_inputs(
    decision: Mapping[str, Any],
    pr_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    head_sha = str(
        decision.get("head_sha")
        or pr_metadata.get("head_sha")
        or pr_metadata.get("headRefOid")
        or ""
    ).strip()
    if not head_sha:
        raise ValueError("press-merge evidence bundle requires one head SHA")

    pr_number = decision.get("pr_number") or pr_metadata.get("number")
    return {
        "repo": decision.get("repo") or pr_metadata.get("repo"),
        "pr_number": pr_number,
        "url": pr_metadata.get("url"),
        "title": pr_metadata.get("title"),
        "base_ref": pr_metadata.get("baseRefName") or pr_metadata.get("base_ref") or decision.get("base"),
        "head_ref": decision.get("branch")
        or pr_metadata.get("head_ref")
        or pr_metadata.get("headRefName"),
        "head_sha": head_sha,
        "is_draft": bool(pr_metadata.get("is_draft") or pr_metadata.get("isDraft") or False),
    }


def _witnesses_from_pr_metadata(pr_metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    latest_reviews = pr_metadata.get("latestReviews")
    if not isinstance(latest_reviews, list):
        return []
    witnesses: list[dict[str, Any]] = []
    for review in latest_reviews:
        if not isinstance(review, Mapping):
            continue
        state = str(review.get("state") or "").upper()
        if state != "APPROVED":
            continue
        author = review.get("author")
        reviewer_login = ""
        if isinstance(author, Mapping):
            reviewer_login = str(author.get("login") or "")
        commit = review.get("commit")
        commit_oid = ""
        if isinstance(commit, Mapping):
            commit_oid = str(commit.get("oid") or "")
        commit_oid = commit_oid or str(review.get("commitOid") or review.get("commit_id") or "")
        witnesses.append(
            {
                "reviewer_login": reviewer_login,
                "commit_oid": commit_oid,
                "state": state,
                "review_id": str(review.get("id") or review.get("databaseId") or ""),
            }
        )
    return witnesses


def _carrier_metadata(repo_root: Path | None, head_ref: str | None) -> dict[str, Any]:
    if repo_root is None or not head_ref:
        return {
            "path": None,
            "blob_sha": None,
            "content_sha256": None,
            "declared_count": None,
            "declared_sha256": None,
            "paths": [],
            "consistent": False,
            "available": False,
        }
    rel = Path(".ce/pr-manifests") / f"{branch_slug(head_ref)}.md"
    path = repo_root / rel
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "path": rel.as_posix(),
            "blob_sha": None,
            "content_sha256": None,
            "declared_count": None,
            "declared_sha256": None,
            "paths": [],
            "consistent": False,
            "available": False,
        }
    identity = parse_carrier(text)
    return {
        "path": rel.as_posix(),
        "blob_sha": _git_blob_sha1(path),
        "content_sha256": _file_sha256(path),
        "declared_count": identity.declared_count if identity else None,
        "declared_sha256": identity.declared_sha256 if identity else None,
        "paths": list(identity.paths) if identity else [],
        "consistent": bool(identity and identity.consistent),
        "available": identity is not None,
    }


def _changelog_fragment(repo_root: Path | None, head_ref: str | None) -> list[dict[str, Any]]:
    if repo_root is None or not head_ref:
        return []
    rel = Path(".ce/changelog") / f"{branch_slug(head_ref)}.md"
    path = repo_root / rel
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    front_matter: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    front_matter[key.strip()] = value.strip()
    return [
        {
            "path": rel.as_posix(),
            "blob_sha": _git_blob_sha1(path),
            "content_sha256": _file_sha256(path),
            "front_matter": front_matter,
        }
    ]


def _validation_payload(validation_capture: Mapping[str, Any] | None) -> dict[str, Any]:
    if not validation_capture:
        return {
            "available": False,
            "command": None,
            "exit_code": None,
            "stdout_sha256": None,
            "stderr_sha256": None,
            "summary": None,
            "source_gap": (
                "ce validate-pr is an optional local diagnostic whose transcript "
                "is not accepted as gate evidence; this bundle does not fake it."
            ),
        }
    return {
        "available": True,
        "command": validation_capture.get("command"),
        "exit_code": validation_capture.get("exit_code"),
        "stdout_sha256": validation_capture.get("stdout_sha256"),
        "stderr_sha256": validation_capture.get("stderr_sha256"),
        "summary": validation_capture.get("summary"),
        "source_gap": None,
    }


def _derived_verdict(
    *,
    staleness_status: str,
    decision: Mapping[str, Any],
    checks_green: bool,
    current_head_approved: bool,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if staleness_status == STALE_STALE:
        return "stale", ["bundle head no longer matches current PR head"]
    if staleness_status == STALE_UNKNOWN:
        reasons.append("current PR head was not observed")
    if decision.get("decision") != "AUTO":
        reasons.append("automerge dry-run decision is not AUTO")
    if not checks_green:
        reasons.append("required checks are not green in the included decision")
    if decision.get("reviewDecision") == "CHANGES_REQUESTED":
        reasons.append("review decision reports changes requested")
    if not current_head_approved:
        reasons.append("no approval witness is bound to the bundle head")
    if reasons:
        return "blocked", reasons
    return "ready_for_human_merge", ["included evidence is current and green"]


def _map_fields(value: Any, source_name: str, prefix: str, out: dict[str, str]) -> None:
    out[prefix or "/"] = source_name
    if isinstance(value, Mapping):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            _map_fields(child, source_name, f"{prefix}/{escaped}", out)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _map_fields(child, source_name, f"{prefix}/{idx}", out)


def assemble_press_merge_evidence(
    *,
    decision_payload: Mapping[str, Any],
    changed_paths: Sequence[str],
    checks_payload: Any | None = None,
    pr_metadata: Mapping[str, Any] | None = None,
    approval_witnesses: Sequence[Mapping[str, Any]] | None = None,
    current_head_sha_observed: str | None = None,
    validation_capture: Mapping[str, Any] | None = None,
    actuation_records: Sequence[Mapping[str, Any]] | None = None,
    daemon_decisions: Sequence[Mapping[str, Any]] | None = None,
    tier_b_ledger: Mapping[str, Any] | None = None,
    external_evidence: Sequence[Mapping[str, Any]] | None = None,
    repo_root: str | Path | None = None,
    minted_at_utc: str | None = None,
    assembler_workflow: str | None = None,
    assembler_run_id: str | None = None,
    assembler_run_attempt: str | None = None,
    read_repo_sha: str | None = None,
    decision_artifact_name: str | None = None,
) -> dict[str, Any]:
    """Assemble a v1 press-merge evidence bundle from explicit inputs."""

    decision = dict(decision_payload)
    metadata = dict(pr_metadata or {})
    subject = _subject_from_inputs(decision, metadata)
    head_sha = str(subject["head_sha"])
    observed_head = current_head_sha_observed or str(
        metadata.get("head_sha") or metadata.get("headRefOid") or head_sha
    )
    staleness_status = head_staleness_status(head_sha, observed_head)
    checks_rows = _normalize_checks_rows(checks_payload)

    witnesses = [dict(w) for w in (approval_witnesses or _witnesses_from_pr_metadata(metadata))]
    current_head_approved = approval_current_for_head(witnesses, head_sha)
    carrier = _carrier_metadata(Path(repo_root) if repo_root else None, subject.get("head_ref"))
    changelog_fragments = _changelog_fragment(
        Path(repo_root) if repo_root else None,
        subject.get("head_ref"),
    )
    checks_green = bool(decision.get("checks_green", False))
    verdict, verdict_reasons = _derived_verdict(
        staleness_status=staleness_status,
        decision=decision,
        checks_green=checks_green,
        current_head_approved=current_head_approved,
    )

    created_at = minted_at_utc or datetime.now(UTC).replace(microsecond=0).isoformat()
    sources = [
        _source(
            "decision",
            "artifact",
            artifact_name=decision_artifact_name,
            artifact_sha256=_json_payload_sha256(decision),
            run_id=assembler_run_id,
            run_attempt=assembler_run_attempt,
            created_at=created_at,
            head_sha=head_sha,
            repo_sha=read_repo_sha,
            producer="ce automerge-decide",
        ),
        _source(
            "live_pr",
            "github_api",
            run_id=assembler_run_id,
            run_attempt=assembler_run_attempt,
            created_at=created_at,
            head_sha=observed_head,
            repo_sha=read_repo_sha,
            producer="gh pr view",
        ),
        _source(
            "checks",
            "github_api",
            run_id=assembler_run_id,
            run_attempt=assembler_run_attempt,
            created_at=created_at,
            head_sha=head_sha,
            repo_sha=read_repo_sha,
            producer="gh pr checks",
        ),
        _source(
            "paths",
            "workflow_file",
            file_path="changed-paths.txt",
            artifact_sha256=hashlib.sha256(
                ("\n".join(sorted({p for p in changed_paths if p})) + "\n").encode("utf-8")
            ).hexdigest(),
            run_id=assembler_run_id,
            run_attempt=assembler_run_attempt,
            created_at=created_at,
            head_sha=head_sha,
            repo_sha=read_repo_sha,
            producer="CE Automerge Decide",
        ),
        _source(
            "validate_pr_gap",
            "known_gap",
            file_path="validators/creator_engine_validator/pr_preflight.py",
            file_line_range="1-6,1000-1009",
            created_at=created_at,
            head_sha=head_sha,
            repo_sha=read_repo_sha,
            producer="ce validate-pr",
        ),
        _source(
            "tier_b_ledger",
            "optional_static_or_artifact",
            created_at=created_at,
            head_sha=head_sha,
            repo_sha=read_repo_sha,
            producer="brain ledger capture",
        ),
    ]
    if carrier["available"]:
        sources.append(
            _source(
                "authorized_manifest",
                "repo_file",
                file_path=carrier["path"],
                artifact_sha256=carrier["content_sha256"],
                created_at=created_at,
                head_sha=head_sha,
                repo_sha=read_repo_sha,
                producer="carrier_gen.write_carriers",
            )
        )
    if changelog_fragments:
        sources.append(
            _source(
                "changelog",
                "repo_file",
                file_path=changelog_fragments[0]["path"],
                artifact_sha256=changelog_fragments[0]["content_sha256"],
                created_at=created_at,
                head_sha=head_sha,
                repo_sha=read_repo_sha,
                producer="carrier_gen.write_carriers",
            )
        )

    tier_b = dict(tier_b_ledger or {})
    tier_b_payload = {
        "available": bool(tier_b),
        "old_record_count": tier_b.get("old_record_count"),
        "new_record_count": tier_b.get("new_record_count"),
        "old_active_count": tier_b.get("old_active_count"),
        "new_active_count": tier_b.get("new_active_count"),
        "old_head_hash": tier_b.get("old_head_hash"),
        "new_head_hash": tier_b.get("new_head_hash"),
        "superseded_assertion_ids": list(tier_b.get("superseded_assertion_ids") or []),
        "source": "tier_b_ledger" if tier_b else "tier_b_ledger_not_captured",
    }

    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "minted_at_utc": created_at,
        "assembler_version": ASSEMBLER_VERSION,
        "assembler_workflow": assembler_workflow,
        "assembler_run_id": assembler_run_id,
        "assembler_run_attempt": assembler_run_attempt,
        "read_repo_sha": read_repo_sha,
        "subject": subject,
        "staleness": {
            "valid_for_head_sha": head_sha,
            "current_head_sha_observed": observed_head or None,
            "status": staleness_status,
        },
        "approval": {
            "review_decision": decision.get("reviewDecision") or metadata.get("reviewDecision"),
            "approving_reviewers": [
                str(w.get("reviewer_login") or "")
                for w in witnesses
                if str(w.get("state") or "").upper() == "APPROVED"
            ],
            "approval_witnesses": witnesses,
            "current_head_approved": current_head_approved,
        },
        "checks": {
            "required": list(decision.get("required_checks") or []),
            "green": checks_green,
            "snapshot": dict(decision.get("checks_snapshot") or {}),
            "rows": checks_rows,
        },
        "decision": {
            "payload": decision,
            "artifact": {
                "name": decision_artifact_name,
                "sha256": _json_payload_sha256(decision),
                "run_id": assembler_run_id,
                "run_attempt": assembler_run_attempt,
            },
        },
        "actuation": {
            "available": bool(actuation_records),
            "records": [dict(r) for r in (actuation_records or [])],
        },
        "validation": {"validate_pr": _validation_payload(validation_capture)},
        "work_sizing": {
            "declared_work_class": decision.get("class"),
            "minimum_work_class": decision.get("minimum_work_class"),
            "size_band": decision.get("size_band"),
            "floor_met": decision.get("size_band") in {"target_advisory", "warn"},
            "ratification_gates": list(decision.get("gates") or []),
            "adr_required": "ADR" in " ".join(str(g) for g in decision.get("gates") or []),
        },
        "paths": {
            "changed_paths": sorted({p for p in changed_paths if p}),
            "authorized_manifest": carrier,
            "authorized_count": carrier["declared_count"],
            "authorized_sha256": carrier["declared_sha256"],
            "fidelity_status": "consistent" if carrier["consistent"] else "missing_or_inconsistent",
            "path_set_source": "decide_workflow_changed_paths",
        },
        "changelog": {"fragments": changelog_fragments},
        "daemon": {"decisions": [dict(d) for d in (daemon_decisions or [])]},
        "tier_b_ledger": tier_b_payload,
        "external_evidence": [dict(e) for e in (external_evidence or [])],
        "summary": {
            "verdict": verdict,
            "verdict_is_authority_bearing": False,
            "reasons": verdict_reasons,
        },
    }

    field_sources: dict[str, str] = {}
    for pointer, source_name in (
        ("/schema_version", "decision"),
        ("/kind", "decision"),
        ("/minted_at_utc", "decision"),
        ("/assembler_version", "decision"),
        ("/assembler_workflow", "decision"),
        ("/assembler_run_id", "decision"),
        ("/assembler_run_attempt", "decision"),
        ("/read_repo_sha", "decision"),
        ("/subject", "live_pr"),
        ("/staleness", "live_pr"),
        ("/approval", "live_pr"),
        ("/checks", "checks"),
        ("/decision", "decision"),
        ("/actuation", "decision"),
        ("/validation", "validate_pr_gap"),
        ("/work_sizing", "decision"),
        ("/paths", "paths"),
        ("/changelog", "changelog" if changelog_fragments else "paths"),
        ("/daemon", "decision"),
        ("/tier_b_ledger", "tier_b_ledger"),
        ("/external_evidence", "decision"),
        ("/summary", "decision"),
    ):
        key = pointer.strip("/")
        _map_fields(bundle[key] if key else bundle, source_name, pointer, field_sources)

    bundle["provenance"] = {
        "sources": [source.to_dict() for source in sources],
        "field_sources": field_sources,
        "source_count": len(sources),
    }
    return bundle


def assemble_press_merge_evidence_from_files(
    *,
    decision_file: str | Path,
    paths_file: str | Path,
    checks_json_file: str | Path | None = None,
    pr_json_file: str | Path | None = None,
    approval_witnesses_json_file: str | Path | None = None,
    current_head_sha_observed: str | None = None,
    repo_root: str | Path | None = None,
    minted_at_utc: str | None = None,
    assembler_workflow: str | None = None,
    assembler_run_id: str | None = None,
    assembler_run_attempt: str | None = None,
    read_repo_sha: str | None = None,
    decision_artifact_name: str | None = None,
) -> dict[str, Any]:
    decision = load_json_file(decision_file)
    if not isinstance(decision, Mapping):
        raise ValueError("decision file must contain a JSON object")
    changed_paths = [
        line.strip()
        for line in Path(paths_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    checks_payload = load_json_file(checks_json_file) if checks_json_file else None
    pr_metadata = load_json_file(pr_json_file) if pr_json_file else {}
    if not isinstance(pr_metadata, Mapping):
        raise ValueError("PR metadata file must contain a JSON object")
    approval_witnesses = (
        load_json_file(approval_witnesses_json_file) if approval_witnesses_json_file else None
    )
    if approval_witnesses is not None and not isinstance(approval_witnesses, list):
        raise ValueError("approval witnesses file must contain a JSON array")
    return assemble_press_merge_evidence(
        decision_payload=decision,
        changed_paths=changed_paths,
        checks_payload=checks_payload,
        pr_metadata=pr_metadata,
        approval_witnesses=approval_witnesses,
        current_head_sha_observed=current_head_sha_observed,
        repo_root=repo_root,
        minted_at_utc=minted_at_utc,
        assembler_workflow=assembler_workflow,
        assembler_run_id=assembler_run_id,
        assembler_run_attempt=assembler_run_attempt,
        read_repo_sha=read_repo_sha,
        decision_artifact_name=decision_artifact_name,
    )


__all__ = [
    "ASSEMBLER_VERSION",
    "KIND",
    "SCHEMA_VERSION",
    "SourceProvenance",
    "approval_current_for_head",
    "assemble_press_merge_evidence",
    "assemble_press_merge_evidence_from_files",
    "canonical_json_bytes",
    "canonical_json_digest",
    "head_staleness_status",
]
