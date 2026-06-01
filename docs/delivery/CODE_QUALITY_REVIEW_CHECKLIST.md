# Code Quality Review Checklist

**Status**: Canonical CE-native checklist. Docs/governance layer only;
introduces no schema field, validator, or runtime. This is the
question-by-question worksheet a reviewer applies when the ratified
envelope requests a **maintainability deep review** depth. It is the
operational companion to the rubric in
[`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md).

Part of the **minimum repo-native delivery control plane** and **not a
Jira clone**. A fresh clone is sufficient to apply this checklist; no
external tracker credential or network state is required.

## a. Purpose and how this differs from the governance review gate

This checklist is **distinct from** the governance review gate in
[`./REVIEW_GATE.md`](./REVIEW_GATE.md). The two answer different
questions and are applied together, not interchangeably:

| Surface | Asks | Output home |
|---|---|---|
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) (§c–§m) | *Governance / scope*: is review evidence required, who may author it, what is in scope, which prohibited surfaces were checked, which non-ratifying verdict applies? | The review-evidence record's governance fields and `verdict`. |
| **This checklist** + [`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md) | *Code quality*: is the change well-decomposed, well-branched, well-bounded, well-placed, non-duplicative, atomic — or did a behavior-correct change worsen the structure? | The same record's `findings`, `blocking_findings`, `non_blocking_findings`, and `recommended_follow_up`, plus verdict shaping. |

