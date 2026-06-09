# PR path manifest — feat(v3.5-A.2b-i): correct OpenShell backend surface to the live-verified gateway

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **A.2b-i — correct the OpenShell `RunnerBackend` policy surface to the
field names the live-verified OpenShell gateway accepts.**

- `validators/creator_engine_validator/runner/openshell_backend.py`: the
  policy-render surface aligned to the live gateway's `PolicyFile` struct.
- `validators/tests/unit/fixtures/openshell_ocsf_textlog.sample`: the recorded
  OCSF sample the parser test reads.
- `validators/tests/unit/test_openshell_backend.py`: unit coverage for the
  corrected surface render and the OCSF parser.

**Version-boundary impact = ZERO.** This slice edits an existing `runner.*`
module's render surface only; no new module, no schema change, no check
registration, no `runner/__init__.py` export; `V3_RUNTIME` stays **28** and
`--list-checks` stays byte-identical.

- **base:** `97dbc28e8c72717759d572ec4b022e854331048a` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=f70d9f86db75f5d232a606d90e89675951d4c52684bf6a690d4fa66ef2df992e

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/runner/openshell_backend.py
validators/tests/unit/fixtures/openshell_ocsf_textlog.sample
validators/tests/unit/test_openshell_backend.py
```
