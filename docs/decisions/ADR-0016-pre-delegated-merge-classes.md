---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0016
title: "Pre-delegated merge classes: MC0, MC1, and MC2 — zero-gesture merge tiers for qualifying PR subsets"
status: accepted
date: "2026-07-19"
decision_makers: ["chmod735 (Operator)"]
consulted: ["delegated-operator controller", "architect-research draft worker"]
informed: []
review_by: "2026-10-19"
mutation_class: governance
evidence_refs:
  - kind: code
    ref: "validators/creator_engine_validator/forge/automerge_policy.py — carrier_changelog_mechanical tier, docs_envelope tier, kill switch, AUTOMERGE_CANARY_WORK_CLASSES"
    tag: automerge-policy-engine
  - kind: code
    ref: "validators/creator_engine_validator/forge/automerge_actuator.py — actuator predicate set, dual-layer kill switch re-verification"
    tag: automerge-actuator
  - kind: code
    ref: "validators/creator_engine_validator/forge/automerge_mutation_policy.yaml — path classifier, fail_closed_class: redaction, required_checks"
    tag: mutation-policy-yaml
  - kind: code
    ref: "validators/creator_engine_validator/work_sizing.py — MUTATION_CLASSES, WORK_CLASSES, _RISK_TABLE (ratification_gates), size_ceremony()"
    tag: work-sizing
  - kind: code
    ref: "validators/creator_engine_validator/checks/work_sizing_floor.py — _size_band(), classify_change_size(), included_lines thresholds"
    tag: work-sizing-floor
  - kind: code
    ref: "validators/creator_engine_validator/checks/path_manifest_fidelity.py — branch_slug(), CarrierIdentity, _run_with_base_per_pr(), scan_document(), _normalize_manifest()"
    tag: path-manifest
  - kind: code
    ref: "validators/creator_engine_validator/ce_cli.py:5144 (_automerge_kill_switch implementation; parser registration at 2021) — ce automerge-kill-switch status|on|off"
    tag: kill-switch-cli
  - kind: doc
    ref: "docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md — two-key doctrine, author/approver separation (FR-007), privileged classes (FR-008), CI-verifies-not-ratifies (FR-013)"
    tag: authority-model
  - kind: doc
    ref: "docs/governance/MUTATION_CLASS_MODEL.md — baseline mutation-class taxonomy, privileged-class ratification rules"
    tag: mutation-class-model
  - kind: adr
    ref: "docs/decisions/ADR-0013-substrate-independent-authority.md — autonomous vs. reserved action taxonomy (D1), human ratification moves to policy level (principle 3)"
    tag: adr-0013
  - kind: doc
    ref: "docs/delivery/REVIEW_GATE.md — review-not-ratification invariant, reviewer identity requirements, author/approver separation"
    tag: review-gate
  - kind: memory
    ref: "controller memory record, 2026-07-17 (internal, not in-repo): MC0 ratified as amended — machine predicate replaces Key-2 for carrier-only diffs; non-author exact-head approval stays mandatory"
    tag: mc0-ratification
  - kind: session
    ref: "controller session record, 2026-07-17 (internal, not in-repo) — Operator ratification of MC0 amended predicate; MC1/MC2 still proposed"
    tag: operator-session-20260717
  - kind: session
    ref: "controller session record, 2026-07-18 (internal, not in-repo) — MC0 predicate ratified; follow-on correction round in progress"
    tag: operator-session-20260718
  - kind: doc
    ref: "deploy/queue-daemon/launch-queue-daemon.sh — queue daemon singleton, approval settle seconds, authorized reviewer env"
    tag: queue-daemon
ratification:
  ratified_by: "chmod735"
  ratified_at: "2026-07-19"
  ratification_prompt_sha: "d99b5dea8268df79e9c95e8a550b20fabae73a1c7ffe68299b43a1eeff5bb0f8"
  quorum: n1_solo
---

# Pre-delegated merge classes: MC0, MC1, and MC2

## 1. Context and problem statement

CE's current merge gate (the "two-key" model) requires two independent authorizations
for every PR before the queue daemon may enqueue it:

- **Key 1** — the controller byte-verifies the PR (path-set digest against the per-PR
  carrier, CI green, carrier integrity), then places an exact-head approval on the
  PR's current head SHA.
- **Key 2** — an independent fresh-context reviewer subagent reads the diff under a
  bounded reviewer-authority-envelope (`docs/operations/REVIEWER_VENUE_AUTHORITY.md`
  G2.007.2) and emits a verdict; the reviewer identity must differ from the PR author.

The controller then triggers `--auto` enqueue, and the singleton queue daemon
(`deploy/queue-daemon/launch-queue-daemon.sh`) completes the merge through GitHub's
merge queue.

This model is correct for the general case and is the standing default. However,
for structurally narrow and machine-verifiable subsets of PRs, Key 2 adds latency
and token cost without adding verification power beyond what the machine predicate
already provides. ADR-0013 ratified the principle that human ratification belongs
at the policy level, not at each individual PR gesture
(`docs/decisions/ADR-0013-substrate-independent-authority.md` §D, principle 3).

This ADR defines three **pre-delegated merge classes** — named, predicate-bounded
policy tiers — that let qualifying PRs merge with zero per-PR human gesture after
the Operator ratifies this policy. "Zero gesture" means no separate merge trigger
after approval; it never means zero human approval. The two invariants that can
never be removed by any merge class are:

1. Non-author exact-head approval is ALWAYS required (the author-not-equal-approver
   wall from Feature 001 FR-007 and ADR-0013 D3).
