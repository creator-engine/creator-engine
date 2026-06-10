"""Peer-authority validation (v3.5-C A-C3 — design §A.5, Hardest Problem 1).

Validates the repo coordination policy (`.ce/coordination.yml`,
`kind: coordination-policy`) against
`schemas/coordination-policy.schema.yaml` plus the peer-authority invariants —
**per-area ownership × a risk-tiered quorum** for two solo-dev peers (no
BDFL). This is NOT a new authority engine: it re-parameterizes the existing
CODEOWNERS + `mutation_class` + independent-review machinery:

- the policy block is well-formed (quorum floors: `privileged >= 2`,
  `non_privileged >= 1`; `no_self_approval` pinned true; an area
  configuration present — `defer_to_codeowners` and/or `area_owners`);
- the policy file is SELF-CLASSIFIED ``governance`` (schema const): changing
  the authority map is privileged → both peers;
- a **privileged** (`PRIVILEGED_NAMES`) ratification carries the required
  quorum of **distinct humans** (both peers);
- a **cross-area** change carries the owning area's peer;
- **no self-approval**: the author's (or seat's) human never counts as a
  ratifier.

**Identity resolution (the §11.5 gap, shipped honestly).** Quorums count
HUMANS, not accounts: every actor label (git author, PR approver, running
seat, App installation) resolves through the policy's ``identity_map`` to a
``human_id``. Two logins of one human are ONE ratifier. An actor that does
NOT resolve **fails closed** (`VAL-PA-IDENTITY-UNRESOLVED`) — it surfaces as
an escalation and never silently counts toward a quorum. Token/account
separation alone is NOT sufficient (CE's own rule); the resolver's declared
limits are documented in `docs/contracts/peer-authority.md`.

The live enforcement path is the generalized
``forge.plan_approval.plan_approved`` (which lazily consumes
:func:`authority_satisfied` below); this check grades the offline/auditable
record form.

This is a **shared** check: it imports the shared engine plus the shared
check module ``mutation_class`` (``PRIVILEGED_NAMES`` — reused verbatim, a
shared→shared edge); it MUST NOT import a v3 module (the `version_boundary`
CODE_UNALLOWED ratchet).

See:
  - `docs/contracts/peer-authority.md`
  - `schemas/coordination-policy.schema.yaml`
  - `docs/contracts/authority-matrix.md` (the role_category × privileged-class
    baseline — a DIFFERENT axis this check references, not a replacement)
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .mutation_class import PRIVILEGED_NAMES

CHECK_NAME = "peer_authority"
CONTRACT = "docs/contracts/peer-authority.md"
SCHEMA = "schemas/coordination-policy.schema.yaml"
KIND_VALUE = "coordination-policy"

# Failure codes (explicit error classes).
CODE_SCHEMA = "VAL-PA-SCHEMA"
CODE_INVALID = "VAL-PA-INVALID"
CODE_AREA_CONFIG = "VAL-PA-AREA-CONFIG"
CODE_QUORUM = "VAL-PA-QUORUM"
CODE_SELF_APPROVAL = "VAL-PA-SELF-APPROVAL"
CODE_AREA_OWNER_MISSING = "VAL-PA-AREA-OWNER-MISSING"
CODE_IDENTITY_UNRESOLVED = "VAL-PA-IDENTITY-UNRESOLVED"


# --- pure authority helpers (also consumed, lazily, by forge.plan_approval) ---

def resolve_actor(actor: str, policy: dict[str, Any]) -> str | None:
    """Resolve an actor label to a ``human_id`` via the policy ``identity_map``.

    The {git author, PR approver, running seat, App installation} → human
    mapping. Returns ``None`` when the actor does not resolve — callers MUST
    fail closed on ``None`` (escalate; never assume).
    """
    identity_map = policy.get("identity_map")
    humans = identity_map.get("humans") if isinstance(identity_map, dict) else None
    if not isinstance(humans, list):
        return None
    for human in humans:
        if not isinstance(human, dict):
            continue
        human_id = human.get("human_id")
        if not isinstance(human_id, str):
            continue
        if actor == human_id:
            return human_id
        for axis in ("github_logins", "seats", "app_installations"):
            labels = human.get(axis)
            if isinstance(labels, list) and actor in labels:
                return human_id
    return None


def required_quorum(policy: dict[str, Any], mutation_class: str | None) -> int:
    """The ratifier count the risk tier requires (privileged → both peers)."""
    authority = policy.get("ratification_authority")
    tiers = authority.get("quorum_by_tier") if isinstance(authority, dict) else None
    tiers = tiers if isinstance(tiers, dict) else {}
    if mutation_class in PRIVILEGED_NAMES:
        value = tiers.get("privileged")
        return value if isinstance(value, int) else 2
    value = tiers.get("non_privileged")
    return value if isinstance(value, int) else 1


def areas_for_paths(
    policy: dict[str, Any], changed_paths: Iterable[str]
) -> dict[str, list[str]]:
    """Map each declared area glob touched by ``changed_paths`` to its owners."""
    authority = policy.get("ratification_authority")
    area_owners = authority.get("area_owners") if isinstance(authority, dict) else None
    if not isinstance(area_owners, dict):
        return {}
    touched: dict[str, list[str]] = {}
    for pattern, owners in area_owners.items():
        if not isinstance(pattern, str) or not isinstance(owners, list):
            continue
        for raw in changed_paths:
            if PurePosixPath(str(raw)).full_match(pattern):
                touched[pattern] = [o for o in owners if isinstance(o, str)]
                break
    return touched


def authority_satisfied(
    policy: dict[str, Any],
    *,
    author: str,
    approvers: Iterable[str],
    seat: str | None = None,
    mutation_class: str | None = None,
    changed_paths: Iterable[str] = (),
) -> tuple[bool, list[str]]:
    """Grade one ratification against the area+tier authority map.

    Returns ``(ok, reasons)`` — ``reasons`` name every violated rule (an empty
    list iff ``ok``). Quorum counts DISTINCT resolved humans; the author's and
    seat's humans never count (no self-approval); an unresolved actor fails
    closed. Every touched declared area needs one of its owners among the
    ratifiers — except an area the AUTHOR's human owns, which authorship
    itself covers (you are the constrained-BDFL of your own area, design
    §A.5; independence is supplied by the quorum rule, not by double-counting
    the owner).
    """
    reasons: list[str] = []
    paths = list(changed_paths)

    author_human = resolve_actor(author, policy)
    if author_human is None:
        reasons.append(f"author {author!r} does not resolve to a human (fail-closed)")
    seat_human = resolve_actor(seat, policy) if seat else None
    if seat and seat_human is None:
        reasons.append(f"seat {seat!r} does not resolve to a human (fail-closed)")

    ratifier_humans: set[str] = set()
    for approver in approvers:
        human = resolve_actor(approver, policy)
        if human is None:
            reasons.append(
                f"approver {approver!r} does not resolve to a human (fail-closed; "
                "does not count toward quorum)"
            )
            continue
        if human == author_human or (seat_human is not None and human == seat_human):
            reasons.append(
                f"approver {approver!r} resolves to the author/seat human "
                f"{human!r} (no self-approval)"
            )
            continue
        ratifier_humans.add(human)

    quorum = required_quorum(policy, mutation_class)
    if len(ratifier_humans) < quorum:
        tier = "privileged" if mutation_class in PRIVILEGED_NAMES else "non_privileged"
        reasons.append(
            f"quorum not met: {len(ratifier_humans)} distinct independent human "
            f"ratifier(s) < required {quorum} for {tier} tier "
            f"(mutation_class={mutation_class!r})"
        )

    covering = set(ratifier_humans)
    if author_human is not None:
        covering.add(author_human)  # an author covers the areas they own
    for pattern, owners in areas_for_paths(policy, paths).items():
        if not (set(owners) & covering):
            reasons.append(
                f"cross-area change touches {pattern!r} but no owning peer "
                f"({owners!r}) is among the ratifiers (or the author)"
            )

    return (not reasons, reasons)


# --- discovery + the registered check ----------------------------------------

def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def iter_policy_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate coordination-policy files under ``paths``."""
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


