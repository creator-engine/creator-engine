"""Ticket-class policy registry loader and validation API (CE624).

This module provides the authoritative, versioned class-policy registry for
autonomous ticket pickup. It is a read-only data-binding layer: it loads the
YAML registry, validates every field with strict fail-closed rules, and exposes
typed frozen dataclasses + accessor functions for the belt to consume.

Design invariants:
  - No network, no subprocess, no disk write. Pure load + validate.
  - Strict unknown-key refusal: any unexpected top-level or per-entry key raises
    TicketClassRegistryError with a field-level message (mirror automerge_policy.py
    error style).
  - v1 activation rule: any class entry with auto_pickup: true MUST carry a
    non-empty, non-whitespace enabling_decision_ref. Violation raises
    TicketClassRegistryError.
  - Approver sets are named references only; no usernames are stored or resolved
    here. Resolution against the identity registry happens at live-recheck time
    inside the belt.
  - Territory denylist takes precedence over allowlist: path_in_territory checks
    the denylist first; a denylist match returns False regardless of allowlist.
  - Path normalization refusal: path_in_territory refuses (returns False) any
    path that is absolute, contains '..', contains a backslash, or starts with
    './'. No silent normalization is performed.
  - Load-time governance cross-check: any class whose allowed_mutation_classes
    does not include 'governance' must not admit any canonical governance probe
    path through its territory (allowlist minus denylist). Violation is refused
    at load time.
  - Load-time selector ambiguity check: registry refuses load if any two class
    entries' required_labels sets are in a subset relation (one is a subset of
    the other), which would make class_for_labels() produce ambiguous results.
  - Imports: stdlib + yaml only (mirrors mutation_classifier.py import posture).
  - NOT wired into pickup.py. That bridge is CE618-1 territory (dev-3).
"""
from __future__ import annotations

import fnmatch
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml

from ..work_sizing import MUTATION_CLASSES, WORK_CLASSES

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Path to the bundled YAML registry (co-located with this module).
DEFAULT_REGISTRY_PATH: Final[Path] = Path(__file__).with_name(
    "ticket_class_registry.yaml"
)

#: Supported registry_version values. Any other value is refused.
SUPPORTED_REGISTRY_VERSIONS: Final[frozenset[int]] = frozenset({1})

#: v1 activation posture — all classes must have auto_pickup: false unless
#: explicitly armed via enabling_decision_ref.
REGISTRY_V1_ACTIVATION_POSTURE: Final[str] = "advisory"

#: Valid collision policy values for a territory entry.
VALID_COLLISION_POLICIES: Final[frozenset[str]] = frozenset({"refuse", "queue"})

#: Valid role values for a class entry.
VALID_ROLES: Final[frozenset[str]] = frozenset(
    {"implementer", "reviewer", "architect", "verification"}
)

#: Valid lane_kind values for a class entry (subset of lane_runtime.LANE_KINDS).
VALID_LANE_KINDS: Final[frozenset[str]] = frozenset(
    {"implementation", "review", "read-only", "approval", "merge", "audit"}
)

#: Valid live_recheck identifiers. New checks must be added here before use.
VALID_LIVE_RECHECKS: Final[frozenset[str]] = frozenset(
    {
        "approval_label_present",
        "applier_in_approver_set",
        "no_open_claim",
        "no_linked_open_pr",
        "base_branch_head_fetched",
    }
)

#: Canonical governance probe paths used for load-time territory safety checks.
#: These correspond to the governance predicates in automerge_mutation_policy.yaml.
#: Any class whose allowed_mutation_classes does not include 'governance' must
#: not admit any of these paths through its territory (allowlist minus denylist).
GOVERNANCE_PROBE_PATHS: Final[tuple[str, ...]] = (
    "docs/decisions/PROBE.md",
    "docs/adr/PROBE.md",
    "docs/governance/PROBE.md",
    "GOVERNANCE.md",
    ".ce/contracts/PROBE.yaml",
)

# Top-level YAML keys allowed in the registry document.
_REGISTRY_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {"registry_version", "activation_posture", "approver_sets", "classes"}
)

# Keys allowed inside an approver_set entry.
_APPROVER_SET_KEYS: Final[frozenset[str]] = frozenset(
    {"description", "resolution_ref"}
)

