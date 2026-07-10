# WORK CLAIM — ce-ops#187 / ce-ops#42 · W8 Slice 1 · `ce dispatch plan` — dry-run dispatch planner

**Seat:** dev-1 (Hetzner VPS, `ssh dev1`). **Role:** implementer. **Single-seat, bounded.**

## Branch
```
git fetch origin && git checkout -b ce187-42-w8-dispatch-plan origin/main
```
dev-1's local main is ~12 commits behind origin. You MUST `git fetch origin` first and branch from `origin/main`, not from your local `main`. Verify with `git log --oneline origin/main -3` before starting.

## Tickets (embedded — you cannot read private ce-ops issues)

### ce-ops#187 — Forge triage (first slice already SHIPPED; this claim builds slice 2)
The FIRST slice of ce-ops#187 (`forge_triage.py` + `ce pickup triage`) is **already merged** on main. Do NOT re-implement it. What remains is the `ce dispatch plan` tool (ce-ops#42).

### ce-ops#42 — `ce dispatch plan` command + label config
Adds a new top-level `ce dispatch` command group with a `plan` subcommand. Purpose: consume a `ce pickup triage` JSON result (or a raw GitHub issues JSON) + an arc ticket + a seat list and emit a structured, deterministic dispatch plan (work-items with seat assignments, work class, mutation class, sizing ceremony output). This is plan-only; it does NOT apply labels, open PRs, launch lanes, or call the forge. It is the "what should we dispatch to whom" answer, offline and reproducible.

## Why this slice (self-contained context)

