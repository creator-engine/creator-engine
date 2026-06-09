# PR path manifest — feat(v3.5-batch): land A.2b-i + D.0.3 + Gate A v2 + Gate B in one combined branch

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **a single combined branch consolidating four already-independently-reviewed
v3.5 PRs**, after Gate C (#182) merged to `main`. Collapsing them avoids the
serial rebase+re-review tax that this repo's branch protection
(`strict` + `dismiss_stale` + code-owner) imposes on a batch of PRs that all
rewrite the single shared `.ce/pr-path-manifest.md`. Each change below was
approved on its own PR; this branch is their faithful union on top of `main`.

- **Gate B (#183)** — scope governed posture to the live ledger (injection-first);
  preserves the posture-gated push hard-deny. Cherry-picked onto `main`; the
  `cli.py`/`hook_check.py`/`test_hook_check.py` overlap with Gate C (#182, already
  on `main`) was resolved by combining both: Gate B's launch-pinned `ledger_root`
  threading + Gate C's `ResolvedManifest`/no-write-authority posture note.
  Files: `.claude/hooks/ce-hook-common.sh`, `.claude/hooks/ce-pretooluse.sh`,
  `docs/operations/CLAUDE_CODE_HOOK_PACK.md`, `cli.py`, `hook_check.py`,
  `lane_runtime.py`, `test_hook_check_cli.py`, `test_ce_lane_cli.py`,
  `test_hook_check.py`.
- **A.2b-i (#181)** — OpenShell backend surface corrected to the live-verified
  gateway, including the ratified `protocol: rest` endpoint axis (omitted only for
  `access: full`). Files: `runner/openshell_backend.py`,
  `tests/unit/fixtures/openshell_ocsf_textlog.sample`, `test_openshell_backend.py`.
- **D.0.3 (#180)** — reproducible dogfood-fleet compute-demand driver. Files:
  `examples/fleet_measure.py`, `fixtures/fleet_measure_sample.jsonl`,
  `test_fleet_measure.py`.
- **Gate A v2 (#184)** — wheel↔source fidelity guard + pyproject package
  auto-discovery. Files: `packaging_runtime.py`, `pyproject.toml`,
  `test_packaging_contract.py`, `wheelhouse/SHA256SUMS`, the app wheel. **The app
  wheel was rebuilt from THIS combined source** (it now packages Gate B's and
  A.2b-i's `.py` changes) and `SHA256SUMS` re-pinned, so the skew guard is green.

**Version-boundary impact = ZERO.** No new `runner.*` module, no schema change,
no check registration, no `runner/__init__.py` export; `V3_RUNTIME` stays **28**
and `--list-checks` stays byte-identical.

- **base:** current `main` (post-#182; `7eb09f3`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=21

AUTHORIZED_PATHS_SHA256=41aa75f327dac68b48036b691649f7188ba4881342fd8f26ef1752bc67c609cc

```text
.ce/pr-path-manifest.md
.claude/hooks/ce-hook-common.sh
.claude/hooks/ce-pretooluse.sh
docs/operations/CLAUDE_CODE_HOOK_PACK.md
examples/fleet_measure.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/packaging_runtime.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/pyproject.toml
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/fixtures/fleet_measure_sample.jsonl
validators/tests/unit/fixtures/openshell_ocsf_textlog.sample
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_fleet_measure.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_packaging_contract.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
