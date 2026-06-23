---
slug: ce-forge-rebase-dismiss-fix
date: 2026-06-23
kind: fixed
scope: forge ruleset adapter (ce-reference-protection-floor emission)
issue: creator-engine#368, ce-ops#151
---

**Stop the CE-emitted repo ruleset from blanket-dismissing standing approvals on
every push (incl. pure rebases), which silently overrode branch-protection
`dismiss_stale_reviews=false`.**

The `ce-reference-protection-floor` repository ruleset was emitted with GitHub's
blunt `dismiss_stale_reviews_on_push: true`. That flag is NOT diff-aware: GitHub
wipes EVERY standing review on ANY head-changing push, including a mechanical
rebase that carries no net content delta. Because rulesets layer on top of
classic branch protection (most-restrictive wins), this override silently
defeated the repo's `dismiss_stale_reviews=false` and dismissed dev-3's APPROVED
review on each rebase force-push of creator-engine#368 (review_dismissed by
`ce-forge-dev-2[bot]`, `dismissal_message: null` — the native-ruleset signature),
leaving `reviewDecision=REVIEW_REQUIRED`. This breaks CE's
rebase-preserves-approval doctrine ([[ce-base-only-refresh-microauth]],
ce-ops#151) and would tax the planned Integrator agent (ce-ops#216).

- **`forge/ruleset.py`** — `RulesetPolicy.dismiss_stale_reviews_on_push` now
  defaults to `False`. CE no longer emits GitHub's blunt dismissal flag;
  re-review-on-content-change is a CE-owned, diff-aware concern (the
  `forge.re_review` lane / ce-ops#151) that dismisses only when the actual diff
  changes and never on a pure rebase. A caller that genuinely wants GitHub's
  blunt behavior may still pass `True`.
- **`forge/github_repo_config.py`** / **`onboard_apply_live.py`** — the two
  ruleset-emit sites no longer propagate the branch-protection
  `dismiss_stale_reviews` floor into the blunt ruleset flag. The classic-
  protection PUT still carries the floor flag (it is governed separately); only
  the ruleset stops blanket-dismissing.
- **`tests/unit/test_ruleset.py`** — regression coverage: the default policy
  emits no blanket-dismiss flag; a rebase-safe live ruleset (flag off) still
  SATISFIES the default policy; and an explicit opt-in (`True`) still emits the
  blunt flag for callers that want stricter content-change re-review.

NOTE (deployed remediation, out of band): this source change fixes future
emission. The ALREADY-LIVE `ce-reference-protection-floor` ruleset on
`creator-engine/creator-engine` (id 17946690) must be updated to set
`dismiss_stale_reviews_on_push=false` to stop the live dismissals — see the PR
description for the exact `gh api` remediation. No wheel rebuild is required: the
validator is built from source (no committed `creator_engine_validator-*.whl` in
`validators/wheelhouse/`); the SHA256SUMS there cover only third-party deps.
