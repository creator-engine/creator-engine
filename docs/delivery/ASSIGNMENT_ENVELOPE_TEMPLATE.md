# Assignment Envelope Template (Manual)

**Status**: Slice E authored draft. This document defines the reusable
manual **Assignment Envelope** template that a Source-ratified
authority hands to a visible Claude Code (or equivalent) consumer in
order to bound a single governed batch. The template is a markdown
contract; concrete machine-readable schemas, dispatcher automation,
and worktree-lifecycle automation are downstream Feature 005 work and
are out of scope for Slice E.

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate and the Feature 002 operating-model Assignment
Envelope contract recorded under
[`../../specs/002-canonical-docs-and-operating-model/spec.md`](../../specs/002-canonical-docs-and-operating-model/spec.md)
FR-005 through FR-011. The template here is the delivery-view
manual surface of that contract; it does not redefine it.

## a. Purpose

A filled Assignment Envelope makes one fact answerable from a fresh
clone:

> Under whose Source-ratified authority, in which isolated worktree,
> against which exact files and prohibited surfaces, with what
> validation and stop conditions, may a named consumer perform this
> single governed batch?

The envelope is the **only** authorized entry point into a governed
mutation. A "go ahead" message on a non-designated surface, a CI
green check, an agent review verdict, or an external tracker green
status MUST NOT substitute for a Source-ratified envelope.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`../../specs/002-canonical-docs-and-operating-model/spec.md`](../../specs/002-canonical-docs-and-operating-model/spec.md) FR-005 through FR-011 | Canonical Assignment Envelope contract recorded in the Feature 002 operating-model spec. Where it differs from this template, the contract controls. |
| Feature 002 §Assignment Envelope (FR-005 through FR-011) | Operating-model envelope schema, ratification posture, and the rule that `/speckit-implement` is permitted only inside a Hermes-authored envelope. |
| Feature 001 FR-007 / FR-008 / FR-016 / FR-020a | Author/approver separation; privileged-class enumeration; ratification flow; ratification record requirements. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | The eleven Ready criteria the envelope is consumed against, and the privileged-class rule. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b | The nine Done criteria the envelope's outcome is evaluated against. |
| [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) | Worktree/branch naming, one-driver-per-worktree rule, and runtime preflight protocol. |
| [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md) | Consumer-side checklist that runs against a filled envelope. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) | Independent verifier-side checklist used after consumption. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) | Review gate the envelope's review/verification evidence fields feed. |
| Optional external trackers | **Non-canonical** references only. A fresh clone is sufficient to consume and audit an envelope; no external tracker credential or network state is required. |

Where this template and any upstream source disagree, the upstream
source of truth controls until Source ratifies a correction.

## c. Template structure

A filled envelope is a markdown document with the following sections
in order. Sections marked **REQUIRED** must be populated for every
envelope; sections marked *(conditional)* are populated only when
their condition is met.

### c.1 Header (REQUIRED)

| Field | Semantics |
|---|---|
| `envelope_id` | Stable identifier (e.g., `sprint-0/slice-e-assignment-runtime-protocol`). Matches the backlog id under `./BACKLOG.md` where one applies. |
| `envelope_title` | One-line human-readable title. |
| `envelope_date` | Calendar date the envelope is authored (UTC date, `YYYY-MM-DD`). |
| `repo` | Repo-relative path or canonical repo name (e.g., `creator-engine`). |
| `base_branch` | The canonical branch the worktree branches from (typically `main`). |
| `base_commit` | The commit SHA the worktree branches from, with a short subject line for human readability. |
| `local_branch` | The local feature branch name. Follows the naming convention in [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) §c. |
| `local_worktree_path` | Repo-relative or absolute path to the isolated worktree directory. Treated as an instance-local fact and MUST NOT be propagated into governed artifacts beyond this envelope. |

### c.2 Source ratification / authority record (REQUIRED)

