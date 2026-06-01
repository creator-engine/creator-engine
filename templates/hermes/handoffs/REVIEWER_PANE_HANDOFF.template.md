# Reviewer-Pane Handoff Template (Maintainability Deep Review)

<!--
This file is the canonical template for a controller-authored handoff
that drives a VISIBLE REVIEWER PANE through a maintainability deep
review. It is the reviewer-side counterpart of
`templates/hermes/handoffs/HANDOFF.template.md`.

An instance fills this template into an instance-local file under
`.hermes/handoffs/<UTC-timestamp>-<batch-slug>-reviewer.md` and relays
that path (plus its byte-level SHA256) to the reviewer pane via the
pointer-only prompt in
`templates/hermes/visible-pane-pointer-prompt.template.md`. The
reviewer pane reads the file directly and verifies the hash before
consumption; it MUST NOT consume any chat-pasted body.

The reviewer drives the rubric in
`docs/quality/MAINTAINABILITY_DEEP_REVIEW.md` and the worksheet in
`docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`, and emits a
review-evidence record against
`schemas/review-evidence.schema.yaml`. The reviewer writes review
evidence and recommendations ONLY; the reviewer MUST NOT edit the
mutation under review.

Upstream Creator Engine MUST NOT track an instance's filled-in copy.
Keep `.hermes/` ignored. Do not commit live PR numbers, absolute
local paths, runtime pane identifiers, or instance-specific
secrets / tokens.

See also:
  - `docs/quality/MAINTAINABILITY_DEEP_REVIEW.md`
  - `docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`
  - `docs/delivery/REVIEW_GATE.md`
  - `docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`
  - `docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `docs/operations/NO_COPY_PASTE_PATTERN.md`
-->

---
kind: hermes-handoff
role: reviewer
mode: maintainability-deep-review
review_depth: maintainability_deep_review
controller: <controller-identity-or-coordinator-name>
ratifier: <ratifier-role-or-identity>
source_authorization_path: <repo-relative-or-absolute-path-to-recommended-prompt>
source_authorization_sha256: <64-lowercase-hex-or-tbd>
repo: <repo-name-or-repo-relative-root>
base_branch: <canonical-branch-typically-main>
reviewed_diff_or_commit_ref: <diff-range-or-commit-ish-under-review>
evidence_output_path: <repo-relative-or-ignored-path-for-the-review-evidence-record>
expected_verdict_field: <one-of: no_blocking_findings | blocking_findings_present | scope_boundary_unclear | cannot_review>
stop_line: <exact-stop-line-the-reviewer-pane-must-emit>
---

# Reviewer-pane handoff: <one-line-title>

Role: reviewer (review evidence + recommendations only)
Repo: <repo-restated>
Review depth: `maintainability_deep_review`

## 1. Source authorization

Source authorized `<controller>` to use this prompt file:

```text
<source_authorization_path-restated>
```

Expected and verified Source prompt SHA256:

```text
<source_authorization_sha256-restated>
```

This handoff is relayed **pointer-only** to the reviewer pane per
[`../visible-pane-pointer-prompt.template.md`](../visible-pane-pointer-prompt.template.md)
and [`../../../docs/operations/NO_COPY_PASTE_PATTERN.md`](../../../docs/operations/NO_COPY_PASTE_PATTERN.md):
the reviewer pane receives a path and the byte-level SHA256, reads the
file from disk, verifies the hash, and halts on mismatch. The reviewer
pane MUST NOT consume any chat-pasted body of this handoff.

## 2. Diff / commit range under review

```text
reviewed_diff_or_commit_ref: <diff-range-or-commit-ish>
base_branch: <canonical-branch>
```

State explicitly the exact diff range or commit-ish the reviewer is to
read, and whether it is a dirty working-tree diff in an allocated
worktree or a pushed branch / PR head.

## 3. Reviewed artifact references

List the repo-relative artifacts in scope for the review (these become
`reviewed_artifact_refs` in the evidence record):

```text
<reviewed-artifact-1>
<reviewed-artifact-2>
...
```

The reviewer's scope is **bounded** by this list and the ratified
envelope; the reviewer does not author evidence on artifacts outside
it ([`../../../docs/delivery/REVIEW_GATE.md`](../../../docs/delivery/REVIEW_GATE.md) §e).

## 4. Reviewer identity and venue

State the reviewer identity and the distinct reviewer venue:

- **Reviewer identity / role**: `role_category: reviewer` per
  [`../../../docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../../../docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md).
  Instantiation of a real reviewer identity is downstream work; until
  then the reviewer pane operates under the envelope's named reviewer
  venue.
- **Independence**: the reviewer venue MUST be distinct from the
  authoring venue of the mutation under review. The reviewer is not
  the author of the change
  ([`../../../docs/delivery/REVIEW_GATE.md`](../../../docs/delivery/REVIEW_GATE.md) §c.3),
  and not its ratifier or merge approver
  ([`../../../docs/delivery/REVIEW_GATE.md`](../../../docs/delivery/REVIEW_GATE.md) §m.5).
