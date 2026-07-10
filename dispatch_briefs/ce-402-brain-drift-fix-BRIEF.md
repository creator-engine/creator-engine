# Seed Brief: ce-402-preflight-failclosed — brain-assertion drift fix (round 2)

- Ticket: ce-ops#402 residual (private tracker — you cannot read it; full context embedded below)
- Branch: `ce-402-preflight-failclosed` (EXISTING branch, open PR #742 — fetch it from origin; do NOT create a new branch)
- Role: implementer
- Worktree: create under `/var/tmp` (NOT `/workspace`)

## What happened (embedded context)

PR #742 (this branch, head `a8f8340c5ed07b828d75282e9d554554a25a7824`) makes the
validate-pr baseline-diff gate fail closed when tests did not execute. It was
approved and enqueued, but the MERGE-GROUP run failed twice on:

`validators/tests/unit/test_ce_brain_drift.py::test_authoritative_migrated_assertions_validate_and_probe`

Three brain-ledger assertions drifted (all with
`evidence_ref: validators/creator_engine_validator/pr_preflight.py`):

- record 41 — `brain-assertion-d1b-01-local-preflight-ci-parity-v2`
- record 97 — `brain-assertion-d1b-42-preflight-committed-clean-tree-v2`
- record 99 — `brain-assertion-d1b-43-preflight-scrubs-credential-env-v2`

Root cause: PR #739 (brain doctrine batch 1) merged to main AFTER this branch
was cut and approved. Those assertions pin `claim.evidence_sha256` to the
content of `pr_preflight.py` as it exists on main. This branch modifies
`pr_preflight.py`, so in the merge group (main + this branch) the pinned
hashes no longer match and the drift gate goes RED. The branch's own PR CI
never saw this because the assertions weren't on main at approval time.

## Your task

1. Fetch `origin/main` and `origin/ce-402-preflight-failclosed`; work on the
   existing branch. Consider whether a rebase onto / merge of current
   origin/main is needed so the branch tree contains the #739/#741 brain
   records at all (it almost certainly is — the assertions live in
   `.ce/brain/assertions.yaml`, which this branch predates). Prefer a merge of
   origin/main into the branch over a rebase (the branch has an open PR with
   review history).
2. Reconcile the three drifted assertions with this branch's modified
   `pr_preflight.py` using the brain ledger's DOCUMENTED procedure. The ledger
   (`.ce/brain/assertions.yaml`) is hash-chained append-only: records carry
   `content_hash`/`prev_hash` chain links. NEVER edit an existing record's
   fields in place — that breaks the chain and the drift gate both. Find and
   use the repo's supersede/append mechanism (start from
   `validators/creator_engine_validator/brain_runtime.py` and any `ce brain`
   CLI surface / `test_ce_brain_drift.py` fixtures showing how `-v2` records
   superseded `-v1`). Append superseding records (e.g. `-v3`) whose
   `claim.evidence_sha256` matches THIS BRANCH's `pr_preflight.py` content,
   with the prior records marked per the documented supersede convention.
3. IMPORTANT semantic check: each assertion's `statement`/`claim.details` must
   still be TRUE of the modified `pr_preflight.py` (CI-parity full-tree
   invocation; committed-state validation refusing dirty trees; credential-env
   scrubbing in pytest subprocesses). Your branch's change (fail-closed
   baseline-diff gate) should not have falsified any of them — verify each
   claim against the code and say so explicitly in your done-report. If one IS
   no longer true, STOP and report; do not paper over it with a re-pinned hash.
4. Note: the local gitignored `.ce/state/brain/` cache can produce FALSE drift
   readings if stale — reconcile from the committed `.ce/brain/assertions.yaml`
   only; a fresh worktree has no stale cache.

## Allowed paths

- `.ce/brain/assertions.yaml` (append-only supersede records)
- Merge commit of origin/main into the branch (no new content beyond conflict resolution; report any conflicts you had to resolve)
- `.ce/changelog/ce-402-preflight-failclosed.md` (update the existing fragment with one line about the assertion supersede)
- `.ce/pr-manifests/ce-402-preflight-failclosed.md` (carrier — regenerate via the `carrier_gen` API against the merge-base with origin/main if the path set changed; do not hand-edit)

Do NOT touch `pr_preflight.py` or any other code file beyond mechanical merge-conflict resolution (report if any).

## Contained-seat mechanics

- Worktree under `/var/tmp`; venv has no activate — use `.venv/bin/python -m pytest ...`.

## Preflight (standing directive, ce-ops#303)

Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in
one pass before commit-for-harvest; run
`validators/tests/unit/test_ce_brain_drift.py` explicitly and confirm the
previously failing test now passes. Known exception: if preflight fails ONLY
on the known ssh-keygen install-spec gap (ce-ops#400), report it as the known
exception.

## Work-class and changelog

This is a small remediation on an existing PR — the PR's declared work class
line already exists in the PR body; do not change it. Update the existing
changelog fragment.

## Stop line

- No pushes, no PR actions, no approvals, no merges, no gate/wall/daemon
  config changes, no toolchain self-update.
- If the documented supersede mechanism doesn't exist or can't express this
  update, STOP and report exactly what you found instead of inventing a
  ledger format.

## Expected evidence

- `test_ce_brain_drift.py` green on the branch (paste the pass line).
- Full preflight GREEN one pass (paste final summary line).
- Explicit statement per assertion (d1b-01/-42/-43) that its claim text is
  still true of the modified pr_preflight.py.
- `git commit && echo SHA`, then emit exactly:
  `READY-FOR-HARVEST ce-402-preflight-failclosed <full-sha>`
