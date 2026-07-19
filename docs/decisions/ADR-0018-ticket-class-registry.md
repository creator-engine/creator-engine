---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0018
title: "Ticket-class policy registry: authority-bearing interface for autonomous ticket pickup"
status: accepted
date: "2026-07-19"
decision_makers: ["chmod735 (Operator)"]
consulted: ["delegated-operator controller", "CE618 belt-readiness research worker (dev-3)"]
informed: []
review_by: "2026-10-19"
mutation_class: governance
evidence_refs:
  - kind: code
    ref: "validators/creator_engine_validator/forge/ticket_class_registry.yaml — versioned class-policy registry, registry_version 1, activation_posture advisory"
    tag: registry-yaml
  - kind: code
    ref: "validators/creator_engine_validator/forge/ticket_class_registry.py — loader, validation API, class_for_labels(), is_pickup_permitted(), path_in_territory()"
    tag: registry-loader
  - kind: code
    ref: "validators/tests/unit/test_ticket_class_registry.py — round-trip, refusal paths, glob matching, selector matching"
    tag: registry-tests
  - kind: code
    ref: "validators/creator_engine_validator/work_sizing.py — WORK_CLASSES, MUTATION_CLASSES (registry enums derive from these)"
    tag: work-sizing
  - kind: code
    ref: "validators/creator_engine_validator/pickup.py:497-506 — selection gap identified by CE618 readiness report; class/territory/policy identity missing at belt entry point"
    tag: pickup-selection-gap
  - kind: code
    ref: "validators/creator_engine_validator/forge/automerge_policy.py — enabling_decision_ref pattern mirrored in registry v1 arming rule"
    tag: automerge-policy-pattern
  - kind: adr
    ref: "docs/decisions/ADR-0016-pre-delegated-merge-classes.md — schema/style precedent; enabling_decision_ref pattern; activation ladder model"
    tag: adr-0016
  - kind: adr
    ref: "docs/decisions/ADR-0013-substrate-independent-authority.md — autonomous vs. reserved action taxonomy (D1); human ratification moves to policy level (principle 3)"
    tag: adr-0013
  - kind: doc
    ref: "docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md — two-key doctrine, author/approver separation (FR-007), privileged classes (FR-008)"
    tag: authority-model
  - kind: doc
    ref: "docs/governance/MUTATION_CLASS_MODEL.md — mutation-class taxonomy"
    tag: mutation-class-model
  - kind: session
    ref: "controller state-root, 2026-07-19 RATIFICATIONS_20260719_INTAKE_SHIFT.md — Operator ratification of intake-shift: class-policy registry as authority-bearing artifact"
    tag: intake-shift-ratification
ratification:
  ratified_by: "chmod735"
  ratified_at: "2026-07-19"
  ratification_prompt_sha: "cec2d5908bcfd622a07011e9bd0d653f8ad070c5dbc529330e6946ec46c1b6f9"
  quorum: n1_solo
---

# Ticket-class policy registry

## 1. Context and problem statement

CE's belt (the autonomous ticket-pickup daemon, CE618) polls forge issues,
normalises hits, and attempts to claim and launch governed lane work. The CE618
belt-readiness research report (dev-3, 2026-07-19) identified a **selection gap**
at `pickup.py:497-506`: role and lane kind are derived solely from the work-item
`kind` field (`review_requested` → `reviewer/review`; everything else →
`implementer/implementation`). No work class, mutation class, territory, or
pre-delegation policy identity is carried or enforced at the belt entry point.

The same report blocked CE618 on a dependency it labelled "CE616 dependency
gate": the existing CE616 schemas (territory-map, checkpoint, operator-decision)
do not supply a canonical, versioned definition that maps a pre-delegated ticket
class to the four required attributes:

1. Authoritative issue/label selectors and allowed work/mutation classes.
2. Territory selector and collision treatment.
3. Allowed role/lane kind and whether automatic pickup is permitted.
4. Required live-read checks, retry/manual-exception disposition, and
   activation posture.

The Operator ratified the intake-shift direction on 2026-07-19 (see
`RATIFICATIONS_20260719_INTAKE_SHIFT.md`, evidence tag `intake-shift-ratification`):
authority moves to (1) ticket opening/triage and (2) approval-for-implementation;
ticket pickup becomes autonomous against a dev-2-authored, versioned,
machine-enforced CLASS-POLICY REGISTRY.