def _check_area_config(policy: dict[str, Any], path: Path) -> list[ValidationError]:
    """An area configuration must exist: defer_to_codeowners and/or area_owners."""
    authority = policy.get("ratification_authority")
    if not isinstance(authority, dict):
        return []  # the schema already rejects this shape
    defer = authority.get("defer_to_codeowners") is True
    owners = authority.get("area_owners")
    has_owners = isinstance(owners, dict) and bool(owners)
    if defer or has_owners:
        return []
    return [make_error(
        CODE_AREA_CONFIG, path, "ratification_authority",
        "the authority map needs an area configuration: defer_to_codeowners: true "
        "and/or a non-empty area_owners map",
        CONTRACT,
    )]


def _check_ratifications(policy: dict[str, Any], path: Path) -> list[ValidationError]:
    """Grade each recorded ratification attestation against the policy."""
    ratifications = policy.get("ratifications")
    if not isinstance(ratifications, list):
        return []
    errors: list[ValidationError] = []
    for idx, entry in enumerate(ratifications):
        if not isinstance(entry, dict):
            continue
        ok, reasons = authority_satisfied(
            policy,
            author=str(entry.get("author", "")),
            seat=entry.get("seat"),
            approvers=[a for a in entry.get("approvers", []) if isinstance(a, str)],
            mutation_class=entry.get("mutation_class"),
            changed_paths=[p for p in entry.get("changed_paths", []) if isinstance(p, str)],
        )
        if ok:
            continue
        for reason in reasons:
            if "does not resolve" in reason:
                code = CODE_IDENTITY_UNRESOLVED
            elif "no self-approval" in reason:
                code = CODE_SELF_APPROVAL
            elif "cross-area" in reason:
                code = CODE_AREA_OWNER_MISSING
            else:
                code = CODE_QUORUM
            errors.append(make_error(
                code, path, f"ratifications/{idx}",
                f"item {entry.get('item_ref')!r}: {reason}",
                CONTRACT,
            ))
    return errors


def validate_policy(policy: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one coordination policy against schema + invariants."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(policy, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_area_config(policy, path))
    errors.extend(_check_ratifications(policy, path))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_AREA_CONFIG, CODE_QUORUM, CODE_SELF_APPROVAL,
     CODE_AREA_OWNER_MISSING, CODE_IDENTITY_UNRESOLVED],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_policy_records([Path(p) for p in paths]):
        try:
            policy = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(policy, dict):
            continue
        errors.extend(validate_policy(policy, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
