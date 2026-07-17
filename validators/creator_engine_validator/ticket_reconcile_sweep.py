"""Pure, offline reduction of strict reconciliation snapshots into advisory evidence."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from collections.abc import Mapping, Sequence
from typing import Any

from jsonschema import Draft202012Validator

from .schema import load_schema

SCHEMA_PATH = "schemas/ticket-reconcile-advisory.schema.yaml"
POLICY_VERSION = "1"
_EVIDENCE_ORDER = (
    "branch",
    "changelog",
    "explicit-closing-ref",
    "incomplete-pagination",
    "missing-merge-sha",
    "multiple-viable-prs",
    "partial-slice",
    "post-merge-ticket-update",
    "repository-ambiguity",
)
_CLOSING_WORD = r"(?:[Cc]lose[sd]?|[Ff]ix(?:e[sd])?|[Rr]esolve[sd]?)"


class SnapshotValidationError(ValueError):
    """Raised when a snapshot is not a bounded, unambiguous offline input."""


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Reject an input outside the strict snapshot contract before reduction."""
    if not isinstance(snapshot, Mapping):
        raise SnapshotValidationError("snapshot must be an object")
    document = load_schema(SCHEMA_PATH)
    schema = {"$ref": "#/$defs/snapshot", "$defs": document["$defs"]}
    errors = sorted(Draft202012Validator(schema).iter_errors(snapshot), key=lambda error: list(error.path))
    if errors:
        raise SnapshotValidationError(_schema_error(errors[0]))
    pagination = snapshot["pagination"]
    cursors = pagination["cursors"]
    if len(cursors) != pagination["page_count"] or cursors[0] is not None:
        raise SnapshotValidationError("pagination cursor sequence is ambiguous")
    _validate_timestamps(snapshot)
    _reject_duplicate_identities(snapshot)


