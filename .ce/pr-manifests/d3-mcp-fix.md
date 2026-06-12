# PR path manifest — esc-g2f-d3-mcp-regression · D3 relative `--mcp-config` fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref d3-mcp-fix
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED fix-gate mandate `esc-g2f-d3-mcp-regression`
(`.ce/state/research/w2-parallel/MANDATE_d3_mcp_regression_fix.md`). A live regression escaped
#207's D3 change: `materialize_dispatch` absolutized the state root — correct for
`envelope_ref`/`brief_ref` (the F5 class) — but `mcp_config_ref` became absolute too, and
Ring-0 CC-D-7 (`claude_launch_spec._is_ce_owned_mcp_path`) REQUIRES a CE-owned RELATIVE
`--mcp-config`, so every `cev3 drive --spawn` author seat refused at `ce launch` (three
conserved refusals: run-{b8-operator-alerting,seat-sentinels,ce11-suite-speed-p2}-20260612T0804*).

Base:
`3bdc129c997d825256c7aa6df7a546561089dc34` (origin/main = #207, the v3.1-G2f venue/seat spawn
hardening; this fix touches only the `spawn_seat` argv-composition introduced/adjacent to that
gate — no unlisted drift).

The fix (smallest-correct, §"The ratified fix"):
In `spawn_seat`, compose the `--mcp-config` ARGUMENT as a path RELATIVE to the launch process
cwd (`os.path.relpath(record.mcp_config_ref, Path.cwd())`) at argv-composition time, and REFUSE
`SpawnRefused` (fail-closed, `mark_spawn_failed`, no spawn side effect) if the relpath escapes
(a `..` prefix — exactly what CC-D-7 also rejects). The dispatch RECORD's `mcp_config_ref` stays
ABSOLUTE (D3 conserved — the record is for readers; the argv is for CC-D-7). `lane_runtime` (the
reviewer-venue path) is untouched — it composes its own relative mcp path (S8-proven).

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/d3-mcp-fix.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — `import os`; in
  `spawn_seat`, relpath-from-cwd `--mcp-config` argv value + fail-closed `..`-escape refusal;
  the RECORD's absolute `mcp_config_ref` unchanged.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — autouse `_drive_posture_cwd`
  fixture (cwd = an ancestor of the dispatch dir, the drive posture); the existing
  `--mcp-config` argv assertion relaxed off the absolute ref; two new tests — relative-argv /
  absolute-record (CC-D-7 accepts the argv), and cwd-escape → `SpawnRefused` with no spawn side
  effect. The D3 absolute-ref tests stay green unmodified.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — wheel
  rebuilt from this branch's source (`v3_seat_bridge.py` is wheel-shipped; the packaging
  contract byte-checks bundled `.py` against source).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=960af3c86ece8fa2676181402087f001129406367bf786f15b6fafb9d3534fbe

```text
.ce/pr-manifests/d3-mcp-fix.md
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_v3_seat_bridge.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
