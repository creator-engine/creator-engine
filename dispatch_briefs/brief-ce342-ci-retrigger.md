# WORK CLAIM — ce-ops#342 · CI re-trigger: add `edited` to pull_request trigger types

**Seat:** dev-4 (container ce-dgx-codex). **Role:** implementer. **Single-seat, bounded.**

## Branch
```
git fetch origin && git checkout -b ce-342-ci-retrigger origin/main
```

## Lane / Ticket
- ce-ops#342: "empty-commit / body-edit doesn't re-trigger CI".

## Why (self-contained — you cannot read private ce-ops issues)
`.github/workflows/validate.yml` uses a bare `pull_request:` trigger with no `types:` key. GitHub's default is `opened`, `synchronize`, `reopened` only. When a PR author edits the PR body (e.g. to fix the `- **Declared work class:** <tier>` line the G5 gate requires), the workflow does NOT re-run — the only workaround today is a manual close+reopen (fragile, undiscoverable).

Fix: add `edited` to the pull_request trigger types. Safe because:
1. The anti-stale-rerun guard ("Resolve live comparison base" step) fetches the LIVE PR head SHA via `gh api` and compares to `git rev-parse HEAD`; for an `edited` event no commit was pushed so the event head == live head → guard passes.
2. The G5 gate reads the PR body from `GITHUB_EVENT_PATH`; on `edited` the payload carries the NEW body → re-reads the fixed line. Correct behavior.
3. No CI loop: CI runs cannot trigger `edited`; only a human editing the PR does.
4. FOOTGUN: specifying `types:` overrides defaults — you MUST include the three original defaults alongside `edited`, or new-PR CI breaks.

The script/helper alternative (empty-commit or close+reopen via gh) was evaluated and rejected for this slice (needs write tokens in-seat, touches more files, doesn't fix the root cause).

## Task
In `.github/workflows/validate.yml`, change the `pull_request:` block from:
```yaml
on:
  pull_request:
```
to:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, edited]
```
No other change to the workflow file. Then create the two mandatory carrier files (below).

## Allowed Paths (CLOSED — nothing else)
```
.github/workflows/validate.yml
.ce/pr-manifests/ce342-ci-retrigger.md
.ce/changelog/ce342-ci-retrigger.md
```
Do NOT touch `ce_cli.py`, `README.md`, `test_v1_docs_reconciliation.py`, any validator source, any schema, any other workflow, `CLAUDE.md`, `AGENTS.md`, or anything not listed. This change adds NO new `ce` CLI group → the 3-file coupling does NOT apply.

## Carrier files
- `.ce/pr-manifests/ce342-ci-retrigger.md`: per an existing carrier model. Per-file purpose for the 3 paths; `- **Declared work class:** tiny`; `AUTHORIZED_PATHS_COUNT=3`; `AUTHORIZED_PATHS_SHA256 = sha256("\n".join(sorted(unique_paths)) + "\n")` over the 3 paths; fenced `text` block listing the 3 paths alphabetically. Regenerate via `carrier_gen.write_carriers` API if available (rm build/egg-info first).
- `.ce/changelog/ce342-ci-retrigger.md`: one-line fragment matching an existing fragment's frontmatter — "pull_request trigger now includes `edited` so PR body edits re-trigger CI".

## Evidence (DoD)
1. `ce validate-pr --base origin/main --head-ref ce-342-ci-retrigger` (≡ `scripts/ce-preflight.sh ... --declared-work-class tiny`) GREEN in ONE pass on a clean committed tree. Use ce validate-pr, NOT raw pytest.
2. `git diff --name-only origin/main..HEAD` lists exactly the 3 allowed paths.
3. PR body contains exactly one line `- **Declared work class:** tiny`.
4. Carrier `AUTHORIZED_PATHS_SHA256` matches the sorted newline-terminated path list.
5. The validate.yml diff is a single hunk adding `types: [opened, synchronize, reopened, edited]`.

## HARD RULES
- Run `ce validate-pr` (not raw pytest) on a CLEAN committed tree BEFORE any push. Two strikes on the same gate → STOP + report the gate.
- PR body MUST contain exactly `- **Declared work class:** tiny`.
- Allowed paths CLOSED; any out-of-scope required file → STOP + report (don't expand scope).
- HOLD: do NOT self-approve/merge/enqueue. Wait for controller confirmation.
- If preflight RED on a KNOWN pre-existing gate unrelated to your diff → report `READY-FOR-HARVEST: branch ce-342-ci-retrigger, <N> commits, preflight green-except-<gate> (pre-existing)`. For a NEW gate failure from your change → STOP + report.

## Stop Line
- Green + push works → push `ce-342-ci-retrigger`, open PR referencing ce-ops#342, report `READY-FOR-HARVEST: branch ce-342-ci-retrigger, <N> commits, preflight GREEN`. Do NOT approve/merge/enqueue.
- Green but push fails (contained self-push gap) → report `READY-FOR-HARVEST: branch ce-342-ci-retrigger, <N> commits, preflight GREEN, push failed (self-push gap)`.
- Preflight RED on the YAML parse check → verify `types:` indentation under `pull_request:`; fix once; same gate again → STOP + report.
