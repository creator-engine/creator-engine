# PCO Fan-In Protocol

**Slice**: PCO Slice 5 (`pco-fanin`)
**Status**: Spec/protocol authored only. Schema, examples, validator,
CLI discoverability, tests, runtime hooks, fan-in executable behavior,
and Integration Queue behavior are deferred to later gates.
**Architectural companion**:
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)

---

## 1. Purpose

`pco-fanin` is the integration-verification step for multi-lane PCO
authorship. Its job is to reconstruct what the lanes actually changed
and observed before any canonical-branch integration decision is made.

Fan-in verification MUST NOT trust a lane's self-report as authority.
It reconstructs lane truth from durable artifacts: tracked files,
validator output, Active-Work Ledger records, Worktree Lease records,
Pane Registry records, Completion Reports, Side-Effect Ledger records,
Git/GitHub evidence cited by those records, and the Source-ratified
Assignment Envelopes that opened the lanes.

The output of fan-in is verification evidence. It is not Source
ratification, not reviewer approval, not merge permission, and not an
Integration Queue entry. Source-ratified canonical-branch integration
remains serialized; Slice 6 owns the later Integration Queue substrate.

## 2. Position in the PCO Sequence

Fan-in runs after one or more lane gates have produced artifacts and
before a serialized integration decision consumes those artifacts. It
answers four questions:

1. Which lanes were authorized to exist?
2. Which artifacts did those lanes produce or mutate?
3. Which side effects occurred or were observed while those lanes were
   active?
4. Is the candidate integrated state mechanically consistent with the
   lane evidence and validator output?

The fan-in step composes the earlier PCO substrates:

| Input substrate | Fan-in use |
|---|---|
| Source-ratified Assignment Envelopes / prompt pointers | Defines lane authority and allowed mutation boundaries. |
| Active-Work Ledger | Reconstructs claim lifecycle, heartbeats, and events. |
| Worktree Lease records | Confirms write authority and worktree contention posture. |
| Pane Registry | Binds visible panes and roles to lane claims. |
| Completion Reports | Confirms each ratified gate returned a deterministic terminal packet. |
| Side-Effect Ledger | Indexes Git/GitHub/tracker/runtime/provider/CI/deploy/credential-adjacent effects without secrets. |
| Tracked artifacts and validator output | Reconstructs the candidate integrated content and mechanical pass/fail posture. |

If an input substrate is absent because its earlier slice has not been
implemented in a given tree, fan-in MUST report that absence explicitly
and distinguish "not yet substrate-backed" from "failed evidence."
Absence is not proof of completion.

## 3. Fan-In Evidence Packet Shape (Prose Contract)

This gate defines a prose contract only. A later schema/validator gate
may turn this shape into a tracked record or command output.

A fan-in evidence packet SHOULD contain:

| Section | Purpose |
|---|---|
| `fan_in_scope` | Candidate base, candidate head or patch set, lane ids, controller ids, and Source-ratified envelope refs. |
| `input_manifest` | Paths/URLs/ids and SHA256s for every consumed tracked artifact, ledger record, completion report, side-effect record, validator log, and Git/GitHub evidence snapshot. |
| `lane_reconstruction` | Per-lane claim lifecycle, lease posture, pane identity, completion-report outcome, and changed-path set. |
| `validator_evidence` | Exact validator commands or outputs used to evaluate the candidate integrated state. |
| `side_effect_reconciliation` | Side effects grouped by lane and classified as expected, unexpected, unresolved, or redaction-limited. |
| `overlap_and_conflict_summary` | File/path/ref/surface overlaps and the mechanical disposition for each. |
| `integration_readiness` | A verification classification such as `ready_for_source_review`, `blocked_unresolved_evidence`, or `blocked_conflict`. |
| `non_authority_statement` | Explicit statement that the packet verifies only and does not ratify, approve, merge, queue, or land anything. |

Every hash in the packet is over exact bytes observed by the fan-in
verifier. Every reference to private or secret-adjacent material MUST
use redaction-safe paths, ids, hashes, or summaries; fan-in MUST NOT
copy raw secrets or private payloads into the packet.

## 4. Reconstruction Rules

Fan-in verification follows these rules:

1. **Envelope-first**: a lane exists for fan-in only if it binds to a
   Source-ratified envelope or prompt pointer, or if the packet marks it
   as advisory/non-governed input that cannot carry integration
   authority.
2. **Ledger-before-report**: the verifier reconstructs lane lifecycle
   from Active-Work Ledger and Worktree Lease records before reading the
   lane's Completion Report summary.
3. **Tracked-content-first**: the verifier computes changed-path sets
   and file hashes from Git/tracked artifacts directly, then compares
   those facts to lane reports.
4. **Validator-output-freshness**: validator evidence is usable only
   when the command, tree/ref, timestamp or run id, and output hash are
   bound to the candidate integrated state.
