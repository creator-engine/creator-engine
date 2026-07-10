# BRIEF — dev-3 — review-analysis of PR #864 (dev-4's ce-ops#426 G11: in-launcher reviewer-authority envelope minting). Read-only, verdict-only, safe concurrent with your builds.
2026-07-06 ~14:1xZ by CE-DEV-2. Framing: this is DEFENSIVE GOVERNANCE review — the feature mints scoped reviewer-authority envelopes so parallel multi-tenant reviewer dispatch stays inside CE's authority model.

Mechanics: `git fetch origin pull/864/head:review-864`, throwaway worktree, baseline STRICTLY `git show <merge-base>:<path>`. Head b5af03c879359c24406c7b08ef88a2e29820f7cc; files: ce_cli.py, lane_runtime.py, test_lane_runtime_reviewer_venue.py, docs (GOVERNED_LANE_LAUNCH_PROTOCOL.md, cli.generated.md), changelog, carrier. Class story.

Embedded ticket context (you can't read ce-ops): ce-ops#426 [G11] per design-gap register ratified #421 — REVIEWER_VENUE_AUTHORITY.md (in-tree, READ IT — it is your bar) names in-launcher minting as out of scope of the current gate; multi-tenant parallel review needs it productized. The unit added `ce lane launch --mint-reviewer-authority`.

Your bars, gate-adjacent so be strict:
1. AUTHORITY SCOPE: the minted envelope must be bounded — reviewer venue only, no approval/merge/gate capability, TTL'd or single-use, never a standing grant. Any path where the envelope could authorize beyond independent review = REQUEST_CHANGES.
2. Author/approver separation intact: nothing lets a seat mint authority to review ITS OWN work.
3. Consistency with REVIEWER_VENUE_AUTHORITY.md's stated invariants — quote any it violates.
4. Test substance: failure-direction proven (minting refused where policy says refuse).
5. Scope/class sanity; docs accurate.
Emit exactly: `VERDICT-864: APPROVE` or `VERDICT-864: REQUEST_CHANGES` + numbered evidence.
