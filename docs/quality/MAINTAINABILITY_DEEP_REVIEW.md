# Maintainability Deep Review (Rubric)

**Status**: Canonical CE-native rubric. Docs/governance layer only.
This document adds a **maintainability deep review** depth to the
existing Creator Engine review apparatus. It introduces no schema
field, no validator, and no runtime; the depth name
`maintainability_deep_review` is **prose and template vocabulary
only** in this gate. Any schema enum, objective signal, or reviewer
runtime that later implements this rubric is a separately ratified
future gate and is out of scope here.

Part of the **minimum repo-native delivery control plane** and **not a
Jira clone**. Layered onto, and subordinate to, the governance review
gate in [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) and
the reviewer identity pattern in
[`../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md).

## a. Purpose

The governance review gate
([`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md)) already
answers *who* may review, *what* is in scope, *which* prohibited
surfaces were checked, and *which* non-ratifying verdict was issued.
It does **not** say whether the change is well-structured. The
review-evidence `findings` field
([`../../schemas/review-evidence.schema.yaml`](../../schemas/review-evidence.schema.yaml))
is free text; nothing names a structural-regression concept, a
decomposition expectation, or a boundary-cleanliness expectation.

The maintainability deep review is the **content rubric** a reviewer
applies *inside* that gate when the ratified envelope calls for it. It
gives a reviewer an actionable, CE-native bar for judging whether a
behavior-correct change also keeps the substrate maintainable, and it
names the one case the governance gate could not previously express: a
change that passes its tests but worsens the structure can still
block.

This document is the rubric (the principles, the finding taxonomy,
the tone, the waiver posture). Its companion checklist
([`../delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`](../delivery/CODE_QUALITY_REVIEW_CHECKLIST.md))
is the question-by-question worksheet, and the reviewer-pane handoff
template
([`../../templates/hermes/handoffs/REVIEWER_PANE_HANDOFF.template.md`](../../templates/hermes/handoffs/REVIEWER_PANE_HANDOFF.template.md))
is the pointer-only relay that drives a reviewer pane against both.

## b. Source-of-truth relationship

This rubric is **subordinate** to the governance review gate and the
review-evidence contract. Where this document and any upstream source
disagree, the upstream source of truth controls until Source ratifies
a correction.

| Upstream source of truth | Role |
|---|---|
| [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) | The governed review gate. Verdict semantics, blocking-finding halt (§i), and the standing non-ratification invariants (§m) are authoritative; this rubric only adds a depth and a structural-regression blocking case within those semantics. |
| [`../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md) | Who may author review evidence and the reviewer-not-author default. The deep-review remit does not widen reviewer authority. |
| [`../delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../delivery/REVIEW_EVIDENCE_TEMPLATE.md) | The evidence template whose `findings`, `blocking_findings`, `non_blocking_findings`, `verdict`, and `recommended_follow_up` fields this rubric maps observations into. |
| [`../../schemas/review-evidence.schema.yaml`](../../schemas/review-evidence.schema.yaml) | The machine-readable evidence shape. This rubric adds **no** field to it. |
| [`../contracts/authority-matrix.md`](../contracts/authority-matrix.md) | The `reviewer` role category: "provides review/advisory text on artifacts under review; does not author the mutation under review." The never-self-authors boundary in §c is this rule. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Reviewer authors evidence, never ratifies; author/approver separation; authority-conflict halt path. |
| [`./QA_STRATEGY.md`](./QA_STRATEGY.md) | Behavioral QA (does it work?) vs. maintainability review (is it well-structured?); the two are complementary and neither erases the other. |

## c. The reviewer boundary: recommend or block, never self-author

A maintainability deep review **never authorizes the reviewer to edit
the mutation under review.** This is the load-bearing CE boundary that
separates this rubric from any external "be ambitious, restructure the
codebase yourself" posture.

1. Under [`../contracts/authority-matrix.md`](../contracts/authority-matrix.md)
   the `reviewer` role "does not author the mutation under review."
   The v2 advisory floor confirms an `agent_reviewer` `may [review,
   test, critique, recommend]` and `may_not` author privileged
   mutations.
