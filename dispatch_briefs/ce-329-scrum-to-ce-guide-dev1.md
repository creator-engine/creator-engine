# SEED BRIEF — ce-ops#329: Agile/SCRUM → CE spec-driven SDLC onboarding guide (public draft) — SEAT: dev-1

**Context:** New contributors/users coming from Agile/SCRUM need a public onboarding guide
mapping familiar SCRUM concepts → CE's spec-driven, ratification-governed SDLC. Draft it as
a public doc (product-lens: NO internal ce-ops# refs, NO internal host/seat identifiers
like dev-N/DGX/herdr, no confidential ecosystem names). Mark it clearly as a DRAFT pending
Operator sign-off before it's linked from the site (do NOT wire it into the site nav yet).

**Branch:** `ce-329-scrum-to-ce-guide` (off `origin/main`). **Role:** implementer. **Work class:** by floor.
**Repo:** creator-engine/creator-engine. Non-contained: self-push + open PR.

## Goal
Write `docs/guide/agile-to-ce-sdlc.md` (there may already be a stub by that name — check
`git show origin/main:docs/guide/agile-to-ce-sdlc.md`; if it exists, EXTEND it, else create).
Map: sprint→arc/wave, backlog→Projects board, story points→work-class (XS/S/M/L), standup→
async controller/seat flow, PR review→independent governed review + ratification, DoD→CI
gates + envelope authority. Ground every claim in CE's actual model (spec→plan→tasks,
carriers, changelog, ratification-not-CI). Keep it welcoming + accurate; product-lens clean.
If the repo renders guide HTML (siblings have .html), produce a matching `.html` render OR
note that rendering is a follow-up (do NOT break `test_site_index_docs_nav`).

## Scope — exactly these
- `docs/guide/agile-to-ce-sdlc.md` (+ its `.html` sibling IF you render it to match existing guides)
- `.ce/pr-manifests/ce-329-scrum-to-ce-guide.md` + `.ce/changelog/ce-329-scrum-to-ce-guide.md`
Docs only. Do NOT touch install.sh/downloads (signed release), code, or site nav wiring.

## Evidence / DoD
- FULL `ce validate-pr` GREEN one pass (TMPDIR=/var/tmp PYTHONPATH=validators; brain-drift reconcile if false-RED).
- Public-docs product-lens: grep your diff for `ce-ops#`, `dev-1/2/3/4`, `DGX`, `herdr`, `tailnet` → must be ZERO.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; push; open PR w/ declared-work-class line + "DRAFT — pending Operator sign-off" in the body. Do NOT approve/merge.
