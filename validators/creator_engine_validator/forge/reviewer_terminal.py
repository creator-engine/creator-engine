"""Strict, fail-closed reviewer terminal v2.

Review prose is deliberately *not* evidence.  The only object which can cross a
review-submission boundary is a parsed version-2 terminal.  In particular this
module does not attempt to "helpfully" recover a verdict from prose: that was
the original confused-deputy bug.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


class ReviewerTerminalRefused(ValueError):
    """The supplied terminal is not a valid v2 review terminal."""


UNVERIFIED_LEGACY = "UNVERIFIED_LEGACY"
REVIEWED = "REVIEWED"
CANNOT_REVIEW = "CANNOT_REVIEW"
BLOCKED = "BLOCKED"
_STATES = frozenset({REVIEWED, CANNOT_REVIEW, BLOCKED})
_VERDICTS = frozenset({"APPROVE", "COMMENT", "REQUEST_CHANGES"})
_SEVERITIES = frozenset({"HIGH", "MEDIUM", "LOW"})
_HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
_BINDINGS = frozenset({
    "repository", "pr_number", "head_sha", "base", "range", "reviewer",
    "author", "review_id",
})
_REVIEWED_KEYS = _BINDINGS | frozenset({
    "version", "state", "verdict", "verified", "findings", "summary", "timestamp",
})
_REFUSAL_KEYS = _BINDINGS | frozenset({
    "version", "state", "reason", "blocker_evidence", "timestamp",
})


@dataclass(frozen=True)
class ReviewerTerminal:
    """One validated v2 terminal, with parser-derived severity counts."""

    state: str
    record: Mapping[str, Any]
    digest: str
    canonical_body: str
    counts: Mapping[str, int]

    @property
    def reviewed(self) -> bool:
        return self.state == REVIEWED


@dataclass(frozen=True)
class ParsedReviewerTerminal:
    """A parsed terminal or the explicit audit-only legacy classification."""

    state: str
    terminal: ReviewerTerminal | None = None
    reason: str = ""
    raw: str | bytes | Mapping[str, Any] | None = None
    rejection_diagnostic: str = ""

    @property
    def verified(self) -> bool:
        return self.terminal is not None and self.terminal.reviewed


def parse_reviewer_terminal(value: str | bytes | Mapping[str, Any]) -> ParsedReviewerTerminal:
    """Parse a strict v2 terminal and retain every rejected input for audit.

    No rejected material is promoted into a :class:`ReviewerTerminal`: prose,
    v1, malformed v2, and count-only output remain receipt-ineligible.  A
    malformed producer assertion is still useful audit evidence, however, so
    the original payload and a refusal diagnostic travel with its explicit
    ``UNVERIFIED_LEGACY`` classification instead of being lost in an exception.
    """
    audit_raw = _audit_payload(value)
    try:
        raw = _load(value)
    except ReviewerTerminalRefused as exc:
        return _legacy(audit_raw, "invalid_json_structure", str(exc))
    if raw is None:
        # The two canonical 2026-07-20 artifacts are explicit refusal reports,
        # not verdict prose.  They remain terminal-less and receipt-ineligible,
        # but retain their refusal arm for audit/reporting rather than being
        # mistaken for a completed review.
        refusal_state = _explicit_refusal_state(audit_raw)
        if refusal_state is not None:
            return ParsedReviewerTerminal(
                refusal_state,
                reason="legacy_explicit_refusal",
                raw=audit_raw,
                rejection_diagnostic="refusal prose is not a v2 terminal and cannot be submitted",
            )
        return _legacy(audit_raw, "non_json_or_legacy", "input is not a v2 terminal")
    if raw.get("version") != 2:
        return _legacy(audit_raw, "non_v2", "terminal version is not 2")
    try:
        terminal = _parse_v2(raw)
    except ReviewerTerminalRefused as exc:
        return _legacy(audit_raw, "invalid_v2", str(exc))
    return ParsedReviewerTerminal(terminal.state, terminal, raw=audit_raw)


def require_reviewed_terminal(
    value: str | bytes | Mapping[str, Any] | ReviewerTerminal,
    *,
    repository: str | None = None,
    pr_number: int | None = None,
    head_sha: str | None = None,
    event: str | None = None,
) -> ReviewerTerminal:
    """Require a receipt-eligible REVIEWED terminal and exact request bindings."""
    parsed = None if isinstance(value, ReviewerTerminal) else parse_reviewer_terminal(value)
    terminal = value if isinstance(value, ReviewerTerminal) else parsed.terminal
    if terminal is None:
        raise ReviewerTerminalRefused(f"review terminal is {parsed.state} and cannot be submitted")
    if terminal.state != REVIEWED:
        raise ReviewerTerminalRefused(f"review terminal state {terminal.state} is a refusal, not a verdict")
    rec = terminal.record
    if repository is not None and rec["repository"] != repository:
        raise ReviewerTerminalRefused("review terminal repository binding mismatch")
    if pr_number is not None and rec["pr_number"] != pr_number:
        raise ReviewerTerminalRefused("review terminal PR binding mismatch")
    if head_sha is not None and rec["head_sha"] != head_sha:
        raise ReviewerTerminalRefused("review terminal head binding mismatch")
    if event is not None and rec["verdict"] != event:
        raise ReviewerTerminalRefused("review terminal event/verdict binding mismatch")
    return terminal


def _load(value: str | bytes | Mapping[str, Any]) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(value, str):
        return None
    # A literal marker from v1 prose is always legacy, even if a future parser
    # learns to recognise adjacent prose.
    if "verified:none" in "".join(value.lower().split()):
        return None
    try:
        obj = json.loads(value, object_pairs_hook=_no_duplicate_keys)
    except (TypeError, json.JSONDecodeError):
        return None
    return dict(obj) if isinstance(obj, Mapping) else None


def _audit_payload(value: str | bytes | Mapping[str, Any]) -> str | bytes | Mapping[str, Any]:
    """Preserve the supplied material without attempting to reinterpret it."""
    if isinstance(value, Mapping):
        return dict(value)
    return value


def _legacy(
    raw: str | bytes | Mapping[str, Any], reason: str, diagnostic: str,
) -> ParsedReviewerTerminal:
    return ParsedReviewerTerminal(
        UNVERIFIED_LEGACY, reason=reason, raw=raw, rejection_diagnostic=diagnostic,
    )


def _explicit_refusal_state(value: str | bytes | Mapping[str, Any]) -> str | None:
    """Classify an explicit refusal report without treating it as review evidence.

    This deliberately recognizes only the two canonical 2026-07-20
    unavailable-inspection report forms: the slash-delimited marker plus the
    target-unavailable or missing-inspectable-evidence reason quoted below.
    It is an audit classification, not a prose-to-v2 promotion: it yields no
    ``ReviewerTerminal`` and therefore cannot issue a receipt.  Generic,
    malformed, or merely similarly worded refusal prose stays
    ``UNVERIFIED_LEGACY``.
    """
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.upper().split())
    canonical_reasons = (
        "THE EXACT REQUESTED TARGET REF AND SHA ARE UNAVAILABLE.",
        "REQUIRED EVIDENCE FOR THE ASSERTED APPROVED-AND-GREEN #1055 REPLAY "
        "YIELDING RAW, BYTE-REPEATABLE `AUTO` IS NOT AVAILABLE IN THE CARRIER "
        "OR LOCALLY INSPECTABLE REVIEW MATERIAL.",
    )
    if "BLOCKED / CANNOT_REVIEW" in normalized and any(
        reason in normalized for reason in canonical_reasons
    ):
        return CANNOT_REVIEW
    return None


def _parse_v2(rec: dict[str, Any]) -> ReviewerTerminal:
    state = rec.get("state")
    if state not in _STATES:
        raise ReviewerTerminalRefused("review terminal v2 state is unknown")
    expected = _REVIEWED_KEYS if state == REVIEWED else _REFUSAL_KEYS
    if set(rec) != expected:
        raise ReviewerTerminalRefused("review terminal v2 has missing, forbidden, or unknown fields")
    _validate_bindings(rec)
    if not isinstance(rec.get("timestamp"), str) or not rec["timestamp"].strip():
        raise ReviewerTerminalRefused("review terminal requires non-empty timestamp")
    if state == REVIEWED:
        _validate_reviewed(rec)
    else:
        _validate_refusal(rec)
    counts = {severity: 0 for severity in _SEVERITIES}
    for finding in rec.get("findings", []):
        counts[finding["severity"]] += 1
    terminal_canonical = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    # Producer records never carry trusted counts.  The submission body does:
    # it is rendered by this parser and therefore cannot represent a
    # count-only/no-inspection result as a completed review.
    rendered = dict(rec)
    if state == REVIEWED:
        rendered["severity_counts"] = {key: counts[key] for key in ("HIGH", "MEDIUM", "LOW")}
    canonical_body = json.dumps(rendered, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(terminal_canonical.encode("utf-8")).hexdigest()
    return ReviewerTerminal(state, rec, digest, canonical_body, counts)


def _validate_bindings(rec: Mapping[str, Any]) -> None:
    if not isinstance(rec["repository"], str) or "/" not in rec["repository"] or not rec["repository"].strip():
        raise ReviewerTerminalRefused("review terminal repository binding is invalid")
    if not isinstance(rec["pr_number"], int) or isinstance(rec["pr_number"], bool) or rec["pr_number"] <= 0:
        raise ReviewerTerminalRefused("review terminal PR binding is invalid")
    if not isinstance(rec["head_sha"], str) or not _HEAD_SHA_RE.fullmatch(rec["head_sha"]):
        raise ReviewerTerminalRefused("review terminal head binding is invalid")
    for key in ("base", "range", "reviewer", "author", "review_id"):
        if not isinstance(rec[key], str) or not rec[key].strip():
            raise ReviewerTerminalRefused(f"review terminal {key} binding is invalid")
    if rec["reviewer"] == rec["author"]:
        raise ReviewerTerminalRefused("review terminal self-review is forbidden")


def _validate_reviewed(rec: Mapping[str, Any]) -> None:
    if rec["verdict"] not in _VERDICTS:
        raise ReviewerTerminalRefused("review terminal verdict is invalid")
    if not isinstance(rec["summary"], str) or not rec["summary"].strip():
        raise ReviewerTerminalRefused("review terminal summary is invalid")
    verified = rec["verified"]
    if not isinstance(verified, list) or not verified:
        raise ReviewerTerminalRefused("REVIEWED requires non-empty structured verified evidence")
    for item in verified:
        if not isinstance(item, Mapping) or set(item) != {"claim", "evidence"}:
            raise ReviewerTerminalRefused("verified evidence must contain only claim and evidence")
        if not all(isinstance(item[key], str) and item[key].strip() for key in ("claim", "evidence")):
            raise ReviewerTerminalRefused("verified evidence claim/evidence must be non-empty")
    findings = rec["findings"]
    if not isinstance(findings, list):
        raise ReviewerTerminalRefused("REVIEWED findings must be an array")
    for item in findings:
        if not isinstance(item, Mapping) or set(item) != {"severity", "summary"}:
            raise ReviewerTerminalRefused("finding must contain only severity and summary")
        if item["severity"] not in _SEVERITIES or not isinstance(item["summary"], str) or not item["summary"].strip():
            raise ReviewerTerminalRefused("finding severity/summary is invalid")


def _validate_refusal(rec: Mapping[str, Any]) -> None:
    if not isinstance(rec["reason"], str) or not rec["reason"].strip():
        raise ReviewerTerminalRefused("refusal terminal requires non-empty reason")
    evidence = rec["blocker_evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ReviewerTerminalRefused("refusal terminal requires blocker evidence")
    for item in evidence:
        if not isinstance(item, Mapping) or set(item) != {"attempt", "result"}:
            raise ReviewerTerminalRefused("blocker evidence must contain only attempt and result")
        if not all(isinstance(item[key], str) and item[key].strip() for key in ("attempt", "result")):
            raise ReviewerTerminalRefused("blocker evidence values must be non-empty")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys before a producer can shadow a binding."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReviewerTerminalRefused("review terminal JSON has duplicate keys")
        result[key] = value
    return result