This ADR defines that registry contract, the field semantics satisfying the four
CE618 requirements, the authority rules that govern it, and the activation ladder
governing when and how classes may be armed for autonomous pickup.

The merge gate remains act-shaped. Autonomy of pickup does not imply autonomy
of merge. The two-key merge model and the MC0/MC1/MC2 ladder (ADR-0016) are
orthogonal to this ADR.

---

## 2. Decision

Author and ratify a **CLASS-POLICY REGISTRY** as a versioned YAML artifact
(`validators/creator_engine_validator/forge/ticket_class_registry.yaml`) backed
by a typed loader module (`ticket_class_registry.py`). The registry is:

- **Versioned**: `registry_version: 1` is the initial version; the loader
  refuses any unknown version.
- **Fail-closed**: any unknown key, wrong type, undeclared enum value, or
  violated constraint raises `TicketClassRegistryError` with a field-level
  message before any belt action.
- **Advisory in v1**: `activation_posture: advisory`; all classes ship with
  `auto_pickup: false`. No autonomous pickup occurs until a class is
  explicitly armed via a governance PR.
- **Authority-bearing**: the registry, not the advisory classifiers
  (`forge_triage.py`, `ce_ops_triage_queue.py`), is the machine-enforced
  source of truth for pickup policy. Advisory classifiers remain in place as
  scheduling hints but yield to the registry on any policy question.

---

## 3. Registry contract (field semantics)

### 3.1 Top-level structure

| Field | Type | Required | Semantics |
|---|---|---|---|
| `registry_version` | integer | yes | Must be in `SUPPORTED_REGISTRY_VERSIONS` (currently `{1}`). Unknown version → refused. |
| `activation_posture` | string | yes | Describes the overall arming stance. In v1 the value is `"advisory"`. Informational; the per-class `auto_pickup` field is the enforcement gate. |
| `approver_sets` | mapping | yes | Named authority sets. Must have at least one entry. Members are NEVER embedded; they are resolved at live-recheck time against the ops identity registry. |
| `classes` | list | yes | Ordered list of class entries. Duplicate `id` values → refused. |

### 3.2 Approver sets

Each approver set carries:

| Field | Type | Required | Semantics |
|---|---|---|---|
| `description` | string | yes | Human-readable description of who this set covers. No usernames, logins, or seat identifiers. |
| `resolution_ref` | string | yes | Pointer to the external identity-registry query that resolves the set at live-recheck time (e.g. `"ce-ops:infra/identity-registry.yaml#role=controller"`). |

**No username or login is ever embedded in the registry.** The registry names
groups; the belt resolves group membership at runtime by reading the ops
identity registry through the governed forge seam.

### 3.3 Class entry fields (CE618 requirement mapping)

**Requirement 1 — issue/label selectors and allowed work/mutation classes:**

| Field | Type | Required | Semantics |
|---|---|---|---|
| `id` | string | yes | Unique identifier for this class. Must be non-empty, unique within the registry. |
| `description` | string | yes | Human-readable description of the class scope and intent. |
| `selectors.required_labels` | list of strings | yes | Every label in this list must appear on the forge issue before the entry is eligible. Non-empty. |
| `selectors.issue_repo_scope` | string | yes | The forge repository the issue must belong to (e.g. `"creator-engine/ce-ops"`). |
| `allowed_work_classes` | list of strings | yes | Work classes permitted for this entry. Must be a non-empty subset of `WORK_CLASSES` (`XS`, `S`, `M`, `L`). |
| `allowed_mutation_classes` | list of strings | yes | Mutation classes permitted for this entry. Must be a non-empty subset of `MUTATION_CLASSES`. Privileged classes (`governance`, `identity`, `security`, `attestation`, `redaction`) should not appear in v1 classes (conservative posture). |

**Requirement 2 — territory selector and collision treatment:**

| Field | Type | Required | Semantics |
|---|---|---|---|
| `territory.path_glob_allowlist` | list of strings | yes | fnmatch glob patterns. Every path in an implementation diff must match at least one pattern before the lane proceeds. Non-empty. |
| `territory.collision_policy` | string | yes | `"refuse"` (default, conservative) — stop and leave for manual intervention. `"queue"` — wait for the conflicting claim to clear. |

