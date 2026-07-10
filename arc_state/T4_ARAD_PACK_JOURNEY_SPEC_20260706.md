# T4 SPEC — Arad pack journey-section upgrade — 2026-07-06 (Claude controller → Operator + codex pack session)

Scope: edits INSIDE tmp/arad-pack-0.3.3/ only (WELCOME_YOUR_CE_JOURNEY.md + the embedded HTML copy
+ INDEX/PACK_MANIFEST if section lists change). The pack territory belongs to the Operator's codex
session — this file is the spec, not an edit. Companion repo/site work is ticketed separately
(user-journey program T1/T2/T3 in ce-ops; the pack should NOT wait on those).

## Ratified constraints (2026-07-06 rulings — hard review bars, do not relitigate)
1. VOCAB: no "bet"/"appetite" anywhere (already clean — keep it that way). Ratify glossed as
   "approve the Scope". User-facing field names ONLY: Goal, Done-when, Budget, Change-type, Ready.
   Completion Report words: Outcome, Verdict, Next.
2. NO BUDGET FRONT-LOAD: the journey teaches the required trio Goal / Done-when / Change-type.
   Budget appears exactly once, as an opt-in aside at the end of the Scope section, lane-aware:
   "On a subscription? You can optionally cap a Scope at a share of your usage meter
   (--budget 20 --budget-unit % --budget-window rolling_5h). On API billing you can cap dollars
   (--budget-unit $). If you don't set one, CE uses safe defaults." Nothing more.
3. CLI-ANCHORED: every stage gets ONE canonical copy-pasteable command block (spec-kit style).
   Plain language = exploration only; state explicitly that governed work begins at the explicit
   verbs and the Scope record — not the chat — is the governing contract. `ce` never `cev3`.
4. PRODUCT LENS: zero internal refs (no ce-ops#, no fleet/seat jargon).

## Required content (order matters)
A. PRIMER (~1 paragraph, for users with NO method background): how CE turns an idea into
   software — "You describe intent → `ce shape` grills it into a Scope (Goal, Done-when,
   Change-type) → you `ce ratify` (approve) → `ce drive --spawn` builds it under CE's gates →
   you review the evidence → ship." Name the three human touchpoints: answer the shape
   questions, ratify, review. Everything else is CE's job.
B. STAGE MAP: Frame → Shape → Build → Review → Ship, one line each: what happens, what artifact
   it produces (Scope record / evidence / completion report), what's mandatory vs optional.
   Show the LOOP honestly: Review can send work back; big ideas become several Scopes.
C. DAILY FLOW with copy-pasteable blocks per step (the codex session's verified 0.3.3 surface):
   ce session → ce launch → explore in plain language → ce shape → ce scope <slug> --goal "…"
   --done-when "…" --change-type code → ce ratify <id> --approver-ref <…> → ce drive --spawn →
   ce report. Each block followed by one sentence: what you'll see, what exists afterward.
D. SCRUM→CE TABLE (Arad comes from Agile-Scrum): epic/story→Scope · sprint→Arc ·
   Definition-of-Done→Done-when · backlog→Ready Scopes · sprint review→completion report +
   evidence · product owner sign-off→ratify. One line note: CE keeps the value loop, drops the
   pace ceremonies (no sprints/velocity/standups).
E. EXISTING-PRD PATH (Arad's actual situation — she has a mythos PRD): put the PRD in the repo
   (docs/prd/…); it informs, never authorizes; create small Scopes citing it
   (--note "Source PRD: docs/prd/mythos.md"); the trading-terminal risk-slicing example already
   in the pack stays — verify it conforms to rulings 1–2 (no budget flags in its command lines
   unless in the opt-in aside).
F. WHAT CE NEVER DOES WITHOUT YOU: keep/strengthen the existing section; align its wording to
   the three-touchpoints framing from A.

## HTML-primary bars (Operator decision: the pack IS an interactive HTML bundle — "website" experience)
- The journey section must be first-class in index.html: in the nav/TOC, sectioned with anchors,
  readable without ever opening the .md sources (the .md files are source material; whether they
  ship in the bundle is a separate open Operator decision — envelope item 3).
- Command blocks must render as real code blocks that copy cleanly from the browser (no prompt
  prefixes like `$` that break paste; one command per block where feasible; a copy affordance if
  the renderer supports it cheaply — do not build JS machinery just for this).
- Verify in an actual browser render (the earlier truncated-bullets defect came from the renderer;
  same class of check applies to code blocks and tables here).

## Explicitly out of scope for the pack
- No duplication of full concepts material (that becomes the repo/site doc pair, T1); once T1
  ships, a later pack revision links it. For THIS send, the pack must stand alone.
- No slash-command/skill instructions for specific harnesses — CLI only.
- No changes outside the journey section + index/manifest consistency.

## Acceptance for the section (Operator preview bar)
A first-time subscription user with no Agile background can: explain CE's loop in one sentence,
run the daily flow by pasting blocks in order, knows exactly when CE will and won't act without
them, and never encounters "bet", "appetite", or a dollar budget.