def reduce_snapshot(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic, nonbinding advisory evidence from supplied data only."""
    validate_snapshot(snapshot)
    if not snapshot["pagination"]["complete"]:
        return [_incomplete_packet(snapshot)]

    tickets = sorted(snapshot["tickets"], key=lambda item: item["number"])
    prs = sorted(snapshot["pull_requests"], key=lambda item: (item["merged_at"], item["number"]))
    packets: list[dict[str, Any]] = []
    for ticket in tickets:
        if "triage:ready" not in ticket["labels"]:
            continue
        viable = [(pr, _evidence_for(ticket, pr, snapshot["ticket_repository"])) for pr in prs]
        viable = [(pr, evidence) for pr, evidence in viable if "explicit-closing-ref" in evidence or {"branch", "changelog"} <= evidence]
        if not viable:
            continue
        for pr, evidence in viable:
            codes = set(evidence)
            if ticket.get("partial_slice"):
                codes.add("partial-slice")
            if len(viable) > 1:
                codes.add("multiple-viable-prs")
            if ticket["updated_at"] > pr["merged_at"]:
                codes.add("post-merge-ticket-update")
            if pr["merge_commit_sha"] is None:
                codes.add("missing-merge-sha")
            disposition = _disposition(ticket, pr, codes)
            packets.append(_packet(snapshot, ticket, pr, codes, disposition))
    return sorted(packets, key=lambda packet: (packet["ticket"]["number"], packet["observation_timestamp"], packet["pull_request"]["number"]))


def render_json(packets: Sequence[Mapping[str, Any]]) -> str:
    """Serialize evidence canonically for stable local staging by a caller."""
    return json.dumps(list(packets), separators=(",", ":"), sort_keys=True) + "\n"


def _reject_duplicate_identities(snapshot: Mapping[str, Any]) -> None:
    tickets = [item["number"] for item in snapshot["tickets"]]
    prs = [item["number"] for item in snapshot["pull_requests"]]
    if len(tickets) != len(set(tickets)) or len(prs) != len(set(prs)):
        raise SnapshotValidationError("duplicate ticket or pull request identity")
    if any(pr["repository"] != snapshot["pull_request_repository"] for pr in snapshot["pull_requests"]):
        raise SnapshotValidationError("cross-repository pull request record")


def _validate_timestamps(snapshot: Mapping[str, Any]) -> None:
    values = [snapshot["observed_at"]]
    values.extend(ticket["updated_at"] for ticket in snapshot["tickets"])
    values.extend(pr["merged_at"] for pr in snapshot["pull_requests"])
    for value in values:
        try:
            datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        except ValueError as exc:
            raise SnapshotValidationError("invalid timestamp") from exc


def _evidence_for(ticket: Mapping[str, Any], pr: Mapping[str, Any], ticket_repository: str) -> set[str]:
    evidence: set[str] = set()
    number = ticket["number"]
    if re.search(rf"(?<![a-z0-9-])ce-{number}-(?![0-9])", pr["head_branch"].lower()):
        evidence.add("branch")
    if _has_closing_reference(pr["body"], ticket_repository, number):
        evidence.add("explicit-closing-ref")
    if any(_changelog_ref_matches(fragment, ticket_repository, number) for fragment in pr["changed_changelog_fragments"]):
        evidence.add("changelog")
    return evidence


def _has_closing_reference(body: str, repository: str, number: int) -> bool:
    ref = re.escape(f"{repository}#{number}")
    pattern = rf"(?m)^\s*{_CLOSING_WORD}\s+{ref}(?:[.!])?\s*$"
    return re.search(pattern, body) is not None


def _changelog_ref_matches(fragment: str, repository: str, number: int) -> bool:
    if not fragment.startswith("---\n"):
        return False
    end = fragment.find("\n---\n", 4)
    if end < 0:
        return False
    front_matter = fragment[4:end].splitlines()
    expected = f"{repository}#{number}"
    return any(line in (f"issue: {expected}", f"ticket: {expected}") for line in front_matter)


def _disposition(ticket: Mapping[str, Any], pr: Mapping[str, Any], codes: set[str]) -> str:
    if codes & {"partial-slice", "multiple-viable-prs", "post-merge-ticket-update", "missing-merge-sha", "repository-ambiguity"}:
        return "REQUIRES_HUMAN_RECHECK"
    if ticket["kind"] == "directive" and not _acceptance_evidence(pr["body"]):
        return "NEEDS_ACCEPTANCE_EVIDENCE"
    return "ADVISORY_PROPOSAL"


def _acceptance_evidence(body: str) -> bool:
    return re.search(r"(?m)^Acceptance-Evidence:\s*\S[^\r\n]*$", body) is not None


def _packet(snapshot: Mapping[str, Any], ticket: Mapping[str, Any], pr: Mapping[str, Any], codes: set[str], disposition: str) -> dict[str, Any]:
    ordered_codes = [code for code in _EVIDENCE_ORDER if code in codes]
    merge_sha = pr["merge_commit_sha"]
    packet: dict[str, Any] = {
        "candidate_key": _candidate_key(snapshot, ticket, pr, ordered_codes),
        "completeness": {"complete": True, "page_count": snapshot["pagination"]["page_count"]},
        "disposition": disposition,
        "evidence_codes": ordered_codes,
        "kind": "ticket-reconcile-advisory",
        "merge_commit_sha": merge_sha or "0" * 40,
        "mode": "advisory",
        "observation_timestamp": snapshot["observed_at"],
        "policy_version": POLICY_VERSION,
        "proposed_action": "HUMAN_REVIEW_CLOSURE" if disposition == "ADVISORY_PROPOSAL" else "NONE",
        "pull_request": {"number": pr["number"], "repository": snapshot["pull_request_repository"]},
        "repositories": {"ticket": snapshot["ticket_repository"], "pull_request": snapshot["pull_request_repository"]},
        "schema_version": "1",
        "snapshot_digest": snapshot["snapshot_digest"],
        "ticket": {"number": ticket["number"], "repository": snapshot["ticket_repository"]},
    }
    return packet


def _candidate_key(snapshot: Mapping[str, Any], ticket: Mapping[str, Any], pr: Mapping[str, Any], codes: Sequence[str]) -> str:
    parts = (
        snapshot["ticket_repository"], str(ticket["number"]), snapshot["pull_request_repository"],
        str(pr["number"]), pr["merge_commit_sha"] or "missing", POLICY_VERSION, *codes,
    )
    return hashlib.sha256("\n".join(parts).encode("ascii")).hexdigest()


def _incomplete_packet(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "completeness": {"complete": False, "page_count": snapshot["pagination"]["page_count"]},
        "disposition": "REQUIRES_HUMAN_RECHECK",
        "evidence_codes": ["incomplete-pagination"],
        "kind": "ticket-reconcile-advisory",
        "mode": "advisory",
        "observation_timestamp": snapshot["observed_at"],
        "policy_version": POLICY_VERSION,
        "proposed_action": "NONE",
        "repositories": {"ticket": snapshot["ticket_repository"], "pull_request": snapshot["pull_request_repository"]},
        "schema_version": "1",
        "snapshot_digest": snapshot["snapshot_digest"],
    }


def _schema_error(error: Any) -> str:
    path = ".".join(str(part) for part in error.path) or "snapshot"
    return f"{path}: {error.message}"