**Requirement 3 — role/lane kind and pickup permission:**

| Field | Type | Required | Semantics |
|---|---|---|---|
| `role` | string | yes | Lane role (`implementer`, `reviewer`, `architect`, `verification`). |
| `lane_kind` | string | yes | Lane kind (`implementation`, `review`, etc.; must be in `LANE_KINDS`). |
| `auto_pickup` | boolean | yes | Whether the belt may autonomously claim this class. In v1 all classes ship `false`. |
| `enabling_decision_ref` | string | no | Required when `auto_pickup: true`; must reference the ADR or governance record that ratified arming. Absent/null is permitted only when `auto_pickup: false`. |

**v1 arming rule (enforced by loader):** if `auto_pickup: true` and
`enabling_decision_ref` is absent or empty, the loader raises
`TicketClassRegistryError`. This mirrors the `enabling_decision_ref` pattern
in `automerge_policy.py`. Violation is a hard refusal, not a warning.

**Requirement 4 — live-read checks, retry/manual-exception:**

| Field | Type | Required | Semantics |
|---|---|---|---|
| `live_rechecks` | list of strings | yes | Ordered list of live-check identifiers the belt must run before acting. Non-empty. Valid identifiers are defined in `VALID_LIVE_RECHECKS` in the loader. |
| `retry.max_attempts` | integer | yes | Maximum number of pickup attempts before escalating. Must be ≥ 1. |
| `retry.on_exhaust` | string | yes | Action on retry exhaustion. `"manual-exception"` — remove from belt queue and escalate to controller. |

**Approver authority:**

| Field | Type | Required | Semantics |
|---|---|---|---|
| `approver_allowlist_ref` | string | yes | Name of an entry in `approver_sets`. Must reference a defined set; unknown refs → refused. |

### 3.4 Live-recheck contract (belt enforcement)

The belt must run every recheck in `live_rechecks` before calling
`work_claims.acquire`. The five standard rechecks are:

| Identifier | What the belt verifies |
|---|---|
| `approval_label_present` | The `approved-for-implementation` label (or class-specific approval label) is still present on the live issue at recheck time. |
| `applier_in_approver_set` | The account that applied the approval label is a member of the class's `approver_allowlist_ref` set, verified against the issue timeline via the forge API. Never verified from in-repo data. |
| `no_open_claim` | No existing `ce-work-claim` marker exists on the issue (dedup + race guard). |
| `no_linked_open_pr` | No open PR in the forge links to this issue (avoids duplicate work). |
| `base_branch_head_fetched` | The belt has fetched the current head of the base branch immediately before spawning. |

All five must pass. Any failing or unavailable recheck → refuse before
`work_claims.acquire` (fail-closed). A recheck that cannot be evaluated
(API error, timeout) is treated as failed, not as passing.

**Approver provenance** is verified against the issue timeline by the belt
wrapper, not by this module. This module provides the `approver_allowlist_ref`
reference; the belt enforces it at runtime.

### 3.5 Selector matching

`class_for_labels(registry, labels)` returns the **first** class entry whose
`selectors.required_labels` is a subset of the provided label set. Order of
definition in the registry determines priority. Returns `None` if no match.

This is a pure, deterministic predicate; it does not read the forge API.

---

## 4. Authority rules

### 4.1 Approver provenance

- The identity of the account that applied the `approved-for-implementation`
  label must be verified against the issue timeline via a live forge API read.
  Static label presence alone is insufficient.
- The verified identity must appear in the named `approver_allowlist_ref` set,
  which is resolved against `ce-ops:infra/identity-registry.yaml` at
  live-recheck time.
- Any mismatch → refuse, no claim, no spawn.

### 4.2 Per-scope daemon leases

- One belt daemon per host; never a global belt.
- The belt holds a singleton lease scoped to the host and the governed ledger
  root. A second belt process on the same host must detect the existing lease
  and exit rather than forming a parallel claim stream.
- The controller manages belt arming and disarming; the belt never self-arms.

### 4.3 Supervision audit

- A supervision audit agent diffs approval acts (label-timeline events) against
  registry criteria periodically.
- The audit agent may not pick up or claim tickets; it is read-only and reports
  deviations to the controller.

---

## 5. Activation ladder

All classes ship in **advisory mode** (`auto_pickup: false`). The ladder
progresses class-by-class through explicit governance PRs.