5. **Side-effect reconciliation**: every externally observable effect
   relevant to integration must be explained by Side-Effect Ledger
   records or explicitly classified as missing/unresolved evidence.
6. **Self-report exclusion**: claims such as "lane complete", "tests
   pass", or "safe to merge" are advisory unless backed by the
   reconstructed artifacts and validator output.
7. **Serialized landing preservation**: fan-in may recommend a
   Source-review posture, but it MUST NOT enqueue, merge, push, retarget,
   approve, or otherwise perform canonical-branch integration.

## 5. Conflict and Drift Classification

Fan-in SHOULD classify each discovered issue into one of these buckets:

| Classification | Meaning |
|---|---|
| `clean` | Evidence reconstructs consistently; no unresolved overlap or stale artifact found. |
| `expected_overlap` | Overlap exists and is explicitly authorized by the envelopes or later Source decision. |
| `stale_artifact` | A lane report, prompt, roadmap entry, or spec sentence describes pre-landed work as future/deferred. |
| `missing_evidence` | Required ledger/report/validator/side-effect evidence is absent or unresolvable. |
| `conflict` | Candidate content or side effects collide in a way not authorized by the envelopes. |
| `redaction_limited` | Verification is bounded by redaction/privacy limits and requires separate Source decision. |

A `stale_artifact`, `missing_evidence`, `conflict`, or
`redaction_limited` item blocks any fan-in classification stronger than
`blocked_unresolved_evidence` unless Source separately ratifies a
narrow exception.

## 6. Predicate Reservation

The future schema/examples/validator or CLI gate reserves the next
additive PCO codes after the Side-Effect Ledger substrate
(`PCO-055` through `PCO-063`) and its boundary statement (`PCO-064`):

| Code | Future check |
|---|---|
| `PCO-065` | Fan-in evidence packet input manifest shape and exact hash binding. |
| `PCO-066` | Candidate integrated state reconstructed from tracked artifacts, not lane self-report. |
| `PCO-067` | Validator output freshness and tree/ref binding. |
| `PCO-068` | Lane authority binding to Source-ratified envelopes and Active-Work Ledger claims. |
| `PCO-069` | Completion Report closure exists for each governed lane. |
| `PCO-070` | Side-Effect Ledger reconciliation for externally observable effects. |
| `PCO-071` | Cross-lane changed-path/ref/surface overlap classification. |
| `PCO-072` | Self-report exclusion: unsupported completion or safety claims are non-authoritative. |
| `PCO-073` | Fan-in packet redaction-safe evidence posture. |

If live `main` later reserves any of these codes before the
implementation gate, the implementation gate MUST choose the next free
additive range and update this protocol before landing code.

## 7. Explicit Non-Goals

Slice 5 spec/protocol authoring does NOT introduce:

- schema files, examples, fixtures, validator code, tests, or CLI
  commands;
- a `pco-fanin` executable or runtime hook;
- side-effect observation automation;
- pane-spawn automation;
- Integration Queue records, queue ordering logic, or canonical-branch
  landing automation;
- GitHub, git, tracker, CI, deploy, provider, MCP, plugin, credential,
  container, network, or runtime mutations;
- branch creation, branch deletion, PR creation, review, approval,
  merge, auto-merge, or merge queue mechanics;
- Source-ratification substitution or Phase 2 autonomy expansion;
- team-mode Features 007 / 008 / 009.

## 8. Slice 5 Boundary Statement

**Slice 5 `pco-fanin` spec/protocol authoring defines integration
verification under multi-lane authorship, the evidence inputs fan-in
must reconstruct, the prose fan-in evidence packet shape,
self-report-exclusion rules, side-effect reconciliation expectations,
conflict/drift classifications, serialized integration preservation,
and the future predicate range `PCO-065` through `PCO-073`. It does
NOT introduce schema files, examples, validator code, tests, CLI
commands, a `pco-fanin` executable, runtime hooks, side-effect
observation automation, GitHub/CI/deploy/provider/MCP/plugin
mutations, credential issuance, secret capture, Slice 6 Integration
Queue behavior, Source-ratification substitution, Phase 2 autonomy
expansion, or team-mode Features 007 / 008 / 009.**

## 9. Future Evidence

The future implementation gate MUST provide:

- `--list-checks` discoverability for fan-in checks if implemented in
  the validator;
- focused fan-in scan or verification command discoverability if a CLI
  is ratified;
- well-formed and malformed examples that cover clean fan-in, stale
  artifacts, missing completion reports, unresolved side effects,
  cross-lane changed-path overlap, stale validator output, and unsafe
  private-payload evidence;
- tests proving read-only behavior and composition with Active-Work
  Ledger, Worktree Lease, Pane Registry, Completion Report, and
  Side-Effect Ledger fixtures;
- clear stop classifications that distinguish mechanical verification
  readiness from Source ratification or Integration Queue authority.
