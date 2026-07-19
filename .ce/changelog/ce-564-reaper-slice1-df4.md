---
slug: ce-564-reaper-slice1-df4
date: 2026-07-19
kind: feature
scope: seat-scratch reaper slice 1 — ce seat-scratch reap
issue: ce-ops#564
---

**Seat-scratch space reaper — slice 1: policy module, CLI surface, and unit tests.**

First implementation slice of the seat-scratch reaper.
Implements the ratified retention policy for per-ticket scratch space on controller hosts.

- **`validators/creator_engine_validator/seat_scratch_reaper.py`** — pure policy module
  with no subprocess or live-seat coupling:
  - Classifies top-level epoch-dir entries into seven policy classes: `worktree` (`wt-*`,
    `day4-*`), `cv_sandbox` (`cv-*`), `pytest_temp` (`pytest-of-*`),
    `preflight_workspace` (`preflight-*`), `validate_pr_cache` (`validate-pr-*`),
    `bundle` (`*.bundle`), `evidence` (small files <50 MB with evidence extensions),
    and `unknown` (fail-closed to retain).
  - Merged-ticket detection via changelog-fragment/pr-manifest presence on the local main
    checkout (the proven signal; `branch -r --merged` is non-informative once branches
    are deleted at merge). Extraction: `ce-NNN` slug from the entry name.
  - Reference guard: refuses to reap anything whose name or absolute path appears in a
    claim/brief file modified within a configurable window (default: 7 days).
  - Freshness guard: anything with mtime within 48 h is always retained.
  - Unknown class: fail-closed — never reaped regardless of age.
  - Pre-reap evidence export: small evidence files are copied to `--evidence-root` with a
    sha256 manifest before any deletion.
  - Two-phase execution: plan phase emits a full TSV manifest (path / size_bytes /
    mtime_iso / class / reason / action); delete phase re-stats each entry to confirm the
    mtime is unchanged (race guard); aborts the entry if it changed.
  - `--dry-run` DEFAULT — `--execute` required for deletion; `O_CREAT | O_EXCL` single-
    instance lock file guards the execute phase.
  - Retention thresholds: worktrees/sandboxes/temps/preflight/validate-pr caches at 7 days
    or merge-confirmation; bundles retained 30 days.

- **`ce seat-scratch reap` CLI surface** wired through `V3_FORWARDING_SHIMS` in
  `ce_cli.py` and the `seat-scratch` subparser in `v3_cli.py` (parallel to `ce reap`).
  Full argument set: `--repo-root`, `--claims-dir`, `--briefs-dir`, `--evidence-root`,
  `--execute`, `--freshness-hours`, `--reap-age-days`, `--bundle-retain-days`,
  `--claims-window-hours`, `--json`.

- **`validators/tests/unit/test_seat_scratch_reaper.py`** — 25 unit tests over a
  synthetic epoch-dir fixture (`tmp_path`): classification of all seven classes,
  freshness guard, claim-reference refusal (name-match and abs-path-match), stale-claim
  exemption, unknown-class retain, merged-ticket detection (changelog and pr-manifest),
  age-threshold reap/retain, evidence export with sha256 manifest, idempotent second run,
  re-stat abort on mtime mutation, re-stat abort on vanished entry, lock-held refusal,
  lock-release after execute, TSV header and row format, ticket-slug extraction, and
  non-existent epoch dir.
