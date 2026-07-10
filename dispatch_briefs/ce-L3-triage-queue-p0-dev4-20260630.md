# SEED BRIEF — L3 forge Triage Ready Queue (P0) — SEAT: dev-4

**Branch:** `ce-L3-triage-ready-queue-p0` off CURRENT origin/main (FIRST run `git fetch origin && git worktree add <wt> origin/main` — you have fetch egress; do NOT work off a stale checkout). **Role:** implementer. **Work class:** declare by floor (story/S expected). **No push auth in-container** → commit + echo SHA; controller harvests.

## Goal (self-contained — do NOT rely on reading any private ticket)
Add **inbound issue auto-triage** to Creator Engine: a new module that classifies newly-opened issues in the `creator-engine/ce-ops` repo (work-class, mutation-class, lane, ready/blocked), writes the result into an **advisory "Triage Ready Queue"** state, and emits a local audit record. **Advisory ONLY** — it must NEVER ratify, approve, review, merge, or authorize dispatch, and must NEVER block CI (fail-open everywhere).

## Ground yourself in the EXISTING code (read these in your checkout — they already exist)
- `validators/creator_engine_validator/forge_triage.py` — REUSE its primitives: `normalize_issue(raw)→IssueCandidate`, `_infer_work_class(candidate)`, `_infer_mutation_class(candidate)`, and the PUBLIC `readiness_blockers(candidate)` (empty tuple = ready; non-empty = blocked + reasons). Call these; do NOT reimplement classification. (They are private-by-underscore — call via `forge_triage._infer_work_class`; document this coupling in a comment + a test guards it.)
- `validators/creator_engine_validator/work_claims.py` — the gh I/O seam pattern: `_gh_api()` supports GET/POST/PATCH; comment read/post helpers. Model your GhRunner on this (injectable, offline-by-default, token via env NEVER argv).
- `.github/workflows/ce-ops-autoclose.yml` + `.github/scripts/ceops_autoclose.py` — the cross-repo write pattern using the `CE_CROSS_REPO_TOKEN` secret (issues:write on ce-ops); model your workflow + PATCH-comment write on this.
- `validators/creator_engine_validator/work_sizing.py` — `WORK_CLASSES`, `size_ceremony`, `normalize_work_class`.
- `validators/creator_engine_validator/ce_cli.py` — add a new INTERNAL `ce triage` group (see below); note `INTERNAL_COMMAND_GROUPS` (suppresses from public docs) and the `cli_reference_autogen_sync` check.
- `scripts/gen_cli_reference.py` — run `--write` after CLI edits to regen `.ce/reference/cli.generated.md`.
- `validators/tests/unit/test_forge_triage.py` — copy its `FakeGh` pattern for your tests.

## P0 scope — exactly these files
**New:**
1. `validators/creator_engine_validator/ce_ops_triage_queue.py` (~200 lines). Symbols: `QUEUE_SENTINEL = "<!-- ce-triage-queue-issue:v1 -->"`, `NON_AUTHORITY_STATEMENT`, frozen `QueueEntry` dataclass (issue_number, repo, title, work_class, mutation_class, lane, readiness, blockers, triaged_at), `LANE_LABEL_MAP` (hardcoded label-substring→L1..L10 table; default `"unclassified"`), `infer_lane()`, `read_queue_comment()`, `parse_queue_entries()` (never raises on malformed rows — skips), `render_queue_body()` (deterministic, idempotent, sentinel + advisory line + Markdown table), `classify_issue()`, `plan_triage_entry()` (PURE, no I/O), `scan_and_triage(..., apply=False, ...)` (plan-by-default; dedup by issue_number, last-write-wins), `upsert_queue_comment(..., apply=False)`, `write_audit_record()`. Zero network on import. Token via env only.
2. `validators/tests/unit/test_ce_ops_triage_queue.py` (~150 lines, all OFFLINE via a FakeGhRunner): empty-body→[], round-trip render↔parse, render idempotent/byte-equal, sentinel + advisory present, no-duplicate-by-issue-number, classify-from-label, infer_lane match + default, readiness blocked/ready, plan_triage_entry pure, **dry-run makes ZERO write calls**, apply=True issues a PATCH, audit record valid JSON w/ advisory statement, and `ce_cli.main(["triage","queue","scan","--help"])` exits 0 (+ inspect --help).
3. `.github/workflows/ce-ops-triage-queue.yml` — `schedule: */30 * * * *` + `workflow_dispatch` (input `apply`, default false); `continue-on-error: true` (advisory, never blocks); pin all action SHAs (match the style of existing workflows); token `CE_CROSS_REPO_TOKEN` via `env:`; runs `ce triage queue scan --repo creator-engine/ce-ops --queue-issue 67 --audit-root $RUNNER_TEMP/... [--apply] --json`; upload audit dir as artifact.

**Changed:** `validators/creator_engine_validator/ce_cli.py` — import the new module; add `"triage"` to `INTERNAL_COMMAND_GROUPS`; add `ce triage queue scan|inspect` subparsers (args: --repo default creator-engine/ce-ops, --queue-issue default 67, --audit-root, --apply, --json) with `help=argparse.SUPPRESS`; add `_triage_queue_scan/_triage_queue_inspect` handlers + dispatch wiring. Then regen `.ce/reference/cli.generated.md` via `gen_cli_reference.py --write` (internal group → likely no visible change; just confirm the `cli_reference_autogen_sync` check is GREEN).

## Controller decisions (locked — implement these)
- **Default `apply=False`** (dry-run). The cron defaults to dry-run; live apply only via `workflow_dispatch` with apply=true. 
- **Readiness/triaged-filter:** use a **date-range fallback** (issues updated in last N hours, default 24) to select candidates — do NOT require a pre-created `ce-triage-queue/processed` label in ce-ops. (Label-based filtering = P1.)
- **Lane source:** the hardcoded `LANE_LABEL_MAP` constant (the one place lane taxonomy is edited). Unmatched → `"unclassified"`.

## DEFER to P1/P2 (do NOT build now): configurable lane YAML; auto-labeling ce-ops issues; Projects-v2 board writes; webhook sub-30-min latency; >100-comment pagination; LLM classification; multi-repo. Keep P0 small + shippable.

## Carrier / changelog / preflight
Carrier `.ce/pr-manifests/ce-L3-triage-ready-queue-p0.md` (carrier_gen, stem==branch slug) + changelog `.ce/changelog/ce-L3-*.md`; carrier path-set == base..HEAD. Run FULL preflight GREEN in ONE pass (`TMPDIR=/var/tmp .venv/bin/python -m pytest -q <your tests>` + the autogen-sync check). venv: `.venv/bin/python` (no activate).

## Stop line
Commit with `git commit && echo <SHA>`; report SHA + files + preflight result + which existing forge_triage primitives you reused. Do NOT push/approve/merge, do NOT create the ce-ops#67 sentinel comment (that's a one-time Operator/controller setup step before the workflow goes live), do NOT scope-creep beyond the P0 file list.
