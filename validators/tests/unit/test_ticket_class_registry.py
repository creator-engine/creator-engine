"""Unit tests for the ticket-class policy registry (CE624).

Coverage:
  1. Round-trip load of the shipped YAML registry.
  2. Refusal paths: unknown top-level key, unknown key in class entry,
     unknown work class, unknown mutation class, missing approver set
     (empty approver_sets dict), undeclared approver_allowlist_ref,
     auto_pickup true without enabling_decision_ref (v1 activation rule),
     auto_pickup true WITH whitespace-only enabling_decision_ref (L1),
     auto_pickup true WITH enabling_decision_ref (should pass).
  3. Territory glob matching (path_in_territory, all_paths_in_territory).
     B1: denylist-first evaluation; governance probe paths denied on docs-only.
     M2: path normalization refusal (absolute, .., backslash, ./prefix).
     Load-time governance territory cross-check (B1).
  4. Selector matching (class_for_labels).
     M1: load-time selector ambiguity refusal.
  5. is_pickup_permitted semantics.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.forge.ticket_class_registry import (
    DEFAULT_REGISTRY_PATH,
    GOVERNANCE_PROBE_PATHS,
    TicketClassEntry,
    TicketClassRegistry,
    TicketClassRegistryError,
    all_paths_in_territory,
    class_for_labels,
    is_pickup_permitted,
    load_ticket_class_registry,
    path_in_territory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "registry.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _minimal_valid_yaml(
    *,
    auto_pickup: bool = False,
    enabling_decision_ref: str | None = None,
    extra_class_keys: str = "",
    extra_top_keys: str = "",
    approver_sets_block: str | None = None,
    work_classes: str = '["XS", "S"]',
    mutation_classes: str = '["docs"]',
) -> str:
    """Build a minimal valid (or intentionally invalid) registry YAML snippet."""
    edr_line = (
        f'    enabling_decision_ref: "{enabling_decision_ref}"'
        if enabling_decision_ref
        else ""
    )
    sets_block = (
        approver_sets_block
        if approver_sets_block is not None
        else """\
approver_sets:
  test-controllers:
    description: "test set"
    resolution_ref: "ce-ops:infra/identity-registry.yaml#role=controller"
"""
    )
    return f"""\
registry_version: 1
activation_posture: advisory
{sets_block}
{extra_top_keys}
classes:
  - id: test-class
    description: "A test class."
    selectors:
      required_labels:
        - "approved-for-implementation"
        - "class:test-class"
      issue_repo_scope: "creator-engine/ce-ops"
    approver_allowlist_ref: "test-controllers"
    allowed_work_classes: {work_classes}
    allowed_mutation_classes: {mutation_classes}
    territory:
      path_glob_allowlist:
        - "docs/**"
        - "*.md"
      collision_policy: refuse
    role: implementer
    lane_kind: implementation
    auto_pickup: {str(auto_pickup).lower()}
{edr_line}
{extra_class_keys}
    live_rechecks:
      - approval_label_present
      - applier_in_approver_set
      - no_open_claim
      - no_linked_open_pr
      - base_branch_head_fetched
    retry:
      max_attempts: 3
      on_exhaust: manual-exception
