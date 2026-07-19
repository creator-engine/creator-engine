---
slug: ce-617-board-sync-df4
date: 2026-07-19
kind: added
scope: forge / board sync adapter + CLI
issue: ce-ops#617
base: f450159fe
---

Adds the Projects-v2 board desired-state sync slice (arc DF-4, lane L4).

- **New module `validators/creator_engine_validator/forge/board_sync.py`.**
  Implements `BoardSyncRef` (project-level coordinates: `project_id`,
  `status_field_id`, `status_options` name→option-id map), `IssueCoord`,
  `DesiredItem`, `BoardItem`, `DriftReport`, and `SyncResult` value types.
  Exposes:
  - `read_board_items()` — paginating GraphQL reader for all project items
    (issues + drafts) with their current Status single-select value;
  - `compute_drift()` — pure comparison of desired vs observed state yielding
    missing items, stale status, orphans, and unknown status options;
  - `sync_board()` — idempotent orchestrator: read → drift → (optionally)
    add missing issues and update stale status fields; orphans are reported
    and never deleted; fail-closed if any desired status name is unknown in
    `ref.status_options`;
  - `load_desired_state()` — YAML schema parser returning `(BoardSyncRef,
    list[DesiredItem])`.
  Reuses `backlog._STATUS_MUTATION`, `backlog._run_json`, and
  `backlog._default_gh_runner` rather than duplicating GraphQL. All GitHub
  calls go through an injectable `GhRunner` seam; no live network in tests.

- **New desired-state YAML `.ce/board/board-state.yaml`.**  Declarative
  mapping of arc/ticket → board Status column for
  `github.com/orgs/creator-engine/projects/1`.  Covers arcs A0–A8
  (A0/A1-style entries superseded by the DF arc series), DF-1 through
  DF-3-N (Done), and the current DF-4 arc with its L4 implementation
  the in-flight L4 implementation tickets.  Contains a SETUP comment
  block with the GraphQL discovery commands to populate the placeholder
  node IDs from the live project.

- **CLI: `ce board sync [--dry-run | --execute] [--state-file PATH]`.**
  Registered in `ce_cli._build_parser()` as the `board` group with a `sync`
  subcommand following the `connector`/`fanin`/`queue` pattern. Dry-run is
  the default; `--execute` applies the drift. `--json` emits a
  machine-readable JSON payload covering `applied`, `drift`, `added`,
  `status_updated`, and `errors` fields.

- **Unit tests `validators/tests/unit/test_board_sync.py`** — 31 tests
  mirroring `test_backlog.py` style: `_Runner` injectable seam (dispatches
  by query type: REST / `addProjectV2ItemById` / `updateProjectV2ItemFieldValue`
  / list-items); drift computation (missing, stale, orphan, case-insensitive
  repo matching, draft exclusion); idempotency (second run on in-sync board
  produces zero write calls); fail-closed on unknown status option; YAML
  schema validation; zero live network assertion.