- **Pane / venue label**: `<reviewer-pane-or-venue-label>`.

## 5. Rubric and checklist the reviewer applies

The reviewer performs a **maintainability deep review** against:

- [`../../../docs/quality/MAINTAINABILITY_DEEP_REVIEW.md`](../../../docs/quality/MAINTAINABILITY_DEEP_REVIEW.md)
  — the rubric: finding taxonomy, the structural-regression-blocks
  rule, waiver posture, tone.
- [`../../../docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`](../../../docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md)
  — the question-by-question worksheet.

Required outcomes the reviewer keeps in view:

1. A **structural regression blocks even when tests pass**; it is
   recorded as a `blocking_findings[]` entry forcing
   `verdict: blocking_findings_present`.
2. Advisory signals are waiver-able only when the ratified envelope
   records the waiver.

## 6. Evidence output path and shape

The reviewer writes the review-evidence record to:

```text
evidence_output_path: <repo-relative-or-ignored-path>
```

The record is authored against
[`../../../docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../../../docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md)
and [`../../../schemas/review-evidence.schema.yaml`](../../../schemas/review-evidence.schema.yaml).
Maintainability observations map into the **existing** fields only —
`findings`, `blocking_findings`, `non_blocking_findings`, `verdict`,
`recommended_follow_up` — per
[`../../../docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`](../../../docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md)
§k. The reviewer adds **no** schema field.

## 7. Validation evidence references the reviewer consults

List the validation/verification evidence the reviewer reads (these
populate the evidence record's references):

```text
<validation-evidence-ref-1>   # e.g., validator run output path
<validation-evidence-ref-2>   # e.g., test-run reference
...
```

Reminder: a green test / CI / validator run is **verification, not a
maintainability pass**, and does not clear a blocking finding
([`../../../docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`](../../../docs/delivery/CODE_QUALITY_REVIEW_CHECKLIST.md) §i, §l).

## 8. Reviewer authority boundary (evidence and recommendations ONLY)

The reviewer pane **MUST NOT** edit the mutation under review. The
reviewer:

- writes review evidence and recommendations only, into the
  `evidence_output_path` record;
- records every remedy as a **recommendation** for a separate,
  separately ratified implementer envelope — never as a reviewer edit
  ([`../../../docs/quality/MAINTAINABILITY_DEEP_REVIEW.md`](../../../docs/quality/MAINTAINABILITY_DEEP_REVIEW.md) §c);
- does not stage, commit, push, open/edit/merge a PR, mutate GitHub or
  any source-host metadata, change branch protection or repo settings,
  delete or rename branches, run deploy automation, or touch secrets;
- does not ratify, approve merge for, or waive a privileged gate on
  the change under review.

Forbidden surfaces and operations are restated by name from the
controller-boundary policy
([`../../../docs/operations/CONTROLLER_BOUNDARY_POLICY.md`](../../../docs/operations/CONTROLLER_BOUNDARY_POLICY.md))
and the standing envelope list. A reviewer edit of the mutation is an
authority-conflict halt.

## 9. Expected verdict field and report-back

The reviewer emits exactly one `verdict` value from the four-value
enum:

```text
expected_verdict_field: <no_blocking_findings | blocking_findings_present | scope_boundary_unclear | cannot_review>
```

The `expected_verdict_field` in the front matter is the controller's
**anticipated** verdict for planning only; the reviewer records the
**honest** verdict its findings support, which may differ. Any
`blocking_findings[]` entry forces `blocking_findings_present`
regardless of the anticipated value.

At completion the reviewer reports:

1. Review depth applied (`maintainability_deep_review`) and artifacts
   reviewed.
2. The evidence record path and its `verdict`.
3. Blocking findings (with taxonomy label, location, recommended
   remediation framed for a separate envelope), if any.
4. Advisory findings and `recommended_follow_up`, if any.
5. Confirmation that **no mutation-under-review file was edited**, and
   no staging / commit / push / PR / GitHub / repo-setting / deploy
   mutation was performed.
6. The exact stop line below.

### Stop line

End the final response with exactly:

```text
<stop-line-restated-from-front-matter>
```

If blocked before the review can be completed, end with exactly:

```text
<BLOCKED-stop-line>
```

## 10. Non-ratification statement

This handoff and the review evidence it produces are **not Source
ratification.** A reviewer verdict — including `no_blocking_findings` —
does not authorize merge, deploy, branch deletion, branch-protection
mutation, or live repository-settings change, and never substitutes
for Source ratification of the change under review
([`../../../docs/delivery/REVIEW_GATE.md`](../../../docs/delivery/REVIEW_GATE.md) §m.1).
A green CI run and a source-host approval are likewise not Source
ratification and do not clear a blocking maintainability finding.
