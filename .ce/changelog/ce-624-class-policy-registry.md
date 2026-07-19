---
slug: ce-624-class-policy-registry
date: 2026-07-19
kind: added
scope: forge / ticket-class policy registry
issue: ce-ops#624
---

**CE624 — Author the ticket-class policy registry: authority-bearing interface for autonomous belt pickup.**

This change delivers the class-policy registry that the CE618 belt-readiness report
(dev-3) identified as the CE616 dependency gate — the missing versioned, machine-enforced
mapping from pre-delegated ticket class to selectors, territory, role/lane, pickup
permission, and live-recheck contract.

Added `validators/creator_engine_validator/forge/ticket_class_registry.yaml`:
- Registry version 1, activation posture advisory.
- Top-level `approver_sets` map: named authority groups with `resolution_ref` pointing
  to the ops identity registry. No usernames or login handles embedded.
- Three initial conservative classes:
  - `docs-only` — docs mutation class, XS/S, territory `docs/**` + `*.md` +
    `.ce/changelog/**` + `.ce/pr-manifests/**`, collision policy `refuse`.
  - `test-hygiene` — code mutation class, XS/S, territory
    `validators/tests/**` + `validators/creator_engine_validator/checks/**`, `refuse`.
  - `carrier-mechanical` — docs mutation class, XS only, territory
    `.ce/changelog/**` + `.ce/pr-manifests/**`, `refuse`.
- All classes: `auto_pickup: false` (advisory posture); five standard live_rechecks;
  retry with `on_exhaust: manual-exception`.

Added `validators/creator_engine_validator/forge/ticket_class_registry.py`:
- `load_ticket_class_registry(path) -> TicketClassRegistry` — strict fail-closed
  loader; unknown keys, wrong types, unknown work/mutation class names, missing
  approver set references all raise `TicketClassRegistryError` with `field` attribute.
- `TicketClassRegistryError(field=...)` typed error mirroring automerge_policy.py style.
- Frozen dataclasses: `TicketClassRegistry`, `TicketClassEntry`, `TerritoryPolicy`,
  `RetryPolicy`, `ApproverSet`.
- v1 arming rule enforced: `auto_pickup: true` without `enabling_decision_ref` raises
  `TicketClassRegistryError` (mirrors `enabling_decision_ref` pattern in ADR-0016).
- Accessors: `class_for_labels()`, `is_pickup_permitted()`, `path_in_territory()`,
  `all_paths_in_territory()`.
- Pure stdlib + yaml; no network, no subprocess, no disk write. NOT wired into
  pickup.py (that is CE618-1, dev-3 territory).

Added `validators/tests/unit/test_ticket_class_registry.py`:
- 45 tests: round-trip load of shipped YAML; refusal paths (unknown keys, unknown
  work/mutation class, empty approver_sets, undeclared ref, auto_pickup true without
  enabling_decision_ref, duplicate ids, invalid collision_policy, unsupported version);
  both sides of the arming rule; territory glob matching; selector matching;
  `is_pickup_permitted` semantics.

Added `docs/decisions/ADR-0018-ticket-class-registry.md`:
- Status: accepted. Ratification: Operator (chmod735), 2026-07-19, intake-shift session.
- Ratification prompt sha: cec2d5908bcfd622a07011e9bd0d653f8ad070c5dbc529330e6946ec46c1b6f9.
- Documents context (intake-shift; autonomy at pickup, not at merge), the four-field
  registry contract, authority rules (approver provenance via issue timeline; per-scope
  daemon lease; supervision audit), activation ladder (all classes advisory in v1;
  per-class arming = governance PR + enabling_decision_ref), and explicit non-goals
  (no auto-approve, no MC2 interaction, no new ce CLI group, no daemon arming).
