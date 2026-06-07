# PR path manifest — v3 G-3.7b.0 `pr_merged` run-outcome model (CI-pure, additive)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the data MODEL half of the gated-merge substrate (G-3.7b.0) — it adds the
**`pr_merged`** terminal run-outcome to the run-disposition vocabulary: a new
member of the spine `RUN_OUTCOMES` tuple + the `runtime-evidence.schema.yaml`
`runtime_run_outcome_record.outcome` enum + the prose contract, plus a new
well-formed `example-runtime-evidence-chain-pr-merged.yml` and accept tests. The
change is **ADDITIVE** — the existing four outcome members + the record shape +
the other `$defs` + `append`/`verify_chain`/`canonical_content_hash` are
byte-unchanged, and there is **NO `schema_version` bump** (the G-3.7.2a
precedent; existing chains still validate). `pr_merged` is **producer-less** in
this slice — its producer (the merge-driving seam + the distinct merge-identity
seam) is the next slice **G-3.7b.1**, and the live merge is the out-of-envelope
**G-3.8**. It touches no orchestrator/run_assembly/forge/check/backend/CLI/wheel
surface and adds no dependency → `--list-checks` STAYS **43**,
`available_backends()` is unchanged, and `check-examples` STAYS **77/0** (the new
well-formed example is absorbed by the whole-`examples/well-formed` expectation
entry — NOT 78). RED→GREEN, CI-pure (no live `gh`/network/`apply=True`). Design
source: the in-repo `docs/architecture/pilot-roadmap.md` §"G-3.7b / G-3.8".

- **base:** `ab83629f1105550985a9577b721a3991cf6c397c`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=a385d83a9af5d20316ec0bb0302816343e9ae3a0483dfd2a8c61b9f19e12ce5f

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-evidence.md
examples/well-formed/runtime-evidence/example-runtime-evidence-chain-pr-merged.yml
schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/unit/test_ce_runtime_evidence.py
```
