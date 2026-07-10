# BRIEF — dev-1 MORNING — 2026-07-07 ~03:4xZ — 2 units, BOTH unblock the merge lane (P0)

Both your approved PRs (#859, #874) are stuck: each fails the merge_group `Validate` run
(merge-queue dequeues them; the pre-merge PR runs were green because they ran on stale bases).
Controller diagnosed both root causes tonight; the fixes are yours (your branches). Standard
rules: self-push allowed (your own PRs), changelog/carrier already exist per branch, no new
carrier needed. Stop lines standard: no approve/merge/signing. Signal per unit:
`READY <branch> <sha>` + one-line evidence.

## U1 — PR #859 `ce-461b-adoption-template-merge-group` — rebase + fix latent \x01 template bug
ROOT CAUSE (verified locally on the merge preview): your new test
`test_ce_workflow_template_triggers_on_merge_group_checks_requested` yaml-parses the FULL
`CE_WORKFLOW_CONTENT` and exposes a latent bug on CURRENT MAIN (your branch base predates it):
`_render_ce_workflow_content()` in `validators/creator_engine_validator/onboard_apply.py`
returns a NON-RAW f-string. The embedded canonicalization code
`rb"\1<published-with-this-spec>"` (2 occurrences, ~lines 193/198 on main) therefore compiles
`\1` as an OCTAL ESCAPE → a literal chr(1) byte in the rendered adoption workflow.
CONSEQUENCE (worse than the test failure): every onboarded repo's rendered workflow
canonicalizes the signed spec with a literal \x01 replacement instead of the group-1 backref,
producing different canonical bytes than the signer (`release_publish.py` line ~228 uses a
correct raw `r"\1<published-with-this-spec>"`) → `content_sha256 mismatch` → adoption
spec-verify FAILS CLOSED in tenant repos. This is tenant-facing.
STEPS:
1. Rebase your branch onto FRESH origin/main (the canonicalization block arrives from main).
2. Fix: escape the backslash in the template — `rb"\\1<published-with-this-spec>"` (BOTH
   occurrences) so the RENDERED workflow contains `rb"\1<...>"`.
3. Regression test (in test_onboard_apply.py): assert no control characters in
   `CE_WORKFLOW_CONTENT` (e.g. `assert not any(ord(ch) < 9 for ch in content)`), and assert the
   rendered canonicalization replacement string `rb"\1<published-with-this-spec>"` appears
   literally in the content.
4. Verify your merge_group-exposed test passes on the rebased+fixed branch:
   `pytest validators/tests/unit/test_onboard_apply.py -q` green.
5. Self-push (force-with-lease after rebase). Signal READY.
Controller will delta re-review + re-approve; approval resets on push — expected.

## U2 — PR #874 `ce-477-continuity-drill` — rebase + re-chain brain-ledger appends
ROOT CAUSE (verified locally on the merge preview): your appended `.ce/brain/assertions.yaml`
records chain from YOUR base's tail (`prev_hash e314d69e63be8c28dd31a0217e08d52049069b6a0c2b...`)
but main's tail moved (now sequence 145, content_hash
`2222984b5d084406bc26cd7da2e79c85eb1ca5d605592d24c256059ea4e15104`). After the textual merge the
hash chain forks mid-ledger → `brain_doctrine_manifest_invalid` → ce_brain_doctrine_coverage
fails inside EVERY example check → the check-examples sweep fails (37 tests) → merge queue
dequeues. Git cannot see this conflict.
STEPS:
1. Rebase onto FRESH origin/main.
2. Re-chain your appended records with the SAME canonical brain-append tool you used to create
   them: first appended record's prev_hash must equal main's tail content_hash (2222984b...),
   sequences renumber from main's tail+1, content_hash cascade recomputed. Do NOT hand-edit
   hashes; regenerate the appends.
3. Verify: `python -m pytest validators/tests/unit/test_cli.py -k check_examples -q` green on
   the rebased branch (this is the exact merge_group failure).
4. Self-push (force-with-lease). Signal READY.
Content was already APPROVED (VERDICT-874R2); the re-chain delta gets a mechanical re-review,
then re-approve → merge → DRILL #1 executes.

## Priority: U1 and U2 both ahead of any restock. U2 first if you must serialize (it gates
## drill #1 and the C5 zero-in-flight window), then U1.
