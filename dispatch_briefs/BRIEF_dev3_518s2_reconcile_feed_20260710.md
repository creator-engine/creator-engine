# DISPATCH — dev-3 — 2026-07-10 — unit: stale-ticket reconcile slice 2 (live-data adapter) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-518s2-reconcile-feed <full-40-hex-sha>`
or `BLOCKED ce-518s2-reconcile-feed <one-line-reason>`.
Branch `ce-518s2-reconcile-feed` off freshly fetched origin/main OR LATER (queue is active;
use what you fetch). Worktree /var/tmp/wt-ce-518s2-reconcile-feed. Focused tests only.
PRE-SIGNAL CHECKLIST: focused tests green + the confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)
Slice 1 landed: `validators/creator_engine_validator/ticket_reconcile.py` — API-agnostic,
report-only matcher over plain-data inputs (open tickets + merged PRs), with a __main__ that
reads two JSON files. Ten stale-open tickets were closed BY HAND today; this slice makes the
sweep one command. STILL REPORT-ONLY: no auto-close, no cron, no state.

## Unit — a thin feed adapter + runner
1. NEW `validators/creator_engine_validator/ticket_reconcile_feed.py`:
   - `collect_inputs(ticket_repo, pr_repo, since_days, runner=subprocess.run)` — shells to the
     `gh` CLI (the repo's standard forge access; no new deps): open issues from the ticket
     repo (number, title, labels), merged PRs from the code repo since N days (number, title,
     head branch, body). Injectable runner seam so tests never touch the network.
   - Emits exactly the plain-data shapes slice 1 consumes (import its types/contracts — do
     not duplicate schema knowledge).
   - `main()`: `--ticket-repo --pr-repo --since-days --json` → runs collect + reconcile +
     prints the slice-1 report (or JSON). Non-zero exit ONLY on operational failure (gh
     errors), NOT on findings (report-only tools don't fail on findings).
2. Fail-closed on gh errors: a failed/malformed gh call raises with the command + stderr —
   never silently returns empty lists (an empty sweep must be distinguishable from a broken one).
3. Tests `validators/tests/unit/test_ticket_reconcile_feed.py`: fixture-driven via the runner
   seam — happy path end-to-end to report lines, gh-failure fail-closed, JSON mode, since-days
   argument passthrough, empty-but-successful sweep (empty report, exit 0).

## Files (allowed writes)
ticket_reconcile_feed.py (NEW), test_ticket_reconcile_feed.py (NEW),
`.ce/changelog/ce-518s2-reconcile-feed.md`, carrier (slug=branch) with exactly:
`- **Declared work class:** S`. Product lens in prose (synthetic repo names in fixtures).

## Stop lines
ticket_reconcile.py (slice 1 is FROZEN — import, don't edit), pr_preflight.py, checks/**,
ce_cli.py, v3_cli.py, forge/**, deploy/**, .github/**, docs/**, brain_intent_materializer.py,
release_acceptance.py, worktree_venv.py, .ce/brain/assertions.yaml.
