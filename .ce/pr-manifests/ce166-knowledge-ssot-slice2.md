# PR path manifest - ce166-knowledge-ssot-slice2

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce166-knowledge-ssot-slice2 --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#166 slice 2 makes the Knowledge-SSOT assertion ledger a tracked
authoritative fleet store, refreshes the local runtime copy at bootstrap, and
checks loaded runtime state for drift from the authoritative ledger.

Per-file purpose:
- **`.ce/brain/assertions.yaml`** *(A)* - authoritative versioned fleet brain
  assertion ledger with bounded migrated shared capability and convention
  assertions.
- **`.ce/changelog/ce166-knowledge-ssot-slice2.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce166-knowledge-ssot-slice2.md`** *(A)* - this closed
  path-set carrier.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(M)* - refreshes
  local runtime state from the authoritative ledger before projection.
- **`validators/creator_engine_validator/brain_probe.py`** *(M)* - adds
  deterministic probes for committed Codex hook and fan-out surfaces.
- **`validators/creator_engine_validator/brain_runtime.py`** *(M)* - adds
  authoritative ledger path/load/sync helpers while preserving local ledger
  validation.
- **`validators/creator_engine_validator/checks/ce_brain_drift.py`** *(M)* -
  fails stale loaded ledgers that diverge from the authoritative store.
- **`validators/tests/unit/test_brain_bootstrap.py`** *(M)* - covers corrected
  authoritative assertions being picked up at next bootstrap.
- **`validators/tests/unit/test_brain_probe.py`** *(M)* - covers new committed
  hook and fan-out surface probes.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(M)* - covers stale
  loaded ledger drift plus migrated assertion validation/probes.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=a37c213ec94a710dce5eb5874849c1f57408dd3cfe15dba06379aa9666a36a1e

```text
.ce/brain/assertions.yaml
.ce/changelog/ce166-knowledge-ssot-slice2.md
.ce/pr-manifests/ce166-knowledge-ssot-slice2.md
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/brain_probe.py
validators/creator_engine_validator/brain_runtime.py
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_brain_bootstrap.py
validators/tests/unit/test_brain_probe.py
validators/tests/unit/test_ce_brain_drift.py
```