This checklist does **not** restate the governance/scope checks of
[`./REVIEW_GATE.md`](./REVIEW_GATE.md); it assumes those are applied
separately. It adds the maintainability dimension on top, and it
shares one piece of machinery with the gate: a blocking maintainability
finding forces `verdict: blocking_findings_present` and halts the batch
([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §i).

Standing boundary (carried from
[`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md)
§c): the reviewer **recommends or blocks; the reviewer never
self-authors the fix.** Every remediation below is recorded for a
separate, separately ratified implementer envelope — never applied by
the reviewer.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md) | The rubric this checklist operationalizes: finding taxonomy, structural-regression rule, waiver posture, tone, provenance. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) | The governed gate. Verdict semantics, blocking-finding halt (§i), and non-ratification invariants (§m) control. |
| [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md) | The evidence template whose fields receive the observations from §c–§j below. |
| [`../../schemas/review-evidence.schema.yaml`](../../schemas/review-evidence.schema.yaml) | The machine-readable evidence shape. This checklist adds **no** field to it. |
| [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) | Reviewer authors evidence only; reviewer-not-author default. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) | The verifier-side scope audit; the natural future home for objective file-delta signals. Distinct from this code-quality pass. |

Where this checklist and any upstream source disagree, the upstream
source controls until Source ratifies a correction.

## c. Decomposition and file size

- [ ] Did any changed file grow past a size where a reader can no
      longer hold its responsibility in mind? Record an oversized file
      as a `file_size_threshold_signal` (advisory; waiver-recorded
      when accepted per
      [`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md)
      §h).
- [ ] Does a single unit (function, validator check, schema block) now
      carry more than one responsibility that wants splitting? Record
      as `structural_simplification_opportunity` (advisory).
- [ ] Did the growth tangle a previously coherent unit such that the
      *next* change to it is materially harder? If so this is a
      `structural_regression` (blocking, §e of the rubric).

## d. Branching and control flow

- [ ] Did the change add net control-flow branching to a changed unit?
      Record growth as a `branching_growth_signal` (advisory).
- [ ] Was an ad-hoc branch threaded into an otherwise clean flow
      (a special case bolted onto a hot path)? Record as
      `spaghetti_branch`; escalate to blocking when it constitutes a
      regression.
- [ ] Is there needless sequential orchestration where a direct,
      single-pass form exists? Record as `avoidable_orchestration`
      (advisory).

## e. Schema and type boundaries

- [ ] Did a YAML schema lose a boundary — a removed
      `unevaluatedProperties: false`, an unbounded
      `additionalProperties`, or an enum widened without need? Record
      as `schema_boundary_looseness`; escalate to blocking when it
      loosens a governed boundary.
- [ ] Did validator/runtime code erode a checked contract — an
      unconstrained `Any`, a swallowed error type, a cast that defeats
      a type boundary? Record as `type_boundary_looseness`; escalate
      to blocking when it erodes a checked contract.
- [ ] Are new boundaries as tight as the contract they protect, or
      looser than necessary?

## f. Layer placement

- [ ] Is each piece of logic in its canonical layer, or did gate
      semantics / contract logic get inlined where a helper or contract
      should own it? Record misplacement as `wrong_layer`; escalate to
      blocking when it is a regression.
- [ ] Does the change respect the existing source-of-truth hierarchy
      (contract over doc over inlined constant)?

## g. Helper reuse

- [ ] Was a helper, predicate, or function reintroduced where a
      canonical one already exists? Record as `duplicate_helper`;
      escalate to blocking when the duplicate diverges from the
      canonical one.
- [ ] Is there a thin wrapper or indirection that adds reading cost
      without earning it? Record as `incidental_indirection`
      (advisory); prefer the direct, boring form.

## h. Atomicity and orchestration

- [ ] Does the change perform in several non-atomic steps what should
      be one coherent update, widening the window for partial-state
      bugs? Record as `non_atomic_update` (advisory).
- [ ] Could a simpler atomic form preserve behavior? Record as
      `structural_simplification_opportunity` (advisory).

## i. Tests vs. maintainability

- [ ] **Do the passing tests mask a structural regression?** A green
      test run, a green CI run, a green external tracker check, or a
      passing validator run **does not** clear a maintainability block
      ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §i.4, §m.7;
      [`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md)
      §e). If the change works but worsens the structure, that is a
      `structural_regression` and it blocks.
- [ ] Is behavioral coverage (per
      [`../quality/QA_STRATEGY.md`](../quality/QA_STRATEGY.md)) being
      treated as evidence the structure is fine? It is not; the two
      gates are evaluated independently.

## j. Verdict shaping

- [ ] If any check above produced a **blocking** finding (a
      `structural_regression`, or an advisory class escalated to
      blocking), the verdict MUST be `blocking_findings_present` and
      the batch halts ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §i) —
      regardless of test or CI state.
- [ ] If only advisory findings remain, the verdict MAY be
      `no_blocking_findings` with the advisories recorded in
      `non_blocking_findings` / `recommended_follow_up`.
- [ ] If scope is unclear, use `scope_boundary_unclear`; if the change
      cannot be reviewed at this depth, use `cannot_review`. The
      four-value enum is unchanged and the verdict is **never** Source
      ratification ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1).

## k. Mapping observations into the evidence record (no schema change)

This checklist adds **no** field to
[`../../schemas/review-evidence.schema.yaml`](../../schemas/review-evidence.schema.yaml).
Each observation lands in a field that already exists:

| Observation kind | Evidence field | How |
|---|---|---|
| Review narrative + depth applied | `findings` (string) | State `maintainability_deep_review` depth, units reviewed, per-class observations in prose. |
| A blocking maintainability finding | one `blocking_findings[]` entry | `artifact_ref` = path/unit; `rule_violated` = the taxonomy label as a descriptive rule string (not a schema enum); `recommended_remediation` = the fix, framed as a **separate implementer envelope**. |
| An advisory maintainability finding | one `non_blocking_findings[]` entry | `artifact_ref` = path/unit; `observation` = taxonomy label + what was seen; `advisory_follow_up` = the non-blocking suggestion. |
| Deferred / cross-batch recommendation | `recommended_follow_up` (string) | Future slices, a refactor envelope, or a signal-calibration deferral. |
| Outcome | `verdict` (4-value enum) | Shaped per §j; unchanged enum; never ratification. |

The taxonomy labels are **review vocabulary**, not schema enums. They
are written into the free-text and structured-string fields above; no
field is added to the schema in this gate.

## l. CI green and source-host approval are not ratification

A standing reminder, restated for the code-quality pass:

1. **CI green is verification, not ratification, and not a
   maintainability pass.** A passing CI run is mechanical validation
   ([`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c); it
   neither substitutes for Source ratification nor clears a blocking
   maintainability finding.
2. **A source-host (e.g., GitHub) review approval or reviewer-token
   approval is source-host approval, not CE Source ratification**
   ([`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md)
   §e). It cannot promote a privileged batch past ratification and
   cannot clear a blocking review finding.
3. **A blocking maintainability finding is cleared only by addressing
   it** — under a separate ratified implementer envelope — or by an
   explicit Source-ratified waiver for the named batch
   ([`../quality/MAINTAINABILITY_DEEP_REVIEW.md`](../quality/MAINTAINABILITY_DEEP_REVIEW.md)
   §h). Neither a green check nor an approval is such a waiver.

## m. Acceptance posture

This document satisfies the docs/governance gate's
code-quality-checklist requirements:

- Is a checklist **distinct from** the governance/scope checks of
  [`./REVIEW_GATE.md`](./REVIEW_GATE.md) (§a).
- Provides sections for decomposition/file size (§c), branching/control
  flow (§d), schema/type boundaries (§e), layer placement (§f), helper
  reuse (§g), atomicity/orchestration (§h), tests-vs-maintainability
  (§i), and verdict shaping (§j).
- Maps observations into the existing `findings`, `blocking_findings`,
  `non_blocking_findings`, `verdict`, and `recommended_follow_up`
  fields without adding a schema field (§k).
- States that CI green and source-host approval never substitute for
  CE ratification or for addressing blocking review findings (§l).
