---
slug: ce160-rulesets-protection-floor
date: 2026-06-20
kind: fixed
scope: v3 forge / onboard apply protection floor
issue: ce-ops#160
base: b25e57b3bf1239c83a34837d90312f15f1d82e6f
---

Apply the CE protection floor on Free-plan private repositories by falling back
from classic branch protection to repository Rulesets when GitHub rejects the
classic API for plan/capability reasons.

- Extended repo Ruleset policies to carry the CE validate required check, strict
  up-to-date enforcement, stale-review dismissal, required review count, and an
  empty bypass actor list.
- Preserved the classic branch protection path for repositories where it is
  available, with a clear surfaced fallback message when the classic PUT is
  plan-unsupported.
- Added a separate squash-only repo merge-method operation and wired the
  onboard protection leg to verify/apply the schema's `squash_only` floor.
- Taught the live apply driver to recognize an already-governed repo through
  either classic protection or the named CE Ruleset floor.
- Added focused unit coverage for the Ruleset payload, classic-to-Ruleset
  fallback, squash-only settings, and live Ruleset detection.