2. All CI required checks must be green before the queue daemon may actuate.

MC0 (Class 2 below) was ratified by the Operator on 2026-07-17 as an amendment to
the A2 packet (see evidence refs `mc0-ratification` and `operator-session-20260717`).
The machine predicate replacing Key 2 for carrier-only diffs is ACTIVE. This ADR
codifies MC0 as formal ratified policy text and adds two new classes (MC1, MC2)
for Operator consideration.

### Baseline authority that never changes

Before defining the merge classes, these invariants apply to all three and cannot
be waived by any per-class policy:

- **Author ≠ approver** (FR-007): always enforced; the actuator re-verifies this
  against the live GitHub API before actuation
  (`automerge_actuator.py:_live_author_approver_independent()`).
- **Exact-head approval**: the approval must bind the PR's current head SHA; any
  push invalidates and requires a new approval.
- **CI required checks green**: `automerge_mutation_policy.yaml` lists `"Validate
  governance artifacts"` as the required check; the actuator verifies all required
  checks green via live API before actuation
  (`automerge_actuator.py:_live_required_checks_green()`).
- **Privileged mutation classes never auto**: `deploy`, `governance`, `identity`,
  `security`, `attestation`, `redaction` always require `operator_front_bet`,
  `operator_human_ratifier`, `non_delegable`, `ring1_push_block`, `operator_merge`
  gates per the risk table (`work_sizing.py:_RISK_TABLE`). These classes are
  explicitly listed in `NON-GOALS §10`.
- **Kill switch fail-closed**: any unevaluable policy predicate → GESTURE (never
  auto-actuates on error). The actuator returns `Dormant` on unreadable live
  policy; the decision engine returns `GESTURE` on any blocker in `auto_blockers`.
- **Enabling decision ref**: every armed run-mode requires an `enabling_decision_ref`
  in the policy state; missing ref → `enabling_decision_ref_missing` blocker.

---

## 2. Class 1 — MC1: Docs-envelope (proposed, not yet ratified)

### a. Name and intent

**MC1 — `docs_envelope`**: Pre-delegated merge class for PRs whose entire diff
touches only documentation and markdown surfaces — `docs/**`, root `*.md` files,
`.ce/changelog/**`, and `.ce/pr-manifests/**` — with no executable, schema, deploy,
governance, identity, security, attestation, or redaction surface. The fresh-context
Key-2 reviewer subagent is still dispatched; what is removed is the post-approval
merge trigger (the queue daemon actuates enqueue automatically after the approval
lands). This is the safest and widest class by path surface.

### b. Machine predicate set

All of the following must hold simultaneously. Any predicate that is unevaluable
resolves as failed (fail-closed):

| # | Predicate | Source |
|---|---|---|
| P1 | `docs_envelope_tier_matches(changed_paths)` is True: every path starts with `docs/`, `.ce/changelog/`, or `.ce/pr-manifests/`, OR is a root-level `*.md` (no `/` in path, ends in `.md`). No empty path in the set. | `automerge_policy.py:919-924` (`docs_envelope_tier_matches`) |
| P2 | `mutation_class_for_paths(changed_paths, policy)` returns `"docs"`. The path classifier (`automerge_mutation_policy.yaml`) must classify ALL changed paths as `docs`; any path that matches `code`, `schema`, `deploy`, or any privileged class escalates the whole PR to GESTURE. Fail-closed class is `redaction`. | `mutation_classifier.py:136-170`; `automerge_mutation_policy.yaml` |
| P3 | `ratification_gates` for `docs` mutation class = `("auto_back_gate",)` only. Verified by `size_ceremony(declared_work_class, "docs")`. | `work_sizing.py:_RISK_TABLE["docs"]` |
| P4 | Declared work class in `{XS, S}` (normalized: `AUTOMERGE_CANARY_WORK_CLASSES`). Aliases: `tiny` → XS, `story` → S. | `automerge_policy.py:39-41`; `work_sizing.py:LEGACY_WORK_CLASS_ALIASES` |
| P5 | `size_band != "split_required"`: included changed lines (after lockfile/vendored/generated exclusions) must be < 1001. `_size_band()`: < 400 → `target_advisory`/XS; < 800 → `warn`/S; ≤ 1000 → `explain_or_split`/M; > 1000 → `split_required` (blocks). | `work_sizing_floor.py:140-147`; `automerge_policy.py:579-580` |
| P6 | All required CI checks green (live re-verification at actuation time). Required check: `"Validate governance artifacts"`. | `automerge_mutation_policy.yaml:required_checks`; `automerge_actuator.py:_live_required_checks_green()` |
| P7 | `review_decision == "APPROVED"` and not `"CHANGES_REQUESTED"`. | `automerge_policy.py:575-578` |
| P8 | Fresh-context Key-2 reviewer subagent submitted verdict under a valid reviewer-authority-envelope (G2.007.2). The approver login in the approval must be the reviewer's login, distinct from the PR author. | `docs/operations/REVIEWER_VENUE_AUTHORITY.md §2` |
| P9 | `author_login != approver_login` (case-insensitive). Re-verified at actuation time against live GH API. | `automerge_actuator.py:_live_author_approver_independent()` |
| P10 | `policy_state.kill_switch == False` (both decision-level and live-policy-level). | `automerge_policy.py:585-586`; `automerge_actuator.py:_live_policy_state()` |
| P11 | Run mode ∈ `{"ceo", "strangeLoop"}` (AUTOMERGE_ARMING_RUN_MODES). | `automerge_policy.py:36-38` |
| P12 | `policy_state.class_flag("docs") == True` AND `policy_state.tier_flag("docs_envelope") == True`. Both must be explicitly armed. | `automerge_policy.py:205-211`; `automerge_actuator.py:118-123` |
| P13 | `enabling_decision_ref` is a non-empty string. Must reference this ADR's ratification record. | `automerge_policy.py:593-594` |
| P14 | PR carrier (`<branch-slug>.md`) is ADDED (status A) in the diff, slug matches `branch_slug(head_ref)`, and the carrier's declared path-set is consistent with the diff (path_manifest_fidelity check green). | `path_manifest_fidelity.py:_run_with_base_per_pr()` |
| P15 | `changed_paths` is non-empty. | `mutation_classifier.py:148-149` |