# Keys allowed inside a class entry.
_CLASS_ENTRY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "description",
        "selectors",
        "approver_allowlist_ref",
        "allowed_work_classes",
        "allowed_mutation_classes",
        "territory",
        "role",
        "lane_kind",
        "auto_pickup",
        "enabling_decision_ref",
        "live_rechecks",
        "retry",
    }
)

# Keys allowed inside a selectors block.
_SELECTORS_KEYS: Final[frozenset[str]] = frozenset(
    {"required_labels", "issue_repo_scope"}
)

# Keys allowed inside a territory block.
_TERRITORY_KEYS: Final[frozenset[str]] = frozenset(
    {"path_glob_allowlist", "path_glob_denylist", "collision_policy"}
)

# Keys allowed inside a retry block.
_RETRY_KEYS: Final[frozenset[str]] = frozenset({"max_attempts", "on_exhaust"})


# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------


class TicketClassRegistryError(Exception):
    """Ticket-class registry could not be loaded or validated safely.

    The ``field`` attribute names the registry field or structural context
    that triggered the refusal (mirrors AutoMergePolicyStateError style).
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field: str | None = field


# ---------------------------------------------------------------------------
# Frozen dataclasses (the typed registry model)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApproverSet:
    """A named set of approvers resolved externally at live-recheck time.

    Members are NEVER embedded in this dataclass. The resolution_ref points
    to the external identity registry query that resolves the set.
    """

    description: str
    resolution_ref: str


@dataclass(frozen=True)
class TerritoryPolicy:
    """Path-glob allowlist + optional denylist and collision treatment.

    Evaluation order (enforced by path_in_territory):
    1. Denylist checked first — any denylist match returns False immediately.
    2. Allowlist checked second — at least one allowlist match required for True.

    The denylist enables a class to use a broad allowlist glob (e.g. ``docs/**``)
    while explicitly excluding governance or other privileged sub-trees.
    """

    path_glob_allowlist: tuple[str, ...]
    path_glob_denylist: tuple[str, ...]  # empty tuple when not set
    collision_policy: str  # "refuse" | "queue"


@dataclass(frozen=True)
class RetryPolicy:
    """Retry configuration for a ticket class."""

    max_attempts: int
    on_exhaust: str  # "manual-exception" (only value in v1)


@dataclass(frozen=True)
class TicketClassEntry:
    """A single, fully-specified ticket class policy unit.

    All fields are present and validated; no optional fields may be absent
    after a successful load (enabling_decision_ref is None when not set).
    """

    id: str
    description: str
    selectors_required_labels: frozenset[str]
    selectors_issue_repo_scope: str
    approver_allowlist_ref: str
    allowed_work_classes: frozenset[str]
    allowed_mutation_classes: frozenset[str]
    territory: TerritoryPolicy
    role: str
    lane_kind: str
    auto_pickup: bool
    enabling_decision_ref: str | None
    live_rechecks: tuple[str, ...]
    retry: RetryPolicy


@dataclass(frozen=True)
class TicketClassRegistry:
    """The versioned, fully-validated ticket-class registry.

    Instances are immutable; all container fields use tuples or frozensets.
    """

    registry_version: int
    activation_posture: str
    approver_sets: tuple[tuple[str, ApproverSet], ...]  # ordered pairs
    classes: tuple[TicketClassEntry, ...]

    def approver_set(self, name: str) -> ApproverSet | None:
        """Return the named ApproverSet, or None if not present."""
        for key, value in self.approver_sets:
            if key == name:
                return value
        return None


# ---------------------------------------------------------------------------
# Internal validation helpers
# ---------------------------------------------------------------------------


def _check_unknown_keys(
    mapping: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = set(mapping.keys()) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise TicketClassRegistryError(
            f"{context}: unknown key(s): {names}",
            field=context,
        )


def _require_str(value: Any, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TicketClassRegistryError(
            f"{field} must be a string", field=field
        )
    if not allow_empty and not value.strip():
        raise TicketClassRegistryError(
            f"{field} must be a non-empty string", field=field
        )
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise TicketClassRegistryError(
            f"{field} must be a boolean", field=field
        )
    return value


def _require_int(value: Any, field: str, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TicketClassRegistryError(
            f"{field} must be an integer", field=field
        )
    if value < minimum:
        raise TicketClassRegistryError(
            f"{field} must be >= {minimum}", field=field
        )
    return value


def _require_str_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or isinstance(value, (str, bytes)):
        raise TicketClassRegistryError(
            f"{field} must be a list", field=field
        )
    result = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise TicketClassRegistryError(
                f"{field}[{i}] must be a string", field=field
            )
        if not item.strip():
            raise TicketClassRegistryError(
                f"{field}[{i}] must be a non-empty string", field=field
            )
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Path safety validation
# ---------------------------------------------------------------------------


def _is_safe_path(path: str) -> bool:
    """Return True iff path is safe for territory evaluation.

    Unsafe forms (all return False — fail-closed):
      - Absolute path: starts with '/'
      - Traversal: contains '..' anywhere in the string
      - Windows separator: contains '\\'
      - Explicit dot-prefix: starts with './'

    No silent normalization is performed. Any unsafe form is treated as
    not-in-territory by path_in_territory.
    """
    if not path:
        return False
    if path.startswith("/"):
        return False
    if ".." in path:
        return False
    if "\\" in path:
        return False
    if path.startswith("./"):
        return False
    return True


# ---------------------------------------------------------------------------
# Per-block parsers
# ---------------------------------------------------------------------------


def _parse_approver_set(name: str, raw: Any) -> ApproverSet:
    if not isinstance(raw, Mapping):
        raise TicketClassRegistryError(
            f"approver_sets.{name} must be an object",
            field=f"approver_sets.{name}",
        )
    _check_unknown_keys(raw, _APPROVER_SET_KEYS, f"approver_sets.{name}")
    description = _require_str(
        raw.get("description", ""), f"approver_sets.{name}.description"
    )
    resolution_ref = _require_str(
        raw.get("resolution_ref"), f"approver_sets.{name}.resolution_ref"
    )
    return ApproverSet(description=description, resolution_ref=resolution_ref)


def _parse_territory(raw: Any, class_id: str) -> TerritoryPolicy:
    ctx = f"classes[{class_id!r}].territory"
    if not isinstance(raw, Mapping):
        raise TicketClassRegistryError(f"{ctx} must be an object", field=ctx)
    _check_unknown_keys(raw, _TERRITORY_KEYS, ctx)

    glob_list = _require_str_list(
        raw.get("path_glob_allowlist"), f"{ctx}.path_glob_allowlist"
    )
    if not glob_list:
        raise TicketClassRegistryError(
            f"{ctx}.path_glob_allowlist must be non-empty",
            field=f"{ctx}.path_glob_allowlist",
        )

    # path_glob_denylist is optional; defaults to empty.
    raw_denylist = raw.get("path_glob_denylist")
    if raw_denylist is None:
        deny_list: list[str] = []
    else:
        deny_list = _require_str_list(raw_denylist, f"{ctx}.path_glob_denylist")

    collision_policy = _require_str(
        raw.get("collision_policy"), f"{ctx}.collision_policy"
    )
    if collision_policy not in VALID_COLLISION_POLICIES:
        raise TicketClassRegistryError(
            f"{ctx}.collision_policy must be one of "
            f"{sorted(VALID_COLLISION_POLICIES)}; got {collision_policy!r}",
            field=f"{ctx}.collision_policy",
        )

    return TerritoryPolicy(
        path_glob_allowlist=tuple(glob_list),
        path_glob_denylist=tuple(deny_list),
        collision_policy=collision_policy,
    )


def _parse_retry(raw: Any, class_id: str) -> RetryPolicy:
    ctx = f"classes[{class_id!r}].retry"
    if not isinstance(raw, Mapping):
        raise TicketClassRegistryError(f"{ctx} must be an object", field=ctx)
    _check_unknown_keys(raw, _RETRY_KEYS, ctx)

    max_attempts = _require_int(
        raw.get("max_attempts"), f"{ctx}.max_attempts", minimum=1
    )
    on_exhaust = _require_str(raw.get("on_exhaust"), f"{ctx}.on_exhaust")

    return RetryPolicy(max_attempts=max_attempts, on_exhaust=on_exhaust)


def _parse_selectors(raw: Any, class_id: str) -> tuple[frozenset[str], str]:
    ctx = f"classes[{class_id!r}].selectors"
    if not isinstance(raw, Mapping):
        raise TicketClassRegistryError(f"{ctx} must be an object", field=ctx)
    _check_unknown_keys(raw, _SELECTORS_KEYS, ctx)

    label_list = _require_str_list(
        raw.get("required_labels"), f"{ctx}.required_labels"
    )
    if not label_list:
        raise TicketClassRegistryError(
            f"{ctx}.required_labels must be non-empty",
            field=f"{ctx}.required_labels",
        )

    issue_repo_scope = _require_str(
        raw.get("issue_repo_scope"), f"{ctx}.issue_repo_scope"
    )

    return frozenset(label_list), issue_repo_scope


def _parse_class_entry(
    raw: Any,
    index: int,
    known_approver_sets: frozenset[str],
) -> TicketClassEntry:
    if not isinstance(raw, Mapping):
        raise TicketClassRegistryError(
            f"classes[{index}] must be an object",
            field=f"classes[{index}]",
        )

    # Extract id early for richer error context.
    class_id = str(raw.get("id") or f"<index {index}>")
    ctx = f"classes[{class_id!r}]"

    _check_unknown_keys(raw, _CLASS_ENTRY_KEYS, ctx)

    _id = _require_str(raw.get("id"), f"{ctx}.id")
    description = _require_str(raw.get("description"), f"{ctx}.description")

    # selectors
    selectors_required_labels, selectors_issue_repo_scope = _parse_selectors(
        raw.get("selectors"), _id
    )

    # approver_allowlist_ref — must reference an existing approver set
    approver_allowlist_ref = _require_str(
        raw.get("approver_allowlist_ref"), f"{ctx}.approver_allowlist_ref"
    )
    if approver_allowlist_ref not in known_approver_sets:
        raise TicketClassRegistryError(
            f"{ctx}.approver_allowlist_ref {approver_allowlist_ref!r} does not "
            f"reference a defined approver set; defined sets: "
            f"{sorted(known_approver_sets)}",
            field=f"{ctx}.approver_allowlist_ref",
        )

    # allowed_work_classes
    raw_wc = raw.get("allowed_work_classes")
    work_class_list = _require_str_list(raw_wc, f"{ctx}.allowed_work_classes")
    if not work_class_list:
        raise TicketClassRegistryError(
            f"{ctx}.allowed_work_classes must be non-empty",
            field=f"{ctx}.allowed_work_classes",
        )
    for wc in work_class_list:
        if wc not in WORK_CLASSES:
            raise TicketClassRegistryError(
                f"{ctx}.allowed_work_classes contains unknown work class {wc!r}; "
                f"valid values: {list(WORK_CLASSES)}",
                field=f"{ctx}.allowed_work_classes",
            )
    allowed_work_classes = frozenset(work_class_list)

    # allowed_mutation_classes
    raw_mc = raw.get("allowed_mutation_classes")
    mutation_class_list = _require_str_list(raw_mc, f"{ctx}.allowed_mutation_classes")
    if not mutation_class_list:
        raise TicketClassRegistryError(
            f"{ctx}.allowed_mutation_classes must be non-empty",
            field=f"{ctx}.allowed_mutation_classes",
        )
    for mc in mutation_class_list:
        if mc not in MUTATION_CLASSES:
            raise TicketClassRegistryError(
                f"{ctx}.allowed_mutation_classes contains unknown mutation class "
                f"{mc!r}; valid values: {list(MUTATION_CLASSES)}",
                field=f"{ctx}.allowed_mutation_classes",
            )
    allowed_mutation_classes = frozenset(mutation_class_list)

    # territory
    territory = _parse_territory(raw.get("territory"), _id)

    # role
    role = _require_str(raw.get("role"), f"{ctx}.role")
    if role not in VALID_ROLES:
        raise TicketClassRegistryError(
            f"{ctx}.role {role!r} is not valid; expected one of "
            f"{sorted(VALID_ROLES)}",
            field=f"{ctx}.role",
        )

    # lane_kind
    lane_kind = _require_str(raw.get("lane_kind"), f"{ctx}.lane_kind")
    if lane_kind not in VALID_LANE_KINDS:
        raise TicketClassRegistryError(
            f"{ctx}.lane_kind {lane_kind!r} is not valid; expected one of "
            f"{sorted(VALID_LANE_KINDS)}",
            field=f"{ctx}.lane_kind",
        )

    # auto_pickup
    auto_pickup = _require_bool(raw.get("auto_pickup"), f"{ctx}.auto_pickup")

    # enabling_decision_ref (optional; required non-empty+non-whitespace when
    # auto_pickup is True — _require_str semantics enforced below)
    enabling_decision_ref_raw = raw.get("enabling_decision_ref")
    if enabling_decision_ref_raw is not None and not isinstance(
        enabling_decision_ref_raw, str
    ):
        raise TicketClassRegistryError(
            f"{ctx}.enabling_decision_ref must be a string or absent",
            field=f"{ctx}.enabling_decision_ref",
        )
    enabling_decision_ref: str | None = (
        enabling_decision_ref_raw if isinstance(enabling_decision_ref_raw, str)
        else None
    )

    # v1 activation rule: auto_pickup true requires enabling_decision_ref
    # that is non-empty AND non-whitespace (mirrors _require_str semantics).
    if auto_pickup:
        if not enabling_decision_ref or not enabling_decision_ref.strip():
            raise TicketClassRegistryError(
                f"{ctx}: auto_pickup is true but enabling_decision_ref is absent, "
                f"empty, or whitespace-only; registry v1 requires a non-empty "
                f"enabling_decision_ref before any class may be armed for "
                f"autonomous pickup",
                field=f"{ctx}.enabling_decision_ref",
            )

    # live_rechecks
    raw_lr = raw.get("live_rechecks")
    live_recheck_list = _require_str_list(raw_lr, f"{ctx}.live_rechecks")
    if not live_recheck_list:
        raise TicketClassRegistryError(
            f"{ctx}.live_rechecks must be non-empty",
            field=f"{ctx}.live_rechecks",
        )
    for lr in live_recheck_list:
        if lr not in VALID_LIVE_RECHECKS:
            raise TicketClassRegistryError(
                f"{ctx}.live_rechecks contains unknown recheck {lr!r}; "
                f"valid values: {sorted(VALID_LIVE_RECHECKS)}",
                field=f"{ctx}.live_rechecks",
            )

    # retry
    retry = _parse_retry(raw.get("retry"), _id)

    return TicketClassEntry(
        id=_id,
        description=description,
        selectors_required_labels=selectors_required_labels,
        selectors_issue_repo_scope=selectors_issue_repo_scope,
        approver_allowlist_ref=approver_allowlist_ref,
        allowed_work_classes=allowed_work_classes,
        allowed_mutation_classes=allowed_mutation_classes,
        territory=territory,
        role=role,
        lane_kind=lane_kind,
        auto_pickup=auto_pickup,
        enabling_decision_ref=enabling_decision_ref,
        live_rechecks=tuple(live_recheck_list),
        retry=retry,
    )


# ---------------------------------------------------------------------------
# Load-time cross-checks (run after all entries are parsed)
# ---------------------------------------------------------------------------


def _check_governance_territory_safety(
    entries: list[TicketClassEntry],
) -> None:
    """Refuse if any class without governance in allowed_mutation_classes
    admits a canonical governance probe path through its territory.

    This is a structural safety check: it verifies that broad allowlist globs
    (e.g. ``docs/**``) cannot inadvertently capture governance surfaces
    (``docs/decisions/**``, ``docs/adr/**``, ``docs/governance/**``,
    ``GOVERNANCE.md``, ``.ce/contracts/**``) for classes that are not
    permitted to touch governance paths.

    The check uses the same path_in_territory logic (denylist first, then
    allowlist) so a correctly set denylist will cause the class to pass.
    """
    for entry in entries:
        if "governance" in entry.allowed_mutation_classes:
            continue  # governance-capable class may touch governance paths
        for probe in GOVERNANCE_PROBE_PATHS:
            if path_in_territory(entry, probe):
                raise TicketClassRegistryError(
                    f"classes[{entry.id!r}]: territory admits governance probe "
                    f"path {probe!r} but allowed_mutation_classes does not "
                    f"include 'governance'; add a path_glob_denylist entry "
                    f"to exclude governance surfaces from this class territory",
                    field=f"classes[{entry.id!r}].territory",
                )


def _check_selector_ambiguity(entries: list[TicketClassEntry]) -> None:
    """Refuse if any two class entries' required_labels sets are in a subset
    relation, which would make class_for_labels() produce ambiguous results.

    The registry refuses load when selector sets are ambiguous (i.e. when one
    class's required_labels is a subset of another's). This replaces the
    'first match wins' ordering with a 'registry refuses ambiguous selectors
    at load' guarantee: if the registry loads, class_for_labels() is unambiguous
    for any label set.

    Practical rule: for every pair (A, B) where A.id != B.id, refuse if
    A.required_labels <= B.required_labels or B.required_labels <= A.required_labels.

    This covers both the direct subset case and the equal-sets case. Each class
    should carry a unique 'class:<id>' label so that its required_labels set is
    incomparable (neither a subset nor a superset) to any other class's set.
    """
    for i, a in enumerate(entries):
        for j, b in enumerate(entries):
            if i >= j:
                continue  # each pair checked once
            a_labels = a.selectors_required_labels
            b_labels = b.selectors_required_labels
            if a_labels <= b_labels or b_labels <= a_labels:
                raise TicketClassRegistryError(
                    f"ambiguous selector sets: classes[{a.id!r}] and "
                    f"classes[{b.id!r}] have required_labels in a subset "
                    f"relation ({sorted(a_labels)!r} vs {sorted(b_labels)!r}); "
                    f"each class must carry a unique 'class:<id>' label so that "
                    f"selector sets are pairwise non-comparable",
                    field="classes",
                )


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_ticket_class_registry(
    path: Path | str | None = None,
) -> TicketClassRegistry:
    """Load and validate the ticket-class registry from a YAML file.

    Parameters
    ----------
    path:
        Path to the registry YAML file. Defaults to the bundled
        ``ticket_class_registry.yaml`` co-located with this module.

    Returns
    -------
    TicketClassRegistry
        Frozen, fully-validated registry instance.

    Raises
    ------
    TicketClassRegistryError
        On any validation failure: unknown key, wrong type, unknown enum
        value, constraint violation (e.g. auto_pickup without
        enabling_decision_ref), governance territory leak, selector
        ambiguity, or malformed YAML.
    OSError
        If the file cannot be read.
    """
    resolved = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    try:
        raw_text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise TicketClassRegistryError(
            f"registry file not readable: {exc}", field="path"
        ) from exc

    try:
        payload = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise TicketClassRegistryError(
            f"registry YAML parse error: {exc}", field="yaml"
        ) from exc

    if not isinstance(payload, Mapping):
        raise TicketClassRegistryError(
            "registry document must be a YAML mapping at the top level",
            field="root",
        )

    _check_unknown_keys(payload, _REGISTRY_TOP_LEVEL_KEYS, "registry")

    # registry_version
    registry_version_raw = payload.get("registry_version")
    if not isinstance(registry_version_raw, int) or isinstance(
        registry_version_raw, bool
    ):
        raise TicketClassRegistryError(
            "registry_version must be an integer", field="registry_version"
        )
    if registry_version_raw not in SUPPORTED_REGISTRY_VERSIONS:
        raise TicketClassRegistryError(
            f"registry_version {registry_version_raw} is not supported; "
            f"supported versions: {sorted(SUPPORTED_REGISTRY_VERSIONS)}",
            field="registry_version",
        )

    # activation_posture
    activation_posture = _require_str(
        payload.get("activation_posture"), "activation_posture"
    )

    # approver_sets
    raw_sets = payload.get("approver_sets")
    if not isinstance(raw_sets, Mapping):
        raise TicketClassRegistryError(
            "approver_sets must be an object", field="approver_sets"
        )
    if not raw_sets:
        raise TicketClassRegistryError(
            "approver_sets must define at least one named set",
            field="approver_sets",
        )
    approver_set_pairs: list[tuple[str, ApproverSet]] = []
    for set_name, set_raw in raw_sets.items():
        parsed = _parse_approver_set(str(set_name), set_raw)
        approver_set_pairs.append((str(set_name), parsed))
    known_approver_set_names = frozenset(name for name, _ in approver_set_pairs)

    # classes
    raw_classes = payload.get("classes")
    if not isinstance(raw_classes, list):
        raise TicketClassRegistryError(
            "classes must be a list", field="classes"
        )
    class_entries: list[TicketClassEntry] = []
    seen_ids: set[str] = set()
    for i, raw_entry in enumerate(raw_classes):
        entry = _parse_class_entry(raw_entry, i, known_approver_set_names)
        if entry.id in seen_ids:
            raise TicketClassRegistryError(
                f"duplicate class id {entry.id!r}",
                field=f"classes[{entry.id!r}].id",
            )
        seen_ids.add(entry.id)
        class_entries.append(entry)

    # Cross-checks (run after all entries are parsed so checks can access
    # the full entry set).
    _check_governance_territory_safety(class_entries)
    _check_selector_ambiguity(class_entries)

    return TicketClassRegistry(
        registry_version=registry_version_raw,
        activation_posture=activation_posture,
        approver_sets=tuple(approver_set_pairs),
        classes=tuple(class_entries),
    )


# ---------------------------------------------------------------------------
# Accessor functions
# ---------------------------------------------------------------------------


def class_for_labels(
    registry: TicketClassRegistry,
    labels: Sequence[str] | frozenset[str],
) -> TicketClassEntry | None:
    """Return the first registry entry whose required_labels are all present
    in ``labels``, or None if no entry matches.

    The registry guarantees at load time that no two entries' required_labels
    sets are in a subset relation (see _check_selector_ambiguity). This means
    for any well-formed issue label set, at most one entry will match. The
    first-match scan is therefore deterministic and unambiguous.

    Parameters
    ----------
    registry:
        A loaded TicketClassRegistry instance.
    labels:
        The label set present on the issue (e.g. from forge API response).

    Returns
    -------
    TicketClassEntry | None
        The first matching entry, or None.
    """
    label_set = frozenset(labels)
    for entry in registry.classes:
        if entry.selectors_required_labels <= label_set:
            return entry
    return None


def is_pickup_permitted(entry: TicketClassEntry) -> bool:
    """Return True iff the registry entry permits autonomous pickup.

    In registry v1 this is always False (activation_posture: advisory).
    The function is provided for forward compatibility: when a class is armed
    (auto_pickup: true + enabling_decision_ref present and non-empty), this
    returns True.

    Note: the caller must also verify the live-recheck list passes before
    acting on a True return. This function only reflects the static policy.
    """
    return bool(entry.auto_pickup) and bool(
        entry.enabling_decision_ref and entry.enabling_decision_ref.strip()
    )


def path_in_territory(entry: TicketClassEntry, path: str) -> bool:
    """Return True iff ``path`` is admitted by the entry's territory policy.

    Evaluation order:
    1. Path safety check — any unsafe path form returns False immediately
       (fail-closed). Unsafe forms: absolute path (starts with '/'), traversal
       (contains '..'), backslash (contains '\\'), dot-slash prefix (starts
       with './'). No silent normalization is performed.
    2. Denylist — if any denylist glob matches, returns False immediately
       (denylist takes precedence over allowlist).
    3. Allowlist — returns True iff at least one allowlist glob matches.

    Uses ``fnmatch.fnmatch`` for glob evaluation (consistent with
    mutation_classifier.py).
    """
    if not _is_safe_path(path):
        return False  # fail-closed: unsafe path forms are not in territory

    # Denylist takes precedence over allowlist.
    for pattern in entry.territory.path_glob_denylist:
        if fnmatch.fnmatch(path, pattern):
            return False

    # Allowlist.
    for pattern in entry.territory.path_glob_allowlist:
        if fnmatch.fnmatch(path, pattern):
            return True

    return False


def all_paths_in_territory(
    entry: TicketClassEntry, paths: Sequence[str]
) -> bool:
    """Return True iff every path in ``paths`` is admitted by the entry's
    territory (denylist-first, then allowlist; unsafe paths fail-closed)."""
    return all(path_in_territory(entry, p) for p in paths)
