# BRIEF — dev-3 — 2026-07-08 — 1 TINY unit: #888 post-merge hygiene batch (N1-N3)

Three non-blocking notes from the PR #888 approval (memory-layer slice, now MERGED on
main). COMMIT-ONLY: signal `READY <branch> <sha> <evidence-path>`; controller harvests.
Fresh /var/tmp worktree off origin/main (must contain merge commit of PR #888 — the
file validators/creator_engine_validator/brain_runtime.py must contain
`content_sha256`; if not, refetch, else BLOCKED-BASE). COMMIT PER ITEM;
PYTEST_ADDOPTS="-n 2".

## U1 — branch `ce-888-hygiene-n1n3` (work class: tiny)

N1 — brain_runtime.py `_resume_state_pointer` (~L1082-1091): the "newest" candidate
is selected by max of (content_sha256, path-string) — max-by-hash is NOT "newest".
Fix: primary sort key = str(path) (resume-state filenames encode timestamps by
convention), tiebreak by hash; add an inline comment stating the selection criterion
(lexicographic path == chronological by filename convention). Keep output fields
unchanged (content_sha256 stays).
N2 — test_brain_runtime.py `test_hydrate_contract_is_byte_identical_for_seeded_resume_state`:
add `resume_path.touch()` (or os.utime) between the two hydrate_contract() calls so
the first==second assertion genuinely pins the mtime→hash fix (it currently cannot
fail on the old code via that assertion).
N3 — same function: the sha256 is computed for the sort key then the file is re-read
to recompute it for the return dict — reuse the already-computed digest (single
read), eliminating the redundant read + TOCTOU window.

Update N1's behavior in any doc/comment that describes newest_resume_state selection.
EVIDENCE: changelog fragment `.ce/changelog/ce-888-hygiene-n1n3.md`; carrier
slug==branch, self-inclusive, `- **Declared work class:** tiny`; evidence summary with
test counts (the N2-touched test must PASS on new code — and note in evidence that
reverting N1's sort to the old hash-first order makes the new selection test fail, if
you add one; a small explicit selection-order test with two seeded resume files named
older/newer IS wanted).

Standing preflight directive (ce-ops#303): FULL local preflight before
commit-for-harvest (-n 2 cap; ENV-SKIP fallback with everything else green, the
controller re-runs host-side).

STOP LINE: brain_runtime.py `_resume_state_pointer` + its tests + changelog/carrier
ONLY. No schema changes, no takeover_runtime, no pushes/PRs/gate acts.
