# CE Work-Management Reality Map — 2026-06-30 (grounded audit)

Input for the work-management TERMINOLOGY CANON synthesis (Operator-requested, do next window w/ fresh context — same shape as the tier canon). Full audit in agent a9934556ce56cce12 transcript.

## The flow (as-is) — opened → classified → backlog → arc → worked
1. **Open:** ALL ce-ops issues opened by `ce-overwatch` (controller). No enforced template (intake contract `docs/contracts/github-issue-intake.md` exists but is "documentation-only, NOT wired"). Seats can't open issues.
2. **Classify (controller, at creation, guided by v3.5-roadmap CRIT/DEFER):** labels + milestone. The `ce-triage` bot (ce-forge-dev-2[bot]) auto-applies on issue events.
3. **Backlog = GitHub Issues under the Sept milestone** (`ce-ops/backlog/README.md` says so literally). No separate system. `ce_triage/` (ce-ops workflow) computes an ADVISORY ready-queue (pinned on ce-ops#67) from `Depends-on/Gated-on` trailers; `forge_triage.py` (creator-engine validator) filters pickup by `ce-pickup/triage-ready` (applied MANUALLY).
4. **Arc lane assignment = 100% controller HAND-CURATION.** No automated promotion from backlog→arc. **This is why #37 vanished:** DEFER (no milestone) + no pickup label + not hand-pulled = invisible by default.
5. **Dispatch:** controller → seat; `work_claims.py` records a local claim (NOT reflected in GitHub).

## Classification = 3 ORTHOGONAL axes (key insight)
- **Type** — issue label (`user-story`, `pitch-arc`, `process`, `[research]`, `[finding]`…). Product/intent kind.
- **Priority/schedule** — `pitch-critical` label + the single milestone **"Sept NVIDIA pitch"** (the ONLY milestone; CRIT→milestone, DEFER→none per v3.5-roadmap §4a).
- **Work-class** — `tiny/story/feature/epic` = PR-DIFF-SIZE gate (`work_sizing.py`/`work_sizing_floor.py`; tiny<400, story 400-799, feature 800-1000, epic>1000). PR-level, enforced by validate-pr. **ORTHOGONAL to issue labels.**

## ⚠️ OVERLOADED TERMS (the canon problem — bigger than expected)
| Term | Conflicting meanings |
|---|---|
| **story** | `user-story` LABEL (product intent) vs `story` WORK-CLASS (400-799 line diff). Same word, different namespaces. |
| **Lane** | (1) persistent ce-ops **Lane issues #1-#7** (design programs: Cockpit-B, v3.5-E/F/G, v4, strangeLoop, Determinism) vs (2) arc-internal **L1-L7** work segments (hand-curated per shift). |
| **Roadmap** | (1) `ce-ops/roadmaps/v3.5-roadmap.md` = PROGRAM PLAN (real SSOT for "what we build") vs (2) `creator-engine/docs/product/ROADMAP.md` = Feature 001-006 governance spec vs (3) `forge_triage.py` "roadmap" = a blocker/aggregate label class. |
| **Wave** | arc-internal Wave 0-3 (hours) vs v3.5-roadmap Wave A-D (months). |
| **Triage** | `ce_triage/` (ce-ops advisory ready-queue workflow) vs `forge_triage.py` (creator-engine validator pickup planner) vs `triage-ready` label. |
| **Backlog** | informal — "all open issues" / "issues under Sept milestone"; no formal object. |

## SSOT GAP (the core finding)
**No single SSOT for the work-management PROCESS** (analogous to `infra/identity-registry.yaml` for topology). Partial/overlapping authorities: v3.5-roadmap.md (workstreams+CRIT/DEFER+milestone-rule, NOT arc lanes), GitHub Issues+milestone (live state), `.ce/state/research/DAYARC_MANDATE_*` (per-arc grants+lanes), issue-intake contract (creation only), backlog/README (just a redirect). **No doc defines the end-to-end flow.** Also: a GitHub **Projects v2 board** (org project 1; Status=Done/In-review/In-flight/Queued/Post-pitch, Anchor=Sept-pitch/v3.1-pilot/Both/v4) EXISTS but currency unknown.

## Canon synthesis seed (my hypothesis to refine w/ Operator)
- **3 nested horizons:** Roadmap (strategic, months) → Arc (execution shift, hours-days) → Ticket (unit). Name + disambiguate each.
- **Separate the 3 classification axes** cleanly + rename to kill the `story` collision (e.g. issue-type "user-story"→"product-story" or work-class "story"→"S/M sizing").
- **Disambiguate Lane (program vs arc-segment), Wave (phase vs batch), Roadmap (program-plan vs feature-spec vs label), Triage.**
- **Define Backlog + Lane + the promotion mechanism** as first-class (close the #37 hole; ce-ops#376 sweep hangs off this).
- **Write a work-management process SSOT** (e.g. `ce-ops/process/work-management.md` or extend v3.5-roadmap) — the missing layer.
- Decide whether the **Projects v2 board** is the live SSOT for ticket-status (and keep it current) or retire it.
