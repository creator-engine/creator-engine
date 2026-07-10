# BRIEF — ce-ops#410 slice 9: promote validation_ledger_binding into the armed required-seam list

Role: implementer. Claim: ce-410-s9-ledger-binding-seam. Branch: `ce-410-s9-ledger-binding-seam`
off CURRENT origin/main. GATE: verify the 8c merge is in your base first:
`git grep -q 'refusing to land unverified tree' origin/main -- validators/creator_engine_validator/conveyor_daemon.py`
— if absent, signal `BLOCKED ce-410-s9-ledger-binding-seam base-missing-8c` and stop.

## Context (self-contained)
The armed conveyor daemon refuses construction unless every required safety seam is injected
(the armed-seam refusal list in ConveyorDaemon.__init__, conveyor_daemon.py ~:366-387: git_runner,
gh_runner, now, ledger_writer, path_allocator, repo_root, bundle_root, daemon_lease,
receipt_issuer). The 8c changelog carries this slice's obligation verbatim: "slice 9 must promote
`validation_ledger_binding` into the armed required-seam list." Today validation_ledger_binding
is optional on the armed path; slice 9 makes armed construction REFUSE (fail closed) when it is
absent, so armed validation can never run without ledger binding.

## Scope
1. conveyor_daemon.py: add validation_ledger_binding to the armed required-seam refusal list —
   same refusal mechanism/error style as the existing seams. Armed=False behavior unchanged.
2. test_conveyor_daemon.py: regression test — constructing ConveyorDaemon(armed=True) with every
   other seam but WITHOUT validation_ledger_binding raises the refusal (assert the seam name in
   the message); armed=False without it still constructs. Audit existing armed-path tests: any
   that construct armed daemons must now supply a binding — update ONLY by ADDING the seam to
   their construction (never weaken an assertion). If a shared fixture/helper builds armed
   daemons, extend the helper.
3. Changelog .ce/changelog/ce-410-s9-ledger-binding-seam.md + carrier via carrier_gen API
   (write_carriers(base="origin/main"); rm build/ + *.egg-info first); carrier slug == branch.

## Allowed paths (exactly these)
validators/creator_engine_validator/conveyor_daemon.py ·
validators/tests/unit/test_conveyor_daemon.py ·
.ce/changelog/ce-410-s9-ledger-binding-seam.md · .ce/pr-manifests/ce-410-s9-ledger-binding-seam.md

## Do NOT touch
conveyor_daemon_runner.py / deploy/** (A1 territory, building in parallel — your change is what
makes ITS injected binding mandatory; no coordination needed, A1 already injects it) ·
conveyor_discovery.py · daemon_lease.py · validation_sandbox_*.py · v3_cli.py/ce_cli.py ·
docs/** · the slice-10 publish-reverify scope (re-deriving tree_sha pre-push is NOT this slice).

## Novelty check (FIRST — semantic)
Inspect the armed-seam refusal list in ConveyorDaemon.__init__ on your origin/main base: if
validation_ledger_binding is ALREADY in the required list (constructing armed without it already
raises), signal BLOCKED already-landed with the line citation. The seam EXISTING as an optional
parameter is expected and not evidence of prior completion.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` (TMPDIR=/var/tmp) GREEN one pass before commit-for-harvest; env-only
container failure -> focused set green (test_conveyor_daemon.py + carrier/changelog checks) +
signal READY with env caveat. Commit: `ce-ops#410 slice 9: require validation_ledger_binding on armed conveyor`.
Signal EXACTLY: `READY-FOR-HARVEST ce-410-s9-ledger-binding-seam <full-40-hex-sha>`
or `BLOCKED ce-410-s9-ledger-binding-seam <reason>`.

## Stop line
No slice-10 scope. No runner/deploy changes. No push (controller harvests unless you are a
self-push seat told otherwise in the dispatch pointer). No review/approve/merge.
