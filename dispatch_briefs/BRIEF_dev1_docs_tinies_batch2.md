# BRIEF — dev-1 docs tinies batch 2 (foreman mode, 4 file-disjoint TINY units)

Role: implementer-foreman (dev-1, non-contained). Each unit: own worktree off FRESH origin/main,
own branch, own PR, own changelog fragment + path-manifest carrier, declared work class `tiny`.
You have gh + egress — use them for the referenced PR review threads. Dispatch units in parallel
worker threads; they are file-disjoint by design — keep them that way.

## MANDATORY first step per unit: semantic novelty check
Name the deliverable seam and verify against FRESH origin/main that it isn't already resolved —
especially vs freshly-merged #810 (docs: correct onboarding command guidance), #807, #811.
Bare keyword greps are not sufficient. If a unit's seam is already resolved on main, do NOT
open a PR for it; report `READY <branch> already-resolved` for that unit and move on.

## U1 — branch `ce-docs-cesession-framing`
Files: docs/guide/pilot-runbook.md + docs/guide/macos*.md ONLY.
(a) Fix the `ce session` framing on those pages: present session/launch per the terminal-first
product lens, consistent with the command-guidance pattern #810 just established on main.
(b) While in pilot-runbook.md: its brownfield answers example is missing the schema-REQUIRED
`answers_version: 1` key — a fresh tenant's first `--inventory` run refuses on it (live-canary
evidence today). Add the key to the example exactly as schemas/install-answers.schema.yaml demands.

## U2 — branch `ce-docs-quickstart-step-numbering`
File: the quickstart guide page ONLY. Seam: step numbering is inconsistent/broken after recent
edits — renumber coherently. If #810 already fixed it, already-resolved.

## U3 — branch `ce-801-installer-envvar-docs`
File: docs/contracts/installer.md ONLY. Seam: PR #801's independent review noted the installer
contract should ENUMERATE the environment variables the installer honors. Read #801's review
thread (`gh pr view 801 --comments` + review bodies) for the exact ask; implement that
enumeration, matching the contract page's existing conventions.

## U4 — branch `ce-docs-brownfield-answers-version`
File: docs/contracts/brownfield-adoption.md ONLY. Same `answers_version: 1` gap as U1(b) but in
the contract page's example snippet(s) (live-canary evidence: schema-required key absent from
the documented example). Fix all example snippets on that page.

## STOP lines (every unit)
⛔ docs/install.sh, docs/downloads/**, docs/llms-install.md are SIGNED release artifacts — NEVER
edit them; if a fix seems to belong there, report it instead (it rides the 0.3.2 re-sign ceremony).
⛔ Public docs = product lens: ZERO ce-ops#/internal-fleet references in any edited page.
⛔ No production code, no schema edits, no CLI changes (no generated-reference regen should be
needed; if a unit seems to require one, STOP and report — that means the unit is mis-scoped).
⛔ Never sign anything. No review/approve/merge/enqueue.

## Evidence bar (every unit)
Standing preflight directive: full `ce validate-pr` GREEN locally in ONE pass before every push —
do not discover gates via CI. Changelog + carrier per branch (carrier stem == branch slug).
Exactly one `- **Declared work class:** tiny` line in each PR body.
Signal per unit: `READY <branch> <40-hex sha> PR=<url>` (or `READY <branch> already-resolved`).
