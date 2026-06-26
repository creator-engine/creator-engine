# PR path manifest - ce177-knowledge-ssot-drift-ci

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce177-knowledge-ssot-drift-ci --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#177 adds a clean-checkout Knowledge-SSOT drift-CI path on top of the
existing brain drift checker. It does not edit workflow files; instead, it makes
the existing drift command verify a tracked authoritative `.ce/brain` ledger
when local `.ce/state` is absent.

Content-stable anchor:
The drift-CI ledger uses a normalized YAML projection over
`.github/workflows/validate.yml` to assert that `on.merge_group.types` contains
`checks_requested`. Raw full-workflow hashes are rejected for workflow/config
evidence so unrelated workflow edits do not create false drift.

Per-file purpose:
- **`.ce/brain/assertions.yaml`** *(A)* - tracked authoritative drift-CI ledger
  with a semantic workflow assertion.
- **`.ce/changelog/ce177-knowledge-ssot-drift-ci.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce177-knowledge-ssot-drift-ci.md`** *(A)* - this closed
  path-set carrier.
- **`validators/creator_engine_validator/checks/ce_brain_drift.py`** *(M)* -
  adds normalized projection verification, rejects brittle workflow full-file
  anchors, and falls back from missing repo-local `.ce/state` to `.ce/brain`.
- **`validators/tests/integration/test_ce_brain_cli.py`** *(M)* - covers CLI
  clean-checkout fallback to the authoritative ledger.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(M)* - covers projection
  pass/drift behavior, unstable workflow hash refusal, and registered drift
  discovery of `.ce/brain`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=b4ce5addbc9b90cfb52b908b895529298f29a5e063c1490ac567045b5669ed3e

```text
.ce/brain/assertions.yaml
.ce/changelog/ce177-knowledge-ssot-drift-ci.md
.ce/pr-manifests/ce177-knowledge-ssot-drift-ci.md
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_ce_brain_drift.py
```
