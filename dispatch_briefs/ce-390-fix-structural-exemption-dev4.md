# CORRECTION BRIEF — ce-ops#390 (dev-4): structural carrier-frontmatter exemption

Your ce-390 branch (76b1e5834) harvested clean but FAILED controller preflight
against current origin/main: 4 carrier pairs merged after you branched
(ce-320/361/376/388) trip the widened scan on their `issue: ce-ops#N` changelog
frontmatter and `# PR path manifest — ce-ops#N` header — and so does this PR's
OWN carrier. Root cause is design, not drift: a STATIC allowlist snapshot cannot
chase files that every future PR generates by construction.

## Fix (controller decision — implement exactly this, option b)
Replace the per-file allowlist entries for routine carrier metadata with a
STRUCTURAL exemption, per the already-ratified convention ("changelog
frontmatter Refs/issue line = the allowed exception"):
1. In public_docs_confidentiality.py: for files under `.ce/changelog/**`, exempt
   ONLY the `issue: ce-ops#N` frontmatter line (and the filename itself) from
   the ce-ops#/ce-ops- ticket-ref patterns; for `.ce/pr-manifests/**`, exempt
   ONLY the `# PR path manifest — ce-ops#N` header line and filename. Everything
   ELSE in those files stays scanned (a real secret in a changelog body must
   still fail). Narrow, line-anchored, fail-closed on any parse ambiguity.
2. Shrink _ALLOWED_OFFENSE_ROWS: remove every entry now covered by the
   structural exemption; keep genuinely file-specific entries.
3. Add tests: (i) carrier pair with routine frontmatter → PASS with empty
   allowlist; (ii) changelog with a ticket-ref in its BODY prose → FAIL;
   (iii) pr-manifest with an extra ce-ops ref beyond the header → FAIL.
4. Recommit to the SAME branch. Run the full local preflight (your origin/main
   is stale — the controller re-verifies against fresh main at re-harvest, so
   note any allowlist entries you cannot verify). Emit
   READY-FOR-HARVEST <sha> when green locally.
Stop line unchanged: no push, no other files, no scope growth.
