# BRIEF — ce-npm-path-fix — PATH fixup corrupts $PATH on npm>=9 (PARALLEL TINY UNIT, dev-1)

Role: implementer (dev-1, self-push, foreman mode). PARALLEL tiny unit — file-disjoint from all
your other units; thread it whenever convenient. Branch `ce-npm-path-fix` off fresh origin/main.

## Bug (live canary evidence, 2026-07-05, VPS npm 9.2.0)
validators/creator_engine_validator/ce_profile_path.py:67-76 emits a ~/.profile block running
`npm bin -g 2>/dev/null`. npm >= 9 REMOVED `npm bin` and prints `Unknown command: "bin"` to
STDOUT, so the redirect doesn't suppress it — the error text lands in `_ce_npm_bin` and is
prepended to $PATH, corrupting it (`PATH=Unknown command: "bin" ... npm help:...`). Consequence:
a tenant's npm-installed claude/codex CLI is never discovered; launch fails exit 127 surfaced only
as `single-controller assertion failed: 0 live controller(s)`.

## Deliverable
Fix the emitted snippet to be npm-version-proof: use `npm prefix -g` (stable across npm versions,
append `/bin`; on Windows-style prefixes not our target) or equivalent; validate the result is an
existing directory before prepending; never prepend anything containing whitespace/newlines that
isn't a real dir. Regenerate/refresh logic: ensure an install that previously wrote the broken
block gets the corrected block on upgrade (the block is CE-managed/delimited — verify the rewrite
path replaces it). Tests: unit tests pinning the emitted snippet (no `npm bin` anywhere; dir-exists
guard present) + a behavioral test simulating an `npm` stub that prints `Unknown command` on
stdout and proving $PATH stays clean.

SEMANTIC NOVELTY CHECK FIRST: confirm `npm bin -g` is still in ce_profile_path.py on fresh main.

## ADDENDUM — NOVELTY STOP REJECTED (controller, with evidence)
Your already-resolved signal is incorrect. Main's build_path_block (lines ~67-74) DOES have an
`npm prefix -g` fallback — but it is UNREACHABLE on npm>=9: `_ce_npm_bin="$(npm bin -g 2>/dev/null
|| true)"` captures the `Unknown command: "bin"` error text from STDOUT (npm>=9 prints it there),
so `_ce_npm_bin` is non-empty garbage, the `[ -z ]` fallback branch never fires, and
`_ce_path_prepend` (which has NO directory-exists guard — read it, lines ~53-58) prepends
multi-line garbage into PATH. This exact corruption was captured live on a clean VPS install
(npm 9.2.0) this morning: PATH began with `Unknown command: "bin" ...`. The semantic bar is "does
a tenant on npm>=9 get a clean PATH?" — the answer on main is NO. Reproduce it yourself with an
npm stub that prints `Unknown command: "bin"` to stdout and exits 1, then fix:
1. Drop `npm bin -g` entirely — derive from `npm prefix -g` (append /bin) as the primary.
2. Add a directory-exists guard to _ce_path_prepend (`[ -d "$1" ]`) so no future garbage can
   corrupt PATH regardless of source.
3. Managed-block refresh on upgrade + tests as originally briefed (snippet pins: no `npm bin`
   anywhere; stub-npm behavioral test proving PATH stays clean).

STOP lines: only ce_profile_path.py + its tests + changelog/carrier; never sign; no
review/approve/merge.
Evidence: full validate-pr GREEN one pass; work class tiny.
Report: `READY ce-npm-path-fix <40-hex sha> PR=<url>`.
