# PR path manifest — v3 G-3.7.2a ratification-record model

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the model half of the fourth G-3.7 slice (3.7.2a). It adds a typed
`runtime_ratification_record` to the runtime-evidence hash chain — a
G-3.6a-shaped additive extension attesting that a run was **ratified** (the
CE-owned, SHA-pinned, single-use ratification). It is its own record type on a
dimension ORTHOGONAL to the container `lifecycle_phase` (never a `lifecycle_phase`
value), and is **value-free**: it carries only opaque digests (`approver_ref` /
`ratified_prompt_sha` / `binding_ref`) + the pinned git `ratified_head_sha` + the
policy/run ids — NEVER a raw account / host / credential / installation
identifier in clear (repo/installation/permissions identity is folded into the
opaque `binding_ref`). The runtime head-SHA assertion that CONSUMES this binding
(a pure refusal in `orchestrator.py` before any `apply=True`) + the record append
are the distinct next slice **3.7.2b** — this slice is the data MODEL only.

The `$def` + a 3rd `records.items` `oneOf` arm go in
`schemas/runtime-evidence.schema.yaml` (the schema EXISTS and IS the enforcer);
`checks/ce_runtime_evidence.py` is byte-unchanged (it delegates record shape to
the schema), the spine's `append`/`verify_chain` are byte-unchanged (only additive
`RATIFICATION_RECORD_KIND`/`_TYPE` constants), and `orchestrator.py`/
`run_assembly.py`/`evidence_sink.py` are untouched. RED→GREEN, **CI-pure**. No
`schema_version` bump (additive, backward-compatible). It touches no
check/backend/CLI/wheel surface and adds no dependency -> `--list-checks` is
**unchanged at 43** and `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`. NOTE on `check-examples`: it **stays 77/0** —
the `check-examples` enumerator validates `examples/well-formed` as a single
whole-directory expectation, so the new well-formed example is absorbed by it (it
does not add a counted entry); a `check` run over the new file passes
`ce_runtime_evidence`, and a malformed ratification record is covered by a unit
test (not a new fixture). Corrections-of-record + the verified ground truth are in
`.hermes/research/v3-g3-7-live-spike-planning-20260606T053007Z/REGROUNDING_LEDGER_G3_7_20260606T063941Z.md`.

- **base:** `d0b151e40788b1a1d0270f7aba05507c21b4abaf`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=26628a938cecf793510bd74474ed979355c653c83ef8e0c4c1bc5e3e62445eb4

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-evidence.md
examples/well-formed/runtime-evidence/example-runtime-evidence-chain-ratified.yml
schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/unit/test_ce_runtime_evidence.py
```
