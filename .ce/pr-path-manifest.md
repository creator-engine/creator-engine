# PR path manifest — v3 G-3.6a roadmap status-flip (`docs/v3-roadmap.md`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **docs-only** PR. It updates `docs/v3-roadmap.md` to reflect that
**G-3.6a** (the run-outcome / terminal-disposition model — a run's terminal
outcome is a typed `runtime_run_outcome` record appended to the same
tamper-evident hash chain, orthogonal to the `provision`/`run`/`collect`/
`teardown` `lifecycle_phase` axis; PR #136, merge commit `bc22681`) is MERGED.
It splits the single planned `G-3.6` gate-status row into **G-3.6a** (`#136` /
`bc22681` / MERGED) + **G-3.6b** (offline composition-root assembly + end-to-end
dry-run, planned), mirrors that split in the MVP gate-map sketch, advances the
status-summary prose and "What's next" pointer
(G-3.0…G-3.5 + G-3.6a merged; G-3.6b next), and adds G-3.6a code-location +
contract notes to the "Where the v3 code lives" table (the `orchestrator.py`
terminal-outcome append, the `runtime_evidence_spine.py` `RUN_OUTCOME_*`
constants, and the `runtime_run_outcome_record` `$def` in
`runtime-evidence.schema.yaml`). It touches **no** Python, schema, or check
surface → `--list-checks` is **unchanged at 43** and `available_backends()` is
unchanged at `('gvisor-proxy', 'local-noop')`; no `ce_cli.py`/wheel change. The
draft passes `ce_terminology_v2` and `no_limitless_strings`.

- **base:** `bc2268130bad7e4cf836e520eed0a6169dee05e7`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
