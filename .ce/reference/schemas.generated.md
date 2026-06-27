<!-- ce-autogen: generator=scripts/gen_schema_reference.py source=schemas/*.yaml -->

# Schema reference

GENERATED FILE -- do not edit by hand. This is a deterministic projection of `schemas/*.yaml`. To refresh it, run `python scripts/gen_schema_reference.py --write` and commit the result; a stale committed copy fails the validator gate (`VAL-AUTOGEN-STALE-SCHEMA`).

Schema files: 67

## Index

| Schema | Title | Root type |
| --- | --- | --- |
| `schemas/active-work-ledger.schema.yaml` | Creator Engine Active-Work Ledger Record | `object` |
| `schemas/architect-evidence.schema.yaml` | Creator Engine Architect Evidence Record | `object` |
| `schemas/authority-matrix.schema.yaml` | Creator Engine Authority Matrix | `array` |
| `schemas/automerge-decision.schema.yaml` | Creator Engine Auto-Merge Decision Record | `object` |
| `schemas/automerge-policy.schema.yaml` | Creator Engine Auto-Merge Policy State | `object` |
| `schemas/brain-assertion.schema.yaml` | Creator Engine Brain Assertion Ledger | `object` |
| `schemas/brain-recall-record.schema.yaml` | Creator Engine Brain Recall Index Entry | `object` |
| `schemas/brownfield-baseline-attestation.schema.yaml` | Creator Engine Brownfield Baseline Attestation | `object` |
| `schemas/ce-event-block.schema.yaml` | Creator Engine CE-event signed block substrate | `object` |
| `schemas/completion-report.schema.yaml` | Creator Engine Completion Report | `object` |
| `schemas/computer-use-authority-envelope.schema.yaml` | Creator Engine computer-use UI side-effect authority envelope | `object` |
| `schemas/connector.schema.yaml` | Creator Engine connector descriptor substrate | `object` |
| `schemas/container-instance.schema.yaml` | Creator Engine Container-Instance Record | `object` |
| `schemas/controller-key.schema.yaml` | Controller Key Record | `object` |
| `schemas/controller-runtime-contract.schema.yaml` | Creator Engine Controller Runtime Contract | `object` |
| `schemas/coordination-policy.schema.yaml` | Creator Engine repo coordination policy (.ce/coordination.yml) | `object` |
| `schemas/crosswalk-register.schema.yaml` | Creator Engine v1 -> v2 Crosswalk Register | `object` |
| `schemas/decision-record.schema.yaml` | Creator Engine Decision Record front-matter | `object` |
| `schemas/devops-privileged-action-broker.schema.yaml` | Creator Engine DevOps privileged-action broker envelope | `object` |
| `schemas/dispatch-record.schema.yaml` | Creator Engine Dispatch Record | `object` |
| `schemas/distributed-claim.schema.yaml` | Creator Engine distributed claim record substrate | `object` |
| `schemas/escalation-record.schema.yaml` | Creator Engine Escalation Record | `object` |
| `schemas/evidence-fan-in-packet.schema.yaml` | Creator Engine Local Read-Only Evidence Fan-In Packet | `object` |
| `schemas/extension-hook-contract.schema.yaml` | Creator Engine extension + hook contract substrate | `object` |
| `schemas/federated-identity-binding.schema.yaml` | Creator Engine federated identity binding record substrate | `object` |
| `schemas/forge-claim.schema.yaml` | Creator Engine forge-projected claim record | `object` |
| `schemas/handoff.schema.yaml` | Creator Engine Hermes Handoff Front Matter | `object` |
| `schemas/harness-seat-contract.schema.yaml` | Creator Engine harness seat-contract substrate | `object` |
| `schemas/identity-record.schema.yaml` | Creator Engine Tenant Identity Record | `object` |
| `schemas/identity-registry.schema.yaml` | Creator Engine GitHub identity and infrastructure registry | `object` |
| `schemas/implementer-evidence.schema.yaml` | Creator Engine Implementer Evidence Record | `object` |
| `schemas/install-answers.schema.yaml` | Creator Engine Install Answers File | `object` |
| `schemas/integration-queue-dry-run.schema.yaml` | Creator Engine Integration Queue Dry-Run Landing Preview | `object` |
| `schemas/mission-brief.schema.yaml` | Creator Engine Mission-Brief record substrate | `object` |
| `schemas/mutation-class.schema.yaml` | Creator Engine Mutation Class Declaration List | `array` |
| `schemas/operating-mode-policy.schema.yaml` | Creator Engine v2 Operating Mode Policy | `object` |
| `schemas/pane-registry.schema.yaml` | Creator Engine Pane Registry Record | `object` |
| `schemas/pcl-record.schema.yaml` | Creator Engine PCL (Project Coordination Ledger) record substrate | `object` |
| `schemas/plan-wrapper-sidecar.schema.yaml` | Creator Engine Plan Wrapper Sidecar | `object` |
| `schemas/playbook.schema.yaml` | Creator Engine playbook workflow | `object` |
| `schemas/recommended-prompt.schema.yaml` | Creator Engine Hermes Recommended-Prompt Front Matter | `object` |
| `schemas/review-evidence.schema.yaml` | Creator Engine Review Evidence Record | `object` |
| `schemas/reviewer-authority-envelope.schema.yaml` | Creator Engine reviewer-venue side-effect-authority envelope | `object` |
| `schemas/reviewer-registry.schema.yaml` | Creator Engine reviewer registry | `object` |
| `schemas/reviewer-triage-decision.schema.yaml` | Creator Engine reviewer triage decision | `object` |
| `schemas/runtime-evidence.schema.yaml` | Creator Engine Runtime Evidence Chain | `object` |
| `schemas/runtime-policy.schema.yaml` | Creator Engine Runtime Policy Record | `object` |
| `schemas/scope.schema.yaml` | Creator Engine Scope Record | `object` |
| `schemas/seat-class-policy.schema.yaml` | Creator Engine Seat-Class Policy Record | `object` |
| `schemas/seat-event.schema.yaml` | Creator Engine Seat Lifecycle Event | `object` |
| `schemas/seat-lifecycle.schema.yaml` | Creator Engine Seat Lifecycle Record | `object` |
| `schemas/secret-grant.schema.yaml` | SecretGrant | `object` |
| `schemas/secret-ref.schema.yaml` | SecretRef | `object` |
| `schemas/secret-zero-grant.schema.yaml` | SecretZeroGrant | `object` |
| `schemas/side-effect-ledger.schema.yaml` | Creator Engine Side-Effect Ledger Record | `object` |
| `schemas/spec-ce-sidecar.schema.yaml` | Creator Engine v2 Spec CE Sidecar | `object` |
| `schemas/spec-wrapper-sidecar.schema.yaml` | Creator Engine Spec Wrapper Sidecar | `object` |
| `schemas/state-boundary-contract.schema.yaml` | Creator Engine State Boundary Contract | `object` |
| `schemas/state-version-record.schema.yaml` | Creator Engine State Version / Migration Record | `object` |
| `schemas/storage-tier-finding.schema.yaml` | Creator Engine storage-tier advisory finding | `object` |
| `schemas/tasks-wrapper-sidecar.schema.yaml` | Creator Engine Tasks Wrapper Sidecar | `object` |
| `schemas/tasks.schema.yaml` | Creator Engine Ratified Tasks Handoff | `object` |
| `schemas/work-sizing-floor.schema.yaml` | Creator Engine Work-Sizing Floor Record | `object` |
| `schemas/work-sizing.schema.yaml` | Creator Engine Work-Sizing Record | `object` |
| `schemas/worker-container-policy.schema.yaml` | Creator Engine Worker-Container Policy Record | `object` |
| `schemas/worker-tier-contract.schema.yaml` | Creator Engine governed worker tier contract | `object` |
| `schemas/worktree-lease.schema.yaml` | Creator Engine Worktree Lease Record | `object` |

## Schemas

### `schemas/active-work-ledger.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Active-Work Ledger Record |
| `$id` | `https://creator-engine.local/schemas/active-work-ledger.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Active-Work Ledger record authored under the Creator Engine Parallel Controller Orchestration (PCO) substrate.

Required fields:

`kind`, `record_type`, `schema_version`, `controller_id`, `lane_id`, `record_timestamp`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `active-work-ledger-record` | Discriminator constant. Records that do not carry this exact value are not governed Active-Work Ledger records under this contract and MUST NOT be validated by the `active_work_ledger_schema` check. |
| `record_type` | string | yes | enum `claim`, `heartbeat`, `event` | Sub-discriminator selecting which structural record shape applies. Drives the `oneOf` per-shape required-field sets. |
| `schema_version` | string | yes | enum `1`, `2`, `3`, `4` | Active-Work Ledger schema version. Slice 0 ships v1; Slice 0.5 adds four event_kind values (`gate_opened`, `gate_closed`, `completion_report_emitted`, `gate_blocked`) as an additive extension and accepts records carry... |
| `controller_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable identifier for the driving Controller (e.g., `hermes-primary`, `nefarious-laptop-a`). Stable per physical operator+host pair. MUST NOT embed secrets, tokens, installation ids, durable actor ids, model identifie... |
| `lane_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Coordination unit identifier. Typically `<feature-or-slice>-<short-suffix>`. |
| `record_timestamp` | oneOf | yes |  | Either an ISO-8601 UTC timestamp (e.g., `2026-05-20T03:30:30Z`) or a source-controlled reference (`commit:<sha>` or `source-controlled:<repo-relative-path>`). A machine-local clock value MUST NOT be presented as autho... |
| `operating_mode` | string | no | enum `strict`, `auto`, `transcendence` | Optional declared operating mode for the lane/record. Absent resolves to `strict`; migration never infers elevation. Elevation to `auto`/`transcendence` requires an Operator-ratified policy and a `ratification_evidenc... |
| `autonomy_class` | string | no | enum `manual`, `supervised`, `delegated_non_privileged`, `operator_ratified_privileged`, `reserved_future_agent_ratification` | Optional declared autonomy class. `reserved_future_agent_ratification` is a schema-visible placeholder only and MUST NOT be an active autonomy (enforced by the carrier validator). |
| `lane_kind` | string | no | enum `read-only`, `implementation`, `review`, `approval`, `merge`, `audit` | Optional lane kind, distinct from `pane_label`. Lets a downstream reviewer/approver/merger lane be a different lane kind from the implementer lane. G2.002.1 only carries the field; PR-review, approval, and merge enfor... |
| `ratification_evidence_ref` | oneOf | no |  | Optional inherited ratification-evidence pointer for elevated modes or privileged lane kinds. Either a repo-relative path/reference string or a structured pointer mapping. The pointer is advisory carriage; it confers... |
| `worktree_path` | string | no | minLength `1` | Repo-relative or absolute path of the physical worktree the claim names. Treated as advisory (not a secret), but required on every `claim` record so that the one-driver-per-worktree rule can be checked. Required on `c... |
| `branch` | string | no | minLength `1` | Optional branch name on which the claim is currently operating. Recommended but not required; pre-worktree planning lanes MAY omit this. |
| `envelope_ref` | anyOf | no |  | Repo-relative path to the Assignment Envelope under whose authority the lane is operating, or the literal `none` for coordination lanes that operate without an envelope (e.g., architect-only planning). Required on `cl... |
| `handoff_ref` | string | no | minLength `1` | Optional repo-relative path to the active handoff document under whose stop line the lane is operating. |
| `recommended_prompt_ref` | string | no | minLength `1` | Optional repo-relative path to the active recommended-prompt document the lane is executing. |
| `lease_seconds` | integer | no | minimum `60`<br>maximum `86400` | Lease duration in seconds. Default value documented in the protocol (3600); the schema validates the range only. A heartbeat older than `lease_seconds` past `last_heartbeat_at` makes the claim stale (advisory in Slice... |
| `claimed_at` | oneOf | no |  | ISO-8601 UTC timestamp (or source-controlled reference) at which the claim was created. Same shape as `record_timestamp`. Required on `claim` records. |
| `last_heartbeat_at` | oneOf | no |  | ISO-8601 UTC timestamp (or source-controlled reference) of the most recent heartbeat the Controller emitted for this claim. For fresh claims, equals `claimed_at`. Same shape as `record_timestamp`. Required on `claim`... |
| `pane_label` | string | no | enum `architect`, `implementer`, `controller`, `reviewer`<br>minLength `1` | Optional human-readable label of the visible pane this claim describes. Generic role label only; NOT a model, tool, CLI, account, or runner binding. |
| `released_at` | oneOf | no |  | Optional ISO-8601 UTC timestamp (or source-controlled reference) at which the claim was closed. When present, the claim is considered released and `release_reason` MUST also be present. |
| `release_reason` | string | no | enum `completed`, `aborted`, `lapsed`, `handed_off` | Required iff `released_at` is present. Records why the claim ended. |
| `claim_ref` | string | no | minLength `1` | Repo-relative path to the claim file this heartbeat updates. Required on `heartbeat` records. |
| `heartbeat_sequence` | integer | no | minimum `0` | Per-claim monotonically non-decreasing sequence counter. The schema validates type and lower-bound only. Slice 1/2's `active_work_ledger_conflicts` check enforces cross-record monotonicity for heartbeat records that r... |
| `emitted_at` | oneOf | no |  | ISO-8601 UTC timestamp (or source-controlled reference) at which the heartbeat was emitted. Same shape as `record_timestamp`. Required on `heartbeat` records. |
| `note` | string | no | maxLength `1024` | Optional free-text status note. Advisory only; MUST NOT contain secrets, tokens, credentials, or actor ids. Slice 0 does not enforce this prohibition mechanically. |
| `event_kind` | string | no | enum `claim_created`, `claim_released`, `claim_lapsed`, `heartbeat_emitted`, `lane_handoff_announced`, `lane_handoff_received`, `gate_opened`, `gate_closed`, `completion_report_emitted`, `gate_blocked`, `container_started`, `container_stopped`, `container_force_reaped` | Event log discriminator. Required on `event` records. The Slice 0 set (`claim_created`, `claim_released`, `claim_lapsed`, `heartbeat_emitted`, `lane_handoff_announced`, `lane_handoff_received`) is preserved. Slice 0.5... |
| `event_id` | string | no | pattern `^[a-z0-9][a-z0-9-]{2,63}$` | Event identifier. Stable within `(controller_id, lane_id, YYYY-MM-DD)` scope. The schema validates shape only; Slice 1/2's `active_work_ledger_conflicts` check enforces scoped uniqueness when `event_timestamp` can be... |
| `event_timestamp` | oneOf | no |  | ISO-8601 UTC timestamp (or source-controlled reference) at which the event occurred. Same shape as `record_timestamp`. Required on `event` records. |
| `subject_claim_ref` | string | no | minLength `1` | Optional repo-relative path to a claim file the event describes (e.g., for `claim_created` / `claim_released` / `claim_lapsed` / `heartbeat_emitted`). |
| `subject_handoff_ref` | string | no | minLength `1` | Optional repo-relative path to a handoff document the event references (used for `lane_handoff_announced` / `lane_handoff_received`). |
| `details` | object | no | unevaluatedProperties `false` | Optional structured event details. Slice 0 keeps this surface narrow; Slice 0.5 adds `completion_report_ref`; Slice 2I-S adds optional container-event detail fields (`instance_id`, `claim_id`, `exit_code`, `reason`, `... |

### `schemas/architect-evidence.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Architect Evidence Record |
| `$id` | `https://creator-engine.local/schemas/architect-evidence.schema.yaml` |
| Root type | `object` |

Machine-readable schema for an architect evidence record authored under the Creator Engine delivery control plane.

Required fields:

`evidence_id`, `design_subject`, `authored_artifact_refs`, `architect_identity_ref`, `architect_role_category`, `authoring_mode`, `design_scope`, `mutation_classes_proposed`, `prohibited_surfaces_acknowledged`, `supporting_evidence_refs`, `recommendations`, `decision_options`, `open_questions`, `verdict`, `recommended_follow_up`, `evidence_timestamp`, `non_ratification_statement`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `evidence_id` | string | yes | pattern `^[a-z][a-z0-9-]*$`<br>minLength `1` | Stable repo-relative identifier for this evidence record, unique within a tenant overlay. |
| `design_subject` | string | yes | minLength `1` | Human-readable statement of the design subject the architect addressed (e.g., the contract, schema, validator surface, decision request, or governance question under design). |
| `authored_artifact_refs` | array | yes | minItems `1`<br>uniqueItems `true` | Repo-relative paths to artifacts the architect authored or proposes to author under this envelope (spec, plan, tasks, decision request, schema draft, prose contract draft, template draft, etc.). External tracker URLs... |
| `architect_identity_ref` | string | yes | minLength `1` | Repo-relative path to the ratified architect identity record under which this evidence is authored. |
| `architect_role_category` | string | yes | const `architect` | Fixed to `architect`. Records with any other `role_category` are not governed architect evidence under this contract. |
| `authoring_mode` | string | yes | enum `manual_human`, `manual_agent`, `mixed_human_and_agent` | Generic authoring-mode label. Concrete tool/model/CLI selection is a deployment-time overlay decision and MUST NOT be hard-coded as an upstream binding here. |
| `design_scope` | string | yes | minLength `1` | Human-readable scope statement naming in-scope and out-of-scope items for this architect evidence. |
| `mutation_classes_proposed` | array | yes | minItems `1`<br>uniqueItems `true` | Mutation classes that the proposed/authored change would touch, per `docs/contracts/mutation-class-taxonomy.md`. Naming a privileged class here does NOT authorize the mutation; the privileged-class envelope still requ... |
| `prohibited_surfaces_acknowledged` | array | yes | minItems `1`<br>uniqueItems `true` | Prohibited-surface labels the architect affirmatively acknowledged are out of authoring scope under this envelope (e.g., `live_repository_settings`, `branch_protection`, `deploy_automation`, `codeowners`, `secrets_or_... |
| `supporting_evidence_refs` | array | yes |  | Repo-relative paths or command-result references the architect consulted (specs, prior contracts, validator output, attestation paths). External tracker URLs are non-canonical and MAY appear only as advisory reference... |
| `recommendations` | string | yes | minLength `1` | Free-text body of architect recommendations and decision context. The body MUST be sufficient for Source to perform ratification independently of the architect's authoring session. |
| `decision_options` | array | yes |  | Structured enumeration of options the architect surfaced for Source ratification. MAY be empty when the recommendation is unitary and no option enumeration is required. At most one option SHOULD carry `recommended_def... |
| `open_questions` | array | yes |  | Open questions the architect surfaced for Source. MAY be empty when the architect has no open questions. |
| `verdict` | string | yes | enum `recommendation_complete`, `recommendation_partial`, `scope_boundary_unclear`, `cannot_author` | Architect-evidence-only outcome. The schema MUST NOT accept any verdict value that implies the architect can ratify, approve merge, waive a privileged gate, modify branch protection, run or modify deploy automation, a... |
| `recommended_follow_up` | string | yes |  | Free-text recommendations for follow-up work (separate envelopes, future slices, deferred items, downstream implementer-class consumption). MAY be empty when there is no follow-up recommendation. |
| `evidence_timestamp` | oneOf | yes |  | Either an ISO-8601 timestamp (e.g., `2026-05-17T12:00:00Z`) or a source-controlled timestamp reference (e.g., `commit:<sha>` or a repo-relative path naming a commit-bound evidence file). A machine-local clock value MU... |
| `non_ratification_statement` | string | yes | minLength `1` | Explicit textual statement that this architect evidence is NOT Source ratification and does not authorize merge, deploy, branch deletion, branch protection mutation, or live repository-settings change. Its absence is... |

### `schemas/authority-matrix.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Authority Matrix |
| `$id` | `https://creator-engine.local/schemas/authority-matrix.schema.yaml` |
| Root type | `array` |

An authority-matrix list with one row per generic role category.

Required fields:

_None declared._

Properties:

_No properties declared._

Array item required fields:

`role_category`, `allowed_instruction_sources`, `allowed_mutation_classes`, `required_ratifier_role`, `allowed_communication_surfaces`, `required_audit_artifacts`

Array item properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `role_category` | string | yes | enum `source`, `ratifier`, `reviewer`, `architect`, `implementer`, `verifier`, `observer` |  |
| `tenant_role_name` | string | no | minLength `1` |  |
| `allowed_instruction_sources` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `allowed_mutation_classes` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `required_ratifier_role` | string | yes | enum `source`, `ratifier`, `reviewer`, `architect`, `implementer`, `verifier`, `observer` |  |
| `allowed_communication_surfaces` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `required_audit_artifacts` | array | yes | minItems `1`<br>uniqueItems `true` |  |

### `schemas/automerge-decision.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Auto-Merge Decision Record |
| `$id` | `https://creator-engine.local/schemas/automerge-decision.schema.yaml` |
| Root type | `object` |

Value-only auto-merge decision record emitted by automerge-decide (dry-run or live classification). Never secret-bearing. Safe to write to disk or emit as JSON for audit.

Required fields:

`decision`, `mutation_class`, `size_band`, `minimum_work_class`, `ratification_gates`, `run_mode`, `kill_switch`, `class_flag`, `checks_green`, `review_decision_blocked`, `rationale`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `decision` | string | yes | enum `AUTO`, `GESTURE_REQUIRED` | The policy decision for this PR. AUTO means all guards passed and the policy engine would auto-merge (if armed). GESTURE_REQUIRED means a human Operator gesture is needed. |
| `mutation_class` | string | yes |  | The highest-risk mutation class across all changed paths, as returned by mutation_class_for_paths(). Fail-closed classifier. |
| `size_band` | string | yes | enum `target_advisory`, `warn`, `explain_or_split`, `split_required`, `unknown` | The size band returned by classify_change_size(). "unknown" when change_stats were not provided. |
| `minimum_work_class` | string | yes |  | The minimum work class required by the size band. |
| `ratification_gates` | array | yes |  | The ratification gates from size_ceremony(work_class, mutation_class). Drives the AUTO vs GESTURE_REQUIRED decision. |
| `run_mode` | string | yes |  | The run_mode from the policy state at decision time. |
| `kill_switch` | boolean | yes |  | The kill_switch value from the policy state at decision time. |
| `class_flag` | boolean | yes |  | The per-class auto_merge flag from the policy state for this mutation_class at decision time. |
| `checks_green` | boolean | yes |  | True if all required checks were green at classification time. |
| `review_decision_blocked` | boolean | yes |  | True if reviewDecision was CHANGES_REQUESTED. |
| `rationale` | array | yes |  | Human-readable list of guard evaluation steps explaining why the decision was AUTO or GESTURE_REQUIRED. |
| `pr_number` | [integer, "null"] | no |  | Optional PR number for audit correlation. |
| `head_sha` | [string, "null"] | no |  | Optional PR head SHA for audit correlation. |

### `schemas/automerge-policy.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Auto-Merge Policy State |
| `$id` | `https://creator-engine.local/schemas/automerge-policy.schema.yaml` |
| Root type | `object` |

Durable, secret-free auto-merge policy state for the CEO-mode policy engine (ce-ops#291 PR-A). Ships with run_mode=dev and all class flags false so nothing auto-merges until an Operator flips the enabling decision (PR...

Required fields:

`run_mode`, `kill_switch`, `classes`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `run_mode` | string | yes | enum `dev`, `ceo`, `strangeLoop` | Master run-mode switch. dev=nothing auto-merges; ceo=docs/none may auto-merge when class flags are on; strangeLoop=future widening (design only). Ships as "dev". |
| `kill_switch` | boolean | yes |  | Emergency halt: true stops all auto-merge instantly regardless of class flags or run_mode. Ships as false. |
| `classes` | object | yes |  | Per-mutation-class flags. Each key is a mutation class name; value is the per-class policy object. All ship as auto_merge: false. |
| `enabling_decision_ref` | [string, "null"] | no |  | Opaque reference to the Operator ratification record that authorises auto-merge for this policy state (e.g. a decision-record path, PR URL, or DAYSHIFT manifest ref). Must be non-null for any auto_merge=true flag to t... |

### `schemas/brain-assertion.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Brain Assertion Ledger |
| `$id` | `https://creator-engine.local/schemas/brain-assertion.schema.yaml` |
| Root type | `object` |

Schema for the first Knowledge-SSOT assertion ledger slice. Assertions are structured records in a deterministic, append-only, content-addressed hash chain. Runtime state lives under the local CE state root (.ce/state...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `brain_assertion` | $ref #/$defs/assertion | no |  |  |
| `kind` | string | no | const `brain-assertion-ledger` |  |
| `record_type` | string | no | const `brain_assertion_ledger` |  |
| `schema_version` | string | no | enum `1` |  |
| `records` | array | no | minItems `1` |  |
| `note` | string | no | maxLength `1024` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `hash` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `assertion_id` | string | no | pattern `^brain-assertion-[a-z0-9][a-z0-9-]{3,96}$` |  |
| `scope` | anyOf | no |  |  |
| `assertion` | object; allOf | no | additionalProperties `false` |  |

### `schemas/brain-recall-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Brain Recall Index Entry |
| `$id` | `https://creator-engine.local/schemas/brain-recall-record.schema.yaml` |
| Root type | `object` |

Schema for one derived brain-recall index entry. The source-of-truth remains the repo-native Markdown file named by source_path; vector-store state is a rebuildable projection and MUST NOT become the canonical record.

Required fields:

`source_path`, `chunk_ref`, `content_hash`, `as_of`, `scope`, `requires_egress`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | no | const `brain-recall-index-entry` |  |
| `record_type` | string | no | const `brain_recall_index_entry` |  |
| `schema_version` | string | no | enum `1` |  |
| `source_path` | string | yes | pattern `^[A-Za-z0-9._/-]+\\.md$`<br>minLength `1`<br>maxLength `4096` | Repo-relative Markdown source-of-truth file. The recall index points back to this file; it does not replace it. |
| `chunk_ref` | string | yes | minLength `1`<br>maxLength `512` | Stable reference to the indexed Markdown chunk within source_path, such as a heading slug or line-range token. |
| `content_hash` | string | yes | pattern `^[0-9a-f]{64}$` | SHA256 hex digest of the canonical chunk content used to derive the vector-store projection. |
| `as_of` | string | yes | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` | UTC point-in-time stamp for the Markdown content snapshot this entry indexes. |
| `scope` | anyOf | yes |  | Privacy scope of the indexed chunk. Confidential chunks require explicit consent before any egress-requiring embedder may process the content. |
| `requires_egress` | boolean | yes |  | True when the embedder used for this derived entry requires network egress. The privacy gate fails closed for confidential scope unless explicit consent is supplied by the caller. |
| `note` | string | no | maxLength `1024` | Optional advisory note. MUST NOT contain secrets, tokens, credentials, or host/account identifiers. |

### `schemas/brownfield-baseline-attestation.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Brownfield Baseline Attestation |
| `$id` | `https://creator-engine.local/schemas/brownfield-baseline-attestation.schema.yaml` |
| Root type | `object` |

Value-free v0 baseline attestation for brownfield no-history capture. The record binds the baseline commit, the captured snapshot digest, the clean scrub summary, the attestor reference, and a content digest. It delib...

Required fields:

`kind`, `record_type`, `schema_version`, `baseline_commit_sha`, `snapshot`, `scrub`, `attestor_ref`, `attested_at`, `content_digest`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `brownfield-baseline-attestation` |  |
| `record_type` | string | yes | const `brownfield_baseline_attestation` |  |
| `schema_version` | string | yes | const `1` |  |
| `baseline_commit_sha` | string | yes | pattern `^[0-9a-f]{40}$` |  |
| `snapshot` | object | yes | additionalProperties `false` |  |
| `scrub` | object | yes | additionalProperties `false` |  |
| `attestor_ref` | string | yes | pattern `^[A-Za-z][A-Za-z0-9_-]{0,31}:[A-Za-z][A-Za-z0-9_-]{0,63}$`<br>minLength `1`<br>maxLength `128` | Value-free attestor label. Must be a local actor class and label pair such as `operator:peer-operator`; never a URL, hostname, filesystem path, repository path, or client-specific locator. |
| `attested_at` | string | yes | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` |  |
| `content_digest` | $ref #/$defs/sha256 | yes |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |

### `schemas/ce-event-block.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine CE-event signed block substrate |
| `$id` | `https://creator-engine.local/schemas/ce-event-block.schema.yaml` |
| Root type | `object` |

G2.003.0 schema for shape-only CE-event signed blocks. Cryptographic signing, key custody, live emission, and queue/connector runtime remain deferred.

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `ce_event_block` | $ref #/$defs/block | no |  |  |
| `ce_event_chain` | array | no | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `hash` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `block` | object | no | additionalProperties `false` |  |

### `schemas/completion-report.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Completion Report |
| `$id` | `https://creator-engine.local/schemas/completion-report.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Completion Report artifact authored under the Creator Engine Parallel Controller Orchestration (PCO) substrate.

Required fields:

`kind`, `schema_version`, `gate_class`, `envelope_ref`, `envelope_sha256`, `controller_id`, `lane_id`, `gate_opened_at`, `gate_closed_at`, `outcome`, `summary`, `recommended_immediate_next_step`, `exact_next_source_prompt`, `terminal_packet_sections_present`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `completion-report` | Discriminator constant. Files that do not carry this exact value are not governed Completion Reports under this contract and MUST NOT be validated by the `completion_report_schema` check. |
| `schema_version` | string | yes | const `1` | Completion Report schema version. Slice 0.5 ships v1; later slices MAY extend via additive optional fields and bump this const (mirroring the active-work-ledger schema discipline). |
| `gate_class` | string | yes | enum `A`, `C-merge`, `C-pr-only`, `D`, `E`, `F` | Trigger class from `docs/operations/COMPLETION_REPORT_PROTOCOL.md`: A — Source-ratified saved prompt execution (universal case; also covers the visible architect/engineer pane subclass); C-merge — Git/GitHub mutation... |
| `envelope_ref` | string | yes | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` | Repo-relative path to the Source-ratified envelope/prompt file whose execution this report returns from. Required on every class. Pointer-only relay per `docs/operations/NO_COPY_PASTE_PATTERN.md`. |
| `envelope_sha256` | string | yes | pattern `^[0-9a-f]{64}$` | SHA256 of the envelope file as Source ratified it, 64 lower-hex. Required on every class. The hash binds the report to the exact bytes Source ratified. |
| `controller_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable identifier for the driving Controller. Same shape as `active-work-ledger.schema.yaml` `controller_id`. |
| `lane_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | PCO lane identifier. Same shape as `active-work-ledger.schema.yaml` `lane_id`. Use `single` when PCO is not active on the gate. |
| `gate_opened_at` | oneOf | yes |  | Timestamp at which the gate opened. Same shape as `active-work-ledger.schema.yaml` `record_timestamp`. |
| `gate_closed_at` | oneOf | yes |  | Timestamp at which the gate ended (success, partial, blocked, or aborted). Same shape as `gate_opened_at`. |
| `outcome` | string | yes | enum `completed`, `partial`, `blocked`, `aborted` | Gate exit code. `completed` and `partial` are reserved for classes A, C-merge, C-pr-only, D, and E. `blocked` and `aborted` are reserved for class F. |
| `summary` | string | yes | minLength `1`<br>maxLength `4096` | Short prose summary. Maps to the `Summary` terminal packet section. |
| `recommended_immediate_next_step` | object | yes | unevaluatedProperties `false` | Maps to the `Recommended immediate next step` terminal packet section. `backlog_refresh_and_source_escalation` covers `NEXT_TASK_PROTOCOL.md` §c.3; `blocker_resolution` covers §c.4; `no_next_gate` is the only value pe... |
| `exact_next_source_prompt` | object; oneOf | yes | unevaluatedProperties `false` | Maps to the `Exact next Source prompt pointer+SHA256` terminal packet section. When `kind == present`, `prompt_path`, `prompt_sha256`, and `canonical_ratification_line` are required. When `kind == none`, `none_rationa... |
| `evidence_artifact_pointers` | array | no |  | Repo-relative pointers to evidence artifacts produced by the gate (e.g., research archive paths, transcript paths, validator output paths). At least one entry is required for class E (enforced by the conditional `oneO... |
| `terminal_packet_sections_present` | object | yes | unevaluatedProperties `false` | Self-declared presence of the three literal terminal-packet section headers in the Markdown body the controller emitted. The runtime hook (Slice 0.5R) cross-verifies these declarations against the actual terminal text... |
| `merge_report` | object | no | unevaluatedProperties `false` | Required iff `gate_class == "C-merge"`. Encodes the ten NEXT_TASK_PROTOCOL.md §b post-merge fields in machine-readable form. This schema does NOT redefine or duplicate the prose ten-field rule; it records the same fac... |
| `pr_action` | string | no | enum `opened`, `edited`, `reviewed`, `closed`, `reopened` | Required iff `gate_class == "C-pr-only"`. |
| `pr_identifiers` | object | no | unevaluatedProperties `false` | Required iff `gate_class == "C-pr-only"`. |
| `side_effect_ledger_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` | Repo-relative path to a Side-Effect Ledger record (Feature 005 Slice 4 / Slice 7 surface). Either this field OR `interim_side_effect_note_ref` + `interim_side_effect_note_sha256` is required iff `gate_class == "D"`. |
| `interim_side_effect_note_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` | Interim side-effect note path used before the Side-Effect Ledger lands. Required-with-sibling per the class-D conditional. |
| `interim_side_effect_note_sha256` | string | no | pattern `^[0-9a-f]{64}$` | SHA256 of the interim side-effect note, 64 lower-hex. |
| `mutation_descriptors` | array | no | minItems `1` | Required iff `gate_class == "D"`. Each entry describes one mutated surface (e.g., MCP config, provider account, tmux session). Identifiers MUST be redacted per the well-formed handoff examples precedent. |
| `research_archive_path` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` | Required iff `gate_class == "E"`. Repo-relative path to the research run archive (typically under `.hermes/research/`). |
| `evidence_index_path` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` | Required iff `gate_class == "E"`. Repo-relative path to the machine-readable evidence index inside the research archive. |
| `blocker_description` | string | no | minLength `1`<br>maxLength `2048` | Required iff `gate_class == "F"`. Names the specific blocker that closed the gate (e.g., "upstream PR not merged", "Source rescinded ratification mid-flight"). |
| `resumption_pointer` | object; oneOf | no | unevaluatedProperties `false` | Required iff `gate_class == "F"`. Names the resumption pointer (a follow-on prompt envelope) or explicitly states no resumption is planned, with rationale. |
| `partial_side_effects` | array | no |  | Optional on class F. Same shape as `mutation_descriptors`. Records any partial side effects that landed before the gate blocked or aborted. |

### `schemas/computer-use-authority-envelope.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine computer-use UI side-effect authority envelope |
| `$id` | `https://creator-engine.local/schemas/computer-use-authority-envelope.schema.yaml` |
| Root type | `object` |

Phase 1 schema for a bounded, auditable authority envelope that authorizes exactly one UI side-effect mechanic on exactly one closed target class. This generalizes the reviewer-authority-envelope pattern beyond mechan...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `computer_use_authority_envelope` | $ref #/$defs/computer_use_authority_envelope | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `login` | string | no | pattern `^[A-Za-z0-9][A-Za-z0-9-]{0,38}$` |  |
| `non_empty_string` | string | no | pattern `\\S`<br>minLength `1` |  |
| `mutation_class` | string | no | enum `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`, `none` | Reuses the scope.schema.yaml planning-layer taxonomy exactly, including none for no repository mutation. |
| `account_target` | object | no | additionalProperties `false` |  |
| `app_target` | object | no | additionalProperties `false` |  |
| `console_setting_target` | object | no | additionalProperties `false` |  |
| `closed_target` | oneOf | no |  |  |
| `computer_use_authority_envelope` | object | no | additionalProperties `false` |  |

### `schemas/connector.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine connector descriptor substrate |
| `$id` | `https://creator-engine.local/schemas/connector.schema.yaml` |
| Root type | `object` |

G2.005.0 shape-only schema for a connector descriptor. A connector descriptor declares the shape of a source-host or tracker connector: its kind, an opaque provider-class label (never a concrete vendor/account binding...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `connector` | $ref #/$defs/connector | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `connector` | object | no | additionalProperties `false` |  |

### `schemas/container-instance.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Container-Instance Record |
| `$id` | `https://creator-engine.local/schemas/container-instance.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Container-Instance record authored under the Creator Engine Parallel Controller Orchestration (PCO) Slice 2I-S substrate.

Required fields:

`kind`, `record_type`, `schema_version`, `instance_id`, `policy_ref`, `image_sha`, `claim_id`, `lease_id`, `started_at`, `stopped_at`, `exit_code`, `mount_manifest_applied`, `secret_grants`, `egress_allowlist_applied`, `enforcement_primitive`, `policy_sha`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `container-instance-record` | Discriminator constant. Records that do not carry this exact value are not governed Container-Instance records under this contract and MUST NOT be validated by the `container_instance` check. |
| `record_type` | string | yes | const `container_instance` | Sub-discriminator. Slice 2I-S defines exactly one record shape; later slices MAY add additional record types via additive extension under a new `schema_version`. |
| `schema_version` | string | yes | enum `1` | Container-Instance schema version. Slice 2I-S ships v1. |
| `instance_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable identifier for this container instance. Unique within `(controller_id, lane_id, YYYY-MM-DD)` scope per protocol. |
| `policy_ref` | object | yes | unevaluatedProperties `false` | Reference to the Worker-Container Policy under which this instance was allocated. Embeds the policy-declared image SHA so `PCO-044` can verify the actual `image_sha` at the instance-record level. |
| `image_sha` | string | yes | pattern `^sha256:[0-9a-f]{64}$` | The actual OCI image SHA used when this container was started. `PCO-044` checks this against `policy_ref.image_sha`; a mismatch indicates the allocator used a different image than the policy declared. |
| `claim_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | The Active-Work Ledger claim this container is bound to. A container instance is bound to exactly one claim; the claim lifecycle governs the container lifetime per `PCO-043`. |
| `lease_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | The Worktree Lease that was live at `allocate_worker` time. Used by audit predicates to verify the container was started under a valid lease. |
| `started_at` | oneOf | yes |  | ISO-8601 UTC timestamp at which the container was started. |
| `stopped_at` | oneOf | yes |  | ISO-8601 UTC timestamp at which the container was stopped, or `null` if the container is still running. Null while running; set on `terminate_worker` or `garbage_collect_worker`. `PCO-043` fires when `claim_released_a... |
| `exit_code` | oneOf | yes |  | Process exit code of the container's main process, or `null` while the container is running. |
| `mount_manifest_applied` | array | yes |  | The set of paths actually bound into the container at start time, distinguishing policy-declared from runtime-granted entries. Subset of (or equal to) the policy's `mount_manifest` plus any runtime-granted extensions. |
| `secret_grants` | array | yes |  | The set of secret names injected into this container via the credential broker, with broker-grant ids and TTLs. Values MUST NOT appear here or anywhere in this record. |
| `egress_allowlist_applied` | array | yes |  | The egress allowlist as actually installed on the worker's network namespace, naming the enforcement primitive SHA and per-rule shape. |
| `enforcement_primitive` | string | yes | enum `pasta`, `slirp4netns`, `iptables`, `none`, `unknown` | Egress enforcement primitive used for this instance. `none` for verification containers that declare no egress. `unknown` records cases where the runtime engine did not surface the primitive identifier. |
| `policy_sha` | string | yes | pattern `^[0-9a-f]{64}$` | Top-level policy SHA for fast audit lookups. MUST equal `policy_ref.policy_sha`. Redundant but required so every container-instance record carries `policy_sha` at its top level per the spec §e.10 invariant. |
| `claim_released_at` | oneOf | no |  | ISO-8601 UTC timestamp at which the Active-Work Ledger claim bound to this container was released (or `null` if the claim is still live). When present and `stopped_at` is `null`, `PCO-043` fires: the container has out... |
| `note` | string | no | maxLength `1024` | Optional free-text note. Advisory only; MUST NOT contain secrets, tokens, credentials, or actor ids. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `applied_mount_entry` | object | no | unevaluatedProperties `false` |  |
| `secret_grant_entry` | object | no | unevaluatedProperties `false` | One secret injected into the container. Values MUST NOT appear here; `unevaluatedProperties: false` enforces that no `secret_value` or equivalent field can be added. |
| `egress_rule` | object | no | unevaluatedProperties `false` |  |

### `schemas/controller-key.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Controller Key Record |
| `$id` | `https://creator.engine/schemas/controller-key.schema.yaml` |
| Root type | `object` |

PCO-025 controller-key record contract. Slice 2.5A is substrate-only: records bind a controller_id to public-key metadata, while private key generation, custody, rotation, and lease-signature verification remain separ...

Required fields:

`kind`, `record_type`, `schema_version`, `tenant_id`, `controller_id`, `key_algorithm`, `public_key`, `issued_at`, `issued_by`, `key_custody_mode`, `status`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | const | yes | const `controller-key-record` |  |
| `record_type` | const | yes | const `controller_key` |  |
| `schema_version` | enum | yes | enum `1` |  |
| `tenant_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `controller_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `key_algorithm` | enum | yes | enum `ed25519` |  |
| `public_key` | object | yes | unevaluatedProperties `false` |  |
| `issued_at` | string | yes | pattern `^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\|source-controlled:.+)$` |  |
| `issued_by` | string | yes | pattern `^source-controlled:[A-Za-z0-9._/-]+$` |  |
| `key_custody_mode` | enum | yes | enum `per_host` |  |
| `status` | enum | yes | enum `active`, `revoked` |  |
| `revoked_at` | string | no | pattern `^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\|source-controlled:.+)$` |  |

### `schemas/controller-runtime-contract.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Controller Runtime Contract |
| `$id` | `https://creator-engine.local/schemas/controller-runtime-contract.schema.yaml` |
| Root type | `object` |

RV1-020 Controller Runtime Contract record for the Creator Engine v1.0 governed runtime kernel (PCO v1 Gate 2).

Required fields:

`kind`, `schema_version`, `role`, `controller_seat`, `harness`, `authority_boundary`, `state_boundary`, `record_timestamp`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `controller-runtime-contract` |  |
| `schema_version` | string | yes | const `1` |  |
| `role` | string | yes | const `controller` |  |
| `description` | string | no | maxLength `2048` |  |
| `controller_seat` | object | yes | unevaluatedProperties `false` |  |
| `harness` | object | yes | unevaluatedProperties `false` |  |
| `authority_boundary` | object | yes | unevaluatedProperties `false` |  |
| `state_boundary` | object | yes | unevaluatedProperties `false` |  |
| `record_timestamp` | $ref #/$defs/timestamp | yes |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `controller_forbidden_surface` | string | no | enum `host-home`, `host-tmux-socket`, `host-ssh-agent`, `host-git-push`, `acp-host-transport`, `raw-host-tui`, `docker-socket`, `podman-socket`, `containerd-socket`, `openbao-root-token`, `ce-root-v1-private-key`, `github-app-private-key` |  |
| `authority_class` | string | no | enum `hermes`, `claude-code`, `codex`, `openclaw`, `hosted-service`, `saas`, `github-connector` |  |
| `timestamp` | oneOf | no |  |  |

### `schemas/coordination-policy.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine repo coordination policy (.ce/coordination.yml) |
| `$id` | `https://creator-engine.local/schemas/coordination-policy.schema.yaml` |
| Root type | `object` |

Machine-readable schema for the repo-level coordination policy `.ce/coordination.yml` — governance-as-data (v3.5-C A-C3, design §A.5). This schema pins the `ratification_authority` block (peer authority = per-area own...

Required fields:

`kind`, `schema_version`, `mutation_class`, `ratification_authority`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `coordination-policy` | Discriminator constant — records without it are not coordination policies and MUST NOT be validated by `peer_authority`. |
| `schema_version` | string | yes | enum `1` |  |
| `mutation_class` | string | yes | const `governance` | SELF-CLASSIFICATION, pinned by the schema: the policy file is always a `governance`-class artifact (privileged) — changing it requires the full privileged ratification bar (both peers). |
| `ratification_authority` | object | yes | unevaluatedProperties `false` | The peer-authority block (per-area ownership × risk-tiered quorum). |
| `identity_map` | object | no | unevaluatedProperties `false` | The {actor → human} resolver data (the §11.5 identity-resolution gap, shipped honestly): an actor not resolvable through this map FAILS CLOSED (VAL-PA-IDENTITY-UNRESOLVED) — it never silently counts toward a quorum. D... |
| `ratifications` | array | no |  | OPTIONAL ratification attestations validated against the policy (quorum per tier, area-owner coverage, no self-approval). The LIVE enforcement path is the generalized `forge.plan_approval.plan_approved`; this list is... |

### `schemas/crosswalk-register.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine v1 -> v2 Crosswalk Register |
| `$id` | `https://creator-engine.local/schemas/crosswalk-register.schema.yaml` |
| Root type | `object` |

G2.001.4 machine-readable shape for the authoritative v1 -> v2 crosswalk register (``specs/v2/_crosswalk.yml``) and any well-formed crosswalk-register fixture.

Required fields:

`schema`, `schema_version`, `authoritative`, `derived_material_note`, `context_disposition`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `schema` | string | yes | const `creator-engine/crosswalk-register` |  |
| `schema_version` | string | yes | minLength `1` |  |
| `schema_status` | string | no |  |  |
| `authoritative` | boolean | yes |  |  |
| `derived_material_note` | string | yes | minLength `1` |  |
| `roles` | array | no |  |  |
| `state_paths` | object | no |  |  |
| `feature_labels` | array | no |  |  |
| `sidecars` | array | no |  |  |
| `context_disposition` | object | yes |  |  |

### `schemas/decision-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Decision Record front-matter |
| `$id` | `https://creator-engine.local/schemas/decision-record.schema.yaml` |
| Root type | `object` |

Machine-readable schema for the YAML front-matter of a **Decision Record** — the durable decision knowledge artifact (v3.5-C A-C1, design §A.1/§A.2). A Decision Record is a *sibling of Skill*, NOT a Scope type: govern...

Required fields:

`kind`, `record_type`, `schema_version`, `id`, `title`, `status`, `date`, `decision_makers`, `review_by`, `mutation_class`, `evidence_refs`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `decision-record` | Discriminator constant. Markdown files whose front-matter does not carry this exact value are not governed Decision Records and MUST NOT be validated by `decision_record`. |
| `record_type` | string | yes | enum `adr`, `rfc` | The wrapped prior-art form: `adr` (MADR 4.0.0; reversible decisions) or `rfc` (Rust RFC + FCP; structural/contested decisions). `disposition` and `fcp` are RFC-only fields. |
| `schema_version` | string | yes | enum `1` |  |
| `id` | string | yes | pattern `^(ADR\|RFC)-[0-9]{4}(-[a-z0-9][a-z0-9-]*)?$` | Stable record id (`ADR-NNNN` / `RFC-NNNN`, optional slug suffix). Cited by `crosswalk` links and by a Scope's `binding_decisions`. |
| `title` | string | yes | minLength `1` |  |
| `status` | string | yes | enum `proposed`, `accepted`, `deprecated`, `superseded` | Lifecycle status. `accepted` is a HUMAN-ratification event (the `decision_record` check requires the `ratification` block for it; nothing auto-promotes a record to `accepted`). `superseded` requires a resolvable `cros... |
| `date` | string | yes | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` | ISO date the decision was recorded. |
| `decision_makers` | array | yes | minItems `1` | The owner stamp — who made/owns this decision (actor labels, value-free). For privileged `mutation_class`, the ratifier MUST NOT be one of these (no self-ratification; enforced by the check). |
| `consulted` | array | no |  | MADR consulted parties (two-way communication). |
| `informed` | array | no |  | MADR informed parties (one-way communication). |
| `review_by` | string | yes | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` | REQUIRED freshness horizon: the ISO date by which this decision must be re-reviewed (decisions rot; an unreviewable-forever record is rejected at the schema layer by requiring this field). |
| `mutation_class` | string | yes | enum `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`, `none` | The blast-radius axis (the shared planning-layer taxonomy plus `none`). Privileged classes (`PRIVILEGED_NAMES`) tier the ratification bar: the ratifier must be independent of `decision_makers`. |
| `evidence_refs` | array | yes | minItems `1` | REQUIRED non-empty grounding: a decision with zero cited evidence is not a governed Decision Record. |
| `policy_sha` | string | no | pattern `^[0-9a-f]{64}$` | Optional SHA256 digest of the governing policy/mandate document this record was authored under (an opaque pin, never the document body). |
| `ratification` | object | no | unevaluatedProperties `false` | The human-ratification attestation. REQUIRED when `status: accepted` (enforced by the check); a `proposed` record carries none. |
| `crosswalk` | object | no | unevaluatedProperties `false` | Supersession + traceability links between records. |
| `disposition` | string | no | enum `merge`, `close`, `postpone` | RFC-only (Rust model): the motion's disposition. Forbidden on `adr` records (schema-conditional below). |
| `fcp` | object | no | unevaluatedProperties `false` | RFC-only (Rust model): the Final Comment Period record. Forbidden on `adr` records (schema-conditional below). |

### `schemas/devops-privileged-action-broker.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine DevOps privileged-action broker envelope |
| `$id` | `https://creator-engine.local/schemas/devops-privileged-action-broker.schema.yaml` |
| Root type | `object` |

Value-free authority envelope for one broker-mediated privileged DevOps action. The envelope records a ratified, scoped grant; it never carries a password, private key, OpenBao token, wrapped token, OTP value, SSH pri...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `privileged_action_envelope` | $ref #/$defs/privileged_action_envelope | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `non_empty_string` | string | no | pattern `\\S`<br>minLength `1` |  |
| `ref_string` | string | no | pattern `^[A-Za-z0-9][A-Za-z0-9_.:/#@+ -]{0,511}$`<br>minLength `1`<br>maxLength `512` |  |
| `seat_id` | string | no | pattern `^ce-dev-[1-9][0-9]*$` |  |
| `role` | string | no | enum `operator`, `controller`, `architect`, `implementer`, `reviewer`, `verification`, `agent_reviewer` |  |
| `requester` | object | no | additionalProperties `false` |  |
| `capability` | object | no | additionalProperties `false` |  |
| `target` | object | no | additionalProperties `false` |  |
| `scope` | object | no | additionalProperties `false` |  |
| `ratification_ref` | object | no | additionalProperties `false` |  |
| `execution` | object; allOf | no | additionalProperties `false` | Execution posture for the action. The cross-field rule below structurally enforces the contract requirement that high or irreversible work is proxied: `execution_mode: capability-handoff` is forbidden whenever `blast_... |
| `audit_hook` | object | no | additionalProperties `false` |  |
| `lease` | object | no | additionalProperties `false` |  |
| `metadata` | object | no | additionalProperties `false` | Optional non-authority descriptive notes. Closed to a fixed allow-list of non-secret descriptive keys so the value-free claim is structurally enforced: an envelope cannot carry an arbitrary key such as `password`, `to... |
| `privileged_action_envelope` | object | no | additionalProperties `false` |  |

### `schemas/dispatch-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Dispatch Record |
| `$id` | `https://creator-engine.local/schemas/dispatch-record.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single dispatch record — the on-disk handoff a `cev3 drive --spawn` materializes from a ratified Scope's assembled `coordination.DispatchPlan` (v3.1-G1 live-spawn keystone). One record li...

Required fields:

`kind`, `record_type`, `schema_version`, `scope_id`, `run_id`, `mutation_class`, `harness`, `unattended`, `session`, `window`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `dispatch-record` | Discriminator constant. Records that do not carry this exact value are not governed dispatch records. |
| `record_type` | string | yes | const `dispatch` |  |
| `schema_version` | string | yes | enum `1` |  |
| `scope_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | The ratified Scope this run was dispatched from (same slug pattern as the Scope record). |
| `run_id` | string | yes | minLength `1` | The minted run identity (`run-<scope_id>-<utcstamp>`). Stable key for the dispatch dir and the run's evidence chain (`<v3-local-state>/runs/<run_id>.runtime-evidence.yaml`). |
| `mutation_class` | string | yes | enum `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`, `none` | The blast-radius/severity tier conserved from the Scope — drives the back gate (mutation_class-tiered human ratification). |
| `scope_ratification` | $ref #/$defs/scope_ratification | no |  | The value-free opaque digests carried through from the assembled plan (the front-gate bet). NEVER a raw account. |
| `harness` | string | yes | enum `claude`, `codex` | The seat harness. `claude` remains the default stronger Ring-1-hook-pack path. `codex` is explicit, low-risk guarded, and gated by CE's managed Codex PreToolUse hook-pack plus containment backstops. |
| `harness_boundary` | string | no | enum `claude_ring1_hookpack`, `codex_managed_pretooluse` | Governance boundary label for the selected harness. `codex_managed_pretooluse` means the Codex PreToolUse managed hook-pack is launch-confirmed; containment and external forge/review/merge gates remain load-bearing. |
| `unattended` | boolean | yes |  | Whether the seat is spawned unattended (default true). When true the bridge appends `--claude-arg=--dangerously-skip-permissions`; CC-D-6 stays the gate on the v1 side (an unconfirmed hook-pack is a fail-closed refusa... |
| `session` | string | yes | minLength `1` | The tmux session the v1 leg spawns the seat into. |
| `window` | string | yes | minLength `1` | The tmux window the seat occupies. |
| `runtime_policy_ref` | string | no | minLength `1` | Shape-only ref to the run's `runtime-policy.yaml` (the merged policy with the appetite→cap run envelope) — read AS DATA by the v1 launch leg via `--runtime-policy`. A path ref, never the policy body. |
| `brief_ref` | string | no | minLength `1` | Shape-only ref to the seat mandate `brief.md` (the pointer target the tmux seed line names). A path ref, never the brief body. |
| `terminal` | oneOf | no |  | The value-free launch evidence stamped after the spawn: the tmux session/window/pane ids the v1 `LaunchResult` returned. Null before spawn. |
| `resource_bound` | oneOf | no |  | The v3.5-F resource-bound stamp from the v1 launch plan (the applied systemd scope/unit + fleet cap, or a `none (<enforcement>)` opt-down string). Null when the seat was launched unbounded with no stamp. |
| `spawned_at` | oneOf | no |  | UTC stamp the seat was spawned (`%Y%m%dT%H%M%SZ`). Null before spawn. |
| `collected_at` | oneOf | no |  | UTC stamp `cev3 collect` folded the run's evidence chain. Null until the run is collected. A LIVE (spawned, uncollected, non-failure-stamped) dispatch projects the Scope to Build/RUN. |
| `spawn_failed_at` | oneOf | no |  | UTC stamp the v1 launch leg (or the brief seed) was REFUSED. Fail-closed: a dispatch carrying this stamp was materialized but never became a live run, so the read-model never projects it as Build/RUN. The failed attem... |
| `spawn_failure_reason` | oneOf | no |  | The value-free refusal text for `spawn_failed_at` (the same message surfaced to the operator) — NEVER a credential/host/account. Absent on a clean spawn. |
| `change` | $ref #/$defs/change | no |  | v3.1-G2a: the value-free pointer to the PR a `cev3 pr --apply` opened for this run's authored branch (stamped by `v3_forge_join.open_change_for_run`). Shape refs ONLY — branch / base / pr_number / head_sha / manifest_... |
| `role` | string | no | enum `implementer`, `reviewer` | v3.1-G2b: the seat role. ABSENT = the G1 implementer dispatch (an authoring seat). `reviewer` marks a distinct CE-governed reviewer venue (provisioned by `v3_seat_bridge.materialize_review_dispatch` + `spawn_review_ve... |
| `review_of` | $ref #/$defs/review_of | no |  | v3.1-G2b: present ONLY on a `role: reviewer` dispatch. The value-free pointer back to the author run + the PR under review + the reviewer-authority envelope path — NEVER a credential, token, or reviewer login (the log... |
| `harness_session_id` | string | no | minLength `1` | v3.1-G2f (F9): the harness session id minted at MATERIALIZE time (a random UUIDv4 — value-free, no credential/host/account) and stamped onto the seat's `--claude-arg=--session-id`, so the harness writes its transcript... |
| `transcript_ref` | string | no | minLength `1` | G1-codex: spawn-stamped shape-only path ref to the Codex JSONL transcript. `cev3 collect` uses this as the primary Codex transcript locator, then falls back to an exact `session_meta.payload.id` lookup under `~/.codex... |
| `codex_bypass_mode` | string | no | enum `config`, `argv` | G1-codex: records how CDX-D-6 was accounted for: verified live `~/.codex/config.toml` posture (`config`) or explicit live Codex bypass flag on argv (`argv`). It does not assert Ring-1 parity. |
| `codex_risk_override` | string | no | pattern `^[0-9a-fA-F]{64}$` | Optional value-free ratification digest recording that the Operator accepted the weaker Codex in-band boundary for a high-risk mutation class. Never a raw account, token, host, or installation id. |
| `transcript_source` | string | no | enum `stamped`, `operator_override`, `unstamped` | v3.1-G2f (F9): the honesty marker `cev3 collect` stamps at fold time recording HOW the folded transcript was located. `stamped` = resolved by the `harness_session_id` exact key (or an explicit `--transcript` whose ste... |
| `seat_env_file_ref` | string | no | minLength `1` | v3.1-G2f (F4/D2): shape-only PATH ref to the seat env file the venue sourced via the `--seat-env-file` exec-wrap. A path ref ONLY — the credential VALUE never enters argv, the tmux server, the Pane Registry, or this r... |
| `events_ref` | string | no | minLength `1` | ce-ops#26: shape-only PATH ref to this seat's append-only lifecycle events surface (`<v3-local-state>/dispatches/<run_id>/events.jsonl`), stamped by the bridge from the v1 `LaunchResult` after the spawn. A path ref ON... |
| `conserve` | boolean | no |  | ce-ops#43: the conserved-evidence marker. When `true`, the dispatch (and the venue/worktree/transcript bound to it) is EVIDENCE and the seat/venue reaper treats it as an ABSOLUTE stop — no teardown, no `pco-release`,... |
| `conserve_reason` | string | no | minLength `1` | ce-ops#43: the value-free operator/policy reason a dispatch is conserved (the same short text surfaced to the operator) — NEVER a credential, host, account, or installation id. Present only alongside `conserve: true`. |
| `conserved_at` | string | no | minLength `1` | ce-ops#43: RFC3339 UTC stamp the conserve marker was applied. Present only alongside `conserve: true`. The reaper never mutates it. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `change` | object | no | unevaluatedProperties `false` |  |
| `review_of` | object | no | unevaluatedProperties `false` |  |
| `scope_ratification` | object | no | unevaluatedProperties `false` |  |
| `terminal` | object | no | unevaluatedProperties `false` |  |

### `schemas/distributed-claim.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine distributed claim record substrate |
| `$id` | `https://creator-engine.local/schemas/distributed-claim.schema.yaml` |
| Root type | `object` |

G2.004.2 schema for shape-only distributed claim records. A distributed claim is the cross-repo / team-mode coordination claim primitive — the distributed analogue of a single-repo PCL lane claim. Claims are content-a...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `distributed_claim` | $ref #/$defs/record | no |  |  |
| `distributed_claim_chain` | array | no | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `hash` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `record` | object | no | additionalProperties `false` |  |

### `schemas/escalation-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Escalation Record |
| `$id` | `https://creator-engine.local/schemas/escalation-record.schema.yaml` |
| Root type | `object` |

Machine-readable schema for one AWAITING-OPERATOR escalation mirrored into the v3 local-state root. Records live under `<v3-local-state>/escalations/<escalation_id>.yaml` and are read by the Cockpit L2 fold as a local...

Required fields:

`kind`, `record_type`, `schema_version`, `escalation_id`, `title`, `decision_needed`, `recommendation`, `created_at`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `escalation-record` | Discriminator constant. Records without this exact value are not governed escalation records. |
| `record_type` | string | yes | const `escalation` |  |
| `schema_version` | string | yes | enum `1` |  |
| `escalation_id` | string; anyOf | yes |  | Stable slug or digest; also the filename stem under `.ce/state/escalations`. |
| `title` | string | yes | minLength `1` |  |
| `decision_needed` | string | yes | minLength `1` | The decision the Operator must make. |
| `recommendation` | string | yes | minLength `1` | Required recommendation for the Operator. This machine-enforces the standing offer-recommendation-on-options rule. |
| `created_at` | string | yes | minLength `1` | ISO-8601 timestamp or forge-created timestamp string. |
| `source_ref` | string | no | minLength `1` | Optional value-free forge marker or local source reference. |
| `resolved_at` | string | no | minLength `1` | Present when the Operator decision is resolved. |
| `resolution` | string | no | minLength `1` | Optional value-free resolution summary. |

### `schemas/evidence-fan-in-packet.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Local Read-Only Evidence Fan-In Packet |
| `$id` | `https://creator-engine.local/schemas/evidence-fan-in-packet.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a Gate 7 local read-only evidence fan-in packet authored by `ce fanin build` under the ignored `.hermes/fan-in/` runtime root (RV1-070 / RV1-071).

Required fields:

`kind`, `schema_version`, `packet_id`, `has_authority`, `source_ratification`, `evidence`, `side_effect_ledger`, `content_hash`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `evidence-fan-in-packet` |  |
| `schema_version` | string | yes | const `1` |  |
| `packet_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,127}$` |  |
| `has_authority` | boolean | yes | const `false` | A fan-in packet never grants authority; this field is constrained to `false` so a packet asserting authority fails schema validation. |
| `source_ratification` | object | yes | unevaluatedProperties `false` |  |
| `evidence` | array | yes | minItems `1` |  |
| `side_effect_ledger` | object | yes | unevaluatedProperties `false` |  |
| `content_hash` | string | yes | pattern `^[0-9a-f]{64}$` |  |

### `schemas/extension-hook-contract.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine extension + hook contract substrate |
| `$id` | `https://creator-engine.local/schemas/extension-hook-contract.schema.yaml` |
| Root type | `object` |

G2.006.0 shape-only schema for a CE extension contract and its hook bindings. An extension (e.g. a Claude Code hook-pack) declares the ring it occupies, its enforcement strength, and the hooks it binds (event, matcher...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `extension_contract` | $ref #/$defs/extension_contract | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `extension_contract` | object | no | additionalProperties `false` |  |
| `hook_contract` | object | no | additionalProperties `false` |  |

### `schemas/federated-identity-binding.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine federated identity binding record substrate |
| `$id` | `https://creator-engine.local/schemas/federated-identity-binding.schema.yaml` |
| Root type | `object` |

G2.004.2 schema for shape-only federated identity binding records. A federated identity binding asserts, as coordination/attestation state only, that a named principal in one repository is the same principal as named...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `federated_identity_binding` | $ref #/$defs/record | no |  |  |
| `federated_identity_chain` | array | no | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `hash` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `record` | object | no | additionalProperties `false` |  |

### `schemas/forge-claim.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine forge-projected claim record |
| `$id` | `https://creator-engine.local/schemas/forge-claim.schema.yaml` |
| Root type | `object` |

Machine-readable schema for the **forge-projected claim record** (v3.5-C A-C4, design §A.4): the team-visible projection of a PCO claim onto the forge (assignee + Projects `Status=Running` — the A.0 invariant: the for...

Required fields:

`kind`, `schema_version`, `repo`, `item_id`, `claimant_instance`, `lease_window`, `claimed_at`, `status`, `idempotency_key`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `forge-claim` | Discriminator constant — records without it are not forge claims and MUST NOT be validated by `forge_claim_dedup`. |
| `schema_version` | string | yes | enum `1` |  |
| `repo` | string | yes | pattern `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$` | The `owner/name` of the ONE backlog's repo. |
| `item_id` | string | yes | minLength `1` | The backlog item (Projects-v2 item node id or issue ref). |
| `claimant_instance` | string | yes | minLength `1` | The claiming CE instance's label (value-free). |
| `lease_window` | string | yes | minLength `1` | The claim's lease window (e.g. an ISO-8601 interval). Part of the idempotency tuple: a retry inside the window is the SAME claim. |
| `claimed_at` | string | yes | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+(Z\|[+-][0-9:]+)$` | ISO-8601 claim timestamp — drives earlier-`claimed_at`-wins reconciliation (surfaced as an escalation, never auto-resolved). |
| `status` | string | yes | enum `planned`, `claimed`, `contended`, `released` | `planned` (plan-by-default, nothing written) · `claimed` (projection live) · `contended` (a competing claimant observed → the contention block is REQUIRED, surfaced as escalation) · `released`. |
| `idempotency_key` | string | yes | pattern `^[0-9a-f]{64}$` | SHA256 over the canonical `(repo, item_id, claimant_instance, lease_window)` tuple — recomputed and enforced by the check (`VAL-FC-IDEMPOTENCY`). |
| `contention` | object | no | unevaluatedProperties `false` | REQUIRED when a second live claimant was observed (`status: contended`). A silent overwrite is never a valid record. |
| `dedup` | object | no | unevaluatedProperties `false` | OPTIONAL dedup link: the triage side PROPOSES it; the deterministic evidence bar is what makes it bind. |

### `schemas/handoff.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Hermes Handoff Front Matter |
| `$id` | `https://creator-engine.local/schemas/handoff.schema.yaml` |
| Root type | `object` |

Schema for the YAML front matter of a Hermes-authored handoff document under `.hermes/handoffs/` and for the canonical template at `templates/hermes/handoffs/HANDOFF.template.md`.

Required fields:

`kind`, `role`, `mode`, `controller`, `ratifier`, `source_authorization_path`, `source_authorization_sha256`, `repo`, `base_branch`, `base_commit`, `allowed_paths_count`, `allowed_paths_sha256`, `stop_line`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | enum `hermes-handoff` |  |
| `role` | string | yes | enum `architect`, `implementer`, `controller`, `reviewer` |  |
| `mode` | string | yes | minLength `1` |  |
| `controller` | string | yes | minLength `1` |  |
| `ratifier` | string | yes | minLength `1` |  |
| `source_authorization_path` | string | yes | minLength `1` |  |
| `source_authorization_sha256` | string; oneOf | yes |  | Lowercase 64-hex SHA256 of the on-disk recommended-prompt or authorization file. The placeholder string `tbd` is permitted in unfilled templates only and MUST be replaced before relay. |
| `repo` | string | yes | minLength `1` |  |
| `base_branch` | string | yes | minLength `1` |  |
| `base_commit` | oneOf | yes |  | Full commit SHA (40 hex chars), or the literal `tbd` placeholder in unfilled templates. |
| `allowed_paths_count` | oneOf | yes |  | Number of unique normalized path lines in the fenced manifest that follows. Templates MAY use the literal `tbd` placeholder. |
| `allowed_paths_sha256` | oneOf | yes |  | Lowercase 64-hex SHA256 of the normalized manifest. Templates MAY use the literal `tbd` placeholder. |
| `stop_line` | string | yes | minLength `1` |  |
| `predecessor_handoff_path` | string | no | minLength `1` |  |
| `predecessor_transcript_sha256` | oneOf | no |  |  |
| `notes` | string | no |  |  |

### `schemas/harness-seat-contract.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine harness seat-contract substrate |
| `$id` | `https://creator-engine.local/schemas/harness-seat-contract.schema.yaml` |
| Root type | `object` |

G2.007.0 shape-only schema for a harness-agnostic Controller-seat contract. A seat_contract declares the harness occupying the Controller seat, the required launch posture, the genuinely posture-defeating modes the se...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `seat_contract` | $ref #/$defs/seat_contract | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `seat_contract` | object | no | additionalProperties `false` |  |
| `launch_posture` | object | no | additionalProperties `false` |  |
| `foreman_dispatch` | object | no | additionalProperties `false` | ce-ops#163 deterministic foreman operating model: governed harness seats launch pinned and dispatch substantive work to explicit worker roles. |
| `dispatch_role` | object | no | additionalProperties `false` |  |
| `required_hook_pack` | object | no | additionalProperties `true` | An embedded G2.006.0 extension_contract (kind hook_pack, ring_1, defeasible/fail-open hooks); validated by reusing the extension_hook_contract vocabulary. |

### `schemas/identity-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Tenant Identity Record |
| `$id` | `https://creator-engine.local/schemas/identity-record.schema.yaml` |
| Root type | `object` |

Required fields:

`tenant_id`, `source_host`, `source_host_installation_id`, `agent_app_slug`, `agent_actor_id`, `runtime_tool`, `role_category`, `authority_context`, `human_ratifier_roles`, `mutation_classes`, `allowed_repositories`, `signing_policy`, `attestation_storage_path`, `ratification_storage_path`, `redaction_storage_path`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `tenant_id` | string | yes | pattern `^[a-z][a-z0-9-]*$`<br>minLength `1` |  |
| `source_host` | string | yes | enum `github` |  |
| `source_host_installation_id` | string | yes | minLength `1` |  |
| `agent_app_slug` | string | yes | minLength `1` |  |
| `agent_actor_id` | string | yes | minLength `1` |  |
| `runtime_tool` | string | yes | minLength `1` |  |
| `role_category` | string | yes | enum `source`, `ratifier`, `reviewer`, `architect`, `implementer`, `verifier`, `observer` |  |
| `authority_context` | object | yes | unevaluatedProperties `false` |  |
| `human_ratifier_roles` | array | yes | minItems `1` |  |
| `mutation_classes` | array | yes | minItems `1` |  |
| `allowed_repositories` | array | yes | minItems `1` |  |
| `signing_policy` | object; allOf | yes | unevaluatedProperties `false` |  |
| `attestation_storage_path` | string | yes | minLength `1` |  |
| `ratification_storage_path` | string | yes | minLength `1` |  |
| `redaction_storage_path` | string | yes | minLength `1` |  |
| `platform_identity_ref` | string | no | minLength `1` |  |

### `schemas/identity-registry.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine GitHub identity and infrastructure registry |
| `$id` | `https://creator-engine.local/schemas/identity-registry.schema.yaml` |
| Root type | `object` |

Machine-readable non-secret SSOT for GitHub identities, App installation bindings, token storage pointers, signing-key custody pointers, host topology, and author/reviewer separation status.

Required fields:

`repos`, `accounts`, `apps`, `tokens`, `signing_keys`, `host_topology`, `authoring_review_matrix`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `repos` | array | yes | minItems `1` |  |
| `accounts` | array | yes | minItems `1` |  |
| `apps` | array | yes | minItems `1` |  |
| `tokens` | array | yes | minItems `1` |  |
| `signing_keys` | array | yes | minItems `1` |  |
| `host_topology` | array | yes | minItems `1` |  |
| `authoring_review_matrix` | array | yes | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `non_empty_string` | string | no | minLength `1` |  |
| `todo_or_string` | string | no | minLength `1` |  |
| `todo_or_integer` | oneOf | no |  |  |
| `noreply_email` | string | no | pattern `^(TODO_VERIFY\|[0-9]+\\+[A-Za-z0-9-]+@users\\.noreply\\.github\\.com)$` |  |
| `string_list` | array | no | minItems `1` |  |
| `openbao_ref` | string | no | pattern `^openbao-ref:[^\\s]+$` |  |
| `openbao_pointer` | object | no | additionalProperties `false` |  |
| `pointer` | object | no | additionalProperties `false` |  |
| `repo_inventory_entry` | object | no | additionalProperties `false` |  |
| `account` | object | no | additionalProperties `false` |  |
| `app` | object | no | additionalProperties `false` |  |
| `token` | object | no | additionalProperties `false` |  |
| `signing_key` | object | no | additionalProperties `false` |  |
| `host_topology_entry` | object | no | additionalProperties `false` |  |
| `authoring_review_entry` | object | no | additionalProperties `false` |  |

### `schemas/implementer-evidence.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Implementer Evidence Record |
| `$id` | `https://creator-engine.local/schemas/implementer-evidence.schema.yaml` |
| Root type | `object` |

Machine-readable schema for an implementer evidence record authored under the Creator Engine delivery control plane.

Required fields:

`evidence_id`, `implementation_subject`, `authored_artifact_refs`, `allowed_path_boundary_refs`, `implementer_identity_ref`, `implementer_role_category`, `execution_mode`, `implementation_scope`, `mutation_classes_executed`, `prohibited_surfaces_acknowledged`, `validation_evidence_refs`, `test_evidence_refs`, `implementation_summary`, `deviations`, `open_questions`, `verdict`, `recommended_follow_up`, `evidence_timestamp`, `non_ratification_statement`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `evidence_id` | string | yes | pattern `^[a-z][a-z0-9-]*$`<br>minLength `1` | Stable repo-relative identifier for this evidence record, unique within a tenant overlay. |
| `implementation_subject` | string | yes | minLength `1` | Human-readable statement of the implementation subject the implementer executed (e.g., the schema, validator surface, template, contract, or code change authored under the Source-ratified implementer-class envelope). |
| `authored_artifact_refs` | array | yes | minItems `1`<br>uniqueItems `true` | Repo-relative paths to artifacts the implementer authored or updated under this envelope (schema, validator check, test, template, prose contract, example, delivery doc, etc.). External tracker URLs are non-canonical... |
| `allowed_path_boundary_refs` | array | yes | minItems `1`<br>uniqueItems `true` | Repo-relative paths declared as the allowed authoring boundary for the envelope (the path manifest the implementer was authorized to touch). Every entry in `authored_artifact_refs` MUST also be inside this boundary; t... |
| `implementer_identity_ref` | string | yes | minLength `1` | Repo-relative path to the ratified implementer identity record under which this evidence is authored. |
| `implementer_role_category` | string | yes | const `implementer` | Fixed to `implementer`. Records with any other `role_category` are not governed implementer evidence under this contract. |
| `execution_mode` | string | yes | enum `manual_human`, `manual_agent`, `mixed_human_and_agent` | Generic execution-mode label. Concrete tool/model/CLI selection is a deployment-time overlay decision and MUST NOT be hard-coded as an upstream binding here. |
| `implementation_scope` | string | yes | minLength `1` | Human-readable scope statement naming in-scope and out-of-scope items for this implementer evidence. |
| `mutation_classes_executed` | array | yes | minItems `1`<br>uniqueItems `true` | Mutation classes the executed change touches, per `docs/contracts/mutation-class-taxonomy.md`. Naming a privileged class here does NOT authorize the mutation; the privileged-class envelope still requires Source ratifi... |
| `prohibited_surfaces_acknowledged` | array | yes | minItems `1`<br>uniqueItems `true` | Prohibited-surface labels the implementer affirmatively acknowledged are out of execution scope under this envelope (e.g., `live_repository_settings`, `branch_protection`, `deploy_automation`, `codeowners`, `secrets_o... |
| `validation_evidence_refs` | array | yes |  | Repo-relative paths or command-result references the implementer produced as validation evidence (validator runs, CLI output references, attestation paths). External tracker URLs are non-canonical and MAY appear only... |
| `test_evidence_refs` | array | yes |  | Repo-relative paths or command-result references the implementer produced as test evidence (unit test files, integration test files, pytest run references). MAY be empty when the envelope explicitly authorizes impleme... |
| `implementation_summary` | string | yes | minLength `1` | Free-text body summarizing what the implementer executed and why. The body MUST be sufficient for a fresh-clone reviewer to understand the executed change independently of the implementer's authoring session and MUST... |
| `deviations` | array | yes |  | Structured enumeration of deviations from the envelope (boundary adjustments requested, ambiguities encountered, scope clarifications applied, expected-fail behavior of malformed examples documented as expected, etc.)... |
| `open_questions` | array | yes |  | Open questions the implementer surfaced for Source review. MAY be empty when the implementer has no open questions. |
| `verdict` | string | yes | enum `implementation_complete`, `implementation_partial`, `scope_boundary_unclear`, `cannot_implement` | Implementer-evidence-only outcome. The schema MUST NOT accept any verdict value that implies the implementer can ratify, approve merge, waive a privileged gate, modify branch protection, run or modify deploy automatio... |
| `recommended_follow_up` | string | yes |  | Free-text recommendations for follow-up work (separate envelopes, future slices, deferred items, downstream review and ratification). MAY be empty when there is no follow-up recommendation. |
| `evidence_timestamp` | oneOf | yes |  | Either an ISO-8601 timestamp (e.g., `2026-05-17T12:00:00Z`) or a source-controlled timestamp reference (e.g., `commit:<sha>` or a repo-relative path naming a commit-bound evidence file). A machine-local clock value MU... |
| `non_ratification_statement` | string | yes | minLength `1` | Explicit textual statement that this implementer evidence is NOT Source ratification and does not authorize merge, deploy, branch deletion, branch protection mutation, live repository-settings change, provider/tool/mo... |

### `schemas/install-answers.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Install Answers File |
| `$id` | `https://creator-engine.local/schemas/install-answers.schema.yaml` |
| Root type | `object` |

Machine-readable schema for `ce-install.answers.yaml` — the declarative, IaC-style operator-answers file of the unified two-mode installer (v3.5-E.3). One engine, two modes: the installer is a single pipeline of journ...

Required fields:

`answers_version`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `answers_version` | integer | yes | const `1` | Answers-file format version. This schema is version 1. |
| `profile` | string | no | enum `solo-pilot`, `team` | Optional defaults profile. `solo-pilot` is the governance-only pilot shape (shared App, reviewer = the authenticated human). |
| `host` | object | no | additionalProperties `false` | Journey step 1 — host & dependencies. |
| `cost` | object | no | additionalProperties `false` | Journey step 2 — cost profile (G-5 wiring, semantics unchanged). |
| `provider` | object | no | additionalProperties `false` | Journey step 3 — provider auth (the LLM credential; stays in/near the box, two-credential custody invariant). Subscription OAuth sessions are DETECTED (credential-file presence, never contents) or driven interactively... |
| `github` | object | no | additionalProperties `false` | Journey step 4 — the GitHub leg, fully decomposed (design §2.2 step 4). |
| `project` | object | no | additionalProperties `false` | Journey step 5 — greenfield first-project inputs. These only apply when `github.mode: new`; E2 owns the workspace checkout and bootstrap smoke, while E4 supplies the first-project read model and minimal scaffold input... |
| `brownfield` | object | no | additionalProperties `false` | Journey step 5 — brownfield project adoption. These inputs correct or ratify the read-only project inventory that `ce onboard --inventory` detects for an existing repo. They are value-free: no raw secrets, scanner sni... |
| `pilot` | object | no | additionalProperties `false` | Journey step 5 — the pilot target. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `secret_ref` | string | no | pattern `^(env\|file\|prompt\|keychain)://\\S+$` | A secret BY REFERENCE, never by value: `env://VAR` · `file:///abs/path` (tmpfs for PEMs) · `prompt://label` (ask at the moment of use, even in file mode) · `keychain://label` (deferred backend). Refs are inert strings... |
| `ratification_binding` | object | no | additionalProperties `false` | The ONE governance-weakening attestation shape (generalizes the G-5 cost opt-out into an installer-wide invariant): a ratified-HUMAN-only binding, by value (it is an attestation, not a secret), with the educate step a... |

### `schemas/integration-queue-dry-run.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Integration Queue Dry-Run Landing Preview |
| `$id` | `https://creator-engine.local/schemas/integration-queue-dry-run.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a Gate 8 (RV1-082) Integration Queue **dry-run** landing preview authored by `ce queue dry-run` under an ignored runtime root (e.g. `.hermes/integration-queue/`).

Required fields:

`kind`, `schema_version`, `preview_id`, `mode`, `has_authority`, `source_ratification`, `landing_order`, `seam_stubs`, `content_hash`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `integration-queue-dry-run-preview` |  |
| `schema_version` | string | yes | const `1` |  |
| `preview_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,127}$` |  |
| `mode` | string | yes | const `dry-run` | v1.0 supports only the local dry-run preview; this field is constrained to `dry-run` so a preview asserting a live mode fails schema validation. |
| `has_authority` | boolean | yes | const `false` | A dry-run landing preview never grants authority; constrained to `false` so a preview asserting authority fails schema validation. |
| `source_ratification` | object | yes | unevaluatedProperties `false` |  |
| `landing_order` | array | yes | minItems `1` | The serialized canonical-branch landing order across lanes, as a preview. Positions are contiguous from 1; each entry pins the verified fan-in packet content hash for the lane it represents. |
| `seam_stubs` | object | yes | unevaluatedProperties `false` | Deferred-not-rejected team-mode / post-v1 seams recorded alongside the preview. They are stubs only: no active integration is implied. |
| `content_hash` | string | yes | pattern `^[0-9a-f]{64}$` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `seam_stub` | object | no | unevaluatedProperties `false` |  |

### `schemas/mission-brief.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Mission-Brief record substrate |
| `$id` | `https://creator-engine.local/schemas/mission-brief.schema.yaml` |
| Root type | `object` |

G2.005.0 shape-only schema for a Mission-Brief record — the bounded task brief a connector carries. A Mission-Brief references an assignment/lane by opaque id, declares the mutation classes it is permitted (which MAY...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `mission_brief` | $ref #/$defs/brief | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `hash` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `brief` | object | no | additionalProperties `false` |  |

### `schemas/mutation-class.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Mutation Class Declaration List |
| `$id` | `https://creator-engine.local/schemas/mutation-class.schema.yaml` |
| Root type | `array` |

A list of mutation class declarations.

Required fields:

_None declared._

Properties:

_No properties declared._

Array item required fields:

`name`, `is_baseline`, `description`, `action_vocabulary`, `agent_permitted_actions`, `human_ratification_required`

Array item properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `name` | string | yes | pattern `^[a-z][a-z0-9-]*$`<br>minLength `1` |  |
| `is_baseline` | boolean | yes |  |  |
| `description` | string | yes | minLength `1` |  |
| `action_vocabulary` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `agent_permitted_actions` | array | yes | uniqueItems `true` |  |
| `human_ratification_required` | boolean | yes |  |  |

### `schemas/operating-mode-policy.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine v2 Operating Mode Policy |
| `$id` | `https://creator-engine.local/schemas/operating-mode-policy.schema.yaml` |
| Root type | `object` |

G2.002.0 operating-mode substrate policy. This schema defines the sidecar policy shape only; runtime propagation is G2.002.1+ work.

Required fields:

`operating_mode`, `autonomy_class`, `default_for_migrated_v1_tenants`, `privileged_floor`, `policy_authority`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `operating_mode` | string | yes | enum `strict`, `auto`, `transcendence` |  |
| `autonomy_class` | string | yes | enum `manual`, `supervised`, `delegated_non_privileged`, `operator_ratified_privileged`, `reserved_future_agent_ratification` |  |
| `default_for_migrated_v1_tenants` | string | yes | const `strict` |  |
| `operator_policy_ref` | $ref #/$defs/operatorPolicyPointer | no |  |  |
| `operator_ratified_policy_ref` | $ref #/$defs/operatorPolicyPointer | no |  |  |
| `ratified_policy_ref` | $ref #/$defs/operatorPolicyPointer | no |  |  |
| `activation_record` | $ref #/$defs/operatorPolicyPointer | no |  |  |
| `privileged_floor` | object | yes | additionalProperties `true` |  |
| `policy_authority` | object | yes | additionalProperties `true` |  |
| `emergency_override` | string | no | enum `operator_only`, `operator-only` |  |
| `risk_coverage` | object | no | additionalProperties `true` |  |
| `risk_inventory` | oneOf | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `nonEmptyString` | string | no | pattern `\\S`<br>minLength `1` |  |
| `operatorPolicyPointer` | oneOf | no |  |  |

### `schemas/pane-registry.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Pane Registry Record |
| `$id` | `https://creator-engine.local/schemas/pane-registry.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Pane Registry record authored under the Creator Engine Parallel Controller Orchestration (PCO) Slice 3 substrate.

Required fields:

`kind`, `record_type`, `schema_version`, `controller_id`, `lane_id`, `claim_ref`, `host_id`, `pane_id`, `role`, `status`, `record_timestamp`, `registered_at`, `last_seen_at`, `visibility`, `terminal`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `pane-registry-record` |  |
| `record_type` | string | yes | const `pane_identity` |  |
| `schema_version` | string | yes | enum `1` |  |
| `controller_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `lane_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `claim_ref` | string | yes | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `host_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Generic operator host identifier. MUST NOT encode durable account, model, provider, token, secret, or credential authority. |
| `pane_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable pane identity for this registry entry. This is a substrate-local pane id, not a provider, model, account, or credential binding. |
| `role` | string | yes | enum `architect`, `implementer`, `reviewer`, `verification` |  |
| `status` | string | yes | enum `starting`, `active`, `blocked`, `closing`, `closed`, `aborted` |  |
| `record_timestamp` | $ref #/$defs/timestamp | yes |  |  |
| `registered_at` | $ref #/$defs/timestamp | yes |  |  |
| `last_seen_at` | $ref #/$defs/timestamp | yes |  |  |
| `visibility` | string | yes | enum `operator_visible`, `operator_inspectable` |  |
| `terminal` | object | yes | unevaluatedProperties `false` |  |
| `claim_record_sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `closed_at` | $ref #/$defs/timestamp | no |  |  |
| `close_reason` | string | no | enum `completed`, `aborted`, `lapsed`, `handed_off`, `operator_closed` |  |
| `worktree_path` | string | no | minLength `1` |  |
| `branch` | string | no | minLength `1` |  |
| `envelope_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `handoff_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `recommended_prompt_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `container_instance_id` | string | no | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `container_instance_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `note` | string | no | maxLength `1024` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | oneOf | no |  |  |

### `schemas/pcl-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine PCL (Project Coordination Ledger) record substrate |
| `$id` | `https://creator-engine.local/schemas/pcl-record.schema.yaml` |
| Root type | `object` |

G2.004.0 schema for shape-only PCL records. PCL is the per-repo authoritative Project Coordination Ledger. Records are content-addressed and hash-chained and are discriminated by record_kind. PCL records never ratify....

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `pcl_record` | $ref #/$defs/record | no |  |  |
| `pcl_chain` | array | no | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `hash` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `record` | object | no | additionalProperties `false` |  |

### `schemas/plan-wrapper-sidecar.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Plan Wrapper Sidecar |
| `$id` | `https://creator-engine.local/schemas/plan-wrapper-sidecar.schema.yaml` |
| Root type | `object` |

Required fields:

`spec_ref`, `plan_mutation_class_summary`, `plan_permitted_actions_summary`, `verification_plan`, `ratification_required`, `identity_policy_ref`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `spec_ref` | string | yes | minLength `1` |  |
| `plan_mutation_class_summary` | array | yes | minItems `1` |  |
| `plan_permitted_actions_summary` | array | yes | minItems `1` |  |
| `verification_plan` | object | yes | unevaluatedProperties `false` |  |
| `ratification_required` | boolean | yes |  |  |
| `identity_policy_ref` | string | yes | minLength `1` |  |

### `schemas/playbook.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine playbook workflow |
| `$id` | `https://creator-engine.local/schemas/playbook.schema.yaml` |
| Root type | `object` |

Machine-checkable workflow descriptor for one CE playbook directory under playbooks/. The descriptor binds a human README, dispatch envelope template, governed briefs, and harness contract into one reusable operating...

Required fields:

`kind`, `schema_version`, `playbook`, `preconditions`, `outputs`, `dispatch`, `gates`, `stages`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `ce-playbook` |  |
| `schema_version` | string | yes | const `1` |  |
| `playbook` | object | yes | unevaluatedProperties `false` |  |
| `preconditions` | $ref #/$defs/non_empty_steps | yes |  |  |
| `outputs` | $ref #/$defs/non_empty_steps | yes |  |  |
| `dispatch` | object | yes | unevaluatedProperties `false` |  |
| `gates` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `stages` | array | yes | minItems `1` |  |
| `ratified_flow_hooks` | array | no | minItems `1` |  |
| `references` | array | no | minItems `1`<br>uniqueItems `true` |  |
| `metadata` | object | no | additionalProperties `true` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `slug` | string | no | pattern `^[a-z0-9][a-z0-9-]{1,96}$` |  |
| `non_empty_string` | string | no | pattern `\\S`<br>minLength `1` |  |
| `dispatch_target` | string | no | enum `governed-seat`, `reviewer-seat`, `author-seat`, `controller-seat`, `human-operator`, `uncontained-courier`, `forge-courier`, `ci` |  |
| `non_empty_steps` | array | no | minItems `1` |  |
| `hook` | object | no | unevaluatedProperties `false` |  |

### `schemas/recommended-prompt.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Hermes Recommended-Prompt Front Matter |
| `$id` | `https://creator-engine.local/schemas/recommended-prompt.schema.yaml` |
| Root type | `object` |

Schema for the YAML front matter of a Source-authored / Source- ratified recommended-prompt document under `.hermes/recommended-prompts/` and for the canonical template at `templates/hermes/recommended-prompts/RECOMME...

Required fields:

`kind`, `role`, `ratifier`, `controller`, `authorized_actor`, `repo`, `base_branch`, `base_commit`, `allowed_paths_count`, `allowed_paths_sha256`, `stop_line`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | enum `hermes-recommended-prompt` |  |
| `role` | string | yes | enum `architect`, `implementer`, `controller`, `reviewer` |  |
| `ratifier` | string | yes | minLength `1` |  |
| `controller` | string | yes | minLength `1` |  |
| `authorized_actor` | string | yes | minLength `1` |  |
| `repo` | string | yes | minLength `1` |  |
| `base_branch` | string | yes | minLength `1` |  |
| `base_commit` | oneOf | yes |  |  |
| `allowed_paths_count` | oneOf | yes |  |  |
| `allowed_paths_sha256` | oneOf | yes |  |  |
| `stop_line` | string | yes | minLength `1` |  |
| `notes` | string | no |  |  |

### `schemas/review-evidence.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Review Evidence Record |
| `$id` | `https://creator-engine.local/schemas/review-evidence.schema.yaml` |
| Root type | `object` |

Machine-readable schema for an independent review evidence record authored under the Creator Engine delivery control plane.

Required fields:

`evidence_id`, `reviewed_artifact_refs`, `reviewed_diff_or_commit_ref`, `reviewer_identity_ref`, `reviewer_role_category`, `reviewer_model`, `authorship_obfuscated`, `adversarial_prompt`, `review_mode`, `review_scope`, `mutation_classes_under_review`, `prohibited_surfaces_checked`, `validation_evidence_refs`, `findings`, `blocking_findings`, `non_blocking_findings`, `verdict`, `recommended_follow_up`, `evidence_timestamp`, `non_ratification_statement`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `evidence_id` | string | yes | pattern `^[a-z][a-z0-9-]*$`<br>minLength `1` | Stable repo-relative identifier for this evidence record, unique within a tenant overlay. |
| `reviewed_artifact_refs` | array | yes | minItems `1`<br>uniqueItems `true` | Repo-relative paths to artifacts under review (spec, plan, tasks, code, docs, validator output, etc.). |
| `reviewed_diff_or_commit_ref` | string | yes | minLength `1` | Reference to the diff range or commit-ish under review. For pre-merge review, the working diff range; for post-merge review, the merged commit-ish. |
| `reviewer_identity_ref` | string | yes | minLength `1` | Repo-relative path to the ratified reviewer identity record under which this evidence is authored. |
| `reviewer_role_category` | string | yes | const `reviewer` | Fixed to `reviewer`. Records with any other `role_category` are not governed review evidence under this contract. |
| `reviewer_model` | string | yes | minLength `1` | Reviewer-supplied model identifier used to assess model-level independence for this evidence. This is an evidence attestation, not a normative upstream product/model binding. |
| `authorship_obfuscated` | boolean | yes |  | True when the reviewer received an authorship-obfuscated prompt or packet for this review. |
| `adversarial_prompt` | boolean | yes |  | True when the review prompt explicitly asked for adversarial blocking-finding discovery rather than agreement or approval. |
| `review_mode` | string | yes | enum `manual_human`, `manual_agent`, `mixed_human_and_agent` | Generic review-mode label. Concrete tool/model/CLI selection is a deployment-time overlay decision and MUST NOT be hard-coded as an upstream binding here. |
| `review_scope` | string | yes | minLength `1` | Human-readable scope statement naming in-scope and out-of-scope items for this evidence. |
| `mutation_classes_under_review` | array | yes | minItems `1`<br>uniqueItems `true` | Mutation classes that the change under review touches, per `docs/contracts/mutation-class-taxonomy.md`. |
| `prohibited_surfaces_checked` | array | yes | minItems `1`<br>uniqueItems `true` | Prohibited-surface labels the reviewer affirmatively checked (e.g., `live_repository_settings`, `branch_protection`, `deploy_automation`, `codeowners`, `secrets_or_tokens`, `instance_local_paths`). |
| `validation_evidence_refs` | array | yes |  | Repo-relative paths or command-result references the reviewer consulted (validator runs, CI output references, attestation paths). External tracker URLs are non-canonical and MAY appear only as advisory references. |
| `findings` | string | yes | minLength `1` | Free-text body of observations. |
| `blocking_findings` | array | yes |  | Structured findings that, per the review gate, prevent advancement past the gate without remediation. MAY be empty only when `verdict` is `no_blocking_findings` or when the verdict explicitly declines to enumerate fin... |
| `non_blocking_findings` | array | yes |  | Advisory findings (style, future-work suggestions, scope clarifications) that do not, by themselves, prevent advancement. |
| `verdict` | string | yes | enum `no_blocking_findings`, `blocking_findings_present`, `scope_boundary_unclear`, `cannot_review` | Evidence-only outcome. The schema MUST NOT accept any verdict value that implies the reviewer can ratify, approve merge, waive a privileged gate, modify branch protection, run or modify deploy automation, or apply liv... |
| `recommended_follow_up` | string | yes |  | Free-text recommendations for follow-up work (separate envelopes, future slices, deferred items). MAY be empty when there is no follow-up recommendation. |
| `evidence_timestamp` | oneOf | yes |  | Either an ISO-8601 timestamp (e.g., `2026-05-17T12:00:00Z`) or a source-controlled timestamp reference (e.g., `commit:<sha>` or a repo-relative path naming a commit-bound evidence file). A machine-local clock value MU... |
| `non_ratification_statement` | string | yes | minLength `1` | Explicit textual statement that this review evidence is NOT Source ratification and does not authorize merge, deploy, branch deletion, branch protection mutation, or live repository-settings change. Its absence is its... |

### `schemas/reviewer-authority-envelope.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine reviewer-venue side-effect-authority envelope |
| `$id` | `https://creator-engine.local/schemas/reviewer-authority-envelope.schema.yaml` |
| Root type | `object` |

G2.007.2 bounded, auditable authority envelope that lets a distinct CE-governed reviewer venue legitimately perform exactly one restricted mechanic (pr_review) on exactly one PR. It is the sanctioned replacement for t...

Required fields:

_None declared._

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `reviewer_authority_envelope` | $ref #/$defs/reviewer_authority_envelope | no |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` |  |
| `reviewer_authority_envelope` | object | no | additionalProperties `false` |  |

### `schemas/reviewer-registry.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine reviewer registry |
| `$id` | `https://creator-engine.local/schemas/reviewer-registry.schema.yaml` |
| Root type | `object` |

Governed reviewer registry for dynamic reviewer triage. This registry is governance/identity-classed data: changes require ratification. It is not a live availability scratchpad; availability is durable declared statu...

Required fields:

`kind`, `schema_version`, `mutation_class`, `reviewers`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `reviewer-registry` |  |
| `schema_version` | string | yes | enum `1` |  |
| `mutation_class` | string | yes | const `governance` |  |
| `reviewers` | array | yes | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `non_empty_string` | string | no | minLength `1` |  |
| `string_list` | array | no |  |  |
| `reviewer` | object | no | additionalProperties `false` |  |
| `isolation_domain_attestation` | object | no | additionalProperties `false` |  |

### `schemas/reviewer-triage-decision.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine reviewer triage decision |
| `$id` | `https://creator-engine.local/schemas/reviewer-triage-decision.schema.yaml` |
| Root type | `object` |

Auditable plan-only reviewer assignment decision. It records candidate generation, eligibility, availability, triage routing, assignment, and escalation facts. It never grants approval, ratification, merge, waiver, re...

Required fields:

`kind`, `schema_version`, `work_ref`, `changed_paths`, `mutation_classes`, `risk_tier`, `candidate_generation`, `eligibility_results`, `availability_results`, `triage_results`, `assignment`, `escalation`, `non_authority_statement`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `reviewer-triage-decision` |  |
| `schema_version` | string | yes | enum `1` |  |
| `work_ref` | object | yes | additionalProperties `false` |  |
| `changed_paths` | $ref #/$defs/string_list | yes |  |  |
| `mutation_classes` | array | yes | minItems `1` |  |
| `risk_tier` | string | yes | enum `low`, `medium`, `high`, `privileged` |  |
| `candidate_generation` | object | yes | additionalProperties `false` |  |
| `eligibility_results` | array | yes |  |  |
| `availability_results` | array | yes |  |  |
| `triage_results` | array | yes |  |  |
| `assignment` | object | yes | additionalProperties `false` |  |
| `escalation` | object | yes | additionalProperties `false` |  |
| `non_authority_statement` | string | yes | const `Reviewer triage assigns review only; it does not approve, ratify, merge, or waive policy.` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `non_empty_string` | string | no | minLength `1` |  |
| `string_list` | array | no |  |  |
| `result` | object | no | additionalProperties `false` |  |
| `triage_result` | object | no | additionalProperties `false` |  |
| `isolation_domain_attestation` | object | no | additionalProperties `false` |  |

### `schemas/runtime-evidence.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Runtime Evidence Chain |
| `$id` | `https://creator-engine.local/schemas/runtime-evidence.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a hash-chained Runtime Evidence chain — the tamper-evident, append-only, content-addressed audit spine for one Creator Engine agent seat's runtime lifecycle (plane C / runtime safety, v3 G-...

Required fields:

`kind`, `record_type`, `schema_version`, `records`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `runtime-evidence-chain` | Discriminator constant. Files that do not carry this exact value are not governed Runtime Evidence chains and MUST NOT be validated by the `ce_runtime_evidence` check. |
| `record_type` | string | yes | const `runtime_evidence_chain` | Sub-discriminator for the chain wrapper. G-1.3a defines exactly one chain shape; later slices MAY add additive record types under a new `schema_version`. |
| `schema_version` | string | yes | enum `1` | Runtime Evidence schema version. G-1.3a ships v1; later slices MAY extend additively without breaking v1 readers. |
| `records` | array | yes | minItems `1` | The ordered, append-only record chain. Element 0 is the genesis record (`prev_hash` = the all-zero sentinel, `sequence` = 0); each subsequent record links to its predecessor by `prev_hash` and increments `sequence`. E... |
| `note` | string | no | maxLength `1024` | Optional free-text note. Advisory only; MUST NOT contain secrets, tokens, credentials, or actor ids. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `runtime_evidence_record` | object | no | unevaluatedProperties `false` |  |
| `runtime_run_outcome_record` | object | no | unevaluatedProperties `false` | A typed terminal run-OUTCOME record (v3 G-3.6a). It attests WHERE a run ended — its terminal disposition — on an axis ORTHOGONAL to the container `lifecycle_phase`. Outcomes are plural and work-type-dependent (a run m... |
| `runtime_ratification_record` | object | no | unevaluatedProperties `false` | A typed run-RATIFICATION record (v3 G-3.7.2a). It attests that a run was RATIFIED — the CE-owned, SHA-pinned, single-use ratification that authorizes the run to act — appended to the SAME tamper-evident hash chain (co... |
| `runtime_agent_action_record` | object | no | unevaluatedProperties `false` | A typed per-action record (v3 G-4). It attests one observed agent action — WHAT was done (`op` × `mutation_class`), at WHAT observation `fidelity`, gated HOW (`classification` + `decision_mode`) — appended to the SAME... |
| `runtime_spend_ledger_record` | object | no | unevaluatedProperties `false` | A typed spend-METER / ledger record (v3 G-5). It attests one metered cost leaf — `$` (API-USD, the fleet regime) or `%` (the single subscription seat meter) — appended to the SAME tamper-evident hash chain (content-ad... |
| `runtime_spend_breach_record` | object | no | unevaluatedProperties `false` | A typed spend-BREACH record (v3 G-5). It attests a circuit-breaker trip — `soft` (~80% alert, continue) or `hard` (100% pause + escalate) — on the nested deny-by-default envelope hierarchy, appended to the SAME tamper... |
| `runtime_change_restamp_record` | object | no | unevaluatedProperties `false` | A typed F6 Phase-0 CHANGE-RE-STAMP record. It attests that the active merge head for a run moved by BASE-ONLY motion and that CE machine-proved rebase-equivalence — unchanged path-set, unchanged content-pins, unchange... |
| `runtime_merge_audit_record` | object | no | unevaluatedProperties `false` | A typed F6 Phase-0 MERGE-AUDIT record. Squash-merge makes the merged commit SHA neither the reviewed PR head nor a parent of it, so the conserved invariant is tree/diff equivalence: the TESTED head tree MUST equal the... |

### `schemas/runtime-policy.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Runtime Policy Record |
| `$id` | `https://creator-engine.local/schemas/runtime-policy.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Runtime Policy record — the declarative plane-C (runtime-safety) isolation contract for one Creator Engine agent seat.

Required fields:

`kind`, `record_type`, `schema_version`, `policy_id`, `policy_sha`, `role`, `image_ref`, `mount_manifest`, `egress_allowlist`, `secret_allowlist`, `grant_extensible`, `grant_authority`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `runtime-policy-record` | Discriminator constant. Records that do not carry this exact value are not governed Runtime Policy records under this contract and MUST NOT be validated by the `ce_runtime_policy` check. |
| `record_type` | string | yes | const `runtime_policy` | Sub-discriminator. G-1.0 defines exactly one record shape; later slices MAY add additional record types via additive extension under a new `schema_version`. |
| `schema_version` | string | yes | enum `1` | Runtime Policy schema version. G-1.0 ships v1. Later slices MAY extend additively via a further version bump without breaking v1 readers. |
| `policy_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable identifier for this policy record. Matches the slug pattern used by controller_id and lane_id across the substrate. |
| `policy_sha` | string | yes | pattern `^[0-9a-f]{64}$` | SHA256 hex digest (64 lowercase hex characters) of the canonical representation of this policy record. Binds a runtime instance to the exact policy version in force at provision time. |
| `role` | string | yes | enum `architect_research`, `implementer`, `verification` | Seat role enum. The three runtime seats carried from the v2 worker-container contract. Additional roles MUST be ratified as additive schema changes; this schema fixes only the three above. |
| `isolation_backend` | string | no | enum `gvisor-proxy`, `openshell`, `local-noop`, `os-native` | Runner-backend selector (the G-1.1 adapter axis). `gvisor-proxy` is the canonical v3 backend — a hardened gVisor container paired with a capability-separation egress proxy (shipped at G-1.2). `openshell` is the fast-f... |
| `image_ref` | object | yes | unevaluatedProperties `false` | Image reference. The digest pin is the normative binding; the check enforces its presence and `sha256:<hex64>` format. |
| `mount_manifest` | array | yes |  | Ordered list of paths to bind into the runtime. Default-deny posture: paths not listed here are NOT accessible inside the runtime. The `ce_runtime_policy` check refuses any manifest that names a host home directory, a... |
| `egress_allowlist` | array | yes |  | Per-seat egress rules. Deny-by-default: an empty array declares no egress (the safe floor, appropriate for the verification seat). Shape only — not a deployment host inventory. Each rule carries an L4/L7 assurance axi... |
| `secret_allowlist` | array | yes |  | Names of secrets the runtime is permitted to inject — names only: no values, no paths, no raw credential material. The `ce_runtime_policy` check refuses any entry that is a path or value, or that names the controller-... |
| `grant_extensible` | boolean | yes |  | When `true`, the Controller MAY extend this policy's mount manifest at runtime. When `false`, the manifest is sealed. Governance-class grants additionally require Source ratification. |
| `grant_authority` | string | yes | enum `controller`, `source` | Authority required to approve runtime mount grants for this policy. `controller`: the Controller alone may approve per-grant extensions. `source`: Source ratification is required (governance-class grants). |
| `controller_id` | string | no | pattern `^[a-z][a-z0-9-]{2,63}$` | Optional: the Controller that authored this policy. Same slug pattern as elsewhere in the substrate. |
| `note` | string | no | maxLength `1024` | Optional free-text note. Advisory only; MUST NOT contain secrets, tokens, credentials, or actor ids. G-1.0 does not enforce this prohibition mechanically. |
| `action_class_allowlist` | array | no |  | v3 G-4 (additive, optional): the per-action allowlist read by the audit-overlay classifier. Each entry grants one `(op, mutation_class)` cell — the cells a faithfully-observed mutating agent action may perform WITHOUT... |
| `gate_mode_ladder` | $ref #/$defs/gate_mode_ladder | no |  | v3 G-4 (additive, optional): the gate-mode ladder the audit-overlay `decide()` control-point resolves (OpenClaw exec-approvals modes + Zed precedence). Optional; when absent the safe `ask` default applies to every gat... |
| `spend_envelopes` | array | no |  | v3 G-5 (additive, optional): the nested deny-by-default spend envelopes (`global` -> `fleet` -> `run`, most-restrictive-wins). Shape only here — the admission-gate + circuit-breaker semantics live in `runner.spend_gat... |
| `max_concurrent_runs` | integer | no | minimum `1` | v3 G-5 (additive, optional): the concurrency envelope dimension — the maximum number of runs admitted at once (a semaphore ceiling). Over-limit admission yields the `throttle` signal (retry with backoff), distinct fro... |
| `model_rates` | array | no |  | v3 G-5 (additive, optional): the per-model API-USD rate table the fleet (`$`) regime meters against. READ LIVE, NEVER HARDCODED — vendor rates / caps drift (e.g. the +50% weekly bump expiring 2026-07-13), so prices li... |
| `spend_cap_enforcement` | string | no | enum `enforce`, `off` | v3 G-5 (additive, optional): the cost-enforcement opt-out lever — an OPERATOR-FACING, RATIFIED-HUMAN-ONLY choice (an agent can never set it; the gate is external to the agent). `enforce` (default): the spend CAPS are... |
| `spend_cap_optout` | $ref #/$defs/spend_cap_optout | no |  | v3 G-5 (additive, optional): the ratification binding REQUIRED when `spend_cap_enforcement` is `off`. Value-free opaque digests proving the opt-out was an explicit ratified human choice. |
| `resource_envelopes` | array | no |  | v3.5-F (additive, optional): the OS-enforced per-seat / per-fleet resource envelopes (the memory axis of fleet resource hardening). Sibling of `spend_envelopes`: shape only here — the systemd-run bounding wrap that en... |
| `resource_enforcement` | string | no | enum `enforce`, `advisory`, `off` | v3.5-F (additive, optional): the resource-enforcement lever, an OPERATOR-FACING, RATIFIED-HUMAN-ONLY choice mirroring `spend_cap_enforcement`. `enforce` (default): seat launches are wrapped in the OS bound and a host... |
| `resource_optout` | $ref #/$defs/resource_optout | no |  | v3.5-F (additive, optional): the ratification binding REQUIRED when `resource_enforcement` is `advisory` or `off`. Value-free opaque digests proving the opt-down was an explicit ratified human choice (mirrors `spend_c... |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `agent_op` | string | no | enum `read`, `write`, `exec`, `egress`, `secret`, `vcs` | The v3 G-4 operation/capability axis: the "do we gate?" axis. `read` is observe-only (never gated); the rest are gateable. |
| `agent_mutation_class` | string | no | enum `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`, `none` | The v3 G-4 blast-radius/severity axis — the shared planning-layer mutation-class taxonomy (`checks.mutation_class`) plus `none`. |
| `action_class_grant` | object | no | unevaluatedProperties `false` | One `(op, mutation_class)` allowlist grant. |
| `gate_mode_ladder` | object | no | unevaluatedProperties `false` | The gate-mode ladder shape. |
| `gate_rule` | object | no | unevaluatedProperties `false` | One `always_*` precedence rule, optionally scoped by op / mutation_class / target_pattern, carrying the Lobster approver-identity fields (shape only). |
| `mount_entry` | object | no | unevaluatedProperties `false` |  |
| `egress_rule` | object | no | unevaluatedProperties `false` |  |
| `spend_envelope` | object | no | unevaluatedProperties `false` |  |
| `model_rate` | object | no | unevaluatedProperties `false` | One model's API-USD rate row. Prices are deployment / vendor data read live from policy — never baked into code. |
| `spend_cap_optout` | object | no | unevaluatedProperties `false` |  |
| `resource_envelope` | object | no | unevaluatedProperties `false` | One resource envelope (the systemd cgroup-v2 property set the bounding wrap applies). Shape only — never a host / credential / account identifier. |
| `resource_optout` | object | no | unevaluatedProperties `false` |  |

### `schemas/scope.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Scope Record |
| `$id` | `https://creator-engine.local/schemas/scope.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Scope record — the v3 coordination layer's ephemeral atomic unit of work (the OUTER loop, v3 G-6). A Scope is a ratifiable, scope-boxed task with testable acceptance criteria, a Sh...

Required fields:

`kind`, `record_type`, `schema_version`, `scope_id`, `intent`, `mutation_class`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `scope-record` | Discriminator constant. Records that do not carry this exact value are not governed Scope records and MUST NOT be validated by `ce_scope`. |
| `record_type` | string | yes | const `scope` |  |
| `schema_version` | string | yes | enum `1` |  |
| `scope_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable slug for this Scope (same pattern as policy_id / controller_id). |
| `intent` | string | yes | minLength `1` | The framed problem/spec — what is being asked and why. The `Frame` output. |
| `acceptance_criteria` | array | no |  | Testable acceptance criteria — the DoR core and the test-first oracle (XP). REQUIRED non-empty for a ready-or-later Scope (enforced by `ce_scope`); a `draft` Scope being framed/shaped may omit it. |
| `appetite` | $ref #/$defs/appetite | no |  | Shape-Up fixed effort budget (NOT an estimate). Seeds the per-run tokenomics envelope via the appetite→spend-cap join (`coordination.appetite_to_spend_envelope`). REQUIRED + derivable for a ready-or-later Scope (enfor... |
| `mutation_class` | string | yes | enum `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`, `none` | The blast-radius/severity axis (the shared planning-layer taxonomy plus `none`). Drives the back gate (the `mutation_class`-tiered `human_ratification_required` ratified-merge — existing machinery). |
| `ratification` | $ref #/$defs/scope_ratification | no |  | The betting-table attestation (the FRONT-gate bet): value-free opaque digests proving a ratifier placed the bet. Its presence is REQUIRED for a ready-or-later Scope (the front gate gates dispatch); `ce_scope` emits `V... |
| `skill_refs` | array | no |  | Optional forward hook to the durable Skill axis (deferred). Shape only. |
| `binding_decisions` | array | no |  | Optional ids of Decision Records (`docs/decisions/` ADRs / `docs/rfcs/` RFCs, e.g. `ADR-0007`) this Scope cites as BINDING context — the A↔B seam (v3.5-C A-C1). A-C1 adds the FIELD only; the readiness enforcement (eve... |
| `crosswalk_parent` | string | no | minLength `1` | Optional light traceability ref up the collapsible crosswalk tree (PRD/epic/story). The register-side `scope_mappings` axis is deferred. |
| `state` | string | no | enum `draft`, `ready`, `in_progress`, `verified`, `ratified`, `done` | The CONSERVED mechanical spec-lifecycle state (conserved verbatim from the stage-vocabulary canon). Absent ⇒ treated as `draft`. This is the source of truth; the cognitive phase is derived from it. |
| `phase` | string | no | enum `Frame`, `Shape`, `Build`, `Review`, `Ship` | OPTIONAL cached cognitive phase (the canon presentation skin). When present it MUST equal the derivation from `state` (`coordination.cognitive_phase`); `ce_scope` emits `VAL-SCOPE-STATE-INCONSISTENT` on drift. The ski... |
| `note` | string | no | maxLength `1024` | Optional advisory note. MUST NOT contain secrets, tokens, or actor ids. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `appetite` | object | no | unevaluatedProperties `false` |  |
| `scope_ratification` | object | no | unevaluatedProperties `false` |  |

### `schemas/seat-class-policy.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Seat-Class Policy Record |
| `$id` | `https://creator-engine.local/schemas/seat-class-policy.schema.yaml` |
| Root type | `object` |

Shape for the foreman-delegation Slice 1 policy. Every CE seat is born a foreman by default; governed policy records pin foreman posture and explicit dispatch surfaces. This schema is record-shape only. Live hook armi...

Required fields:

`kind`, `schema_version`, `policy_id`, `policy_sha`, `seat_class`, `default_seat_class`, `recursion`, `delegation_required_mutation_classes`, `foreman_dispatch`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `seat-class-policy-record` |  |
| `schema_version` | string | yes | enum `1` |  |
| `policy_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `policy_sha` | string | yes | pattern `^[0-9a-f]{64}$` | Opaque digest of the ratified policy content. This is not a credential. |
| `seat_class` | string | yes | const `foreman` | Launch-pinned class for governed seats. Valid policy records are foreman by construction; unknown/absent runtime values resolve to foreman in the pure resolver and later live hook wiring. |
| `default_seat_class` | string | yes | const `foreman` | Born-a-foreman default. The record may not weaken this default. |
| `recursion` | object | yes | unevaluatedProperties `false` |  |
| `delegation_required_mutation_classes` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `coordination_path_prefixes` | array | no | uniqueItems `true` |  |
| `foreman_dispatch` | object | yes | unevaluatedProperties `false` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `dispatch_role` | object | no | unevaluatedProperties `false` |  |

### `schemas/seat-event.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Seat Lifecycle Event |
| `$id` | `https://creator-engine.local/schemas/seat-event.schema.yaml` |
| Root type | `object` |

Machine-readable schema for ONE seat lifecycle sentinel event — a single JSON object on a single line of an append-only `events.jsonl` (ce-ops#26). Every `ce launch`-ed governed seat owns one such file at `<v3-local-s...

Required fields:

`v`, `event`, `ts`, `seat_id`, `run_id`, `writer`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `v` | integer | yes | const `1` | Integer schema version, REQUIRED from day one. Bumped only on a breaking line-shape change; readers MUST tolerate-skip an unknown major. |
| `event` | string | yes | enum `launched`, `exited`, `outcome_resolved` | Closed enum v1. `launched` is appended before the seat child starts; `exited` on ANY termination (the blocking watcher's completion trigger); `outcome_resolved` is the OPTIONAL best-effort follow-up (§3.4). `progress`... |
| `ts` | string | yes | pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` | UTC RFC3339 stamp (`date -u +%Y-%m-%dT%H:%M:%SZ`), wrapper-observed. |
| `seat_id` | string | yes | minLength `1` | The seat identity (§3.1): the dispatch `run_id` for a dispatch-driven seat, else the `lane_id`, else a `<session>--<window>` slug for a bare Controller seat. Joins the event stream to its dispatch directory. |
| `run_id` | oneOf | yes |  | The dispatch `run_id` when the seat is dispatch-driven (the key the run's evidence chain is filed under), else `null` for a v1-only launch. |
| `writer` | string | yes | const `launcher_wrapper` | Closed enum v1 — the writer-role rule made data. The launcher's supervisor wrote this line; the seat's model never writes the file. |
| `pid` | integer | no | minimum `0` | `event: launched` only — the wrapper's pid (the seat process-tree root), for reader-side liveness/staleness (§3.9). |
| `command_sha256` | string | no | pattern `^[0-9a-f]{64}$` | `event: launched` only — sha256 digest of the inner argv. NEVER the command text (value-free; the ps-leak lesson). |
| `exit_code` | integer | no | minimum `0`<br>maximum `255` | `event: exited` only — the mechanical exit code the wrapper observed. A signal-killed child yields `128 + signum` (137 = OOM-group SIGKILL). |
| `signal` | oneOf | no |  | `event: exited` only, OPTIONAL — readers MAY derive (`exit_code > 128 ⇒ exit_code - 128`); the wrapper does not compute it (keeps the shell minimal). Absent in wrapper-written lines. |
| `outcome` | oneOf | no |  | `event: outcome_resolved` only — THE conserved run-OUTCOME enum, identical to `runtime-evidence.schema.yaml`'s `outcome` (a unit test pins the two so they cannot drift). `null` when the chain was absent/unreadable. |
| `outcome_source` | string | no | enum `runtime_evidence`, `unresolved` | `event: outcome_resolved` only — honest-tiering: `runtime_evidence` when the chain was read; `unresolved` when absent/unreadable (outcome null). |
| `evidence_ref` | oneOf | no |  | `event: outcome_resolved` only — shape-only path ref to the chain document consulted; `null` when no chain was found. |

### `schemas/seat-lifecycle.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Seat Lifecycle Record |
| `$id` | `https://creator-engine.local/schemas/seat-lifecycle.schema.yaml` |
| Root type | `object` |

Machine-readable schema for one CE-substrate-owned seat lifecycle record. Records live under `.hermes/active-work-ledger/seats/<host_id>/<seat_id>.yaml` and bind spawn-time seat identity to terminal, dispatch, work-cl...

Required fields:

`kind`, `record_type`, `schema_version`, `seat`, `work`, `dispatch`, `terminal`, `harness`, `resources`, `lifecycle`, `policy`, `retirement`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `seat-lifecycle-record` |  |
| `record_type` | string | yes | const `seat_lifecycle` |  |
| `schema_version` | string | yes | enum `1` |  |
| `seat` | object | yes | unevaluatedProperties `false` |  |
| `work` | object | yes | unevaluatedProperties `false` |  |
| `dispatch` | object | yes | unevaluatedProperties `false` |  |
| `terminal` | object | yes | unevaluatedProperties `false` |  |
| `harness` | object | yes | unevaluatedProperties `false` |  |
| `resources` | object | yes | unevaluatedProperties `false` |  |
| `lifecycle` | object | yes | unevaluatedProperties `false` |  |
| `policy` | object | yes | unevaluatedProperties `false` |  |
| `retirement` | object | yes | unevaluatedProperties `false` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | string | no | minLength `1` |  |

### `schemas/secret-grant.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | SecretGrant |
| `$id` | `https://creator-engine.local/schemas/secret-grant.schema.yaml` |
| Root type | `object` |

Required fields:

`grant_id`, `run_id`, `seat_id`, `secret_ref`, `lease_id`, `token_accessor_ref`, `issued_at`, `expires_at`, `delivery_ref`, `audit_ref`, `revoked_at`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `grant_id` | string | yes | minLength `1` |  |
| `run_id` | string | yes | minLength `1` |  |
| `seat_id` | string | yes | minLength `1` |  |
| `secret_ref` | object | yes | additionalProperties `false` |  |
| `lease_id` | anyOf | yes |  |  |
| `token_accessor_ref` | anyOf | yes |  |  |
| `issued_at` | string | yes | format `date-time` |  |
| `expires_at` | string | yes | format `date-time` |  |
| `delivery_ref` | anyOf | yes |  |  |
| `audit_ref` | string | yes | minLength `1` |  |
| `revoked_at` | anyOf | yes |  |  |

### `schemas/secret-ref.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | SecretRef |
| `$id` | `https://creator-engine.local/schemas/secret-ref.schema.yaml` |
| Root type | `object` |

Required fields:

`backend`, `mount`, `path`, `field`, `version`, `purpose`, `owner_ref`, `policy_sha`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `backend` | string | yes | minLength `1` |  |
| `mount` | string | yes | minLength `1` |  |
| `path` | string | yes | minLength `1` |  |
| `field` | string | yes | minLength `1` |  |
| `version` | anyOf | yes |  |  |
| `purpose` | string | yes | minLength `1` |  |
| `owner_ref` | string | yes | minLength `1` |  |
| `policy_sha` | string | yes | pattern `^[0-9a-f]{64}$` |  |

### `schemas/secret-zero-grant.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | SecretZeroGrant |
| `$id` | `https://creator-engine.local/schemas/secret-zero-grant.schema.yaml` |
| Root type | `object` |

Required fields:

`grant_id`, `run_id`, `requester_seat_id`, `seat_id`, `role_name`, `auth_mount`, `issued_at`, `expires_at`, `delivery_ref`, `wrap_accessor_ref`, `wrapped_accessor_ref`, `audit_ref`, `revoked_at`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `grant_id` | string | yes | minLength `1` |  |
| `run_id` | string | yes | minLength `1` |  |
| `requester_seat_id` | string | yes | pattern `^dev-[1-9][0-9]*$` |  |
| `seat_id` | string | yes | pattern `^dev-[1-9][0-9]*$` |  |
| `role_name` | string | yes | pattern `^ce-dev-[1-9][0-9]*$` |  |
| `auth_mount` | string | yes | pattern `^[A-Za-z0-9][A-Za-z0-9_-]*$` |  |
| `issued_at` | string | yes | format `date-time` |  |
| `expires_at` | string | yes | format `date-time` |  |
| `delivery_ref` | string; allOf | yes | minLength `1` |  |
| `wrap_accessor_ref` | anyOf | yes |  |  |
| `wrapped_accessor_ref` | anyOf | yes |  |  |
| `audit_ref` | string | yes | minLength `1` |  |
| `revoked_at` | anyOf | yes |  |  |

### `schemas/side-effect-ledger.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Side-Effect Ledger Record |
| `$id` | `https://creator-engine.local/schemas/side-effect-ledger.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Side-Effect Ledger record authored under the Creator Engine Parallel Controller Orchestration (PCO) Slice 4 substrate.

Required fields:

`kind`, `record_type`, `schema_version`, `controller_id`, `lane_id`, `claim_ref`, `effect_id`, `effect_kind`, `effect_status`, `occurred_at`, `record_timestamp`, `summary`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `side-effect-ledger-record` |  |
| `record_type` | string | yes | const `side_effect` |  |
| `schema_version` | string | yes | const `1` |  |
| `controller_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `lane_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `claim_ref` | string | yes | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `effect_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,127}$` |  |
| `effect_kind` | string | yes | enum `github_mutation`, `git_mutation`, `tracked_file_change`, `external_tracker_mutation`, `runtime_process_action`, `container_action`, `provider_mcp_plugin_config_change`, `network_ci_deploy_action`, `credential_secret_adjacent_event` |  |
| `effect_status` | string | yes | enum `requested`, `started`, `succeeded`, `failed`, `cancelled`, `observed`, `unknown` |  |
| `occurred_at` | $ref #/$defs/timestamp | yes |  |  |
| `record_timestamp` | $ref #/$defs/timestamp | yes |  |  |
| `summary` | string | yes | minLength `1`<br>maxLength `2048` |  |
| `actor_role` | string | no | enum `controller`, `architect`, `implementer`, `reviewer`, `verification` |  |
| `pane_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `pane_record_sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `active_work_ledger_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `active_work_ledger_record_sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `completion_report_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `completion_report_sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `integration_queue_ref` | string | no | pattern `^[A-Za-z0-9_./-]+$`<br>minLength `1` |  |
| `subject_ref` | string | no | minLength `1`<br>maxLength `2048` |  |
| `subject_sha256` | string | no | pattern `^[0-9a-f]{64}$` |  |
| `subject_git_sha` | string | no | pattern `^[0-9a-f]{7,40}$` | Git object SHA for records whose subject is a commit/ref publish event. Kept top-level so full 40-character commit SHAs do not need to be encoded into redaction-scanned free-form detail strings. |
| `evidence_refs` | array | no | minItems `1` |  |
| `redactions` | array | no | minItems `1` |  |
| `details` | object | no |  |  |
| `sequence` | integer | no | minimum `1` | Append-order position of this record within its (controller_id, lane_id) Side-Effect Ledger runtime chain. Written by `ce ledger record`; absent on hand-authored substrate examples. |
| `previous_record_sha256` | string | no | pattern `^[0-9a-f]{64}$` | SHA256 of the previous runtime record's exact file bytes, binding this record to the append-only hash chain. The genesis record uses the all-zero sentinel. Written by `ce ledger record`. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | oneOf | no |  |  |

### `schemas/spec-ce-sidecar.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine v2 Spec CE Sidecar |
| `$id` | `https://creator-engine.local/schemas/spec-ce-sidecar.schema.yaml` |
| Root type | `object` |

Formal G2.001.3 schema for v2 spec.ce.yml sidecars. This schema covers the validator-visible shape currently used by specs/v2/001-v2-foundation-substrate/spec.ce.yml.

Required fields:

`schema`, `schema_version`, `schema_status`, `ce_metadata_kind`, `spec`, `gate`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `schema` | const | yes | const `creator-engine/spec.ce.yml` |  |
| `schema_version` | string | yes | minLength `1` |  |
| `schema_status` | string | yes | enum `formalized`, `forward-declared-bootstrap` |  |
| `ce_metadata_kind` | const | yes | const `spec-ce-sidecar` |  |
| `spec` | object | yes | additionalProperties `true` |  |
| `gate` | object | yes | additionalProperties `true` |  |
| `authority_basis` | object | no | additionalProperties `true` |  |
| `operating_mode_relevance` | object | no | additionalProperties `true` |  |
| `authority` | object | no | additionalProperties `true` |  |
| `requirements` | array | no |  |  |
| `risk_inventory` | array | no | minItems `1` |  |
| `required_validation` | array | no | minItems `1` |  |
| `terminology_canon` | object | no | additionalProperties `true` |  |
| `state_boundary` | object | no | additionalProperties `true` |  |
| `hermes_write_freeze` | object | no | additionalProperties `true` |  |
| `importer_contract` | object | no | additionalProperties `true` |  |
| `role_enum_v2` | object | no | additionalProperties `true` |  |
| `role_constraints` | object | no | additionalProperties `true` |  |
| `operating_mode_policy` | object | no | additionalProperties `true` |  |
| `no_destructive_v1_removal` | object | no | additionalProperties `true` |  |
| `migrated_v1_default_mode` | object | no | additionalProperties `true` |  |
| `controller_decidable_decisions` | object | no | additionalProperties `true` |  |
| `preserved_floors` | object | no | additionalProperties `true` |  |
| `crosswalk_ref` | string | no | minLength `1` |  |
| `adr_refs` | array | no |  |  |

### `schemas/spec-wrapper-sidecar.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Spec Wrapper Sidecar |
| `$id` | `https://creator-engine.local/schemas/spec-wrapper-sidecar.schema.yaml` |
| Root type | `object` |

Required fields:

`id`, `title`, `tenant`, `owner_role`, `status`, `spec_type`, `mutation_class`, `permitted_actions`, `scope`, `acceptance_criteria`, `verification`, `ratification_required`, `identity_policy_ref`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | string | yes | minLength `1` |  |
| `title` | string | yes | minLength `1` |  |
| `tenant` | string | yes | minLength `1` |  |
| `owner_role` | string | yes | minLength `1` |  |
| `status` | string | yes | enum `draft`, `ready`, `in_progress`, `verified`, `ratified`, `done` |  |
| `spec_type` | string | yes | enum `decision_record`, `implementation_spec`, `research_report`, `handoff`, `retro`, `test_spec`, `tenant_config` |  |
| `mutation_class` | string | yes | pattern `^[a-z][a-z0-9-]*$` |  |
| `permitted_actions` | array | yes | minItems `1` |  |
| `scope` | string | yes | minLength `1` |  |
| `acceptance_criteria` | array | yes | minItems `1` |  |
| `verification` | object | yes | unevaluatedProperties `false` |  |
| `ratification_required` | boolean | yes |  |  |
| `identity_policy_ref` | string | yes | minLength `1` |  |
| `attestation_record_ref` | string | no | minLength `1` |  |
| `ratification_record_ref` | string | no | minLength `1` |  |

### `schemas/state-boundary-contract.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine State Boundary Contract |
| `$id` | `https://creator-engine.local/schemas/state-boundary-contract.schema.yaml` |
| Root type | `object` |

RV1-021 State Boundary Contract record for the Creator Engine v1.0 local governed runtime kernel (PCO v1 Gate 2).

Required fields:

`kind`, `schema_version`, `state_root`, `allowed_write_roots`, `forbidden_write_roots`, `tracked_artifact_policy`, `secret_policy`, `record_timestamp`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `state-boundary-contract` |  |
| `schema_version` | string | yes | const `1` |  |
| `description` | string | no | maxLength `2048` |  |
| `state_root` | string | yes | const `.hermes/` |  |
| `allowed_write_roots` | array | yes | minItems `1` |  |
| `forbidden_write_roots` | array | yes | minItems `1` |  |
| `tracked_artifact_policy` | const | yes | const `refuse` |  |
| `secret_policy` | object | yes | unevaluatedProperties `false` |  |
| `state_root_gitignored` | boolean | no |  |  |
| `record_timestamp` | $ref #/$defs/timestamp | yes |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | oneOf | no |  |  |

### `schemas/state-version-record.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine State Version / Migration Record |
| `$id` | `https://creator-engine.local/schemas/state-version-record.schema.yaml` |
| Root type | `object` |

RV1-022 State Version / Migration record shape for future `.hermes/` local state migrations in the Creator Engine v1.0 local governed runtime kernel (PCO v1 Gate 2).

Required fields:

`kind`, `schema_version`, `state_namespace`, `state_version`, `migration_id`, `migration_status`, `record_timestamp`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `state-version-record` |  |
| `schema_version` | string | yes | const `1` |  |
| `description` | string | no | maxLength `2048` |  |
| `state_namespace` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` |  |
| `state_version` | integer | yes | minimum `0` |  |
| `migration_id` | string | yes | pattern `^(none\|[a-z0-9][a-z0-9-]{2,127})$` |  |
| `migration_status` | string | yes | enum `not-required`, `pending`, `applied`, `blocked` |  |
| `record_timestamp` | $ref #/$defs/timestamp | yes |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `timestamp` | oneOf | no |  |  |

### `schemas/storage-tier-finding.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine storage-tier advisory finding |
| `$id` | `https://creator-engine.local/schemas/storage-tier-finding.schema.yaml` |
| Root type | `object` |

Machine-readable schema for the **advisory storage-tier finding** (v3.5-C A-C2, design §A.3/§A.2): when a CE instance produces a knowledge artifact, two ADVISORY classifications — relevance (project/team-relevant vs i...

Required fields:

`kind`, `schema_version`, `artifact_ref`, `advisory`, `classifications`, `promotion`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `storage-tier-finding` | Discriminator constant. Records without this exact value are not governed storage-tier findings and MUST NOT be validated by `storage_tier_finding`. |
| `schema_version` | string | yes | enum `1` |  |
| `artifact_ref` | string | yes | minLength `1` | Pointer to the classified knowledge artifact (path or opaque ref). |
| `advisory` | boolean | yes | const `true` | ALWAYS true — a storage-tier finding is advisory by construction. A record claiming otherwise is rejected at the schema layer. |
| `classifications` | array | yes | minItems `1` | One entry per artifact part. More than one entry = the SPLIT form (one artifact, several tiers). |
| `promotion` | object | yes | unevaluatedProperties `false` | The promotion state. A finding is BORN unpromoted; the transition is a human-ratification event recorded on the spine — there is NO code path that flips `promoted` without `ratification_ref`. |

### `schemas/tasks-wrapper-sidecar.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Tasks Wrapper Sidecar |
| `$id` | `https://creator-engine.local/schemas/tasks-wrapper-sidecar.schema.yaml` |
| Root type | `object` |

Required fields:

`spec_ref`, `tasks`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `spec_ref` | string | yes | minLength `1` |  |
| `tasks` | array | yes | minItems `1`<br>uniqueItems `true` |  |

### `schemas/tasks.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Ratified Tasks Handoff |
| `$id` | `https://creator-engine.local/schemas/tasks.schema.yaml` |
| Root type | `object` |

Reference schema for `tasks.ce.yml`, the ratified-tasks to worker handoff contract. This schema defines the design-pass shape only; semantic digest recomputation and runtime enforcement require a later Operator-ratifi...

Required fields:

`kind`, `schema_version`, `source`, `ratification`, `sha_binding`, `tasks`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `tasks-handoff` |  |
| `schema_version` | string | yes | enum `1` |  |
| `source` | $ref #/$defs/source_refs | yes |  |  |
| `ratification` | $ref #/$defs/ratification | yes |  |  |
| `sha_binding` | $ref #/$defs/task_set_sha_binding | yes |  |  |
| `tasks` | array | yes | minItems `1` |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `source_refs` | object | no | unevaluatedProperties `false` |  |
| `ratification` | object | no | unevaluatedProperties `false` |  |
| `task_set_sha_binding` | object | no | unevaluatedProperties `false` |  |
| `task` | object | no | unevaluatedProperties `false` |  |
| `task_scope` | object; anyOf | no | unevaluatedProperties `false` |  |
| `verification` | object | no | unevaluatedProperties `false` |  |
| `task_sha_binding` | object | no | unevaluatedProperties `false` |  |
| `harness_contract` | object | no | unevaluatedProperties `false` |  |
| `repo_path` | string | no | minLength `1` | Repo-relative path; absolute paths are refused. |
| `exact_repo_path` | allOf | no |  | Exact repo-relative path; glob characters are refused. |
| `allowed_scope_path` | anyOf | no |  | Exact repo-relative path, or a limited glob anchored under a named directory. Recursive `**`, root-level bare globs, and unanchored globs are refused. Examples: `docs/x.md` and `src/foo/*.py` pass; `**` and `*.py` fail. |
| `repo_path_or_glob` | string | no | minLength `1` | Repo-relative path or limited glob; absolute paths are refused. |
| `hex64` | string | no | pattern `^[0-9a-f]{64}$` |  |

### `schemas/work-sizing-floor.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Work-Sizing Floor Record |
| `$id` | `https://creator-engine.local/schemas/work-sizing-floor.schema.yaml` |
| Root type | `object` |

Deterministic F2 floor record for work-sizing. change_stats are caller- supplied line/file stats, typically parsed from git diff --numstat output. The validator recomputes sizing_floor from those deterministic inputs...

Required fields:

`kind`, `schema_version`, `intent_ref`, `declared_work_class`, `change_stats`, `sizing_floor`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `work-sizing-floor-record` |  |
| `schema_version` | string | yes | enum `1` |  |
| `intent_ref` | string | yes | minLength `1` |  |
| `declared_work_class` | string | yes | enum `tiny`, `story`, `feature`, `epic` |  |
| `change_stats` | array | yes |  | Deterministic per-path line/file stats. Generated, lockfile, and vendored paths remain in this input list but are excluded from included line totals. |
| `sizing_floor` | object | yes | unevaluatedProperties `false` |  |

### `schemas/work-sizing.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Work-Sizing Record |
| `$id` | `https://creator-engine.local/schemas/work-sizing.schema.yaml` |
| Root type | `object` |

CI-pure sizing record for the Frame→Shape work-sizing engine spine. The record is the deterministic ceremony emitted by size_ceremony(work_class, mutation_class): work_class selects decomposition depth and artifacts;...

Required fields:

`kind`, `schema_version`, `intent_ref`, `work_class`, `mutation_class`, `artifact_set`, `decomposition_depth`, `ratification_gates`, `adr_required`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `sizing-record` |  |
| `schema_version` | string | yes | enum `1` |  |
| `intent_ref` | string | yes | minLength `1` | Value-free reference to the intake intent. The pure F1 function emits `unbound` because binding to a live intake is deferred. |
| `work_class` | string | yes | enum `tiny`, `story`, `feature`, `epic` |  |
| `mutation_class` | string | yes | enum `none`, `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction` |  |
| `artifact_set` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `decomposition_depth` | integer | yes | minimum `0`<br>maximum `3` | Size-axis depth: 0=tiny/no decomposition, 1=story/tasks, 2=feature/stories/tasks, 3=epic/features/stories/thin slice. |
| `ratification_gates` | array | yes | minItems `1`<br>uniqueItems `true` |  |
| `adr_required` | boolean | yes |  |  |

### `schemas/worker-container-policy.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Worker-Container Policy Record |
| `$id` | `https://creator-engine.local/schemas/worker-container-policy.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Worker-Container Policy record authored under the Creator Engine Parallel Controller Orchestration (PCO) Slice 2I-S substrate.

Required fields:

`kind`, `record_type`, `schema_version`, `policy_id`, `policy_sha`, `role`, `runtime_engine`, `image_ref`, `mount_manifest`, `egress_allowlist`, `secret_allowlist`, `grant_extensible`, `grant_authority`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `worker-container-policy-record` | Discriminator constant. Records that do not carry this exact value are not governed Worker-Container Policy records under this contract and MUST NOT be validated by the `worker_container_policy` check. |
| `record_type` | string | yes | const `worker_container_policy` | Sub-discriminator. Slice 2I-S defines exactly one record shape; later slices MAY add additional record types via additive extension under a new `schema_version`. |
| `schema_version` | string | yes | enum `1` | Worker-Container Policy schema version. Slice 2I-S ships v1. Later slices MAY extend additively via a further version bump without breaking v1 readers. |
| `policy_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable identifier for this policy record. Matches the slug pattern used by controller_id and lane_id throughout the PCO substrate. |
| `policy_sha` | string | yes | pattern `^[0-9a-f]{64}$` | SHA256 hex digest (64 lowercase hex characters) of the canonical JSON representation of this policy record. Used by container-instance records and audit predicates to bind instances to the exact policy version in forc... |
| `role` | string | yes | enum `architect_research`, `implementer`, `verification` | Role enum. Exactly three roles are normative in Slice 2I-S. Additional roles (e.g., connector workers per Feature 008) MUST be ratified as additive schema changes; this schema fixes only the three above. |
| `runtime_engine` | string | yes | enum `podman-rootless`, `docker-rootless` | Runtime engine identifier. `podman-rootless` is the canonical v1 engine (OSD-I-1 decision); `docker-rootless` is the deployment-time overlay for environments where rootless Docker is operationally preferred. Both run... |
| `image_ref` | object | yes | unevaluatedProperties `false` | Image reference combining name and content-addressable SHA. The SHA is normative for policy binding; the name is advisory. |
| `mount_manifest` | array | yes |  | Ordered list of filesystem paths to bind into the worker container. Default-deny posture: paths not listed here are NOT accessible inside the container. `PCO-045` refuses policies whose mount manifest contains forbidd... |
| `egress_allowlist` | array | yes |  | Per-role egress rules. Shape only — not a deployment host inventory. The concrete host list is a deployment-time overlay per the architect report §7.c boundary. An empty array declares no-egress (appropriate for verif... |
| `secret_allowlist` | array | yes |  | Names of secrets the runtime engine is permitted to inject into this worker via the credential broker. Names only — no values, no paths, no raw credential material. `PCO-045` refuses any policy whose allowlist names t... |
| `grant_extensible` | boolean | yes |  | When `true`, the Controller MAY invoke `grant_path_capability` at runtime to extend this policy's mount manifest with additional paths. When `false`, the mount manifest is sealed. Per OSD-I-7, governance-class grants... |
| `grant_authority` | string | yes | enum `controller`, `source` | Authority required to approve runtime mount grants for this policy. `controller`: Controller alone may approve per-grant extensions. `source`: Source ratification is required (governance-class grants, per OSD-I-7). Us... |
| `controller_id` | string | no | pattern `^[a-z][a-z0-9-]{2,63}$` | Optional: the Controller that authored this policy. Same slug pattern as in the Active-Work Ledger schema. |
| `lane_binding` | object | no | unevaluatedProperties `false` | Optional binding to a specific lane and worktree. When present, the policy is scoped to that lane; when absent the policy is reusable across lanes. |
| `note` | string | no | maxLength `1024` | Optional free-text note. Advisory only; MUST NOT contain secrets, tokens, credentials, or actor ids. Slice 2I-S does not enforce this prohibition mechanically. |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `mount_entry` | object | no | unevaluatedProperties `false` |  |
| `egress_rule` | object | no | unevaluatedProperties `false` |  |

### `schemas/worker-tier-contract.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine governed worker tier contract |
| `$id` | `https://creator-engine.local/schemas/worker-tier-contract.schema.yaml` |
| Root type | `object` |

ce-ops#244 shape for first-class governed in-process workers spawned by a foreman. The worker carries inherited Ring-1/refusal/envelope governance, no ambient credentials, bounded capabilities, and a structured result...

Required fields:

`kind`, `schema_version`, `worker_id`, `role`, `lane_kind`, `depth`, `max_depth`, `governed_worker_contract`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `ce-worker-spawn-record` |  |
| `schema_version` | string | yes | const `1` |  |
| `worker_id` | string | yes | minLength `1` |  |
| `role` | string | yes | enum `researcher`, `implementer`, `reviewer` |  |
| `lane_kind` | string | yes | enum `read-only`, `implementation`, `review` |  |
| `depth` | integer | yes | minimum `1` |  |
| `max_depth` | integer | yes | minimum `1` |  |
| `governed_worker_contract` | $ref #/$defs/governed_worker_contract | yes |  |  |

Definitions:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `capability` | string | no | enum `read`, `research`, `edit`, `test`, `review`, `structured_result`, `push`, `self_approve`, `create_issues`, `task_other_seats` |  |
| `governed_worker_contract` | object | no | additionalProperties `false` |  |

### `schemas/worktree-lease.schema.yaml`

| Metadata | Value |
| --- | --- |
| Title | Creator Engine Worktree Lease Record |
| `$id` | `https://creator-engine.local/schemas/worktree-lease.schema.yaml` |
| Root type | `object` |

Machine-readable schema for a single Worktree Lease record authored under the Creator Engine Parallel Controller Orchestration (PCO) substrate.

Required fields:

`kind`, `record_type`, `schema_version`, `controller_id`, `lane_id`, `record_timestamp`, `lease_id`, `worktree_path`, `acquired_at`, `lease_seconds`, `expires_at`

Properties:

| Property | Shape | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | const `worktree-lease-record` | Discriminator constant. Records that do not carry this exact value are not governed Worktree Lease records under this contract and MUST NOT be validated by the `worktree_lease_schema` check. |
| `record_type` | string | yes | const `worktree_lease` | Sub-discriminator. Slice 2A defines exactly one record shape; later slices MAY add additional record types via additive extension under a new `schema_version`. |
| `schema_version` | string | yes | enum `1`, `2` | Worktree Lease schema version. Slice 2A ships v1. PCO-024 (Slice 2.5B) ships v2, which adds the ``worktree_lease_signature`` field. v1 records remain valid; v2 records must carry a ``worktree_lease_signature``. v1 rec... |
| `controller_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Stable identifier for the driving Controller. Same shape and same caveats as in `schemas/active-work-ledger.schema.yaml`: stable per physical operator+host pair; MUST NOT embed secrets, tokens, installation ids, durab... |
| `lane_id` | string | yes | pattern `^[a-z][a-z0-9-]{2,63}$` | Coordination unit identifier the Controller intends to claim under this lease. Typically `<feature-or-slice>-<short-suffix>`. Lease coverage is keyed by `(controller_id, worktree_path)`, not by `lane_id`; lane uniquen... |
| `record_timestamp` | oneOf | yes |  | Either an ISO-8601 UTC timestamp (e.g., `2026-05-21T03:08:08Z`) or a source-controlled reference (`commit:<sha>` or `source-controlled:<repo-relative-path>`). A machine-local clock value MUST NOT be presented as autho... |
| `lease_id` | string | yes | pattern `^[a-z0-9][a-z0-9-]{2,63}$` | Lease identifier. Stable within `(controller_id, lane_id, YYYY-MM-DD)` scope. Mirrors the `event_id` shape from the Active-Work Ledger schema. Slice 2A does not enforce cross-record uniqueness mechanically beyond the... |
| `worktree_path` | string | yes | minLength `1` | Repo-relative or absolute path of the physical worktree this lease intends to claim. Treated as advisory (not a secret), but required so that lease/lease and lease/claim coverage can be checked mechanically. The `work... |
| `acquired_at` | oneOf | yes |  | ISO-8601 UTC timestamp (or source-controlled reference) at which the lease was acquired. Same shape as `record_timestamp`. |
| `lease_seconds` | integer | yes | minimum `60`<br>maximum `86400` | Lease duration in seconds. Default value documented in the protocol (3600); the schema validates the range only. A lease is live when `now < expires_at`; an `expires_at` in the past is the structural expiry signal. |
| `expires_at` | oneOf | yes |  | ISO-8601 UTC timestamp (or source-controlled reference) at which the lease expires. Same shape as `record_timestamp`. A lease whose `expires_at` is in the past is considered expired and no longer covers a claim under... |
| `pane_label` | string | no | enum `architect`, `implementer`, `controller`, `reviewer` | Optional generic role label of the visible pane this lease describes. Same enum and same prohibition surface as in the Active-Work Ledger schema. NOT a model, tool, CLI, account, or runner binding. |
| `branch` | string | no | minLength `1` | Optional branch name the lease intends to operate on. Recommended but not required; pre-branch planning leases MAY omit this. |
| `envelope_ref` | anyOf | no |  | Optional repo-relative path to the Assignment Envelope under whose authority the lease is operating, or the literal `none` for coordination lanes that operate without an envelope. The envelope, not the lease, remains... |
| `note` | string | no | maxLength `1024` | Optional free-text status note. Advisory only; MUST NOT contain secrets, tokens, credentials, or actor ids. Slice 2A does not enforce this prohibition mechanically. |
| `worktree_lease_signature` | object | no | additionalProperties `false` | PCO-024 lease signature block. Required for schema_version "2"; must be absent for schema_version "1". The signing payload is the canonical UTF-8 JSON encoding (compact, sorted keys) of the lease record with this fiel... |