### Phase 0 — Registry v1 ships (this ADR)

All three initial classes (`docs-only`, `test-hygiene`, `carrier-mechanical`)
are advisory. The belt may read the registry and surface candidates but may not
autonomously claim or spawn without an explicit `--enable-launch` override
(existing canary gate in `pickup.py`).

### Phase 1 — CE618-1: class-gated pickup bridge (dev-3)

Dev-3 bridges the registry into the belt pipeline (wires `class_for_labels`,
territory checks, and live-recheck results into the claim path). The belt can
now produce class-tagged outcomes and enforce territory; it still will not
autonomous-claim because all classes remain `auto_pickup: false`.

### Phase 2 — Arming individual classes

For each class to be armed:
1. A governance PR adds `enabling_decision_ref` (citing the authorising session
   or ADR) and sets `auto_pickup: true` in the registry YAML.
2. The PR follows the full two-key gate (Key 1 + Key 2 + merge class).
3. The governance mutation class (privileged) applies; no auto-merge of
   registry arming PRs.
4. The MC1 zero-gesture merge drill and the actuator hardening
   (ce-ops#622) must complete before arming any class.
5. The narrowest class (`carrier-mechanical`) is the first candidate; broader
   classes (`docs-only`, `test-hygiene`) follow after demonstrated stability.

The activation ladder is one-at-a-time: no two classes are armed in the same
governance PR.

---

## 6. Non-goals

The following are explicitly out of scope for v1 of this registry:

1. **No auto-approve.** The registry governs pickup permission, not approval
   authority. The two-key merge model (ADR-0016) is unchanged; the registry
   does not extend merge authority.
2. **No MC2 interaction.** The `xs_s_within_territory` merge class (ADR-0016
   §4) requires a territory registry and policy-fired reviewer-dispatch that
   are not wired in this ADR. The pickup registry and the merge-class territory
   registry may share design patterns but are separate artifacts.
3. **Conveyor/harvest unchanged.** The harvest/dispatch mechanics, conveyor
   daemon deployment, and seed-file lifecycle are unaffected by this ADR.
4. **No new `ce` CLI command group.** The loader is a pure Python module; it
   exposes no CLI surface and adds no `ce` command group.
5. **No embedding of usernames.** The registry must never contain login
   handles, email addresses, or seat identifiers. All identity resolution
   happens at live-recheck time via the ops identity registry.
6. **No privileged mutation classes in v1 class definitions.** Classes in v1
   must not list `governance`, `identity`, `security`, `attestation`, or
   `redaction` in `allowed_mutation_classes`. These surfaces remain fully
   two-key.
7. **No daemon activation.** No belt daemon is armed or deployed by this ADR.
   The `--enable-launch` canary gate remains off by default.

---

## 7. Relationship to existing ADRs and prior decisions

| Prior artifact | Relationship |
|---|---|
| ADR-0013 §D, principle 3 | This ADR implements principle 3 at the ticket-pickup level: ratification moves to policy (this ADR + per-class arming PR) rather than per-act gesture. |
| ADR-0016 (merge classes) | Orthogonal: merge authority remains act-shaped. Autonomy of pickup ≠ autonomy of merge. The `enabling_decision_ref` arming pattern is directly mirrored from ADR-0016's `automerge_policy.py` implementation. |
| CE618 belt-readiness report | This ADR closes the CE616 dependency gate by defining the four required attributes the report identified as missing. |
| `forge_triage.py`, `ce_ops_triage_queue.py` | Advisory classifiers; remain in place as scheduling hints. Yield to the registry on all policy decisions. |
| `AUTHORITY_AND_RATIFICATION_MODEL.md` | Author/approver separation (FR-007) preserved: the approver who applies `approved-for-implementation` must differ from the implementer; verified at live-recheck via issue timeline. |

---

## 8. Ratification requirements

This ADR required Operator ratification before the registry may be shipped.
Ratification was given on 2026-07-19 as part of the intake-shift session (see
`RATIFICATIONS_20260719_INTAKE_SHIFT.md`, evidence tag `intake-shift-ratification`).

**For per-class arming:** A separate governance PR for each class, citing this
ADR's ratification record as the authority basis, is required. No class may be
armed without an `enabling_decision_ref` that points to a ratified governance
record (this ADR or a subsequent amendment).
