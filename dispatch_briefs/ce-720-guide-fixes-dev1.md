# SEED BRIEF — Fix review findings on PR #720 (Agile/SCRUM→CE guide) — SEAT: dev-1

**Context:** Your PR #720 (branch `ce-329-scrum-to-ce-guide`, docs/guide/agile-to-ce-sdlc.md rewrite)
got REQUEST_CHANGES from governed review. Confidentiality/product-lens passed CLEAN. Two BLOCKING
findings must be fixed on the SAME branch (push updates the PR):

**Blocker 1 — restore CE's canonical stage vocabulary.** `docs/architecture/stage-vocabulary.md`
(Frame → Shape → Build → Review → Ship) is CE's locked canon and every sibling guide references it
(welcome.md, understanding-ce.md, solo-ceo-onboarding.md, solo-dev-onboarding.md, pilot-runbook.md,
getting-started-step-by-step.md, contributing-to-ce.md). The new guide never mentions those stages,
never cites stage-vocabulary.md, and has ZERO markdown links to any other doc — it introduces a
parallel disconnected vocabulary (`spec -> plan -> tasks -> implementation -> ...`, ~lines 33-34).
Fix: anchor the SCRUM mapping to the five canonical stages (as the PREVIOUS version of this same
file did), cite stage-vocabulary.md, and add the natural cross-links (welcome, understanding-ce,
contributing-to-ce) so a first-time reader gets ONE vocabulary with a bridge, not two.

**Blocker 2 — the "unlinked draft" banner is false.** Lines ~3-7 and ~233-241 claim the guide "stays
unlinked until Operator sign-off". In reality the file is ALREADY linked from published pages:
docs/guide/welcome.md:206, solo-ceo-onboarding.md:259 (+ its rendered .html), solo-dev-onboarding.md:277
(+ .html). Merging makes this content live at those entry points immediately. Fix: remove/replace the
false banner premise — keep a simple "Draft — content pending final Operator review" note if desired,
but do not claim non-linkage; do NOT edit the other pages (out of carrier scope).

**Non-blocking (apply if cheap):** (a) "Arc"/"wave" terms appear nowhere else in docs/ and may be
stale vs the ratified work-management canon — prefer neutral wording (e.g. "batch of work") over
inventing hierarchy terms; (b) the claim that EVERY unit of work has a written spec+plan overstates
the tiered model (docs/contracts/work-sizing-tiers.md: XS=scope_card, S=intent+scope+tasks, M=full
spec/plan/tasks) — add a one-line caveat.

**Branch:** `ce-329-scrum-to-ce-guide` (existing — fetch and continue it). **Role:** implementer.
**Obligations:** carrier `.ce/pr-manifests/ce-329-scrum-to-ce-guide.md` must still match base..HEAD
(same 3 paths unless you must touch more — avoid it). Update the changelog fragment if the summary
changes. Run the FULL local validator preflight (`ce validate-pr`, CI-parity) before self-push; do
not discover gates via CI. Self-push to the same branch (updates PR #720), echo the commit SHA.