| Field | Semantics |
|---|---|
| `ratifier` | Identifies the ratifier. For Sprint 0 / v0.1 privileged classes this MUST be `source` (Feature 001 FR-008). Once Source ratifies delegation, a `source`-delegated `ratifier` MAY appear for non-privileged classes. |
| `ratification_record_ref` | Repo-relative path or quoted excerpt of the Source-ratification record authorizing this envelope, OR an explicit waiver field referencing the Source-ratified text that waives normal requirements for this named batch. |
| `ratification_scope` | One-paragraph restatement of what Source ratified: which mutation classes, which paths, which prohibited surfaces, and which mechanics (e.g., "author docs only; no staging/commit/push/PR/merge/branch deletion under this envelope"). |
| `waivers_named` | List any explicit Source-ratified waivers in effect for this envelope (e.g., "named waiver of formal reviewer-identity requirement for this batch only, because Feature 004 has not yet instantiated a governed reviewer identity"). Absence of a waiver means none applies. |

The ratifier field is intentionally distinct from any review evidence
field below: **review evidence is not Source ratification**, per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1 and Feature 002 FR-013 /
FR-017.

#### c.2.1 Operating-mode carriers *(optional; G2.002.1 pure carriers)*

These fields **carry** operating-mode posture from the
[operating-mode substrate](../../specs/v2/002-operating-mode-substrate/spec.md)
into the envelope. They are **pure carriers**: they record posture and **mint
no authority**. They do not relax §c.2 ratification, §c.3 mutation classes, or
the Operator-only privileged floor. Absent fields resolve to `strict`.

| Field | Semantics |
|---|---|
| `operating_mode` | Optional; `strict | auto | transcendence`. Default `strict`. `auto`/`transcendence` require an Operator-ratified policy and a `ratification_evidence_ref`; migration never infers elevation. |
| `autonomy_class` | Optional; the operating-mode autonomy enum. `reserved_future_agent_ratification` is reserved-inactive and MUST NOT be an active autonomy. |
| `lane_kind` | Optional; `read-only | implementation | review | approval | merge | audit`. Lets a downstream reviewer/approver/merger lane be a distinct lane kind; PR-review/approval/merge enforcement is downstream, not in this carrier. |
| `ratification_evidence_ref` | Optional inherited ratification-evidence pointer required for elevated modes or privileged (`approval`/`merge`) lane kinds. Advisory carriage; confers no authority by itself. |

These carriers travel on the Active-Work Ledger record under the lane's
`envelope_ref` (see
[`../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`](../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md)
§h); G2.002.1 introduces no standalone assignment-envelope schema.

### c.3 Mutation classes (REQUIRED)