**Deny-set: any path matching any of the following predicates escalates to GESTURE regardless of other predicates:**
- Matches `validators/**`, `tools/**`, `src/**`, `app/**`, `apps/**`, `packages/**` (code class)
- Matches `schemas/**`, `*.schema.yaml`, `*.schema.json` (schema class)
- Matches `deploy/**`, `.github/**`, `Dockerfile*`, `Containerfile`, `docker-compose.yml` (deploy class)
- Matches `docs/contracts/**`, `contracts/**`, `GOVERNANCE.md`, `CODEOWNERS`, `governance/**` (governance class)
- Matches any identity, security, attestation, or redaction path pattern from `automerge_mutation_policy.yaml`

### c. Evidence bundle emitted at merge time

The automerge decision engine writes a structured JSON record to
`.ce/state/automerge/decisions/<pr_number>-<head_sha>.json`
(`automerge_policy.py:DEFAULT_AUTOMERGE_DECISIONS_RELATIVE`). This record must
include all of the following fields; their presence is the audit trail:

| Field | Required content |
|---|---|
| `decision` | `"AUTO"` |
| `tier` | `"docs_envelope"` |
| `tier_flag` | `true` |
| `path_envelope` | `"docs/**,*.md,.ce/changelog/**,.ce/pr-manifests/**"` |
| `mutation_class` | `"docs"` |
| `class_flag` | `true` |
| `work_class` | normalized declared class (`"XS"` or `"S"`) |
| `size_band` | one of `{"target_advisory", "warn", "explain_or_split"}` (not `"split_required"`) |
| `changed_paths` | full list of paths in the diff |
| `pr_number` | GitHub PR number |
| `head_sha` | exact head SHA at decision time |
| `author_login` | PR author login |
| `approver_login` | approver login (must differ from author) |
| `checks_green` | `true` |
| `reviewDecision` | `"APPROVED"` |
| `enabling_decision_ref` | this ADR's ratification reference |
| `policy_sha` | SHA256 of the active mutation policy JSON |
| `run_mode` | `"ceo"` or `"strangeLoop"` |
| `kill_switch` | `false` |

The actuator emits an `audit_record` field on every actuation result (Actuated,
Refused, Dormant) (`automerge_actuator.py:_audit_record()`). The `surface` field
is always `"ce-automerge-actuator"`. These records must be retained in daemon
state under `CE_QUEUE_DAEMON_ROOT` for post-arc review.

### d. Kill switch and fail-closed behavior

**Per-class disarm:**
```bash
# arm: set tier flag to false
# policy.json: tiers.docs_envelope.auto_merge = false
# (set via governance PR updating the policy materialization variables;
#  no direct edit of policy.json)
```

**Global kill switch:**
```bash
ce automerge-kill-switch on   # arms global kill switch immediately
ce automerge-kill-switch off  # clears kill switch
ce automerge-kill-switch status  # reads current state
```
(Implemented in `_automerge_kill_switch`, `ce_cli.py:5144`; reads/writes `.ce/state/automerge/policy.json`.)

**Fail-closed rules:**
- Live policy unreadable → `Dormant` (no actuation)
- Any predicate returns unexpected value → `Refused` with reason code, no actuation
- `gh pr view` or `gh pr checks` API call fails → `Refused`
- `required_checks` list empty or missing → `Refused: required_checks_empty`
- Kill switch True at decision time → `auto_blockers: ["kill_switch"]` → GESTURE
- Kill switch True at actuation time (re-read live policy) → `Refused: live_kill_switch_active`
- Tier flag not True → `Refused: live_tier_flag_not_true`
- Path predicate fails at actuation re-verification → `Refused: tier_docs_envelope_path_predicate_failed`

### e. What human gesture is removed; what authority remains

**Removed:** The post-approval merge trigger. Previously the controller manually
called `gh pr merge --auto` (or equivalent) after approving. The queue daemon now
actuates enqueue automatically once predicates P1–P15 are simultaneously satisfied.

