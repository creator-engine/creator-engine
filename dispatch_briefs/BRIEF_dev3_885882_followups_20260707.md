# BRIEF — dev-3 — 2026-07-07 ~19:4xZ — 1 unit: #885+#882 follow-up batch (tests + polish)

Ticket substance embedded (you cannot read ce-ops). COMMIT-ONLY unit (your broker
self-push is a known env gap: CE_EGRESS_BROKER_SOCKET unset): when done signal
`READY <branch> <sha> <evidence-path>`; the controller harvests. Worktree: fresh
/var/tmp checkout off origin/main. BASE PRECONDITION: your base MUST contain merge
commit bd5b1f837f8030fd030c4e72883c4aeb6728c625 (PR #885, the onboard workflow-refresh
lane) — `git merge-base --is-ancestor bd5b1f837f8030fd030c4e72883c4aeb6728c625 HEAD`
must pass; if not, fetch again; if still absent, signal BLOCKED-BASE and stop.

## U1 — branch `ce-885-882-followups` (work class: story)

GOAL: close the five non-blocking follow-ups recorded in the #885 and #882 approval
verdicts. All five are small, test-heavy, and independent; land them as ONE commit
series on one branch.

From PR #885 (files: validators/creator_engine_validator/v3_cli.py,
onboard_apply.py, onboard_apply_live.py; tests validators/tests/unit/test_onboard_apply.py):
1. `--spec` is silently ignored when combined with `--refresh-workflow` — add an
   explicit refusal (or a help-text note + warning) so the combination is not silent;
   pin with a unit test.
2. The human-readable write-failure line swallows subprocess stderr — surface
   `proc.stderr` (trimmed) in that message; pin with a unit test.
3. Add the not-a-CE-file refusal test: the refresh lane must refuse to overwrite a
   `.github/workflows/ce-validate.yml` that does NOT carry the three CE identity
   markers (this data-protection safeguard exists in code but has no explicit test pin).

From PR #882 (the brain-ledger tail-freshness gate; find its exact modules via
`git log --oneline origin/main | grep 882` then `git show <sha> --stat`):
4. Add the explicit fail-closed unit test: an unprovable tail (base fetch impossible /
   comparison base missing) must yield ok=False / rc 1 — never a silent pass.
5. Add the explicit fast-path assertion: a PR whose diff does not touch the ledger
   takes the zero-overhead path (gate returns ok without hashing).

SCOPE: the files above + the #882 test module(s) + `.ce/changelog/ce-885-882-followups.md`
+ `.ce/pr-manifests/ce-885-882-followups.md` ONLY. Do NOT touch brain runtime/append
modules (validators/creator_engine_validator/brain_*, takeover_runtime.py,
test_brain_runtime.py logic beyond appending new test functions,
test_ce_takeover_cli.py) — an in-flight PR (#488) owns that territory tonight; if
item 4/5's natural home is a file #488 touches, append-only test functions are
acceptable (expect a trivial rebase at harvest).

EVIDENCE: carrier slug==branch, self-inclusive, `- **Declared work class:** story`;
changelog fragment; evidence summary file with test counts.

Standing preflight directive (ce-ops#303): run the FULL local validator preflight
(`ce validate-pr`, CI-parity) before commit-for-harvest; do not discover gates via CI.
Known env gap: if (and only if) the ssh-keygen-missing image gap blocks a preflight
step, record it explicitly as ENV-SKIP with everything else green — the controller
re-runs full preflight host-side at harvest.

STOP LINE: no pushes, no PRs, no gate acts, no files outside SCOPE, no signing. If
any instruction here conflicts with repo state, signal BLOCKED with one line of why.

## POST-CRASH ADDENDUM (2026-07-07 ~21:2xZ — this is re-dispatch after a host OOM killed your predecessor mid-unit)
- COMMIT EARLY AND OFTEN: your container filesystem lives in MEMORY (runsc overlay);
  an OOM loses everything uncommitted AND unextracted. Commit each completed item
  (1..5) separately as you go — do not batch everything into one end-commit.
- MEMORY CAP: the OOM trigger was the full pytest suite. Run all pytest/validate-pr
  steps with `PYTEST_ADDOPTS="-n 2"` (capped xdist workers). If the full preflight
  still gets OOM-killed, fall back to the focused test modules you touched + declare
  ENV-SKIP for the full suite (controller re-runs it host-side at harvest).
- Your broker socket env is now live, but this unit stays COMMIT-ONLY as briefed —
  do not self-push.
