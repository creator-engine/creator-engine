# PR path manifest - ce213-carrier-presence-gate

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce213-carrier-presence-gate --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Declared work class: story

Scope:
ce-ops#213 hardens the Validate workflow so PRs without their governance
carriers cannot pass CI. The change is limited to the path-manifest verifier,
its CLI and CI wiring, protocol documentation, and focused tests.

Per-file purpose:
- **`.ce/changelog/ce213-carrier-presence-gate.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce213-carrier-presence-gate.md`** *(A)* - this closed
  path-set carrier.
- **`.github/workflows/validate.yml`** *(M)* - runs the path-manifest gate in
  required-carrier mode for pull requests.
- **`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`** *(M)* - documents
  CI required-mode, required changelog fragments, and retained neutral default
  behavior when the flag is absent.
- **`validators/creator_engine_validator/checks/path_manifest_fidelity.py`**
  *(M)* - adds CI-required carrier and changelog presence checks while
  preserving neutral default behavior.
- **`validators/creator_engine_validator/cli.py`** *(M)* - exposes
  `--require-carrier` for the verifier.
- **`validators/tests/unit/test_path_manifest_fidelity.py`** *(M)* - covers
  missing carrier, missing changelog, and required-mode pass cases.
- **`validators/tests/unit/test_work_sizing_floor_ci_wiring.py`** *(M)* -
  asserts Validate passes the required-mode flag.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=a29831237aee0078731250ef215610384f74efaa2cd7baa17dbe8c26aea7372f

```text
.ce/changelog/ce213-carrier-presence-gate.md
.ce/pr-manifests/ce213-carrier-presence-gate.md
.github/workflows/validate.yml
docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/creator_engine_validator/cli.py
validators/tests/unit/test_path_manifest_fidelity.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```