"""


# ---------------------------------------------------------------------------
# 1. Round-trip load of the shipped YAML
# ---------------------------------------------------------------------------


def test_shipped_registry_loads_successfully():
    """The bundled ticket_class_registry.yaml loads without error."""
    registry = load_ticket_class_registry()
    assert isinstance(registry, TicketClassRegistry)


def test_shipped_registry_version_is_1():
    registry = load_ticket_class_registry()
    assert registry.registry_version == 1


def test_shipped_registry_has_three_classes():
    registry = load_ticket_class_registry()
    assert len(registry.classes) == 3


def test_shipped_registry_class_ids():
    registry = load_ticket_class_registry()
    ids = {entry.id for entry in registry.classes}
    assert ids == {"docs-only", "test-hygiene", "carrier-mechanical"}


def test_shipped_registry_all_auto_pickup_false():
    """All v1 shipped classes have auto_pickup: false (advisory posture)."""
    registry = load_ticket_class_registry()
    for entry in registry.classes:
        assert entry.auto_pickup is False, (
            f"class {entry.id!r} has auto_pickup=True in advisory v1 registry"
        )


def test_shipped_registry_approver_set_exists():
    registry = load_ticket_class_registry()
    aset = registry.approver_set("persistent-controllers")
    assert aset is not None
    assert aset.resolution_ref  # non-empty reference


def test_shipped_registry_all_classes_reference_valid_approver_set(tmp_path):
    """Each class entry references a defined approver set."""
    registry = load_ticket_class_registry()
    defined = frozenset(name for name, _ in registry.approver_sets)
    for entry in registry.classes:
        assert entry.approver_allowlist_ref in defined, (
            f"class {entry.id!r} references undefined set "
            f"{entry.approver_allowlist_ref!r}"
        )


def test_shipped_registry_docs_only_territory():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    globs = entry.territory.path_glob_allowlist
    assert "docs/**" in globs
    assert "*.md" in globs


def test_shipped_registry_carrier_mechanical_work_class_xs_only():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "carrier-mechanical")
    assert entry.allowed_work_classes == frozenset({"XS"})


def test_shipped_registry_test_hygiene_mutation_class_code():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "test-hygiene")
    assert "code" in entry.allowed_mutation_classes


def test_shipped_registry_all_live_rechecks_nonempty():
    registry = load_ticket_class_registry()
    for entry in registry.classes:
        assert entry.live_rechecks, f"class {entry.id!r} has no live_rechecks"


def test_shipped_registry_path_constant_points_to_existing_file():
    assert DEFAULT_REGISTRY_PATH.exists()


# ---------------------------------------------------------------------------
# 2. Refusal paths
# ---------------------------------------------------------------------------


def test_refuses_unknown_top_level_key(tmp_path):
    content = _minimal_valid_yaml(extra_top_keys="unknown_top_level_key: oops")
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "unknown_top_level_key" in str(exc_info.value)


def test_refuses_unknown_class_entry_key(tmp_path):
    content = _minimal_valid_yaml(extra_class_keys="    bad_field: not_allowed")
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "bad_field" in str(exc_info.value)


def test_refuses_unknown_work_class(tmp_path):
    content = _minimal_valid_yaml(work_classes='["XS", "BOGUS"]')
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "BOGUS" in str(exc_info.value)


def test_refuses_unknown_mutation_class(tmp_path):
    content = _minimal_valid_yaml(mutation_classes='["docs", "nonexistent"]')
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "nonexistent" in str(exc_info.value)


def test_refuses_empty_approver_sets(tmp_path):
    """An empty approver_sets mapping is refused (no authority defined)."""
    content = _minimal_valid_yaml(approver_sets_block="approver_sets: {}\n")
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "approver_sets" in str(exc_info.value).lower()


def test_refuses_approver_allowlist_ref_not_defined(tmp_path):
    """A class referencing an undeclared approver set name is refused."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          real-set:
            description: "real"
            resolution_ref: "ce-ops:infra/identity-registry.yaml#role=controller"
        classes:
          - id: bad-ref
            description: "test"
            selectors:
              required_labels:
                - "approved-for-implementation"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: "nonexistent-set"
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: ["docs/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 2
              on_exhaust: manual-exception
    """)
    p = tmp_path / "registry.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "nonexistent-set" in str(exc_info.value)


def test_refuses_auto_pickup_true_without_enabling_decision_ref(tmp_path):
    """v1 activation rule: auto_pickup true without enabling_decision_ref is refused."""
    content = _minimal_valid_yaml(auto_pickup=True, enabling_decision_ref=None)
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    err = str(exc_info.value)
    assert "auto_pickup" in err or "enabling_decision_ref" in err


def test_accepts_auto_pickup_true_with_enabling_decision_ref(tmp_path):
    """auto_pickup true WITH enabling_decision_ref is accepted (armed class).

    Uses *.md as territory so the governance cross-check passes (GOVERNANCE.md
    is denied by the denylist added for that scenario — but we use a territory
    that doesn't touch docs/** so no cross-check issue arises).
    Actually uses .ce/changelog/** which matches no governance probe path.
    """
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          test-controllers:
            description: "test set"
            resolution_ref: "ce-ops:infra/identity-registry.yaml#role=controller"
        classes:
          - id: test-class
            description: "An armed test class."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:test-class"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: "test-controllers"
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist:
                - ".ce/changelog/**"
                - ".ce/pr-manifests/**"
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: true
            enabling_decision_ref: "docs/decisions/ADR-0018-ticket-class-registry.md"
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 3
              on_exhaust: manual-exception
    """)
    p = _write_yaml(tmp_path, content)
    registry = load_ticket_class_registry(p)
    assert len(registry.classes) == 1
    entry = registry.classes[0]
    assert entry.auto_pickup is True
    assert entry.enabling_decision_ref == "docs/decisions/ADR-0018-ticket-class-registry.md"


def test_accepts_auto_pickup_false_without_enabling_decision_ref(tmp_path):
    """Normal advisory case: auto_pickup false, no enabling_decision_ref. Should load.

    Uses a narrow territory (.ce/changelog/**) to avoid triggering the
    governance cross-check that applies to docs/** territory.
    """
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          test-controllers:
            description: "test set"
            resolution_ref: "ce-ops:infra/identity-registry.yaml#role=controller"
        classes:
          - id: test-class
            description: "Advisory class."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:test-class"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: "test-controllers"
            allowed_work_classes: ["XS", "S"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist:
                - ".ce/changelog/**"
                - ".ce/pr-manifests/**"
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 3
              on_exhaust: manual-exception
    """)
    p = _write_yaml(tmp_path, content)
    registry = load_ticket_class_registry(p)
    assert registry.classes[0].auto_pickup is False
    assert registry.classes[0].enabling_decision_ref is None


def test_refuses_registry_version_2(tmp_path):
    """Unsupported registry_version is refused."""
    content = _minimal_valid_yaml().replace(
        "registry_version: 1", "registry_version: 2"
    )
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "registry_version" in str(exc_info.value)


def test_refuses_missing_registry_version(tmp_path):
    content = _minimal_valid_yaml()
    content = "\n".join(
        line for line in content.splitlines() if not line.startswith("registry_version")
    )
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError):
        load_ticket_class_registry(p)


def test_refuses_duplicate_class_ids(tmp_path):
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          test-controllers:
            description: "test set"
            resolution_ref: "ce-ops:infra/identity-registry.yaml#role=controller"
        classes:
          - id: test-class
            description: "First definition."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:test-class"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: "test-controllers"
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: ["docs/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 2
              on_exhaust: manual-exception
          - id: test-class
            description: "Duplicate id — should be refused."
            selectors:
              required_labels:
                - "class:dupe"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: "test-controllers"
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: ["docs/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 2
              on_exhaust: manual-exception
    """)
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "duplicate" in str(exc_info.value).lower()


def test_refuses_invalid_collision_policy(tmp_path):
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: c
            description: d
            selectors:
              required_labels: ["approved-for-implementation"]
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: ["docs/**"]
              collision_policy: invalid-value
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert "collision_policy" in str(exc_info.value)


def test_error_has_field_attribute(tmp_path):
    """TicketClassRegistryError carries a typed field attribute."""
    content = _minimal_valid_yaml(extra_top_keys="bad_key: value")
    p = _write_yaml(tmp_path, content)
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    assert exc_info.value.field is not None


# ---------------------------------------------------------------------------
# 3. Territory glob matching
# ---------------------------------------------------------------------------


def test_path_in_territory_docs_glob():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert path_in_territory(entry, "docs/guide/index.md")
    assert path_in_territory(entry, "docs/reference/cli.md")
    assert path_in_territory(entry, "README.md")
    assert path_in_territory(entry, ".ce/changelog/my-change.md")
    assert path_in_territory(entry, ".ce/pr-manifests/my-change.md")
    # Governance sub-tree must be denied even though docs/** is in allowlist
    assert not path_in_territory(entry, "docs/decisions/ADR-0018.md")


def test_path_in_territory_docs_glob_rejects_code():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert not path_in_territory(entry, "validators/creator_engine_validator/forge/x.py")
    assert not path_in_territory(entry, "deploy/docker-compose.yml")


def test_path_in_territory_test_hygiene():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "test-hygiene")
    assert path_in_territory(entry, "validators/tests/unit/test_foo.py")
    assert path_in_territory(entry, "validators/tests/integration/test_bar.py")
    assert path_in_territory(entry, "validators/creator_engine_validator/checks/my_check.py")


def test_path_in_territory_test_hygiene_rejects_forge():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "test-hygiene")
    assert not path_in_territory(entry, "validators/creator_engine_validator/forge/automerge_policy.py")
    assert not path_in_territory(entry, "docs/guide/index.md")


def test_path_in_territory_carrier_mechanical():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "carrier-mechanical")
    assert path_in_territory(entry, ".ce/changelog/ce-624-class-policy-registry.md")
    assert path_in_territory(entry, ".ce/pr-manifests/ce-624-class-policy-registry.md")


def test_path_in_territory_carrier_mechanical_rejects_docs():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "carrier-mechanical")
    assert not path_in_territory(entry, "docs/guide/index.md")
    assert not path_in_territory(entry, "README.md")


def test_all_paths_in_territory_true():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    paths = [
        "docs/guide/index.md",
        ".ce/changelog/my-change.md",
        ".ce/pr-manifests/my-change.md",
        "README.md",
    ]
    assert all_paths_in_territory(entry, paths)


def test_all_paths_in_territory_false():
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    paths = [
        "docs/guide/index.md",
        "validators/creator_engine_validator/forge/bad.py",  # not in territory
    ]
    assert not all_paths_in_territory(entry, paths)


def test_all_paths_in_territory_empty_list():
    """Empty list should return True (vacuously all paths match)."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert all_paths_in_territory(entry, [])


# ---------------------------------------------------------------------------
# 4. Selector matching (class_for_labels)
# ---------------------------------------------------------------------------


def test_class_for_labels_docs_only_match():
    registry = load_ticket_class_registry()
    labels = frozenset({"approved-for-implementation", "class:docs-only", "wc:S"})
    entry = class_for_labels(registry, labels)
    assert entry is not None
    assert entry.id == "docs-only"


def test_class_for_labels_test_hygiene_match():
    registry = load_ticket_class_registry()
    labels = frozenset({"approved-for-implementation", "class:test-hygiene"})
    entry = class_for_labels(registry, labels)
    assert entry is not None
    assert entry.id == "test-hygiene"


def test_class_for_labels_carrier_mechanical_match():
    registry = load_ticket_class_registry()
    labels = frozenset({"approved-for-implementation", "class:carrier-mechanical"})
    entry = class_for_labels(registry, labels)
    assert entry is not None
    assert entry.id == "carrier-mechanical"


def test_class_for_labels_no_match_missing_required():
    registry = load_ticket_class_registry()
    # Missing "approved-for-implementation"
    labels = frozenset({"class:docs-only"})
    entry = class_for_labels(registry, labels)
    assert entry is None


def test_class_for_labels_no_match_no_class_label():
    registry = load_ticket_class_registry()
    # Has approved-for-implementation but no class: label
    labels = frozenset({"approved-for-implementation", "wc:S"})
    entry = class_for_labels(registry, labels)
    assert entry is None


def test_class_for_labels_returns_none_for_empty():
    registry = load_ticket_class_registry()
    entry = class_for_labels(registry, frozenset())
    assert entry is None


def test_class_for_labels_accepts_sequence():
    registry = load_ticket_class_registry()
    labels = ["approved-for-implementation", "class:docs-only"]
    entry = class_for_labels(registry, labels)
    assert entry is not None
    assert entry.id == "docs-only"


# ---------------------------------------------------------------------------
# 5. is_pickup_permitted semantics
# ---------------------------------------------------------------------------


def test_is_pickup_permitted_false_for_advisory_entry():
    """All shipped classes have auto_pickup=False; is_pickup_permitted returns False."""
    registry = load_ticket_class_registry()
    for entry in registry.classes:
        assert not is_pickup_permitted(entry)


def test_is_pickup_permitted_true_when_armed(tmp_path):
    """An armed class (auto_pickup true + enabling_decision_ref) returns True.

    Uses .ce/changelog/** territory to avoid the governance cross-check that
    fires on docs/** territory without a denylist.
    """
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          test-controllers:
            description: "test set"
            resolution_ref: "ce-ops:infra/identity-registry.yaml#role=controller"
        classes:
          - id: test-class
            description: "Armed test class."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:test-class"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: "test-controllers"
            allowed_work_classes: ["XS", "S"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist:
                - ".ce/changelog/**"
                - ".ce/pr-manifests/**"
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: true
            enabling_decision_ref: "docs/decisions/ADR-0018-ticket-class-registry.md"
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 3
              on_exhaust: manual-exception
    """)
    p = _write_yaml(tmp_path, content)
    registry = load_ticket_class_registry(p)
    entry = registry.classes[0]
    assert is_pickup_permitted(entry)


def test_is_pickup_permitted_false_when_auto_pickup_false_and_ref_present(tmp_path):
    """auto_pickup false even with enabling_decision_ref → not permitted."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: c
            description: d
            selectors:
              required_labels: ["approved-for-implementation", "class:c"]
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: [".ce/changelog/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            enabling_decision_ref: "ADR-0018"
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    registry = load_ticket_class_registry(p)
    entry = registry.classes[0]
    assert entry.auto_pickup is False
    assert not is_pickup_permitted(entry)


# ---------------------------------------------------------------------------
# L1: enabling_decision_ref whitespace-only refusal
# ---------------------------------------------------------------------------


def test_refuses_auto_pickup_true_with_whitespace_only_enabling_decision_ref(tmp_path):
    """L1: whitespace-only enabling_decision_ref with auto_pickup true is refused."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: c
            description: d
            selectors:
              required_labels: ["approved-for-implementation", "class:c"]
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: [".ce/changelog/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: true
            enabling_decision_ref: "   "
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    err = str(exc_info.value)
    assert "auto_pickup" in err or "enabling_decision_ref" in err


# ---------------------------------------------------------------------------
# B1: denylist-first evaluation; governance probe path denial; load-time check
# ---------------------------------------------------------------------------


def test_docs_only_denylist_denies_all_governance_probe_paths():
    """B1: All 10 governance probe paths are denied for docs-only."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    for probe in GOVERNANCE_PROBE_PATHS:
        assert not path_in_territory(entry, probe), (
            f"docs-only territory should deny governance probe {probe!r} "
            f"but path_in_territory returned True"
        )


def test_docs_only_denylist_items_present():
    """B1: docs-only carries all 10 governance denylist entries (one per
    predicate in automerge_mutation_policy.yaml governance section)."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    denylist = entry.territory.path_glob_denylist
    # All 10 governance predicates must appear in the denylist
    assert ".ce/contracts/**" in denylist
    assert "docs/contracts/**" in denylist
    assert "contracts/**" in denylist
    assert "playbooks/**" in denylist
    assert "governance/**" in denylist
    assert "GOVERNANCE.md" in denylist
    assert "CODEOWNERS" in denylist
    assert "docs/decisions/**" in denylist
    assert "docs/adr/**" in denylist
    assert "docs/governance/**" in denylist


def test_docs_only_denylist_does_not_block_plain_docs():
    """B1: non-governance docs paths are still admitted after denylist check."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert path_in_territory(entry, "docs/guide/getting-started.md")
    assert path_in_territory(entry, "docs/reference/cli.md")


def test_load_time_refuses_governance_path_in_docs_territory(tmp_path):
    """B1: a class with docs/** allowlist and no denylist is refused at load
    because the governance cross-check detects probe path leakage."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: leaky-docs
            description: "Docs class without governance denylist."
            selectors:
              required_labels: ["approved-for-implementation", "class:leaky-docs"]
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist:
                - "docs/**"
                - "*.md"
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    err = str(exc_info.value)
    assert "governance" in err.lower()


def test_load_time_accepts_docs_class_with_correct_denylist():
    """B1: The shipped registry loads without governance territory error
    because docs-only carries the full governance denylist."""
    registry = load_ticket_class_registry()
    assert any(e.id == "docs-only" for e in registry.classes)


def test_load_time_refuses_docs_class_missing_docs_contracts_denylist(tmp_path):
    """B1: docs/** allowlist with all governance denylisted EXCEPT docs/contracts/**
    is refused — docs/contracts/PROBE.yaml leaks through docs/**."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: leaky-docs
            description: "Missing docs/contracts/** in denylist."
            selectors:
              required_labels: ["approved-for-implementation", "class:leaky-docs"]
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist:
                - "docs/**"
                - "*.md"
              path_glob_denylist:
                - ".ce/contracts/**"
                - "contracts/**"
                - "playbooks/**"
                - "governance/**"
                - "GOVERNANCE.md"
                - "CODEOWNERS"
                - "docs/decisions/**"
                - "docs/adr/**"
                - "docs/governance/**"
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    err = str(exc_info.value)
    # The probe that escapes is docs/contracts/PROBE.yaml
    assert "docs/contracts" in err or "governance" in err.lower()


def test_denylist_has_precedence_over_allowlist(tmp_path):
    """B1: a path that matches both allowlist and denylist is denied."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: with-denylist
            description: "Class with overlapping allow/deny."
            selectors:
              required_labels: ["approved-for-implementation", "class:with-denylist"]
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist:
                - ".ce/changelog/**"
                - "docs/**"
              path_glob_denylist:
                - ".ce/contracts/**"
                - "docs/contracts/**"
                - "contracts/**"
                - "playbooks/**"
                - "governance/**"
                - "GOVERNANCE.md"
                - "CODEOWNERS"
                - "docs/decisions/**"
                - "docs/adr/**"
                - "docs/governance/**"
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    registry = load_ticket_class_registry(p)
    entry = registry.classes[0]
    # docs/guide is allowed (allowlist matches, not in denylist)
    assert path_in_territory(entry, "docs/guide/index.md")
    # docs/decisions is denied (denylist wins even though docs/** matches)
    assert not path_in_territory(entry, "docs/decisions/ADR-0018.md")
    # .ce/changelog is allowed
    assert path_in_territory(entry, ".ce/changelog/ce-624.md")


# ---------------------------------------------------------------------------
# M1: load-time selector ambiguity refusal
# ---------------------------------------------------------------------------


def test_shipped_registry_selectors_are_unambiguous():
    """M1: The shipped 3-class registry has pairwise non-comparable selector sets."""
    registry = load_ticket_class_registry()
    entries = list(registry.classes)
    for i, a in enumerate(entries):
        for j, b in enumerate(entries):
            if i >= j:
                continue
            a_lbs = a.selectors_required_labels
            b_lbs = b.selectors_required_labels
            assert not (a_lbs <= b_lbs or b_lbs <= a_lbs), (
                f"classes {a.id!r} and {b.id!r} have ambiguous selector sets"
            )


def test_load_time_refuses_ambiguous_selectors_subset(tmp_path):
    """M1: class A labels ⊆ class B labels → refused at load."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: broad
            description: "Only approved-for-implementation."
            selectors:
              required_labels:
                - "approved-for-implementation"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: [".ce/changelog/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
          - id: narrow
            description: "Superset of broad — ambiguous."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:narrow"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: [".ce/changelog/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError) as exc_info:
        load_ticket_class_registry(p)
    err = str(exc_info.value)
    assert "ambiguous" in err.lower() or "subset" in err.lower()


def test_load_time_refuses_equal_selector_sets(tmp_path):
    """M1: two classes with identical required_labels are refused (equal ⊆ equal)."""
    content = textwrap.dedent("""\
        registry_version: 1
        activation_posture: advisory
        approver_sets:
          s:
            description: d
            resolution_ref: ref
        classes:
          - id: alpha
            description: "Class alpha."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:shared"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: [".ce/changelog/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
          - id: beta
            description: "Class beta — same labels as alpha."
            selectors:
              required_labels:
                - "approved-for-implementation"
                - "class:shared"
              issue_repo_scope: "creator-engine/ce-ops"
            approver_allowlist_ref: s
            allowed_work_classes: ["XS"]
            allowed_mutation_classes: ["docs"]
            territory:
              path_glob_allowlist: [".ce/changelog/**"]
              collision_policy: refuse
            role: implementer
            lane_kind: implementation
            auto_pickup: false
            live_rechecks:
              - approval_label_present
              - applier_in_approver_set
              - no_open_claim
              - no_linked_open_pr
              - base_branch_head_fetched
            retry:
              max_attempts: 1
              on_exhaust: manual-exception
    """)
    p = tmp_path / "r.yaml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(TicketClassRegistryError):
        load_ticket_class_registry(p)


# ---------------------------------------------------------------------------
# M2: path normalization refusal
# ---------------------------------------------------------------------------


def test_path_in_territory_rejects_absolute_path():
    """M2: absolute path (starts with /) returns False fail-closed."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert not path_in_territory(entry, "/docs/guide/index.md")
    assert not path_in_territory(entry, "/README.md")


def test_path_in_territory_rejects_dotdot_traversal():
    """M2: traversal form (contains ..) returns False fail-closed."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert not path_in_territory(entry, "docs/../validators/forge/x.py")
    assert not path_in_territory(entry, "../README.md")
    assert not path_in_territory(entry, "docs/../../etc/passwd")


def test_path_in_territory_rejects_backslash():
    """M2: backslash in path returns False fail-closed."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert not path_in_territory(entry, "docs\\guide\\index.md")
    assert not path_in_territory(entry, "docs/guide\\index.md")


def test_path_in_territory_rejects_dotslash_prefix():
    """M2: path starting with ./ returns False fail-closed."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    assert not path_in_territory(entry, "./docs/guide/index.md")
    assert not path_in_territory(entry, "./README.md")


def test_all_paths_in_territory_rejects_dotdot():
    """M2: all_paths_in_territory returns False if any path has traversal."""
    registry = load_ticket_class_registry()
    entry = next(e for e in registry.classes if e.id == "docs-only")
    paths = [
        "docs/guide/index.md",          # safe
        "docs/../validators/forge/x.py", # traversal — safe path fails closed
    ]
    assert not all_paths_in_territory(entry, paths)
