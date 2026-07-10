# CORRECTION 2 — ce-390 (dev-4): accept repo-qualified carrier ticket-ref form

Controller re-harvest of 219b6a40d went RED on ONE structural gap: your exemption
regexes anchor bare `^issue: ce-ops#\d+$` / `^# PR path manifest — ce-ops#\d+`,
but main also carries the repo-qualified form (`issue: creator-engine/ce-ops#385`
etc.). Census on current main: 319 bare-form + ≥7 qualified-form carriers
(ce-385, docs-agile-to-ce-sdlc, ceops95, ce149, ce99…) — both forms are live, so
the structural exemption must accept both. Controller decision:

1. Widen ONLY the structural-exemption anchors to `^issue: (creator-engine/)?ce-ops#\d+$`
   (and the manifest header + any slug/self-reference equivalents) — keep the
   line-anchored, sole-occurrence discipline exactly as-is. Do NOT widen the
   detection patterns themselves.
2. Add tests: qualified-form changelog frontmatter + qualified-form manifest
   header both PASS with empty allowlist; qualified-form ref in BODY prose still FAILS.
3. Recommit same branch, local preflight (your main is stale — controller
   re-verifies), READY-FOR-HARVEST <sha>.