**Not removed:**
- Non-author exact-head approval (Key 1 approval; mandatory; no exception)
- Fresh-context Key-2 reviewer (dispatcher must still launch the reviewer
  subagent; the reviewer's APPROVED verdict is P7/P8)
- All CI required checks
- Controller byte-verification (Key 1 path-set digest + carrier integrity)
- Operator policy ratification of this ADR (one-time, governs all MC1 PRs)
- Audit trail (decision JSON + actuator audit record retained per merge)

**Authority that remains:**
- Operator: ratifies this policy; arms/disarms the global kill switch;
  may disarm per-class flag at any time without further governance.
- Controller: maintains Key 1 (byte-verify + approve); dispatches Key-2 reviewer.
- Queue daemon: actuates enqueue only; never approves; never extends authority
  beyond this predicate set.

---

## 3. Class 2 — MC0: Carrier-changelog only (RATIFIED 2026-07-17, codified here)

### a. Name and intent

**MC0 — `carrier_changelog_mechanical`**: Pre-delegated merge class for PRs whose
entire diff consists of exactly the per-PR carrier file and its companion changelog
fragment (same branch slug; no other paths). These are provably metadata-only PRs
whose correctness is fully determined by machine verification. For this class, the
fresh-context Key-2 LLM reviewer subagent is **replaced** by the machine predicate;
the byte-verified predicate IS Key 2. Non-author exact-head approval is still
mandatory (Key 1 approval is not removed).

This class was ratified by the Operator on 2026-07-17 ("the machine predicate
replaces the fresh-context Key-2 reviewer" — see `ce-mc0-active-merge-class.md`
evidence ref). This ADR is the formal policy record codifying that ratification.
The tier has been implemented in the automerge engine since before ratification
(`AUTOMERGE_TIER_CARRIER_CHANGELOG = "carrier_changelog_mechanical"`,
`automerge_policy.py:42`).

### b. Machine predicate set

All of the following must hold simultaneously:

| # | Predicate | Source |
|---|---|---|
| P1 | `carrier_changelog_tier_matches(changed_paths)` is True: every path in the set starts with `.ce/changelog/` OR `.ce/pr-manifests/`. No empty path in the set. | `automerge_policy.py:912-916` (`carrier_changelog_tier_matches`; `_CARRIER_CHANGELOG_PREFIXES = (".ce/changelog/", ".ce/pr-manifests/")`) |
| P2 | The PR adds exactly one changelog fragment: a single file under `.ce/changelog/<slug>.md` (ADDED, not modified/deleted). | `path_manifest_fidelity.py:_run_with_base_per_pr()` (status A check) |
| P3 | The PR adds exactly one carrier file: a single file under `.ce/pr-manifests/<slug>.md` (ADDED, not modified/deleted). | `path_manifest_fidelity.py:_run_with_base_per_pr()` |
| P4 | The slug of the carrier file exactly matches `branch_slug(head_ref)`, and the changelog slug matches the carrier slug (same filename stem for both). | `path_manifest_fidelity.py:branch_slug()`; enforced by the `_carrier_stem` check |
| P5 | The carrier's `*_PATHS_COUNT` and `*_PATHS_SHA256` declarations are self-consistent with the fenced path-set (`path_manifest_fidelity.scan_document()` passes with no errors). The carrier's declared path-set lists EXACTLY the two files changed in the diff (self-inclusive). | `path_manifest_fidelity.py:scan_document()`, `_normalize_manifest()` |
| P6 | The carrier lists `- **Declared work class:** XS` or `- **Declared work class:** S` (or legacy aliases `tiny`/`story`). Declared work class ∈ AUTOMERGE_CANARY_WORK_CLASSES. | `automerge_policy.py:39-41`; `work_sizing.py:LEGACY_WORK_CLASS_ALIASES` |
| P7 | `mutation_class_for_paths(changed_paths, policy)` returns `"docs"`. All paths match `docs` predicates in `automerge_mutation_policy.yaml` (`.ce/changelog/**`, `.ce/pr-manifests/**` both match the `docs` predicate). | `automerge_mutation_policy.yaml:path_predicates.docs`; `mutation_classifier.py:136-170` |
| P8 | `size_band != "split_required"`: included changed lines < 1001. For purely mechanical carrier/changelog pairs this will typically be `target_advisory` (< 400 lines). | `work_sizing_floor.py:_size_band()`; `automerge_policy.py:579-580` |
| P9 | All required CI checks green (live re-verification at actuation). Required check: `"Validate governance artifacts"`. | `automerge_mutation_policy.yaml:required_checks`; `automerge_actuator.py:_live_required_checks_green()` |
| P10 | `review_decision` is `"APPROVED"` (not `"CHANGES_REQUESTED"`). | `automerge_policy.py:575-578` |
| P11 | `author_login != approver_login` (case-insensitive), re-verified at actuation from live GH API. | `automerge_actuator.py:_live_author_approver_independent()` |
| P12 | `policy_state.kill_switch == False` (both decision-level and live-policy-level). | `automerge_policy.py:585-586`; `automerge_actuator.py:117` |
| P13 | Run mode ∈ `{"ceo", "strangeLoop"}`. | `automerge_policy.py:36-38` |
| P14 | `policy_state.class_flag("docs") == True` AND `policy_state.tier_flag("carrier_changelog_mechanical") == True`. | `automerge_policy.py:205-211` |
| P15 | `enabling_decision_ref` is non-empty; must reference this ADR's ratification record (or the prior 2026-07-17 MC0 ratification record as a valid predecessor). | `automerge_policy.py:593-594` |

**No CHANGES_REQUESTED block:** If any reviewer has submitted CHANGES_REQUESTED,
the PR is blocked regardless of other predicates (`automerge_policy.py:575-576`).

**Deny-set:** Any path NOT starting with `.ce/changelog/` or `.ce/pr-manifests/`
in the diff immediately moves the PR to `carrier_changelog_tier_matches() = False`
→ tier = None → GESTURE. This is the primary containment boundary.

### c. Evidence bundle emitted at merge time

Same schema as Class 1, with the following mandatory field values:

| Field | Required content |
|---|---|
| `decision` | `"AUTO"` |
| `tier` | `"carrier_changelog_mechanical"` |
| `tier_flag` | `true` |
| `path_envelope` | `".ce/changelog,.ce/pr-manifests"` |
| `mutation_class` | `"docs"` |
| `changed_paths` | exactly the two paths: `[".ce/changelog/<slug>.md", ".ce/pr-manifests/<slug>.md"]` |
| `approver_login` | non-author GitHub login who placed the exact-head approval |

In addition, a **predicate summary note** SHOULD be written to the PR body or a
commit message by the controller at approval time, noting: "MC0 predicate verified:
carrier `<slug>`, digest `<PATHS_SHA256>`, size band `<band>`, CI green." This is
advisory for human audit; the machine record is the canonical evidence.

### d. Kill switch and fail-closed behavior

**Per-tier disarm:**
Set `tiers.carrier_changelog_mechanical.auto_merge = false` in the policy state.
This can be done by updating the `CE_AUTOMERGE_TIER_CARRIER_CHANGELOG` environment
variable to a falsy value and re-materializing the policy via the governed workflow
(`automerge_policy.py:AUTOMERGE_TIER_CARRIER_CHANGELOG_ENV`).

**Global kill switch:** same as Class 1 (`ce automerge-kill-switch on`).

**Fail-closed rules (additional to Class 1):**
- `carrier_changelog_tier_matches()` fails at actuation re-verification →
  `Refused: tier_carrier_changelog_path_predicate_failed`
  (`automerge_actuator.py:360-361`)
- Carrier slug does not match `branch_slug(head_ref)` → CI gate blocks before
  decision reaches the automerge engine (path_manifest check fails in CI)
- Carrier self-consistency check fails (count/hash mismatch) → CI gate blocks
- More than two files in the diff → P1 predicate will fail (at least one path
  won't start with `.ce/changelog/` or `.ce/pr-manifests/`)

### e. What human gesture is removed; what authority remains

**Removed:** The fresh-context Key-2 LLM reviewer subagent. For provably-mechanical
carrier+changelog-only diffs (where the path set, size, and carrier integrity are
machine-verifiable), dispatching a fresh-context reviewer adds nothing beyond what
the machine predicate already checks. The controller does NOT spawn a reviewer
subagent for MC0-qualifying diffs. This is the amendment ratified 2026-07-17.

Also removed: the post-approval merge trigger (same as Class 1).

**Not removed:**
- Non-author exact-head approval (Key 1 approval; mandatory without exception)
- Controller byte-verification (Key 1 path-set digest: `sha256("\n".join(sorted(unique_paths)) + "\n")` against carrier)
- All CI required checks
- Operator policy ratification (this ADR formalizes the 2026-07-17 ratification)
- Audit trail (decision JSON + actuator audit record)

**Authority that remains:**
- Operator: ratified the predicate on 2026-07-17; arms/disarms kill switch at
  any time.
- Controller: Key 1 byte-verify + non-author approval; the predicate itself is
  the controller's Key-2 delegation for this class.
- Queue daemon: actuates enqueue only; never approves.

---

## 4. Class 3 — MC2: XS/S bounded code within seat territory (proposed, implementation gap)

### a. Name and intent

**MC2 — `xs_s_within_territory`**: Pre-delegated merge class for PRs whose entire
diff (a) has a declared work class of XS or S, (b) touches only paths within the
authoring seat's registered territory, and (c) has passed a fresh-context
policy-fired AutoReview (not controller-dispatched; dispatched by the automerge
decision engine from the policy's reviewer-dispatch configuration). The fresh-context
reviewer is still required (unlike MC0); what is removed is the post-approval merge
trigger and the need for the controller to be present when the approval arrives.

**Implementation gap (must be resolved before this class is armed):** The current
automerge engine has no territory registry and no policy-fired reviewer-dispatch
mechanism. Both must be implemented and validated before this class may be transitioned
from `proposed` to `ratified`. This ADR defines the design target and predicate set.

### b. Machine predicate set

All of the following must hold simultaneously:

| # | Predicate | Source / Gap |
|---|---|---|
| P1 | Declared work class ∈ `{XS, S}`. | `automerge_policy.py:39-41` (existing) |
| P2 | `size_band ∈ {"target_advisory", "warn"}` (not `"explain_or_split"` or `"split_required"`): included changed lines < 800. | `work_sizing_floor.py:_size_band()` (existing, tighter bound than Class 1) |
| P3 | ALL changed paths are within the authoring seat's claimed territory. The territory is a path-set declared in the seat's active territory record (`active_work_ledger` or equivalent registry entry). Any path outside the registered territory → GESTURE. | **GAP: territory registry check not yet implemented in automerge engine** |
| P4 | Changed path set is disjoint from all other active seats' territory claims (no path conflicts). | **GAP: not yet implemented** |
| P5 | `mutation_class_for_paths(changed_paths, policy)` ∈ `{"docs", "code"}`. Any path escalating to `schema`, `deploy`, or any privileged class → GESTURE. | `mutation_classifier.py:136-170` (existing); deny-set below |
| P6 | `ratification_gates` for the mutation class ∈ `{("auto_back_gate",), ("distinct_review", "operator_merge")}`. Schema, deploy, and privileged classes are excluded by P5. | `work_sizing.py:_RISK_TABLE` (existing) |
| P7 | A fresh-context AutoReview was policy-fired (not controller-dispatched) and returned `APPROVED` by a reviewer whose login differs from the PR author. The reviewer-authority-envelope must be `mechanic: pr_review`, `capability: independent_review_venue`, `pr_number` matching this PR, and `head_sha` matching the exact head at decision time. | **GAP: policy-fired reviewer-dispatch not yet implemented; reviewer-authority-envelope seam (G2.007.2) is implemented but not wired to automerge trigger path** |
| P8 | `review_decision == "APPROVED"` (not `"CHANGES_REQUESTED"`). | `automerge_policy.py:575-578` (existing) |
| P9 | `author_login != approver_login`, re-verified at actuation from live GH API. | `automerge_actuator.py:_live_author_approver_independent()` (existing) |
| P10 | All required CI checks green (live re-verification at actuation). | `automerge_actuator.py:_live_required_checks_green()` (existing) |
| P11 | `policy_state.kill_switch == False`. | `automerge_policy.py:585-586` (existing) |
| P12 | Run mode ∈ `{"ceo", "strangeLoop"}`. | `automerge_policy.py:36-38` (existing) |
| P13 | Per-class tier flag `xs_s_within_territory.auto_merge == True` in policy state. | **GAP: tier not yet registered in `_AUTOMERGE_TIERS`** |
| P14 | `enabling_decision_ref` is non-empty, references this ADR's ratification. | `automerge_policy.py:593-594` (existing) |
| P15 | Carrier and changelog present, consistent, slug matches (same requirements as Class 1). | `path_manifest_fidelity.py` (existing) |

**Deny-set (any of these → GESTURE regardless of other predicates):**
- Any path matching `schemas/**`, `*.schema.yaml`, `*.schema.json` (schema class)
- Any path matching `deploy/**`, `.github/**`, `Dockerfile*` (deploy class)
- Any path matching any privileged class pattern from `automerge_mutation_policy.yaml`
- Any path matching `validators/creator_engine_validator/forge/approval_capability.py` (attestation surface)
- Any path outside the seat's registered territory (P3)
- Any path under another seat's territory (P4)
- `mutation_class_for_paths()` returns anything not in `{"docs", "code"}` (P5)

**Implementation work required before arming Class 3:**
1. Territory registry: a machine-readable mapping of seat ID → authorized path-set,
   consulted by the automerge decision engine at classify time.
2. Policy-fired reviewer-dispatch: the queue daemon (or a companion daemon) must be
   able to launch a fresh-context reviewer subagent under a valid
   reviewer-authority-envelope when a PR satisfies P1–P2, P5–P6, and is within
   territory per P3–P4, without the controller being present.
3. New automerge tier `xs_s_within_territory` registered in `_AUTOMERGE_TIERS`
   and `AutoMergePolicyState.tiers` with its own `tier_flag`.
4. AutoReview result linked to the automerge decision: the decision engine must
   verify that a valid policy-fired reviewer verdict (APPROVED) exists for the
   exact head SHA before emitting `"AUTO"`.

### c. Evidence bundle emitted at merge time

Same schema as Class 1, plus:

| Field | Required content |
|---|---|
| `tier` | `"xs_s_within_territory"` |
| `territory_claim_ref` | identifier/hash of the seat's active territory claim used to verify P3–P4 |
| `autoreview_envelope_id` | `envelope_id` from the policy-fired reviewer-authority-envelope |
| `autoreview_head_sha` | head SHA at the time the AutoReview verdict was issued (must equal `head_sha`) |
| `reviewer_login` | login of the policy-fired reviewer (must differ from `author_login`) |

### d. Kill switch and fail-closed behavior

Same as Class 1/2. Additional:
- Territory check fails or territory registry unreadable → `Refused` (fail-closed)
- Policy-fired reviewer envelope missing or invalid → GESTURE (Key-2 not satisfied)
- AutoReview verdict is `"blocking_findings_present"` or `"cannot_review"` → GESTURE
- AutoReview verdict on mismatched head SHA → GESTURE (stale review)
- Territory conflict detected (P4) → GESTURE

### e. What human gesture is removed; what authority remains

**Removed:** The post-approval merge trigger. The controller does not need to be
present when the policy-fired AutoReview completes and the approval arrives; the
queue daemon actuates enqueue automatically.

**Not removed:**
- Non-author exact-head approval (Key 1 approval; mandatory)
- Fresh-context Key-2 reviewer (policy-fired, not controller-dispatched; but still
  a fresh-context independent review)
- Controller byte-verification (Key 1 path-set + territory membership check)
- All CI required checks
- Operator policy ratification (this ADR)
- Audit trail (decision JSON + actuator record + AutoReview envelope)

**Authority that remains:**
- Operator: ratifies this policy; arms/disarms kill switch; may narrow territory
  definitions at any time.
- Controller: Key 1 byte-verify + non-author approval; does NOT dispatch reviewer.
- Policy engine: fires the reviewer-authority-envelope; reviewer is policy-sourced.
- Queue daemon: actuates enqueue only; never approves.

---

## 5. Rollout order

Class 2 (MC0) is already active. The ordered rollout for this ADR is:

**Phase 1 — Class 2 formal codification (this ADR ratification):**
- MC0 predicate text in this ADR replaces the informal 2026-07-17 session record as
  the canonical policy text. No change to daemon behavior.
- Demonstration cycle: collect per-class metrics (see §6) for the next 10 MC0 merges
  post-ratification.

**Phase 2 — Class 1 (MC1 docs-envelope):**
- Prerequisite: Class 2 demonstration cycle complete; metrics show predicate is stable
  (zero spurious GESTURE on qualifying PRs; zero false AUTO on non-qualifying PRs).
- Arms `tiers.docs_envelope.auto_merge = true` in policy state via a governance PR.
- Requires Key-2 reviewer for all MC1 PRs; the AutoReview subagent is still dispatched.
- Collect MC1 metrics for next 20 docs PRs before considering Phase 3.

**Phase 3 — Class 3 (MC2 XS/S within territory):**
- Prerequisite: Class 1 demonstration cycle complete AND implementation gaps (P3, P4,
  P7, P13 from §4b) closed and validated by full pytest suite + preflight.
- Territory registry design and policy-fired reviewer-dispatch require a separate
  design ADR or explicit Operator direction before implementation begins.
- Implementation tracked separately; this ADR provides the predicate target only.

---

## 6. Per-class metrics to report at arc close

These metrics are emitted per class from the automerge decision records in
`.ce/state/automerge/decisions/`. The controller reports them at arc DF-4 close:

### Class 2 (MC0 / carrier_changelog_mechanical):
- Total `decision == "AUTO"` with `tier == "carrier_changelog_mechanical"` since ratification
- Total `decision == "GESTURE"` with `tier == "carrier_changelog_mechanical"` (false negatives for qualifying PRs)
- False-negative rate: GESTURE decisions where post-hoc inspection confirms all predicates were satisfied (bug in predicate)
- False-positive rate: AUTO decisions where any predicate is revealed non-satisfied in retrospect (security-relevant)
- Actuation success rate: `ActuationResult.status == "Actuated"` / total AUTO decisions
- Latency reduction: median time from push to merge queue entry (MC0 vs. full two-key PRs)

### Class 1 (MC1 / docs_envelope):
- Same set as Class 2 with `tier == "docs_envelope"`
- Additional: fresh-context reviewer dispatch count (reviewer must still be dispatched)
- AutoReview round-trip latency (approval submission to actuation)

### Class 3 (MC2 / xs_s_within_territory):
- Deferred until Phase 3 arms

**Gate for MC1/MC2 progression:** zero confirmed false-positive (AUTO on non-qualifying)
events; false-negative rate < 5% (qualifying PRs landing GESTURE due to predicate bug);
no security or confidentiality finding in any AUTO-merged diff.

---

## 7. Threat notes

For each class: what a malicious or buggy PR could attempt and which predicate stops it.

### Class 2 (MC0):

| Threat | Predicate that stops it |
|---|---|
| Add a code file alongside the carrier | P1: `carrier_changelog_tier_matches()` → False (any path not in `.ce/changelog/` or `.ce/pr-manifests/` exits the tier immediately) |
| Submit a carrier with a mismatched slug (to claim another branch's authority) | P4 + CI gate: `branch_slug(head_ref)` mismatch → `path_manifest_carrier_slug_mismatch` in CI before decision |
| Submit a carrier listing paths not in the diff (to pre-authorize future changes) | P5: `scan_document()` detects count/hash inconsistency; CI `path_manifest_fidelity` check fails |
| Self-review (author ≈ approver) | P11: `_distinct_login_pair()` + live re-verification at actuation |
| Post approval on a stale head, then push | `actuate_if_ready()` uses `head_sha` from decision; live checks run on current head; stale approval does not satisfy the live-author/live-checks re-verification |
| Bypass kill switch by sending a pre-armed decision file | `actuate_if_ready()` re-reads live policy state before acting (`_live_policy_state()`); stale decision with `kill_switch: false` is rejected if live policy has kill_switch True |
| Include `.github/` or `deploy/` file in a carrier-tier PR | P1: path does not start with `.ce/changelog/` or `.ce/pr-manifests/` → tier mismatch |
| Include `docs/contracts/` (governance surface) in carrier | P1: same; governance paths not in `.ce/` namespace |

### Class 1 (MC1):

| Threat | Predicate that stops it |
|---|---|
| Include a Python file in `docs/` (e.g., `docs/scripts/build.py`) | P2: `mutation_class_for_paths()` → if any path matches `validators/**` or `tools/**` → `code` class → not in AUTO_CLASSES → GESTURE. BUT `docs/scripts/build.py` would match `docs/**` only (not `validators/**`); mutation policy would classify as `docs`. Resolution: extend deny-set to reject non-markdown files under `docs/` if the file extension is executable. **Note: this is a residual risk in the current mutation policy YAML for Class 1; executable files under `docs/` classified as `docs` mutation class.** |
| Include `docs/contracts/authority-matrix.yml` | P2 check: `docs/contracts/**` matches `governance` predicate in `automerge_mutation_policy.yaml` → mutation_class = "governance" (privileged) → GESTURE |
| Include `.github/workflows/*.yml` | P2: matches `deploy` predicate → GESTURE; also P1 via docs_envelope check: `.github/**` not in the docs envelope |
| Include `schemas/*.yaml` | P1: `schemas/**` not a docs path; P2: matches `schema` class → GESTURE |
| No reviewer (self-approve) | P8/P9: fresh-context reviewer verdict required; self-approval blocked |

**Residual risk for Class 1:** Non-markdown executable or config files that happen to reside under `docs/` (e.g., `docs/scripts/`, `docs/hooks/`) would pass the path predicate but should not auto-merge. Mitigation: extend `docs_envelope_tier_matches()` with an explicit allow-list of file extensions (`*.md`, `*.html`, `*.txt`, `*.png`, `*.svg`, image formats) OR extend the deny-set in the mutation policy to re-classify `docs/**/*.py`, `docs/**/*.sh`, `docs/**/*.yaml` as `code` or `schema`. This risk is rated LOW given CE's current `docs/` content pattern (no executables) but must be evaluated before arming.

### Class 3 (MC2):

| Threat | Predicate that stops it |
|---|---|
| Include paths outside the seat's territory | P3: territory registry check → GESTURE |
| Claim a territory that overlaps another active seat | P4: territory disjointness check → GESTURE |
| Include `.github/` or a privileged path | P5: mutation_class escalates to `deploy` or privileged → GESTURE |
| Schema change disguised as code | P5: `schemas/**` → `schema` class → GESTURE |
| Forge a policy-fired reviewer envelope | G2.007.2 seam: reviewer-authority-envelope requires a `ratified_prompt_sha` that matches a ratified reviewer prompt SHA; forgery of the prompt SHA is computationally infeasible |
| AutoReview on a stale head | P7: `head_sha` in envelope must match exact head SHA at decision time |

---

## 8. Non-goals

The following categories of PRs are **explicitly excluded** from all three merge
classes and must remain two-key (full Key 1 + Key 2 + controller enqueue) until a
separate governance ratification covers them:

1. **Security-class changes**: any path matching security predicates in
   `automerge_mutation_policy.yaml` (`tools/egress-broker/**`,
   `validators/creator_engine_validator/forge/cred_injection_proxy.py`, etc.)
2. **Dependency updates**: `package.json`, `pyproject.toml`, `requirements*.txt`,
   lockfiles — excluded by the `lockfile` category in `excluded_path_category()`;
   but actual dependency manifests (non-lockfile) are code-class and not auto.
3. **Public-surface documentation with confidentiality exposure risk**: public-facing
   `docs/` that undergoes confidentiality scanner review remains Key 2 (the scanner
   is the fresh-context reviewer for that surface; the scanner result is the
   Key-2 verdict).
4. **Governance changes**: any path matching governance predicates (`docs/contracts/**`,
   `GOVERNANCE.md`, `CODEOWNERS`, etc.). Governance mutation class is privileged.
5. **Release and deploy changes**: `.github/**`, `deploy/**`, CI workflows,
   `Dockerfile*`. Deploy mutation class is privileged.
6. **Identity, attestation, redaction changes**: always privileged; non-delegable;
   ring-1 push block applies.
7. **Schema changes**: `schemas/**`. Schema class gates are `operator_front_bet` +
   `operator_merge`.
8. **ADR or ratification records**: governance class; always two-key.
9. **Any PR with `size_band == "split_required"`** (> 1000 included lines after
   exclusions): must be split before it can qualify for any merge class.
10. **Any PR touching the automerge machinery itself**: `forge/automerge_*.py`,
    `forge/mutation_classifier.py`, `ce_cli.py` automerge sections, the policy YAML,
    the kill-switch CLI. These are governance/code-class changes that require Key 2.

---

## 9. Relationship to existing ADRs and prior decisions

| Prior artifact | Relationship |
|---|---|
| ADR-0013 (substrate-independent authority) §D, principle 3 | This ADR implements principle 3: "Human-rooted ratification moves up to the policy level." The merge class ratification is exactly the policy-level gesture. |
| ADR-0013 §D1 autonomous/reserved taxonomy | Merge/enqueue action is classified as `autonomous` when predicates hold; reserved otherwise. This ADR defines the predicates precisely. |
| Feature 001 FR-007 (author/approver separation) | Preserved by P9/P11 in all three classes; re-verified at actuation time. |
| Feature 001 FR-008 (privileged classes) | Privileged classes are explicitly excluded (§8 non-goals). |
| Feature 002 FR-013 (CI verifies, never ratifies) | CI green is a gate predicate, not ratification. Machine predicate replaces LLM reviewer review; it is not ratification; Operator policy ratification of this ADR is the ratification event. |
| `docs/delivery/REVIEW_GATE.md` §m.1 | Review evidence is not ratification — still holds. For MC0 the machine predicate IS the Key-2 evidence; for MC1/MC2 the fresh-context reviewer verdict is the Key-2 evidence. Neither substitutes for the Operator ratification of this ADR. |
| `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md` §d | Review-vs-ratification distinction maintained. |
| `docs/governance/MUTATION_CLASS_MODEL.md` | Non-privileged classes (`docs`, `code`) are eligible for merge-class delegation; privileged classes (`deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`) are not and remain in §8 non-goals. |
| `ce-mc0-active-merge-class.md` (2026-07-17 ratification) | This ADR formalizes that ratification as a governance document. The controller session record of 2026-07-17 (internal, evidence tag operator-session-20260717) is the evidence of Operator consent; this ADR is the policy text that gives that consent a machine-checkable form. |

---

## 10. Ratification requirements

This ADR requires Operator ratification before Classes 1 or 3 may be armed. Class 2
is already ratified (2026-07-17); this ADR formalizes that ratification.

**For Class 2 (codification only):** ratification of this ADR text supersedes the
session record as the canonical policy document. No behavioral change at ratification;
existing MC0 behavior continues under the formal text.

**For Class 1 (new):** Operator ratification of this ADR PLUS explicit arming
(setting `tiers.docs_envelope.auto_merge = true` in the policy state via a governance
PR) is required before the queue daemon actuates MC1 merges.

**For Class 3 (new, proposed):** Operator ratification of this ADR PLUS
implementation of the territory registry and policy-fired reviewer-dispatch (with
their own governance PRs) PLUS explicit per-class arming is required. Class 3 MUST
NOT be armed before all implementation gaps in §4b are closed.

**Ratification record format:** The controller must emit a ratification record in the
standard format (`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md §b`) naming
the Operator, the ratification date, and the `ratification_prompt_sha` of the prompt
that produced this ADR draft.
