# PR path manifest — v3 G-3.5 evidence persistence sink (`evidence_sink.py`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR (it adds Python under `validators/`). It adds the G-3.5
evidence persistence sink: a new top-level `evidence_sink.py` exporting
`file_evidence_sink(root, *, write=None) -> EvidenceSink`, which serializes a
run's `CollectedEvidence` (the `AuditOverlayBackend` hash-chain) into a durable
file matching `schemas/runtime-evidence.schema.yaml` — persisting iff
`verify_chain()==[]` AND the chain validates against the schema, else raising a
value-free `EvidencePersistRefused` and writing nothing. The write goes through
an injectable `write` seam (the lone live line); the new
`tests/unit/test_evidence_sink.py` drives every path with a fake `write` (zero
live filesystem write / network / subprocess). It reuses `CollectedEvidence`,
`verify_chain` / `CHAIN_KIND` / `CONTENT_HASH_FIELD`, and `validate_with_schema`
by import; it adds **no** `@register` check, **no** backend, and **no** schema
(the runtime-evidence schema + `ce_runtime_evidence` check pre-exist) →
`--list-checks` is **unchanged at 43** and `available_backends()` is unchanged
at `('gvisor-proxy', 'local-noop')`; no `ce_cli.py`/wheel/`requirements`/
`pyproject.toml` change. The frozen runtime-evidence substrate
(`runtime_evidence_spine.py`, `schemas/runtime-evidence.schema.yaml`,
`checks/ce_runtime_evidence.py`), `orchestrator.py`, and every backend stay
byte-unchanged. The `run_plan` `evidence_sink` seam + the run-outcome model are
G-3.6 (this slice REFUSES a `change-opened` chain rather than persist it).

- **base:** `59ecf8b32449da1decca6461b2ae9e85a1f47e9b`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=863a219c6f3ae42161fd098142b4bc65a245334c99308cd261d38a9ca359b1a4

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/evidence_sink.py
validators/tests/unit/test_evidence_sink.py
```