| Field | Semantics |
|---|---|
| `anticipated_mutation_classes` | Array of Feature 001 baseline mutation classes the envelope authorizes, per [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md). Privileged classes (`deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`) trigger Feature 001 FR-008 and the privileged-class rule in [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §c. |
| `dominant_class` | The single most privileged class in `anticipated_mutation_classes`. Drives the ratifier and review-gate requirements. |

Mutations not enumerated here are out of scope and MUST be refused
by the consumer regardless of how mechanically convenient they
appear.

### c.4 Authorized actor / role / pane (REQUIRED)

| Field | Semantics |
|---|---|
| `authorized_actor` | Human-readable identifier for the consumer (e.g., "Claude Code architect/implementer in the visible pane"). Concrete tool / model / host / account bindings are deployment-time overlay decisions per [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) §c and MUST NOT be hard-coded as upstream constants. |
| `role_category` | Feature 001 baseline role category, per [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md): typically `implementer` or `architect` for an envelope consumer. |
| `pane_identity` | The visible pane/session the actor will operate from, if relevant for one-driver-per-worktree (e.g., "visible Claude Code pane in the named worktree"). Treated as runtime-local context. |
| `controller` | The coordinating identity that authored or relayed the envelope (e.g., "Nefarious as controller/verifier"). The controller is **not** the ratifier unless they are Source. |

Author/approver separation (Feature 001 FR-007) applies: the
`authorized_actor` MUST NOT be the `ratifier`, and MUST NOT author
the review evidence that authorizes their own merge.

### c.5 Exact allowed files and allowed operations (REQUIRED)

| Field | Semantics |
|---|---|
| `allowed_create_paths` | Exhaustive list of repo-relative paths the envelope permits the consumer to **create**. |
| `allowed_update_paths` | Exhaustive list of repo-relative paths the envelope permits the consumer to **update** (minimal coherence updates only, unless explicitly broadened). |
| `allowed_operations` | Enumerated operations the consumer may perform on those paths (e.g., `author`, `update`, `add cross-reference`). Bulk operations such as `delete`, `rename`, `chmod`, or `mv` are not included unless named explicitly. |
| `path_complement_rule` | One-line statement that anything not enumerated above is out of scope and MUST be refused. |

The allowed-paths set is **closed**. If the consumer believes a
mutation outside the allowed set is necessary, the consumer halts
and escalates per §c.11 stop condition rather than broadening scope
implicitly.

Per
[`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md)
§c, the envelope MUST declare the manifest's normalized count and
SHA256 alongside the fenced manifest block. The required shape is:

| Field | Semantics |
|---|---|
| `allowed_paths_count` (or `*_PATHS_COUNT=` declaration) | The number of unique, normalized path lines across `allowed_create_paths` and `allowed_update_paths`. The shape `<NAME>_PATHS_COUNT=<integer>` immediately precedes the fenced manifest. |
| `allowed_paths_sha256` (or `*_PATHS_SHA256=` declaration) | The SHA256 of the normalized (sorted, deduplicated, LF-joined, one trailing newline, UTF-8) manifest. The shape `<NAME>_PATHS_SHA256=<64 lowercase hex>` immediately precedes the fenced manifest. |
| fenced manifest block | A ```` ```text ```` block immediately following the declarations whose body is one repo-relative path per non-empty line, sorted, deduplicated. |

The consumer recomputes the count and SHA256 from the fenced block at
preflight time and halts on any mismatch (count, hash, or the
`path_manifest_init_py_corruption` regression class). The
verifier-side `path_manifest_fidelity` check is the validator
implementation of this rule. The pointer-only relay rule in
[`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md)
applies to the envelope as a whole, so the fenced manifest never
travels through a paste pipeline.

### c.6 Explicitly prohibited surfaces and forbidden operations (REQUIRED)

Restate, by name, the surfaces and operations the envelope forbids,
even where overlap with the path complement in §c.5 is obvious.
Restating makes the scope audit mechanical. At minimum:

| Forbidden surface / operation | Restatement |
|---|---|
| `.github/` | No mutation to `.github/` contents or workflow files. |
| `CODEOWNERS` | No creation or mutation of any CODEOWNERS file. |
| live source-host settings | No mutation of live repository settings, branch protection, environments, labels, PR/issue/assignment metadata, or external tracker state on any host. |
| `deploy_automation` | No execution or mutation of deploy automation. |
| `specs/` / `schemas/` / `validators/` / `templates/` / `examples/` / `tenants/` | No mutation; substrate-owned. |
| canonical docs subtrees | No mutation to `docs/contracts/`, `docs/product/`, `docs/architecture/`, `docs/governance/`, `docs/quality/`, `docs/devops/`, `docs/security/` unless an envelope is explicitly ratified for one of these subtrees. |
| `unrelated branches` | No mutation, force-push, deletion, or check-out interaction with branches outside the envelope. |
| `secrets_or_tokens` | No introduction, leakage, or reliance on secrets, tokens, credentials, or accounts. |
| `instance_local_paths` | No introduction of machine-local absolute paths, local terminal identifiers, local session identifiers, or forensic session-backup paths into governed artifacts. |
| forbidden git/gh operations | No `git add`, `git commit`, `git push`, `gh pr` / merge, branch deletion, worktree removal, repository-setting mutation, or hook bypass under this envelope unless Source separately ratifies the mechanics. |

The envelope MAY tighten or extend this list, but it MUST NOT
silently loosen any of the items above.

### c.7 Dependencies and prerequisites (REQUIRED)

| Field | Semantics |
|---|---|
| `predecessor_items` | Backlog ids whose status is required to be `Ratified` or `Done` before this envelope is consumed, per `./DEPENDENCIES.md`. |
| `predecessor_status_observed` | Observed delivery-view status of each predecessor at envelope-author time. |
| `readiness_evidence` | Citation to the [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b criteria the backlog row satisfied at promotion. |
| `external_tracker_references` | Optional, **non-canonical** pointers (e.g., `ENG-1234`). MUST NOT substitute for any repo-visible field per [`./README.md`](./README.md) §d. |

### c.8 Implementation instructions (REQUIRED)

A bounded, ordered set of instructions the consumer will execute.
Each instruction MUST be reconstructable from repository artifacts.
Instructions:

1. Cite the file(s) to create or update by repo-relative path.
2. Cite the content smoke criteria the file is expected to satisfy.
3. Name any cross-reference updates required for coherence.
4. Name any wording rules (e.g., "use careful 'this batch authors'
   wording; do not declare canonical Done until after merge").
5. Name the order of operations when order is load-bearing.

Instructions MUST NOT describe staging, commit, push, PR, merge,
branch deletion, or repository-setting mechanics unless the envelope
has separately ratified those mechanics in §c.2.

### c.9 Validation commands and expected results (REQUIRED)

| Field | Semantics |
|---|---|
| `validation_commands` | Exact, copy-pasteable command lines the consumer will run locally. Only commands that do not stage, commit, push, merge, delete branches, or mutate repository settings are permitted. |
| `expected_results` | Per-command expected exit status, expected stdout signal (e.g., "only allowed docs/delivery files appear"), and what counts as a passing run. |
| `skipped_checks` | Any check intentionally skipped, with rationale. Skipping a relevant check without rationale fails the Definition of Done per [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.2. |

Typical commands include `git status --short --branch --untracked-files=all`,
`git branch --show-current`, `git log -1 --oneline`,
`git diff --name-only`, `git diff --check`, the Creator Engine
validator's `check-examples` and `scan-no-limitless` subcommands when
applicable, and any stale-language scans that bear on this batch.

### c.10 Scope-audit commands (REQUIRED)

| Field | Semantics |
|---|---|
| `scope_audit_commands` | Exact command lines an independent verifier will run to confirm scope boundary (typically `git diff --name-only \| sort`, prohibited-surface greps, validator runs). |
| `expected_audit_results` | Allowed paths only; no prohibited-surface paths; clean whitespace per `git diff --check`; no stale-language matches per the named scan. |

Scope-audit commands MAY overlap with §c.9 validation commands; the
distinction is that §c.10 is run by the independent verifier rather
than by the consumer.

### c.11 Review / verification evidence fields (REQUIRED)

| Field | Semantics |
|---|---|
| `consumer_self_report` | The consumer's structured report-back: changed files, commands run, exit statuses, skipped checks and rationale, stop line. Counts as **verification evidence**, not Source ratification. |
| `independent_verifier_record` | Reference to Nefarious / Hermes scope-audit evidence per [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md). Counts as **verification evidence**, not Source ratification. |
| `independent_review_evidence_ref` *(conditional)* | Path or quoted excerpt of a governed review-evidence record authored under [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md). Required when the batch is reviewable and no Source-ratified waiver applies; otherwise the named waiver in §c.2 stands in. |
| `review_gate_state` | Resulting state per [`./REVIEW_GATE.md`](./REVIEW_GATE.md): cleared, waived, blocked on findings, blocked on missing identity, or `cannot_review`. |

### c.12 Dry-run or handoff evidence fields *(conditional)*

When the envelope is itself a dry-run or rehearsal (e.g., the Slice E
authoring batch, which rehearses the envelope contract without
executing a downstream assignment), the following fields apply:

| Field | Semantics |
|---|---|
| `dry_run_marker` | Explicit boolean / sentence stating this envelope is non-authorizing for downstream work (e.g., "Dry run; does NOT execute a downstream assignment; does NOT create a downstream branch / worktree / PR / commit / stage; does NOT assign a real implementation task"). |
| `dry_run_evidence_ref` | Repo-relative path to the dry-run evidence document (e.g., [`./ASSIGNMENT_ENVELOPE_DRY_RUN.md`](./ASSIGNMENT_ENVELOPE_DRY_RUN.md)). |
| `handoff_artifact_ref` | Optional reference to a Hermes/Nefarious handoff artifact that preceded this envelope. Handoff artifacts MUST NOT be co-mingled with governed evidence in a way that obscures the author/approver separation contract. |

### c.13 Stop condition (REQUIRED)

The envelope MUST name an **explicit stop condition** that the
consumer reaches before any of the following mechanics occur:

- staging (`git add`)
- commit (`git commit`)
- push (`git push`)
- pull request creation, modification, or comment
- merge or fast-forward
- branch deletion or worktree removal
- repository-setting mutation on any host
- hook bypass (`--no-verify`, signing bypass, etc.)

The stop condition states the exact wording the consumer ends with.
The expected pattern is: "End of <batch name>. Awaiting <controller>
independent verification and Source validation before staging,
commit, push, PR, merge, or branch deletion."

The consumer MUST NOT cross the stop line unless Source separately
ratifies the mechanics in its own follow-up envelope clause.

## d. Filled-envelope worked example

For a worked example of this template filled in against the Slice E
worktree/branch this batch lives in, see
[`./ASSIGNMENT_ENVELOPE_DRY_RUN.md`](./ASSIGNMENT_ENVELOPE_DRY_RUN.md).
That document is non-authorizing: it rehearses the contract and
makes the resulting evidence auditable, but it does not assign a
real downstream implementation task and does not authorize any
mechanics named in §c.13.

## e. Operating-procedure rules

1. An envelope's `ratifier` and `independent_review_evidence_ref` are
   independent fields. A `no_blocking_findings` review verdict is
   never ratification; only the named `ratifier` (Source for
   privileged classes) ratifies the underlying change.
2. Once an envelope is consumed, the envelope's allowed-paths /
   prohibited-surfaces / stop-condition fields are **frozen**.
   Amendments require a Source-ratified envelope amendment recorded
   under §c.2; ad hoc widening by the consumer is an authority
   conflict per Feature 002 FR-018.
3. An envelope that omits any REQUIRED section is **not consumable**.
   The next governed action for an incomplete envelope is either an
   author-side fix under the current envelope's authority or a
   ratification request to Source for a corrected envelope.
4. External tracker IDs MAY appear in §c.7 as non-canonical pointers,
   but they MUST NOT be cited as ratification, as readiness evidence,
   or as Done evidence per [`./README.md`](./README.md) §d.
5. Instance-local facts (absolute filesystem paths beyond the
   envelope-local `local_worktree_path`, terminal pane identifiers,
   secrets, credentials, tokens, in-flight PR numbers for work that
   has not merged) MUST NOT propagate from an envelope into governed
   artifacts; merged PR numbers in canonical-branch commit subjects
   MAY be cited as historical evidence.

## f. Acceptance posture for Slice E

This document satisfies the Slice E envelope's
`ASSIGNMENT_ENVELOPE_TEMPLATE.md` requirements:

- Names the envelope id, date, repo, base branch / commit, local
  branch, and local worktree path (§c.1).
- Names the Source-ratified decision / authority record field (§c.2),
  including a dedicated `ratifier` field that is intentionally distinct
  from any review evidence.
- Names anticipated mutation classes and the dominant class (§c.3).
- Names the authorized actor / role / pane identity and the
  controller / consumer split (§c.4).
- Names the exact allowed files and allowed operations (§c.5) and the
  explicitly prohibited surfaces and forbidden operations (§c.6).
- Names dependencies and prerequisites (§c.7), implementation
  instructions (§c.8), validation commands and expected results
  (§c.9), and scope-audit commands (§c.10).
- Names review / verification evidence fields (§c.11), keeping review
  evidence distinct from Source ratification.
- Names dry-run / handoff evidence fields (§c.12) for non-authorizing
  envelopes.
- Names the explicit stop condition (§c.13) before any staging /
  commit / push / PR / merge / branch deletion / repository-setting
  mutation unless Source separately ratifies the mechanics.
