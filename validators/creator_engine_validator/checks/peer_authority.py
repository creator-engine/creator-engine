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
from .decision_record import iter_decision_records
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
# N=1 carve-out (the honest `quorum: n1_solo` recording mode). These are NEW
# failure CLASSES on the EXISTING check — no new check, no check-count delta.
CODE_N1_SOLO_EXPIRED = "VAL-PA-N1-SOLO-EXPIRED"
CODE_N1_SOLO_REQUIRED = "VAL-PA-N1-SOLO-REQUIRED"

# The only lawful value of the honest solo-mode marker.
N1_SOLO = "n1_solo"


# --- pure authority helpers (also consumed, lazily, by forge.plan_approval) ---


def distinct_humans(policy: dict[str, Any]) -> set[str]:
    """The set of DISTINCT ``human_id`` values the policy resolves.

    Quorum cardinality counts HUMANS, never accounts/seats/app-installations.
    Invalid or empty ``human_id`` entries are not counted (they remain
    schema/identity failures handled elsewhere). The N=1 carve-out keys every
    map-sensitive decision (auto-expiry, laundered-quorum) off ``len`` of this
    set: exactly 1 ⇒ the native solo mode; ≥ 2 ⇒ team mode (solo records
    expire).
    """
    identity_map = policy.get("identity_map")
    humans = identity_map.get("humans") if isinstance(identity_map, dict) else None
    resolved: set[str] = set()
    if isinstance(humans, list):
        for human in humans:
            if not isinstance(human, dict):
                continue
            human_id = human.get("human_id")
            if isinstance(human_id, str) and human_id:
                resolved.add(human_id)
    return resolved

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
    quorum_mode: str | None = None,
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

    ``quorum_mode`` is the honest solo-mode marker recorded on the ratification
    (``n1_solo`` or ``None``). Callers that omit it keep the pre-carve-out
    tier-based behaviour exactly. With ``quorum_mode == "n1_solo"`` the privileged
    cardinality passes ONLY when the map resolves exactly one human and one
    independent resolved ratifier is present; it AUTO-EXPIRES once the map
    resolves ≥ 2 humans. With it omitted, a privileged record leaning on the
    SOLE resolved human is failed with the precise laundered-quorum guard
    (record the honest solo mode) rather than the generic quorum shortfall.
    """
    reasons: list[str] = []
    paths = list(changed_paths)
    privileged = mutation_class in PRIVILEGED_NAMES

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

    humans = distinct_humans(policy)
    if quorum_mode == N1_SOLO:
        # Honest solo mode: a recording of the quorum CARDINALITY, not a bypass.
        if not privileged:
            reasons.append(
                f"quorum: n1_solo is reserved for privileged ratifications "
                f"(mutation_class={mutation_class!r} is non-privileged; non-privileged "
                "area ownership is the existing solo-owner behaviour and needs no marker)"
            )
        elif len(humans) >= 2:
            reasons.append(
                f"quorum: n1_solo auto-expired: the identity map now resolves "
                f"{len(humans)} distinct humans (>= 2); the solo carve-out is no longer "
                "valid (automatic expiry at the second human, not a manual migration)"
            )
        elif len(ratifier_humans) < 1:
            reasons.append(
                "quorum: n1_solo names no independent resolved human ratifier — the sole "
                "human must actually ratify (fail-closed; the marker is never solo authority "
                "on its own)"
            )
        # else: exactly one human + one independent resolved ratifier ⇒ lawful solo.
    else:
        quorum = required_quorum(policy, mutation_class)
        if len(ratifier_humans) < quorum:
            if privileged and len(humans) == 1 and len(ratifier_humans) == 1:
                # Laundered-quorum guard: a one-human map can NEVER reach the
                # privileged floor of 2 — the record is leaning on the sole
                # human and must record the honest solo mode (quorum: n1_solo).
                reasons.append(
                    f"privileged ratification under a one-human identity map relies on the "
                    f"sole human {sorted(ratifier_humans)!r} but omits quorum: n1_solo "
                    f"(laundered quorum: distinct humans = 1, not the privileged floor of "
                    f"{quorum} — accounts do not sum to humans; record the honest solo mode)"
                )
            else:
                tier = "privileged" if privileged else "non_privileged"
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


def _reason_code(reason: str) -> str:
    """Map an ``authority_satisfied`` reason string to its failure class."""
    if "does not resolve" in reason:
        return CODE_IDENTITY_UNRESOLVED
    if "no self-approval" in reason:
        return CODE_SELF_APPROVAL
    if "cross-area" in reason:
        return CODE_AREA_OWNER_MISSING
    if "auto-expired" in reason:
        return CODE_N1_SOLO_EXPIRED
    # The laundered-quorum guard and the reserved-for-privileged misuse both
    # name the marker; their precise class is VAL-PA-N1-SOLO-REQUIRED.
    if N1_SOLO in reason:
        return CODE_N1_SOLO_REQUIRED
    return CODE_QUORUM


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
            quorum_mode=entry.get("quorum"),
        )
        if ok:
            continue
        for reason in reasons:
            code = _reason_code(reason)
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


# --- N=1 Decision-Record cross-check (map-sensitive: auto-expiry / laundered) --

def _policy_scope_root(policy_path: Path) -> Path:
    """The directory whose Decision Records a coordination policy governs.

    A repo policy lives at ``<root>/.ce/coordination.yml`` and governs records
    under ``<root>``; a co-located fixture policy at ``<dir>/coordination.yml``
    governs records under ``<dir>``. Returns an absolute path.
    """
    resolved = policy_path.resolve()
    parent = resolved.parent
    if parent.name == ".ce":
        return parent.parent
    return parent


def _governs(dr_path: Path, policy_path: Path, policy: dict[str, Any]) -> bool:
    """Does ``policy`` govern ``dr_path``'s decision AREA?

    A record is in scope iff its path — taken relative to the policy's scope
    root — matches one of the policy's declared ``area_owners`` globs. This is
    the §10 fixture-scoping guard: the repo policy declares only its decision
    surfaces (``docs/decisions/**`` / ``docs/rfcs/**``), so unrelated example
    Decision Records (e.g. ``validators/examples/decision-record/``, which have
    NO co-located coordination policy) are NOT graded against the repo's
    one-human identity map; each co-located N=1 fixture is graded only against
    its own neighbouring policy.
    """
    authority = policy.get("ratification_authority")
    area_owners = authority.get("area_owners") if isinstance(authority, dict) else None
    if not isinstance(area_owners, dict) or not area_owners:
        return False
    try:
        rel = dr_path.resolve().relative_to(_policy_scope_root(policy_path))
    except ValueError:
        return False
    rel_posix = PurePosixPath(rel.as_posix())
    for pattern in area_owners:
        if not isinstance(pattern, str):
            continue
        try:
            if rel_posix.full_match(pattern):
                return True
        except (ValueError, TypeError):
            continue
    return False


def grade_decision_record_quorum(
    policy: dict[str, Any], dr_path: Path, record: dict[str, Any]
) -> list[ValidationError]:
    """Grade one governed Decision Record's ``ratification.quorum`` against the
    policy's CURRENT identity map.

    Map-sensitive ONLY (auto-expiry at the second human; the laundered-quorum
    guard); it does not re-verify the record's other Decision-Record invariants
    (those are the ``decision_record`` check's job) nor the truth of its
    ``evidence_refs``. Applies solely to accepted privileged records — the
    surface where a ratifier could be leaning on the sole human to satisfy
    privileged authority.
    """
    if record.get("status") != "accepted":
        return []
    if record.get("mutation_class") not in PRIVILEGED_NAMES:
        # `quorum: n1_solo` on a non-privileged record is a DR-shape misuse,
        # owned by the decision_record check (VAL-DR-N1-SOLO-MISUSED).
        return []
    ratification = record.get("ratification")
    if not isinstance(ratification, dict):
        return []  # accepted-without-ratification is the decision_record check's job
    quorum = ratification.get("quorum")
    ratified_by = ratification.get("ratified_by")
    makers = record.get("decision_makers")
    makers = makers if isinstance(makers, list) else []
    humans = distinct_humans(policy)
    ratifier_human = resolve_actor(ratified_by, policy) if isinstance(ratified_by, str) else None
    maker_humans = {resolve_actor(m, policy) for m in makers if isinstance(m, str)}
    maker_humans.discard(None)

    field = "ratification/quorum"
    if quorum == N1_SOLO:
        if len(humans) >= 2:
            return [make_error(
                CODE_N1_SOLO_EXPIRED, dr_path, field,
                f"quorum: n1_solo auto-expired: the coordination-policy identity map now "
                f"resolves {len(humans)} distinct humans (>= 2); the solo carve-out is no "
                "longer valid (automatic expiry at the second human, not a migration)",
                CONTRACT,
            )]
        if len(humans) != 1:
            return [make_error(
                CODE_N1_SOLO_EXPIRED, dr_path, field,
                f"quorum: n1_solo requires exactly one resolved human in the identity map; "
                f"found {len(humans)}",
                CONTRACT,
            )]
        if ratifier_human is None:
            return [make_error(
                CODE_IDENTITY_UNRESOLVED, dr_path, "ratification/ratified_by",
                f"ratified_by {ratified_by!r} does not resolve to a human through the "
                "identity_map (fail-closed; an unresolved ratifier never counts as solo "
                "authority)",
                CONTRACT,
            )]
        if ratifier_human in maker_humans:
            return [make_error(
                CODE_SELF_APPROVAL, dr_path, "ratification/ratified_by",
                f"quorum: n1_solo does not bypass no-self-approval: ratifier {ratified_by!r} "
                f"resolves to the same human {ratifier_human!r} as a decision_maker",
                CONTRACT,
            )]
        return []  # exactly one human + an independent resolved ratifier ⇒ lawful solo
    # quorum omitted on a privileged accepted record: laundered-quorum guard.
    # A one-human map can never reach the privileged floor of 2; a record whose
    # ratifier resolves to that sole human is leaning on them — possibly while
    # spreading author/ratifier across two ACCOUNTS of the same human to mimic
    # independence. The honest record marks quorum: n1_solo (string-distinct
    # accounts dodge the decision_record self-ratification check, so this
    # human-level guard is where account-multiplicity laundering is caught).
    if len(humans) == 1 and ratifier_human is not None and ratifier_human in humans:
        return [make_error(
            CODE_N1_SOLO_REQUIRED, dr_path, field,
            f"privileged accepted Decision Record under a one-human identity map relies on "
            f"the sole human {ratifier_human!r} to satisfy privileged authority but omits "
            "quorum: n1_solo (laundered quorum: distinct humans = 1, not the privileged "
            "floor of 2 — accounts do not sum to humans; record the honest solo mode)",
            CONTRACT,
        )]
    return []


def _cross_check_decision_records(
    paths: list[Path], policies: list[tuple[Path, dict[str, Any]]]
) -> list[ValidationError]:
    """Grade every governed Decision Record's quorum mode against its owning
    policy's identity map. Parse errors for self-named records are surfaced by
    the decision_record check, not duplicated here."""
    if not policies:
        return []
    records, _parse_errors = iter_decision_records(paths)
    errors: list[ValidationError] = []
    for dr_path, record in records:
        for policy_path, policy in policies:
            if _governs(dr_path, policy_path, policy):
                errors.extend(grade_decision_record_quorum(policy, dr_path, record))
    return errors


# --- the registered check ------------------------------------------------------

@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_AREA_CONFIG, CODE_QUORUM, CODE_SELF_APPROVAL,
     CODE_AREA_OWNER_MISSING, CODE_IDENTITY_UNRESOLVED,
     CODE_N1_SOLO_EXPIRED, CODE_N1_SOLO_REQUIRED],
)
def run(paths: Iterable[Path]) -> CheckResult:
    path_list = [Path(p) for p in paths]
    errors: list[ValidationError] = []
    policies: list[tuple[Path, dict[str, Any]]] = []
    for record_path in iter_policy_records(path_list):
        try:
            policy = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(policy, dict):
            continue
        errors.extend(validate_policy(policy, record_path))
        policies.append((record_path, policy))
    errors.extend(_cross_check_decision_records(path_list, policies))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
