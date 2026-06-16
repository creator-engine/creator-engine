---
slug: ce99-p1-devops
date: 2026-06-16
kind: added
scope: v3 forge / repo-scope devops automation
issue: creator-engine/ce-ops#99
base: bcf84649ab6343784bd1aa45690f32ded21ba339
---

P1 of ce-ops#99 adds plan-by-default, unit-tested repo-scope GitHub
devops operations to the v3 forge layer.

- Added repo ruleset upsert/delete operations with `bypass_actors` limited to
  GitHub App `Integration` actors using `bypass_mode: pull_request`; the
  ruleset requires one approving review and does not require CODEOWNERS review.
- Added independent reviewer App approval submission using only
  `pull_requests:write`, with GitHub 422 self-approval failures surfaced
  fail-closed.
- Added GraphQL per-PR auto-merge enablement plus a separate repo-level
  `allow_auto_merge` toggle.
- Added operation token bindings in `v3_forge_join`: merge uses
  `contents:write` only, repo configuration/rulesets use
  `administration:write`, reviewer approval uses `pull_requests:write` only,
  and per-PR auto-merge uses `contents:write` plus `pull_requests:write`.
- Wired new `cev3`-only verbs: `configure-repo`, `ruleset`,
  `review-submit`, and `auto-merge`.
- Rebuilt the validator app wheel and refreshed `validators/wheelhouse/SHA256SUMS`.

Live `apply=True` calls remain runnable but are integration-gated outside this
unit-test PR.
