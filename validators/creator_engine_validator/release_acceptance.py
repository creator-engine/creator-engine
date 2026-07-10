"""Release-acceptance state mechanics for repository-visible RC records.

Release-acceptance state lives in one record per candidate under
``.ce/release-acceptance/<rc-id>.yml``. This module keeps the mechanics pure:
callers pass record dictionaries and evidence bundles in, and receive updated
records or fail-closed refusal reasons back.

The ``rc_marked -> rehearsal_required`` transition is intentionally an
explicit governed action. It is not automatic after RC marking; applying it
requires a recorded actor and evidence reference, the same as the rest of the
authority-changing release-acceptance transitions.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "1"
RELEASE_ACCEPTANCE_DIR = Path(".ce") / "release-acceptance"

NONE = "none"
RC_MARKED = "rc_marked"
REHEARSAL_REQUIRED = "rehearsal_required"
REHEARSAL_PASSED = "rehearsal_passed"
PROMOTION_RATIFIED = "promotion_ratified"
PROMOTED = "promoted"
DOGFOOD_RING_CONSUMED = "ring0_consumed"
CLOSURE_READY = "closure_ready"
CLOSED = "closed"
HELD = "held"
SUPERSEDED = "superseded"
REOPENED = "reopened"

STATES = (
    RC_MARKED,
    REHEARSAL_REQUIRED,
    REHEARSAL_PASSED,
    PROMOTION_RATIFIED,
    PROMOTED,
    DOGFOOD_RING_CONSUMED,
    CLOSURE_READY,
    CLOSED,
    HELD,
    SUPERSEDED,
    REOPENED,
)

# Transition table and entry evidence mirror the design specification.
# Authoritative source: docs/design/release-acceptance-stage.md § "State Machine"
ENTRY_EVIDENCE: dict[str, tuple[str, ...]] = {
    RC_MARKED: (
        "RC tag/ref",
        "source commit",
        "initial acceptance record",
        "release ticket ref",
    ),
    REHEARSAL_REQUIRED: ("record transition after RC marking",),
    REHEARSAL_PASSED: (
        "valid rehearsal JSON from the existing harness family",
        "zero failures",
        "no disallowed stubs",
        "candidate identity bound to the RC",
    ),
    PROMOTION_RATIFIED: ("ratification record linked in ratification_ref",),
    PROMOTED: ("promotion ratification plus immutable evidence links",),
    DOGFOOD_RING_CONSUMED: (
        "dogfood ring evidence bound to rc_id, source_commit, and artifact digest",
    ),
    CLOSURE_READY: (
        "promoted state",
        "dogfood ring evidence",
        "closure integrity checks",
        "persistent-state probes for deploy-class claims",
    ),
    CLOSED: ("closure reference and final acceptance record update",),
    HELD: (
        "failing rehearsal",
        "missing evidence",
        "probe drift",
        "ambiguous identity",
        "ratification refusal",
    ),
    SUPERSEDED: ("new RC record links back through supersedes_rc_id",),
    REOPENED: ("Source-ratified reopen or rollback record",),
}

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    NONE: frozenset({RC_MARKED}),
    RC_MARKED: frozenset({REHEARSAL_REQUIRED, SUPERSEDED}),
    REHEARSAL_REQUIRED: frozenset({REHEARSAL_PASSED, HELD, SUPERSEDED}),
    REHEARSAL_PASSED: frozenset({PROMOTION_RATIFIED, HELD}),
    PROMOTION_RATIFIED: frozenset({PROMOTED}),
    PROMOTED: frozenset({DOGFOOD_RING_CONSUMED, REOPENED}),
    DOGFOOD_RING_CONSUMED: frozenset({CLOSURE_READY, REOPENED}),
    CLOSURE_READY: frozenset({CLOSED, REOPENED}),
    CLOSED: frozenset({REOPENED}),
    HELD: frozenset({REHEARSAL_REQUIRED, SUPERSEDED}),
    SUPERSEDED: frozenset(),
    REOPENED: frozenset(),
}

SUPPORTED_REHEARSAL_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})
_HEX40_RE = re.compile(r"[0-9a-fA-F]{40}\Z")
_HEX64_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
_RC_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    old_state: str
    new_state: str
    record: dict[str, Any] | None = None
    reason: str | None = None
    details: tuple[str, ...] = ()


def record_path(repo_root: str | Path, rc_id: str) -> Path:
    """Return the authoritative repository-visible record path for an RC."""

    _validate_rc_id(rc_id)
    return Path(repo_root) / RELEASE_ACCEPTANCE_DIR / f"{rc_id}.yml"


def new_rc_record(
    *,
    rc_id: str,
    rc_ref: str,
    source_commit: str,
    release_ticket_ref: str,
    actor: str,
    evidence_ref: str,
    artifact_manifest_sha256: str | None = None,
    now: str | None = None,
) -> TransitionResult:
    """Build the initial ``rc_marked`` record through a governed transition."""

    if not actor or not evidence_ref:
        return TransitionResult(False, NONE, RC_MARKED, reason="governed_action_required")
    validation = _validate_initial_fields(
        rc_id=rc_id,
        rc_ref=rc_ref,
        source_commit=source_commit,
        release_ticket_ref=release_ticket_ref,
        artifact_manifest_sha256=artifact_manifest_sha256,
    )
    if not validation.allowed:
        return TransitionResult(False, NONE, RC_MARKED, reason=validation.reason, details=validation.details)
    transitioned_at = now or ""
    record = {
        "schema_version": SCHEMA_VERSION,
        "rc_id": rc_id,
        "rc_ref": rc_ref,
        "source_commit": source_commit.lower(),
        "artifact_manifest_sha256": artifact_manifest_sha256.lower()
        if artifact_manifest_sha256 is not None
        else None,
        "release_ticket_ref": release_ticket_ref,
        "state": RC_MARKED,
        "state_updated_at": transitioned_at,
        "promotion_evidence": {
            "fresh_tenant_rehearsal_ref": None,
            "dogfood_ring_ref": None,  # design schema uses ring0_dogfood_ref; renamed here to avoid collision with enforcement_ring
            "persistent_state_probe_refs": [],
        },
        "ratification_ref": None,
        "closure_ref": None,
        "supersedes_rc_id": None,
        "superseded_by_rc_id": None,
        "transitions": [
            _transition_log_entry(
                old_state=NONE,
                new_state=RC_MARKED,
                actor=actor,
                evidence_ref=evidence_ref,
                transitioned_at=transitioned_at,
            )
        ],
    }
    return TransitionResult(True, NONE, RC_MARKED, record=record)


def is_legal_transition(old_state: str | None, new_state: str) -> bool:
    old = old_state or NONE
    return new_state in LEGAL_TRANSITIONS.get(old, frozenset())


def transition_record(
    record: Mapping[str, Any],
    new_state: str,
    *,
    actor: str | None,
    evidence_ref: str | None,
    now: str | None = None,
    updates: Mapping[str, Any] | None = None,
) -> TransitionResult:
    """Apply one governed state transition to a release-acceptance record."""

    old_state = str(record.get("state", NONE))
    if not actor or not evidence_ref:
        return TransitionResult(False, old_state, new_state, reason="governed_action_required")
    if new_state not in STATES:
        return TransitionResult(False, old_state, new_state, reason="unknown_state")
    if old_state not in LEGAL_TRANSITIONS:
        return TransitionResult(False, old_state, new_state, reason="unknown_state")
    if not is_legal_transition(old_state, new_state):
        return TransitionResult(False, old_state, new_state, reason="illegal_transition")

    transitioned_at = now or ""
    updated = deepcopy(dict(record))
    updated["state"] = new_state
    updated["state_updated_at"] = transitioned_at
    if updates:
        _merge_updates(updated, updates)
    _bind_entry_evidence(updated, new_state, evidence_ref)
    transitions = list(updated.get("transitions") or [])
    transitions.append(
        _transition_log_entry(
            old_state=old_state,
            new_state=new_state,
            actor=actor,
            evidence_ref=evidence_ref,
            transitioned_at=transitioned_at,
        )
    )
    updated["transitions"] = transitions
    return TransitionResult(True, old_state, new_state, record=updated)


def check_rehearsal_promotion_evidence(
    record: Mapping[str, Any],
    rehearsal_bundle: Mapping[str, Any],
    *,
    expected_stage_names: Sequence[str] = (),
    ratified_stub_exception_ref: str | None = None,
    ratified_image_exception_ref: str | None = None,
) -> GateDecision:
    """Fail-closed check for fresh-tenant rehearsal promotion evidence."""

    rc_id = _lookup_candidate_field(rehearsal_bundle, "rc_id")
    source_commit = _lookup_candidate_field(rehearsal_bundle, "source_commit")
    missing = tuple(key for key, value in (("rc_id", rc_id), ("source_commit", source_commit)) if value in (None, ""))
    if missing:
        return GateDecision(
            False,
            "evidence_format_insufficient",
            tuple(f"missing {key}" for key in missing),
        )

    if str(rehearsal_bundle.get("schema_version")) not in SUPPORTED_REHEARSAL_SCHEMA_VERSIONS:
        return GateDecision(False, "unsupported_rehearsal_schema_version")
    if not rehearsal_bundle.get("harness_version"):
        return GateDecision(False, "missing_harness_version")
    if str(rc_id) != str(record.get("rc_id")) or str(source_commit).lower() != str(record.get("source_commit")).lower():
        return GateDecision(False, "candidate_identity_mismatch")

    expected_artifact_digest = record.get("artifact_manifest_sha256")
    observed_artifact_digest = _lookup_candidate_field(rehearsal_bundle, "artifact_manifest_sha256")
    if expected_artifact_digest is not None and str(observed_artifact_digest).lower() != str(expected_artifact_digest).lower():
        return GateDecision(False, "candidate_identity_mismatch", ("artifact digest mismatch",))

    summary = rehearsal_bundle.get("summary")
    if not isinstance(summary, Mapping):
        return GateDecision(False, "missing_rehearsal_summary")
    if int(summary.get("failed", -1)) != 0:
        return GateDecision(False, "rehearsal_failed")
    stubbed = int(summary.get("stubbed", -1))
    if stubbed != 0 and not ratified_stub_exception_ref:
        return GateDecision(False, "disallowed_stubs")

    observed_stages = _stage_names(rehearsal_bundle)
    missing_stages = tuple(stage for stage in expected_stage_names if stage not in observed_stages)
    if missing_stages:
        return GateDecision(
            False,
            "first_hour_stages_missing",
            tuple(f"missing stage {stage}" for stage in missing_stages),
        )

    if _mounted_developer_checkout(rehearsal_bundle):
        return GateDecision(False, "developer_checkout_mounted")
    if _image_requires_digest_exception(rehearsal_bundle) and not ratified_image_exception_ref:
        return GateDecision(False, "container_image_not_digest_pinned")

    observed_cli_identity = _lookup_candidate_field(rehearsal_bundle, "observed_cli_source_commit")
    if observed_cli_identity and str(observed_cli_identity).lower() != str(record.get("source_commit")).lower():
        return GateDecision(False, "candidate_identity_mismatch", ("observed CLI source commit mismatch",))
    return GateDecision(True)


def check_closure_integrity(
    record: Mapping[str, Any],
    *,
    release_ticket_ref: str,
    evidence_registry: Mapping[str, Mapping[str, Any]] | None = None,
    deploy_class_claims: Sequence[Mapping[str, Any] | str] = (),
) -> GateDecision:
    """Pure closure check over record, linked evidence data, and ticket claims."""

    if record.get("release_ticket_ref") != release_ticket_ref:
        return GateDecision(False, "release_ticket_mismatch")
    state = record.get("state")
    if state not in {CLOSURE_READY, CLOSED}:
        return GateDecision(False, "closure_state_invalid")
    if state == CLOSED and not record.get("closure_ref"):
        return GateDecision(False, "closure_ref_missing")

    promotion_evidence = record.get("promotion_evidence")
    if not isinstance(promotion_evidence, Mapping):
        return GateDecision(False, "promotion_evidence_missing")
    rehearsal_ref = promotion_evidence.get("fresh_tenant_rehearsal_ref")
    if not rehearsal_ref:
        return GateDecision(False, "fresh_tenant_rehearsal_missing")
    if not _evidence_ref_is_accepted(rehearsal_ref, evidence_registry):
        return GateDecision(False, "fresh_tenant_rehearsal_unaccepted")

    # Consumer details are defined in docs/design/release-acceptance-stage.md.
    dogfood_ref = promotion_evidence.get("dogfood_ring_ref")
    if not dogfood_ref:
        return GateDecision(False, "dogfood_ring_evidence_missing")
    if not _dogfood_evidence_binds_record(dogfood_ref, record, evidence_registry):
        return GateDecision(False, "dogfood_ring_identity_mismatch")

    if not record.get("ratification_ref"):
        return GateDecision(False, "ratification_ref_missing")
    persistent_probe_refs = tuple(promotion_evidence.get("persistent_state_probe_refs") or ())
    if not _deploy_claims_have_persistent_probes(deploy_class_claims, persistent_probe_refs):
        return GateDecision(False, "persistent_state_probe_missing")
    return GateDecision(True)


def _validate_initial_fields(
    *,
    rc_id: str,
    rc_ref: str,
    source_commit: str,
    release_ticket_ref: str,
    artifact_manifest_sha256: str | None,
) -> GateDecision:
    try:
        _validate_rc_id(rc_id)
    except ValueError as exc:
        return GateDecision(False, "invalid_rc_id", (str(exc),))
    if not rc_ref:
        return GateDecision(False, "missing_rc_ref")
    if not _HEX40_RE.fullmatch(source_commit):
        return GateDecision(False, "invalid_source_commit")
    if not release_ticket_ref:
        return GateDecision(False, "missing_release_ticket_ref")
    if artifact_manifest_sha256 is not None and not _HEX64_RE.fullmatch(artifact_manifest_sha256):
        return GateDecision(False, "invalid_artifact_manifest_sha256")
    return GateDecision(True)


def _validate_rc_id(rc_id: str) -> None:
    if not _RC_ID_RE.fullmatch(rc_id):
        raise ValueError(f"invalid release candidate id: {rc_id!r}")


def _transition_log_entry(
    *,
    old_state: str,
    new_state: str,
    actor: str,
    evidence_ref: str,
    transitioned_at: str,
) -> dict[str, str]:
    return {
        "from": old_state,
        "to": new_state,
        "actor": actor,
        "evidence_ref": evidence_ref,
        "transitioned_at": transitioned_at,
    }


def _merge_updates(record: dict[str, Any], updates: Mapping[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(record.get(key), Mapping):
            merged = dict(record[key])
            _merge_updates(merged, value)
            record[key] = merged
        else:
            record[key] = deepcopy(value)


def _bind_entry_evidence(record: dict[str, Any], new_state: str, evidence_ref: str) -> None:
    promotion_evidence = record.setdefault("promotion_evidence", {})
    if new_state == REHEARSAL_PASSED:
        promotion_evidence["fresh_tenant_rehearsal_ref"] = evidence_ref
    elif new_state == PROMOTION_RATIFIED:
        record["ratification_ref"] = evidence_ref
    elif new_state == DOGFOOD_RING_CONSUMED:
        promotion_evidence["dogfood_ring_ref"] = evidence_ref
    elif new_state == CLOSED:
        record["closure_ref"] = evidence_ref


def _lookup_candidate_field(bundle: Mapping[str, Any], key: str) -> Any:
    if key in bundle:
        return bundle[key]
    candidate = bundle.get("candidate")
    if isinstance(candidate, Mapping):
        return candidate.get(key)
    return None


def _stage_names(bundle: Mapping[str, Any]) -> frozenset[str]:
    raw_stages = bundle.get("stages") or []
    names: set[str] = set()
    if isinstance(raw_stages, Sequence) and not isinstance(raw_stages, (str, bytes)):
        for stage in raw_stages:
            if isinstance(stage, str):
                names.add(stage)
            elif isinstance(stage, Mapping) and stage.get("name"):
                names.add(str(stage["name"]))
    return frozenset(names)


def _mounted_developer_checkout(bundle: Mapping[str, Any]) -> bool:
    context = bundle.get("fresh_tenant_context")
    if isinstance(context, Mapping) and context.get("mounted_developer_checkout") is True:
        return True
    return bundle.get("mounted_developer_checkout") is True


def _image_requires_digest_exception(bundle: Mapping[str, Any]) -> bool:
    image_digest = bundle.get("container_image_digest")
    if image_digest:
        return False
    image = bundle.get("container_image")
    if not isinstance(image, str) or not image:
        return False
    return "@sha256:" not in image


def _evidence_ref_is_accepted(
    evidence_ref: Any,
    evidence_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if evidence_registry is None:
        return True
    evidence = evidence_registry.get(str(evidence_ref))
    return bool(evidence and evidence.get("accepted") is True)


def _dogfood_evidence_binds_record(
    evidence_ref: Any,
    record: Mapping[str, Any],
    evidence_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if evidence_registry is None:
        return True
    evidence = evidence_registry.get(str(evidence_ref))
    if not evidence or evidence.get("accepted") is not True:
        return False
    if str(evidence.get("rc_id")) != str(record.get("rc_id")):
        return False
    if str(evidence.get("source_commit")).lower() != str(record.get("source_commit")).lower():
        return False
    expected_digest = record.get("artifact_manifest_sha256")
    if expected_digest is None:
        return evidence.get("artifact_manifest_sha256") in (None, "")
    return str(evidence.get("artifact_manifest_sha256")).lower() == str(expected_digest).lower()


def _deploy_claims_have_persistent_probes(
    deploy_class_claims: Sequence[Mapping[str, Any] | str],
    persistent_probe_refs: Sequence[Any],
) -> bool:
    if not deploy_class_claims:
        return True
    probe_ref_set = {str(ref) for ref in persistent_probe_refs if ref}
    if not probe_ref_set:
        return False
    for claim in deploy_class_claims:
        if isinstance(claim, Mapping):
            probe_ref = claim.get("persistent_state_probe_ref")
            if str(probe_ref) not in probe_ref_set:
                return False
        else:
            # Fail-closed: non-Mapping claims cannot name a probe_ref; refuse immediately.
            return False
    return True