2. Every maintainability remedy a reviewer identifies is therefore a
   **recommendation**, not an edit. It lands in the evidence record as
   either a `blocking_findings[].recommended_remediation` (when the
   finding blocks) or a `non_blocking_findings[].advisory_follow_up` /
   `recommended_follow_up` (when it is advisory).
3. Acting on a recommendation — actually restructuring the code — is a
   **separate `code`/`schema`/`docs` implementer envelope**, authored
   by a distinct actor, ratified on its own. A reviewer who edits the
   mutation has crossed into authoring and triggers the
   authority-conflict halt path in
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).
4. The reviewer is not the ratifier and not the merge approver of the
   change they reviewed
   ([`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §m.5,
   [`../delivery/MERGE_APPROVAL_CHECKLIST.md`](../delivery/MERGE_APPROVAL_CHECKLIST.md) §d.3).

## d. Review depth: `maintainability_deep_review`

`maintainability_deep_review` is the **name of a review depth** —
prose and template vocabulary that the ratified envelope and the
reviewer-pane handoff use to request a structural review rather than a
governance skim.

1. It is **not** a schema enum in this gate. The review-evidence
   schema's `review_mode` enum (`manual_human`, `manual_agent`,
   `mixed_human_and_agent`) records *who/how* a review was performed,
   not *how deeply*. This gate does not add a depth axis to the
   schema; a future, separately ratified gate may.
2. Until then, a reviewer asked for a `maintainability_deep_review`
   records that fact in the evidence `findings` prose (e.g., "Review
   depth: maintainability_deep_review per envelope <ref>") and applies
   this rubric and its checklist. The depth name is the contract
   between the envelope and the reviewer, carried in prose.
3. A governance review and a maintainability deep review are different
   *depths* against the same gate. A governance skim that emits
   `no_blocking_findings` makes **no** claim about structure; only a
   review performed at `maintainability_deep_review` depth does.

## e. Structural regression can block even when tests pass

The defining rule of this rubric: **a structural regression is a
blocking finding regardless of test or CI state.**

1. A *structural regression* is a change that is behavior-correct —
   its tests pass, CI is green — but leaves the substrate measurably
   harder to maintain than before: a file pushed well past a sane
   size, a hot path tangled with an ad-hoc branch, logic placed in the
   wrong layer, a helper duplicated rather than reused, or a boundary
   loosened.
2. When a reviewer at `maintainability_deep_review` depth identifies a
   structural regression, it is recorded as a `blocking_findings[]`
   entry and the verdict is `blocking_findings_present`, **even if
   every test passes.** Per
   [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §i the
   batch halts at the review gate.
3. A green CI run, a green external tracker check, a passing validator
   run, or an `agent` commentary verdict **does not** clear a
   structural-regression block
   ([`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §i.4,
   §m.7). Tests prove the change works; they do not prove it is
   maintainable.
4. This rule changes **no** verdict enum and adds **no** schema field.
   It is the existing `blocking_findings`/`blocking_findings_present`
   machinery applied to a structural finding class.

## f. Finding taxonomy

The taxonomy below is CE-native. Each class is a vocabulary label a
reviewer writes into evidence — into `blocking_findings[].rule_violated`
for a blocking finding, or into the `non_blocking_findings[].observation`
/ `advisory_follow_up` text for an advisory one. **No taxonomy label is
a schema enum in this gate**; they are review vocabulary mapped into
the existing free-text and structured fields (see §g).

Default severity is the reviewer's starting posture, not a fixed
schema value. An advisory class **escalates to blocking** when the
same observation also constitutes a structural regression under §e; a
`structural_regression` defaults to blocking and de-escalates only
when the ratified envelope explicitly directs otherwise (§h).

| Finding class | What it names | Default severity |
|---|---|---|
| `structural_regression` | A behavior-correct change that worsens maintainability (the umbrella class of §e). | **Blocking** |
| `structural_simplification_opportunity` | A behavior-preserving reframing that would materially simplify the design; a recommendation, never a reviewer edit. | Advisory |
| `file_size_threshold_signal` | A file created or grown past a sane size threshold; an advisory signal calibrated so CE's own large files do not spuriously block, waiver recorded when accepted. | Advisory |
| `branching_growth_signal` | A net growth in control-flow branching in a changed unit; advisory unless it tangles a hot path. | Advisory |
| `spaghetti_branch` | An ad-hoc branch threaded into an otherwise coherent flow, raising the cost of the next change to that flow. | Advisory → blocking when a regression |
| `incidental_indirection` | A thin wrapper, indirection, or "magic" layer that adds reading cost without earning it; prefer the direct, boring form. | Advisory |
| `schema_boundary_looseness` | An over-permissive YAML schema: a missing `unevaluatedProperties: false`, an unbounded `additionalProperties`, or an enum widened without need, weakening a contract boundary. | Advisory → blocking when it loosens a governed boundary |
| `type_boundary_looseness` | An untyped or over-broad boundary in validator/runtime code (e.g., an unconstrained `Any`, a swallowed error type) that erodes a checked contract. | Advisory → blocking when it erodes a checked contract |
| `wrong_layer` | Logic placed outside its canonical layer (e.g., gate semantics inlined where a contract or helper should own them). | Advisory → blocking when a regression |
| `duplicate_helper` | A helper, predicate, or function reintroduced where a canonical one already exists; reuse the canonical layer. | Advisory → blocking when it diverges from the canonical one |
| `non_atomic_update` | A change that performs in several non-atomic steps what should be a single coherent update, widening the window for partial-state bugs. | Advisory |
| `avoidable_orchestration` | Needless sequential orchestration where a direct, single-pass form exists. | Advisory |

A reviewer MAY name a maintainability observation that does not fit a
listed class; it is recorded in the `findings` prose and, if it
blocks, mapped per §g with a descriptive `rule_violated` string. The
taxonomy is a floor, not a closed set.

## g. Mapping findings into the existing evidence record

This rubric adds **no** field to
[`../../schemas/review-evidence.schema.yaml`](../../schemas/review-evidence.schema.yaml).
Every maintainability observation maps into a field that already
exists:

1. **Narrative** → `findings` (free text). State the review depth
   applied (`maintainability_deep_review`), the units reviewed, and
   the per-class observations in prose.
2. **A blocking maintainability finding** → one `blocking_findings[]`
   entry:
   - `artifact_ref`: the repo-relative path (and unit) of the
     regression;
   - `rule_violated`: the taxonomy label (e.g.,
     `structural_regression`, `wrong_layer`) — written as the
     descriptive rule string, **not** as a schema enum value;
   - `recommended_remediation`: the recommended restructuring, framed
     as work for a **separate implementer envelope**, never a reviewer
     edit.
   Any `blocking_findings[]` entry forces `verdict:
   blocking_findings_present` and halts the batch
   ([`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §i).
3. **An advisory maintainability finding** → one
   `non_blocking_findings[]` entry:
   - `artifact_ref`: the path/unit;
   - `observation`: the taxonomy label plus what was seen;
   - `advisory_follow_up`: the suggested (non-blocking) follow-up.
4. **Cross-batch or deferred recommendations** → `recommended_follow_up`
   (free text): future slices, a separate refactor envelope, or a
   deferred objective-signal calibration.
5. The four-value `verdict` enum is unchanged. A maintainability deep
   review still emits exactly one of `no_blocking_findings`,
   `blocking_findings_present`, `scope_boundary_unclear`, or
   `cannot_review`, and it is **never** Source ratification
   ([`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §m.1).

## h. Waiver posture

1. **Advisory signals are waiver-able.** A `file_size_threshold_signal`,
   a `branching_growth_signal`, or any advisory class may be accepted
   without remediation when the ratified envelope records the waiver
   (the reason the signal does not block this batch). The waiver is
   recorded in the batch's Source-ratified envelope or in the evidence
   `recommended_follow_up`; it is not implied by silence and is not
   implied by a green test run.
2. **Structural regression defaults to blocking.** A
   `structural_regression` (§e) blocks unless the ratified envelope
   **explicitly** directs otherwise for the named batch, mirroring the
   independent-review waiver pattern in
   [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §c.4. The
   default is the block; the waiver is the exception and must be
   written down.
3. A reviewer **cannot** waive their own finding by re-grading it. Only
   the ratified envelope (Source authority) may direct that a
   structural regression not block; the reviewer records the finding
   and the verdict honestly either way.
4. Thresholds for the objective signals (file size, branching growth)
   are deliberately calibrated to advisory + waiver-recorded so that
   CE's own current tree, which contains legitimately large files,
   does not spuriously block delivery. A non-waiver-able hard
   threshold is **not** part of this rubric.

## i. Reviewer tone guidance

Maintainability findings are about the code, not the author. The
reviewer voice is:

1. **Direct.** Name the regression and the location plainly; do not
   soften a real block into a suggestion.
2. **Specific.** Cite the file, the unit, and the concrete structural
   cost (what the next change to this code now pays). A finding a
   reader cannot act on is not yet a finding.
3. **Evidence-backed.** Tie each finding to what is visible in the
   diff or the tree — the grown file, the added branch, the duplicated
   helper — not to taste. The `artifact_ref` and `findings` prose
   carry the evidence.
4. **Non-rude.** Critique the structure, never the person. Serious and
   exacting is the bar; dismissive or contemptuous is not. The goal is
   a more maintainable substrate, recorded in a form a separate
   implementer envelope can act on.

## j. Relationship to behavioral QA

Behavioral QA ([`./QA_STRATEGY.md`](./QA_STRATEGY.md)) asks **does it
work?**; maintainability deep review asks **is it well-structured?**
They are complementary and orthogonal:

1. A green QA / test result is necessary but **not sufficient**. It
   does not erase a structural-regression block (§e); the two gates
   are evaluated independently.
2. A maintainability block does not imply a behavioral defect, and a
   behavioral defect is not, by itself, a maintainability finding;
   each is recorded under its own gate.
3. Neither gate is Source ratification. QA evidence and review
   evidence are both advisory/governance evidence with no merge,
   deploy, branch-protection, or repository-settings authority.

## k. Provenance

This rubric is **CE-native**. Its principles were re-authored in
Creator Engine vocabulary; there is **no tracked dependency on any
external review skill or repository, and no verbatim external text is
copied into any tracked CE artifact.** The maintainability ideas are
expressed against CE's actual surfaces (Python validators, YAML
schemas, Markdown governance docs) and CE's authority model (reviewer
recommends or blocks, never self-authors). Any future verbatim reuse
of external material would require its own provenance review and is
out of scope; the closed-door posture is to author CE-native text.

## l. Acceptance posture

This document satisfies the docs/governance gate's
maintainability-deep-review-rubric requirements:

- States the purpose and the source-of-truth subordination to the
  governance review gate (§a, §b).
- States the reviewer boundary — recommend or block, **never
  self-author** the fix under reviewer authority (§c).
- Names the review depth `maintainability_deep_review` as prose /
  template vocabulary only, not a schema enum in this gate (§d).
- States the structural-regression rule: a structural regression can
  block even when tests pass (§e).
- Enumerates the CE-native finding taxonomy, including
  `structural_regression`, `structural_simplification_opportunity`,
  `file_size_threshold_signal`, `branching_growth_signal` /
  `spaghetti_branch`, `incidental_indirection`,
  `schema_boundary_looseness`, `type_boundary_looseness`,
  `wrong_layer`, `duplicate_helper`, and `non_atomic_update` /
  `avoidable_orchestration` (§f).
- Maps every finding into the existing `findings`,
  `blocking_findings`, `non_blocking_findings`, `verdict`, and
  `recommended_follow_up` fields without adding a schema field (§g).
- States the waiver posture: advisory signals are waiver-able when the
  envelope records the waiver; structural regression defaults to
  blocking unless the envelope explicitly directs otherwise (§h).
- States reviewer tone guidance: direct, specific, evidence-backed,
  non-rude (§i).
- Distinguishes behavioral QA from maintainability review and states
  that QA/test success does not erase a structural review block (§j).
- States the CE-native provenance with no tracked external dependency
  and no verbatim external text (§k).
