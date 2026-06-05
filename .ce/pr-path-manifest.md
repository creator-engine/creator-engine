# PR path manifest — v3 G-3.6a run-outcome / terminal-disposition model

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR resolves the **G-3.6a run-outcome / terminal-disposition model**
(Operator-decided Option A): a run's terminal outcome is modelled as a typed
`runtime_run_outcome` record appended to the SAME tamper-evident hash chain —
orthogonal to the container `lifecycle_phase` axis, never a `lifecycle_phase`
value. This makes a real PR-opening run's evidence schema-valid + persistable
(replacing the G-3.5 sink's `change-opened` refuse-stub). The change is:

- `schemas/runtime-evidence.schema.yaml` — a new `runtime_run_outcome_record`
  `$def` admitted via a `records.items` `oneOf` (`outcome` enum + a value-free
  `change_set` pointer; no `lifecycle_phase`).
- `validators/creator_engine_validator/runtime_evidence_spine.py` — additive
  `RUN_OUTCOME_RECORD_KIND` / `RUN_OUTCOME_RECORD_TYPE` / `RUN_OUTCOMES`
  constants (no behavior change).
- `validators/creator_engine_validator/orchestrator.py` — the terminal step now
  appends a typed `runtime_run_outcome` record via the spine `append` (instead
  of a `lifecycle_phase="change-opened"` record), reusing one clock instance and
  capturing the `ChangeRef`'s `pr_number` when present.
- a new well-formed example fixture + the `docs/contracts/runtime-evidence.md`
  contract section + the flipped/added unit tests.

The sink (`evidence_sink.py`), the audit overlay (`runner/audit_overlay.py`), the
`ce_runtime_evidence` check, and every backend are **byte-unchanged** — the check
delegates record shape to the schema and the sink persists any schema-valid
chain, so admitting the new record type flips the refuse-stub for free.
`--list-checks` is **unchanged at 43**; `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`; no `ce_cli.py`/wheel/requirements/pyproject
change. The contract doc passes `ce_terminology_v2` and `no_limitless_strings`.

- **base:** `258a8fb6943487fc194788d09e1f9967da0cb5d1`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=c8e729720c7dc6fbd1c26f12ea9c8206fbd89987161734d5b532106748d99f9a

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-evidence.md
examples/well-formed/runtime-evidence/example-runtime-evidence-chain-pr-opened.yml
schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/unit/test_ce_runtime_evidence.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_orchestrator.py
```