The CE day-shift arc (W8) has four deliverables:
1. Build triage planner — **DONE** (merged as ce-ops#187 slice 1)
2. `ce dispatch plan` tool (#42) — **THIS CLAIM**
3. Label-automation `belt-pickup-ready` — FUTURE (needs live forge token, reserved operator run)
4. Forge cron first prod run — OPERATOR GESTURE (deferred)

Starting with `ce dispatch plan` is the right first move: it is greenfield code in `ce_cli.py` (free from other in-flight lanes), requires no forge credentials, has no mutation authority, and directly feeds W7 (the belt pickup poller can use the dispatch plan's seat assignments as hints).

## Codebase context (read these before writing)

Read these files to understand the patterns you must follow:

1. **`validators/creator_engine_validator/forge_triage.py`** — the sibling module. Your new `dispatch_plan.py` is a thin composition layer over it. Reuse `IssueCandidate`, `TriageAction`, `TriageResult`, `plan_triage()`. Do NOT copy-paste their logic.

2. **`validators/creator_engine_validator/ce_cli.py`** lines 1386–1449 (the `ce pickup` group wiring) and lines 2998–3033 (`_pickup_triage` handler) — this is the EXACT pattern you must follow for the new `ce dispatch` group.

3. **`validators/tests/unit/test_v1_docs_reconciliation.py`** lines 52–63 — the inventory guard. Adding `ce dispatch` to `ce_cli.py` will BREAK this test unless you also update the expected set and the README.

4. **`validators/creator_engine_validator/work_sizing.py`** — `size_ceremony(work_class, mutation_class)` and `WORK_CLASSES`/`MUTATION_CLASSES`. Use these; do not re-implement.

5. **`README.md`** lines 111–116 — the command group listing. Adding `ce dispatch` requires a mention here or the inventory test will fail.

## Task

### 1. New module `validators/creator_engine_validator/dispatch_plan.py`

```python
"""Dispatch plan composer for W8 forge-triage lane (ce-ops#42).

Consumes a TriageResult from forge_triage.plan_triage() and a seat list,
and emits a deterministic DispatchPlan: each triage-ready item gets a seat
assignment, a branch-name suggestion, and the sizing ceremony output.
This module is plan-only and makes NO mutations (no labels, no launches,
no forge calls).
"""
```

The module must expose:

- `DispatchPlanItem(dataclass, frozen=True)` — one item in the plan. Fields: `issue` (IssueCandidate), `arc_ticket` (str), `work_class` (str), `mutation_class` (str), `sizing` (Mapping), `seat` (str | None), `suggested_branch` (str), `pickup_label` (str).
- `DispatchPlan(dataclass, frozen=True)` — the full plan. Fields: `arc_ticket` (str), `pickup_label` (str), `items` (tuple[DispatchPlanItem, ...]), `skipped` (tuple[Mapping, ...]).
- `plan_dispatch(*, arc_ticket, issues, repo=None, pickup_label=DEFAULT_PICKUP_LABEL, assign_to=()) -> DispatchPlan` — calls `forge_triage.plan_triage()` and composes the result into a `DispatchPlan`. Round-robins seats across items. Derives `suggested_branch` as `"{owner}-{number}-{slug}"` where slug = first 5 words of title lowercased, hyphened, safe.
- `DEFAULT_PICKUP_LABEL = forge_triage.DEFAULT_PICKUP_LABEL` (re-export).

Keep the module **pure**: no subprocess, no network, no disk, no side effects. All its logic is deterministic given the same inputs.

### 2. Wire `ce dispatch plan` in `ce_cli.py`

Add a new `dispatch` command group with a `plan` subcommand. Follow the EXACT same parser + dispatch-dict + handler pattern as `ce pickup triage`:

Parser (add to `_build_parser()`):
```
dispatch = groups.add_parser("dispatch", help="plan and inspect governed seat dispatch (ce-ops#42)")
dispatch_sub = dispatch.add_subparsers(dest="dispatch_cmd")
dp = dispatch_sub.add_parser("plan", help="emit a deterministic seat-dispatch plan from issues JSON")
dp.add_argument("--arc-ticket", required=True, dest="arc_ticket")
dp.add_argument("--issues-json", default="-", dest="issues_json")
dp.add_argument("--repo", default=None)
dp.add_argument("--label", default=dispatch_plan.DEFAULT_PICKUP_LABEL)
dp.add_argument("--seat", action="append", dest="dispatch_seats", default=[])
dp.add_argument("--json", action="store_true", dest="json_output")
```

Handler `_dispatch_plan(args) -> int` — reads issues JSON (stdin or file), calls `dispatch_plan.plan_dispatch(...)`, prints human-readable or JSON output. JSON output must include `{"kind": "dispatch-plan", "arc_ticket": ..., "pickup_label": ..., "count": N, "items": [...], "skipped_count": ..., "skipped": [...]}`.

Dispatch dict: `_DISPATCH_DISPATCH = {"plan": _dispatch_plan}`. Add the `dispatch` group handler in `main()` following the same pattern as `pickup`.

Import `dispatch_plan` at the top of `ce_cli.py` alongside `forge_triage`.

### 3. Update the inventory guard test (`validators/tests/unit/test_v1_docs_reconciliation.py`)

At line ~57, add `"dispatch"` to the expected `_ce_command_groups()` set. IMPORTANT: read the set EXACTLY as it appears in the file and add only `"dispatch"` — do not guess the other members; copy the existing set verbatim and insert the one new entry. Also update `README.md` to include `ce dispatch` in the command group list (add it after `ce pickup`).

### 4. Unit tests `validators/tests/unit/test_dispatch_plan.py`

Write tests for:
- Happy path: 3 open issues → 3 plan items, round-robin seat assignment.
- Skip reasons propagate from `plan_triage` (blocked, assigned, aggregate, hold marker).
- `suggested_branch` is path-safe (no spaces, no special chars).
- `plan_dispatch` is deterministic: same inputs → same output, no ordering variance.
- CLI JSON output shape: `kind == "dispatch-plan"`, `count == len(items)`.
- CLI human-readable output: prints one line per item with seat + work_class.
- `--json` flag: output is valid JSON.
- Empty issue list: returns a plan with 0 items, 0 skipped.

Follow the test style in `validators/tests/unit/test_forge_triage.py` — use the `_issue()` helper pattern, inject fake data, no subprocess.

## Allowed paths

EXACTLY these files and no others:
- `validators/creator_engine_validator/dispatch_plan.py` (NEW)
- `validators/creator_engine_validator/ce_cli.py` (MODIFY — add `ce dispatch` group + import)
- `validators/tests/unit/test_dispatch_plan.py` (NEW)
- `validators/tests/unit/test_v1_docs_reconciliation.py` (MODIFY — update inventory set)
- `README.md` (MODIFY — add `ce dispatch` to the command list)
- `.ce/changelog/ce187-42-w8-dispatch-plan.md` (NEW — changelog fragment)
- `.ce/pr-manifests/ce187-42-w8-dispatch-plan.md` (NEW — per-PR path-set carrier)

**DO NOT TOUCH:** `forge_triage.py`, `work_sizing.py`, `pickup.py`, `.github/workflows/**`, `schemas/**`, `forge/mutation_classifier.py`, `forge/automerge_policy.py`, `v3_cli.py`.

## HARD RULES

1. **Run full `ce validate-pr` GREEN in ONE pass before any push.** Use `ce validate-pr` (not raw pytest) — the host `/tmp/.git` false-fail trap is real; `ce validate-pr` runs hermetically (TMPDIR=/var/tmp). The gate runs: full pytest suite + work-sizing-floor check + path-manifest carrier check + G5 body line. Fix ALL gates in one pass; do not whack-a-mole.

2. **`ce validate-pr` command:** From the repo root: `ce validate-pr --base origin/main --head-ref ce187-42-w8-dispatch-plan` (or `python -m creator_engine_validator.ce_cli validate-pr --repo-root . --base origin/main --head-ref ce187-42-w8-dispatch-plan`). This is `story`-sized (one command group + module + tests = code mutation).

3. **PR body MUST carry this exact line** (required by the G5 gate in CI):
   ```
   - **Declared work class:** story
   ```
   No other format is accepted. Do not use `### Changes`, `**Work class:**`, or put it in a code block.

4. **PR path-manifest carrier** (`.ce/pr-manifests/ce187-42-w8-dispatch-plan.md`) must list ALL and ONLY the files you touched, with `AUTHORIZED_PATHS_COUNT` and `AUTHORIZED_PATHS_SHA256` correct. Regenerate via the carrier_gen Python API (`carrier_gen.write_carriers(base=<merge-base-sha>)`) rather than hand-editing the hash; remove any stray `validators/build/` / egg-info artifacts first (the CLI dirty-checks on them).

5. **Do NOT push until the controller confirms.** dev-1 is NOT contained (it CAN self-push) — but you must still HOLD: when you have a green validate-pr, report `READY-FOR-HARVEST: branch ce187-42-w8-dispatch-plan, <N> commits, preflight green` and WAIT. Do NOT `git push`, do NOT `gh pr create`, do NOT approve/merge/enqueue. The controller holds the merge gate.

## Evidence (DoD)

- Full `ce validate-pr` GREEN: pytest passes, work-sizing floor passes (story), path-manifest check passes, G5 line present.
- `ce dispatch plan --arc-ticket creator-engine/ce-ops#67 --issues-json <some-file> --repo creator-engine/ce-ops --json` emits valid JSON with `kind == "dispatch-plan"`.
- `ce dispatch plan --help` prints usage without error.
- Inventory test passes: `_ce_command_groups()` includes `"dispatch"`.
- README mentions `ce dispatch`.
- `git log --oneline origin/main..HEAD` + `git diff --stat origin/main..HEAD`.
- PR body contains exactly one `- **Declared work class:** story` line.

## Stop Line

- **Plan-only. `dispatch_plan.py` MUST NOT call `apply_triage_result`, `gh api`, `subprocess`, open files for write, or launch lanes.** It is a read-only composition module.
- Green + ready → report `READY-FOR-HARVEST: branch ce187-42-w8-dispatch-plan, <N> commits, preflight green`. Do NOT push.
- Preflight RED on a new gate → STOP + report the failing gate by name and error text.
- If the inventory guard test fails after adding `"dispatch"` → you missed copying the full set; read the test file's set verbatim and add only the one entry.
- If the path-manifest gate fails → your carrier's file list does not match what you actually touched. Regenerate the carrier; do not edit the gate.
- If you need a file not in the allowed list → STOP and report to the controller; do not expand scope.
