# SEED BRIEF — L2 automerge canary: close the live-data gap (P0) — SEAT: dev-4

**Branch:** `ce-L2-automerge-canary-livedata` off CURRENT origin/main (FIRST `git fetch origin` + worktree off origin/main — main now has #686 XS/S/M/L rename + #690 work-class choices back-compat). **Role:** implementer. **Work class:** declare by floor (S likely). **No push auth** → commit + echo SHA; controller harvests. **SAFETY-CRITICAL lane — read the SAFETY section.**

## Context (self-contained — do NOT rely on reading any private ticket)
CE has an automerge "canary" path that is ~90% built + tested: a decision engine (`forge/automerge_policy.py decide_automerge()`), a live-re-verifying actuator (`forge/automerge_actuator.py actuate_if_ready()`), both CI workflows (`.github/workflows/automerge-decide.yml`, `automerge-actuate.yml`), a kill-switch, and audit-JSONL. The envelope is enforced: armed only when `run_mode ∈ {ceo,strangeLoop}`, docs-class only, author≠approver, single-PR, required-checks-green, kill-switch honored, audit-logged.

**THE GAP (the one thing P0 fixes):** `automerge-decide.yml`'s decide step passes **empty** check data (`--checks-json '{"checks":{}}'`) and **empty** approver/review (`--approver-login ""`, `--review-decision ""`). So `decide_automerge()` ALWAYS returns GESTURE (checks_green=False, author_approver_not_distinct) → the actuator always refuses (`decision_not_auto`). The path never fires even when armed. P0 wires LIVE PR data into the decide step for `pull_request` events so a genuinely-eligible docs-class PR can reach an AUTO decision.

## Scope — exactly these changes
**A. `.github/workflows/automerge-decide.yml` (the core fix):**
- Add to job `permissions`: `pull-requests: read` and `checks: read` (keep `contents: read`).
- Add a step (pull_request events only; skip when no PR number, e.g. merge_group) that uses `gh` (token `${{ github.token }}`) to query the LIVE PR: `reviewDecision`, the APPROVED reviewer's login (from `latestReviews`), the declared work class parsed from the PR body (`- **Declared work class:** <X>`), and required-check statuses (`gh pr checks --json name,state,conclusion`). Emit these as step outputs; write checks JSON to a temp file (avoid shell-quoting issues). FAIL-CLOSED: if any `gh` query errors, emit empty values (current dormant behavior) — never error the workflow.
- Update the "Run automerge decision" step to pass the REAL values (`--review-decision`, `--approver-login`, `--declared-work-class`, `--checks-json @file`) instead of the hardcoded empties. The `merge_group` path KEEPS empty data (advisory only — the actuator re-verifies independently).

**B. Work-class aliases — REUSE, do not reinvent:** main already has `normalize_work_class` + `WORK_CLASS_INPUTS` (from #686/#690) accepting both XS/S/M/L and legacy tiny/story. In `automerge_policy.py` and `automerge_actuator.py`, the canary work-class check must accept the canary tier in BOTH naming schemes by calling `normalize_work_class()` (or reusing the shared constant) — do NOT add a new parallel alias dict. Canary tier = the two smallest classes (XS/S ≡ tiny/story).

**C. `ce_cli.py` — observability only (safe):** enhance `automerge-status` output to show the live arming state read from the policy file: `arming state: ARMED(run_mode=ceo)/DISARMED`, `enabling_ref`, `kill_switch`. This is the DoD's "visible audit trail" piece. No new module.

**D. Tests (enhance existing `test_automerge_policy.py` + `test_automerge_actuator.py`):**
- `decide` returns AUTO when run_mode armed + real green checks + APPROVED + distinct author/approver + docs-class + canary work-class + enabling_ref present.
- XS/S (and legacy tiny/story) accepted in the canary work-class gate; M/L (feature/epic) rejected.
- kill_switch=true overrides armed → GESTURE.
- DISARMED default (run_mode=dev) → GESTURE, no gh calls.
- actuator: armed strangeLoop actuates same as ceo (FakeGh, no real gh); kill-switch live-override refuses (existing test); audit JSONL has status/acted/single_pr (existing test).

## 🔒 SAFETY (MANDATORY — this lane can arm live auto-merge)
- Do NOT read, set, change, or reference the GitHub repo VARIABLES `CE_AUTOMERGE_RUN_MODE` / `CE_AUTOMERGE_ENABLING_REF` / `CE_AUTOMERGE_KILL_SWITCH` in any file, config, or test. They are managed by the Operator out-of-band.
- Preserve the **disarmed-by-default structural property**: with no policy state / run_mode=dev, decide→GESTURE and actuator→Dormant BEFORE any gh call. Existing tests assert this — they must stay green.
- The change must be incapable of auto-merging anything on its own; arming remains an external var-set (Operator R1).
- Do NOT touch the broker/Surface-B run-mode deployment, the operating_mode_policy bridge, or a single-PR mechanical gate — those are P1 (note them, don't build).

## Carrier / changelog / preflight
Carrier `.ce/pr-manifests/ce-L2-automerge-canary-livedata.md` (carrier_gen, stem==branch slug) + changelog `.ce/changelog/ce-L2-*.md`; path-set == base..HEAD. Run FULL preflight GREEN in ONE pass (the automerge policy/actuator tests + carrier/changelog gates). venv: `.venv/bin/python`.

## Stop line
Commit with `git commit && echo <SHA>`; report SHA + files + preflight result + a clear note that you did NOT touch arming vars and the disarmed-default tests pass. Do NOT push/approve/merge. The controller will harvest and HOLD the merge pending Operator R1 go-live confirmation (merging this makes docs-class auto-merge LIVE because the repo is already armed in ceo mode). No scope creep beyond A–D.
