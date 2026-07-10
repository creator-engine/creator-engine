# SEED BRIEF — ce-ops#402 + ce-ops#403 validator hardening batch (dev-3)

Two file-disjoint S tickets, one seat, TWO separate branches/worktrees — do not
mix their diffs. This brief is SELF-CONTAINED; do not attempt to read the
tickets. Everything you need is embedded below.

- **Role**: implementer (governed seat). Build, test, commit. You do NOT push,
  approve, merge, or touch any gate. Controller harvests.
- **Worktrees**: create under `/var/tmp` (NOT /workspace), one per ticket,
  branched off `origin/main` (fetch first; you have git egress — if fetch fails,
  say so in the done-report).
- venv has no activate — use `.venv/bin/python -m pytest`.
- **Standing preflight directive (ce-ops#303)**: run the FULL local validator
  preflight (`ce validate-pr`, CI-parity) before every commit-for-harvest; do
  not discover gates via CI. KNOWN ENV EXCEPTION on this host: the Install-spec
  signature guard fails because `ssh-keygen` is absent (ce-ops#400). That ONE
  failure is acceptable — record it verbatim in the done-report; every other
  gate must be GREEN. Controller re-runs the full preflight host-side at harvest.
- **Per-PR artifacts** (each ticket): `.ce/changelog/<branch>.md` fragment +
  `.ce/pr-manifests/<branch>.md` carrier regenerated via the carrier_gen API
  (CarrierSpec positional signature; fetch fresh main before regen; rm
  validators/build + egg-info first).
- **Done = commit SHA**: end each ticket with `git commit && git rev-parse HEAD`
  and put both SHAs in the done-report. A done-report without verifiable SHAs is
  not done. Emit `READY-FOR-HARVEST <branch> <sha>` per ticket when its full
  preflight (modulo the ssh-keygen exception) is green.

---

## Ticket 1 — ce-ops#402 (branch `ce-402-preflight-failclosed`, work class S)

**Title**: validate-pr baseline-diff gate can FALSE-GREEN when pytest is
unavailable (identical failure both sides = "zero new failures").

**Problem** (found during the ce-390 harvest 2026-07-02): running validate-pr
with a python that lacks pytest still reports PASS — the baseline-diff test
gate compares head vs baseline failure sets, and when the pytest subprocess
fails identically on BOTH sides (e.g. ModuleNotFoundError), the diff is empty
→ "zero new failures" → PASS. A harvest worktree without its own .venv
silently degrades to this false-green.

**Fix (fail-closed)**: the gate must assert the test run actually EXECUTED —
distinguish "tests ran and some failed" from "pytest missing or crashed"
(pytest exit codes: 0/1 = ran; 2/3/4 = interrupted/internal error/usage error;
5 = no tests collected; a nonzero collected-test count is the strongest
signal). FAIL the preflight when either side's run is invalid (did not execute
or collected zero tests). Also add one line to the authoring/contract doc the
gate already cites: invoke validate-pr via the repo venv python.

**Where**: the baseline-diff gate lives in
`validators/creator_engine_validator/pr_preflight.py` (see also
`grading_spine.py` if the diff logic is shared). Allowed paths: that module,
its unit/integration tests, one doc line, changelog+carrier. Add tests: (a)
pytest-missing on both sides → preflight FAILS with an actionable message;
(b) zero-collected on one side → FAILS; (c) genuine identical failures on both
sides (tests really ran) → still passes as today.

## Ticket 2 — ce-ops#403 (branch `ce-403-scanner-hardening`, work class S)

**Title**: confidentiality-scanner hardening — pooled NOT-BLOCKING findings
from the #738 two-review quorum. Target module:
`validators/creator_engine_validator/public_docs_confidentiality.py` + its two
test files.

1. **ALLOWED_OFFENSES shrink-only ratchet**: no staleness enforcement today —
   a deleted file's (path, token-class) entry sits inert and would silently
   exempt a future re-created file at that path. Add the analogous
   only-shrinks test that KNOWN_PENDING already has. NOTE: seed the snapshot
   from CURRENT origin/main (entries were added as recently as PR #738's
   merge-group reconcile) and drop entries whose files no longer exist.
2. **Stat-level fail-closed**: `Path.is_file()` swallows OSError (~line 390) —
   a tracked file unreadable at the STAT level silently skips instead of
   failing closed; only read-level failures are covered today.
3. **Empty-scan floor**: an empty tracked-file list passes green — add a
   minimum-scan-floor sanity check so "scanned nothing" cannot read as "clean".
4. **Missing tests**: duplicate issue:-line collision; git ls-files subprocess
   failure path.
5. **NIT**: remove the dead `public_doc_files()` compat alias (no callers).

**Stop line (both tickets)**: no changes outside the named modules/tests/doc
line/changelog/carrier. No edits to check registry semantics, no new CLI
surface, no gate-adjacent files (queue daemon, approval wall). If a fix seems
to require touching anything else, STOP that ticket and report instead.
