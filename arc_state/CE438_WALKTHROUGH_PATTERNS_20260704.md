# ce-ops#438 Phase-1 Research — Getting-Started/Walkthrough Patterns (2026-07-04)
> Architect-research deliverable. Sources: spec-kit spec-driven.md (raw fetch), BMAD
> docs.bmad-method.org/tutorials/getting-started/ + /explanation/analysis-phase/, and direct reads
> of CE's docs/guide/* + stage-vocabulary.md + onboard docstrings. Full detail below is the
> worker's report, controller-annotated.

## Reference verdicts
- **BMAD getting-started = the structural model.** Promise-first opening → do-first escape hatch
  (bmad-help) → concepts → full path. Table-driven vocabulary (4 tables incl. terminal Quick
  Reference). Daily loop ("The Build Cycle") structurally separate from one-time setup. Two-tier
  progressive disclosure (tutorial links out to concept pages; verified on analysis-phase page).
  Honest caveats ("Story counts are guidance, not definitions") + Common Questions FAQ. ~2,800
  words, heading depth 4, only 2 code blocks — pedagogy rides on tables.
- **spec-kit spec-driven.md = cautionary contrast.** ~6,000-word concept-first manifesto; zero
  tables; worked example only at §7 (12h-vs-15min comparison, not followable); no caveats; trust
  via constitutional rhetoric not evidence. Reject as structure; our audience = ease-first.

## 12 transferable patterns (abbrev.)
1 promise-first opening (B) · 2 vocabulary TABLES not prose (B) · 3 daily-loop vs setup separation
(B) · 4 tutorial→concept link-out disclosure (B+B') · 5 honest caveats + FAQ (B) · 6 repeating
per-step microstructure what-you-do/what-CE-does/what-you-see (CE's own docs) · 7 ONE continuous
worked example (CE's solo-dev-onboarding + first-value doc; BMAD lacks!) · 8 rendered transcript
trust devices (CE Completion Report blocks) · 9 irreducible-gestures who-decides table (CE mode
docs) · 10 link-out discipline (CE welcome→understanding→runbook chain) · 11 BMAD-correspondence
bridge (stage-vocabulary.md has it; reader-facing docs don't yet) · 12 step time-estimates: in
NEITHER reference; CE would originate — and it tensions with Budget≠time-estimate doctrine.

## 5 anti-patterns in CE docs today
1. welcome.md "Where to go next" still RECOMMENDS getting-started-step-by-step.md which
   self-labels as retired spec-kit legacy (front door → dead doc).
2. Vocabulary tables duplicated near-verbatim across solo-dev + solo-ceo onboarding docs.
3. No single continuous REAL example packaged as reader-facing pedagogy (rate-limit-login =
   synthetic; first-value doc = real but operator/env-var voice).
4. Zero honest-caveats/FAQ device anywhere in onboarding docs.
5. Zero time estimates (see pattern 12 tension — address head-on in FAQ, don't fabricate).

## Proposed outline (9 sections, ~2,600-3,000 words)
1 The promise (~150) · 2 Get running, compressed + two-rails callout + hard link-outs (~250) ·
3 Meet the loop: five-word table + BMAD bridge (~300) · 4 THE WORKED EXAMPLE: one ticket through
Frame→Shape→Build→Review→Ship, per-phase you/CE/what-you-see with rendered Scope card +
Completion Report; explicit Review/Ship-is-external-grading differentiator (~900-1100) · 5 Daily
loop, mode-agnostic w/ one branch note (~300) · 6 Irreducible-gestures table, single canonical
(~150) · 7 Honest caveats/Common questions incl. Budget≠time (~250) · 8 Under-the-hood dig-in
links only (~200) · 9 Where-next routing (~100).

## Title recommendation
"Complete Walkthrough" — avoids collision with retired legacy getting-started doc; accurate to
full-journey scope; welcome.md link text stays true with one-line target swap. "Getting Started"
defensible ONLY if legacy file is retired in the same change.

## Controller answers to worker's open questions
- Q5 (bmad-help equivalent): `ce ask` exists (support-agent foundations landed; docs-as-skills
  grounded) — the walkthrough SHOULD name it as the escape hatch; mutually reinforcing.
- Remaining Shape questions → Operator: legacy-doc fate; worked-example mode (rec: Dev mode, CEO
  branch-noted) + source (rec: synthesized-realistic in reader voice, transcript structures
  borrowed from the real run; genericize any tenant specifics); title; time-estimate policy
  (rec: no fabricated times; FAQ addresses why, per Budget doctrine).
