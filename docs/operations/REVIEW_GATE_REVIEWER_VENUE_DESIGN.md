# Review Gate Reviewer-Venue Design Plan

**Status**: creator-engine/creator-engine#104 architect/design-gate output. This document is
bounded planning only. It does not implement runtime code, schema
changes, validators, CI wiring, launcher behavior, GitHub behavior, or
reviewer-venue spawning.

## 1. Purpose

creator-engine/creator-engine#104 identifies a Review Gate ambiguity: a distinct GitHub
reviewer account or token can submit a source-host approval, but that
does not prove that an independent CE reviewer venue performed semantic
review. The Review Gate needs a future implementation plan that can
separate these facts:

- semantic independent review evidence;
- mechanical source-host reviewer-token approval;
- Controller fan-in verification after review;
- Source ratification or an explicit Source-ratified waiver.

The invariant is the existing one from the delivery contracts: a
reviewer who authored the mutation under review is not independent
unless Source explicitly ratified a narrow exception for the named
scope.

## 2. Sources Reconciled

This plan reconciles the issue's named sources without amending them:

| Source | Design consequence |
|---|---|
| [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) | The future gate must block missing or non-independent review evidence unless a Source-ratified waiver exists. |
| [`../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md) | Reviewer identity authorizes evidence authoring only, not ratification, merge, or repository mutation. |
| [`../contracts/review-evidence.md`](../contracts/review-evidence.md) and [`../../templates/review-evidence.template.yaml`](../../templates/review-evidence.template.yaml) | Review evidence is the canonical semantic review artifact. Future fields must preserve the evidence-only verdict model. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | The authoring Controller/implementer lane must not verify or ratify its own authored mutation. |
| [`./GOVERNED_LANE_LAUNCH_PROTOCOL.md`](./GOVERNED_LANE_LAUNCH_PROTOCOL.md) | A live reviewer venue is already modeled as `--role reviewer --lane-kind review`; any future Review Gate must consume that venue identity. |
| [`./REVIEWER_VENUE_AUTHORITY.md`](./REVIEWER_VENUE_AUTHORITY.md) | Reviewer-token `gh pr review` authority is a bounded side-effect seam for a distinct reviewer venue, not proof of semantic review by itself. |
| [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md) | A distinct reviewer venue needs transcript archive/hash evidence analogous to implementer lanes. |
| [`./COMPLETION_REPORT_PROTOCOL.md`](./COMPLETION_REPORT_PROTOCOL.md) | Completion reports need explicit fields that distinguish review evidence, venue, token approval, and waiver facts. |

## 3. Core Model

The future Review Gate should treat review-readiness as a four-part
state machine:

1. `review_required`: the PR or batch needs independent review under
   the existing Review Gate.
2. `semantic_review_evidence`: a distinct reviewer venue produced a
   durable review evidence artifact with an evidence-only verdict.
3. `reviewer_token_approval`: a source-host review approval was
   submitted by an authorized reviewer token or app identity.
4. `fan_in_verification`: the Controller verified that the evidence,
   venue, approval, and head SHA still match before any next action.

Only the second state can satisfy semantic independent review. The
third state is mechanical source-host evidence and may support GitHub
branch protection or source-host workflow, but it must not be labeled
as independent semantic review unless it is backed by the second state.

## 4. Same-Seat Semantic Review Blocker

The future gate should compute an `authoring_venue_ref` and a
`reviewer_venue_ref` before accepting review evidence. At minimum, the
comparison needs these inputs:

- authoring Controller/session or implementer lane id;
- authored PR number and head SHA;
- source-host PR author account;
- active claim/lane/worktree identity;
- reviewer identity record ref;
- reviewer venue ref;
- reviewer evidence artifact ref;
- optional Source-ratified waiver ref.

If the active Controller/session authored the mutation and attempts to
perform semantic review in the same context, the gate should refuse with
an explicit blocker:

```text
BLOCKER_SAME_SEAT_REVIEW_VENUE
```

The blocker means: semantic independent review cannot be satisfied from
the authoring seat. The allowed next actions are:

- route to a distinct governed reviewer venue;
- record that separate evidence already exists and fan in that evidence;
- halt for Source clarification;
- proceed only under a Source-ratified waiver that names the PR/head/scope.

The blocker must not prevent a Controller from performing fan-in
verification after a separate reviewer venue completes. The distinction
is action-scoped: semantic review is blocked from the authoring seat;
mechanical verification of external evidence is allowed when it does
not relabel the Controller's own judgment as review evidence.

## 5. Independent Evidence vs Token Approval

The future gate should validate two separate artifact families.

Semantic independent review evidence:

- is authored by a ratified reviewer identity;
- is produced from a distinct reviewer venue;
- cites the reviewed diff or commit ref and PR head SHA;
- cites transcript archive/hash evidence for the reviewer venue where
  the runtime supports transcript capture;
- uses the existing evidence-only verdict values;
- carries the mandatory non-ratification statement.

Mechanical reviewer-token approval:

- is a source-host side effect such as `gh pr review --approve`;
- may be authorized through a reviewer-authority envelope;
- must be bound to one PR and one head SHA for audit;
- may be submitted after independent evidence exists;
- must be reported as mechanical approval, not as semantic review.

If a reviewer-token approval exists but no independent evidence exists,
the future gate should report a missing evidence blocker rather than
passing review. If independent evidence exists but no reviewer-token
approval exists, the gate may pass semantic review while separately
reporting that source-host approval is absent, depending on the target
branch policy.

## 6. Reviewer Venue Transition Semantics

When same-seat review is blocked, the future routing behavior should be:

1. Preserve a pointer-only handoff to the reviewer prompt and reviewed
   artifact set, including SHA256 for each prompt or handoff file.
2. Launch or reference a distinct visible reviewer venue. For the
   current lane-launch contract, the venue is distinct only when
   `role=reviewer` and `lane_kind=review`.
3. Bind the reviewer venue to the exact PR number and head SHA under
   review.
4. If the venue must submit source-host review, provide only a bounded
   reviewer-authority envelope for `mechanic: pr_review`.
5. Archive/hash the reviewer venue transcript and cite that archive in
   the review evidence or completion report.
6. Stop at a reviewer stop line that emits review evidence, findings,
   verdict, transcript ref, and any source-host review action taken.
7. Return to Controller fan-in. The Controller checks evidence shape,
   venue distinctness, head-SHA freshness, and whether token approval is
   present or still needed.

The transition should be fail-closed: if no distinct venue can be
launched or referenced, the PR remains blocked at review routing. A
hidden/background sub-agent is not a distinct CE reviewer venue unless a
future Source-ratified design gives it identity, transcript,
hook-inheritance, evidence, and fan-in semantics.

## 7. Completion Report and Evidence Field Impact

Future schema work should add fields without weakening the existing
review-evidence contract. Candidate fields:

Review evidence record additions:

- `reviewer_venue_ref`: repo-relative or governed sidecar pointer to
  the reviewer venue record.
- `reviewer_venue_kind`: enum such as `visible_lane`,
  `ratified_subagent_venue`, or `external_evidence_only`.
- `reviewer_transcript_ref`: pointer to the archived transcript.
- `reviewer_transcript_sha256`: byte-level transcript hash.
- `authored_mutation_refs`: PR/head/path refs used to prove the
  reviewer venue did not author the mutation under review.
- `reviewer_token_approval_ref`: optional source-host approval ref,
  explicitly mechanical.

Completion report additions:

- `independent_review_evidence_ref`;
- `reviewer_venue_ref`;
- `reviewer_identity_ref`;
- `reviewer_token_approval_ref`;
- `reviewer_token_approval_kind`;
- `source_ratification_ref`;
- `source_waiver_ref`;
- `review_gate_result`;
- `review_gate_blocker_code`;
- `review_gate_head_sha`.

The report should be able to state one of these outcomes precisely:

- independent evidence exists and source-host approval was submitted by
  the reviewer venue;
- independent evidence exists and token approval was submitted later as
  a mechanical Controller action;
- independent evidence exists but source-host approval is intentionally
  absent or not required;
- Source waived independent review for a named scope;
- same-seat semantic review was blocked.

## 8. Claude Code and Hermes Runtime Differences

Claude Code:

- The committed hook-pack can enforce shell-level restricted mechanics
  and receive a launch-pinned reviewer-authority ref.
- Ordinary hidden/background Claude subagents are not automatically CE
  reviewer venues. They lack the required visible venue identity and
  transcript/fan-in guarantees unless a future design explicitly
  ratifies that path.
- A governed reviewer venue should therefore be a separate visible lane
  or another ratified venue class, not the authoring Controller context
  switching GitHub tokens.

Hermes:

- Completion-report runtime enforcement is explicitly deferred in the
  current Completion Report Protocol.
- Hermes can orchestrate prompt pointers, handoffs, and fan-in, but the
  Review Gate should not assume Hermes has a send-blocking runtime hook
  until a ratified Hermes-side change lands.
- Hermes-side evidence should be treated as orchestration/fan-in
  evidence unless it references a distinct reviewer venue with its own
  transcript and review evidence.

Shared rule:

- Runtime names are deployment-time bindings. The Review Gate should
  validate venue separation, evidence, and authority references rather
  than hard-coding a product, model, account, token, or source-host app
  as the reviewer.

## 9. Source-Ratified Waiver Semantics

A waiver is allowed only when Source explicitly ratifies a narrow
exception. It must not be inferred from a reviewer token, a passing CI
run, a green branch protection status, or a Controller statement.

Minimum waiver fields for a future schema:

- `waiver_ref`;
- `ratifier_role: source`;
- `ratified_at` or source-controlled timestamp reference;
- `scope_kind`, such as `named_pr_head` or `named_batch`;
- `pr_number` when applicable;
- `head_sha` when applicable;
- `allowed_without_independent_review: true`;
- `reason`;
- `expires_at` or `single_use: true`;
- `non_independent_review_label_required: true`.

When a waiver is used, completion reports and PR bodies must not call
the result independent review. The correct statement is that Source
waived independent review for the named scope and the gate proceeded
under that waiver.

## 10. Future Tests and Validator Fixtures

Future implementation should add fixtures before runtime behavior:

- same Controller/session authored the PR and attempts inline semantic
  review: fails with `BLOCKER_SAME_SEAT_REVIEW_VENUE`;
- same source-host reviewer token submits approval without independent
  evidence: fails review evidence gate while recording mechanical
  approval;
- distinct reviewer venue with review evidence and transcript hash:
  passes semantic review evidence;
- distinct reviewer venue evidence exists and Controller submits a later
  mechanical reviewer-token approval: passes with approval labeled
  mechanical;
- Source waiver names PR and head SHA: gate proceeds but records
  non-independent waiver semantics;
- waiver names a different head SHA: fails closed;
- reviewer venue is `role=reviewer` but not `lane_kind=review`: fails
  distinct-venue validation;
- hidden/background sub-agent lacks ratified venue semantics: fails or
  routes, not accepted as independent review;
- head SHA changed after review evidence: fails stale-review check;
- completion report omits independent evidence, venue ref, approval ref,
  or waiver ref when required: fails schema validation.

Fixture naming should keep the failure mode clear, for example:

```text
validators/examples/review-gate/same-seat-semantic-review.ce.yml
validators/examples/review-gate/distinct-reviewer-evidence.ce.yml
validators/examples/review-gate/mechanical-approval-only.ce.yml
validators/examples/review-gate/source-waiver-named-head.ce.yml
validators/examples/review-gate/source-waiver-stale-head.ce.yml
```

## 11. Non-Goals

This design does not:

- implement Review Gate validation;
- add or change schemas;
- add fixtures;
- wire CI;
- change launcher behavior;
- mint reviewer-authority envelopes;
- submit GitHub reviews;
- change branch protection, CODEOWNERS, repository settings, or merge
  behavior;
- declare Claude Code or Hermes as the only allowed reviewer runtime.

The next implementation gate should be a separate, Source-ratified
slice with an explicit path manifest and tests.
