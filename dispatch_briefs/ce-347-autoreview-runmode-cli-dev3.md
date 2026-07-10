# SEED BRIEF — ce-ops#347: AutoReview --run-mode CLI wiring — SEAT: dev-3

**Context (self-contained — embed; do not rely on reading the private ticket):**
PR #613 (ce-ops#341) landed LIBRARY-level `run_mode` in the egress self-review broker
`tools/egress-broker/ce_egress_self_review_broker.py`: `parse_request`,
`submit_self_review`, `SelfReviewServer`, and `serve()` all accept `run_mode`; the
never-APPROVE self-approval guard is **fail-closed by default** (None/"dev" → APPROVE
REFUSED; only explicit "strangeLoop" relaxes it); `run_mode` is **host-injected, NOT
readable from the request payload** (security-critical — keep it that way). Independently
reviewed as security-sound.

**REMAINING GAP (this lane):** the CLI entrypoint `main()` does not pass `run_mode` into
`serve()`, and `_build_parser()` has no `--run-mode` argument. So the daemon always runs
fail-closed (safe), but an operator cannot opt into strangeLoop via the CLI. Wire it.

**Branch:** `ce-347-autoreview-runmode-cli` (off `origin/main`).
**Role:** implementer. **Work class:** declare by diff floor (likely S; XS/S/M/L).
**Repo:** creator-engine/creator-engine. Contained VPS seat: worktree `/var/tmp`, branch off
`origin/main` (git fetch first), signal READY-FOR-HARVEST when done (controller harvests).

## Goal
- Add `--run-mode` to `_build_parser()` with choices covering at least `dev` and
  `strangeLoop` (mirror the exact literals the library already recognizes — grep for how
  `run_mode` is compared, e.g. `_is_strangeloop` / the "strangeLoop" string; do NOT invent
  new mode names). **Default = fail-closed** (absent → the same safe default as today, i.e.
  None/"dev" → APPROVE refused).
- Pass the parsed value through `main()` → `serve(run_mode=...)` so the daemon honors it.
- **Security invariants (must hold):** run_mode comes ONLY from the CLI/host, NEVER from
  the request payload; any value other than the explicit strangeLoop literal stays
  fail-closed; no code path lets a request self-select strangeLoop. Add an explicit test
  that a payload attempting to set run_mode cannot relax the guard.

## Scope — exactly these
- `tools/egress-broker/ce_egress_self_review_broker.py` (`_build_parser`, `main`; do NOT
  touch the guard logic itself — only wire the flag through)
- its tests (broker tests dir — add: `--run-mode strangeLoop` relaxes; absent/`dev` stays
  fail-closed; payload cannot inject run_mode; help text lists the flag)
- `.ce/pr-manifests/ce-347-autoreview-runmode-cli.md` + `.ce/changelog/ce-347-autoreview-runmode-cli.md`
Do NOT touch anything else. Code diff with tests → test-coupling satisfied.

## Evidence / DoD
- Owned gates + targeted broker tests GREEN in-container (note any env-noise; controller
  runs full validate-pr on the DGX host venv at harvest with PYTHONPATH=validators).
- Show the fail-closed-by-default + payload-cannot-inject tests passing in the report.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; signal READY-FOR-HARVEST. Do NOT push/approve/merge.
