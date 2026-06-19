# PR path manifest - ce115-wave1-controller-containment

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce115-wave1-controller-containment

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Wave 1 scope for ce-ops#115 Controller containment on 2026-06-19. Build exactly
Gates 1 and 2 of the adopted `cedev2 -> DGX` containment blueprint, rebased on
`origin/main` `83242b984067e0c6f45e072550fdbf589004e64e`, and exclude Gates
3-7. Gate 1 updates schema/protocol/validator enforcement for
`role: controller`, contained Controller posture, and forbidden-surface
predicates. Gate 2 adds `deploy/dgx-controller-runsc` as a sibling of merged
ce-ops#128 / `3d9e86a`.

The changes:
- The Controller Runtime Contract supports legacy `host-local` records and
  contained records with `.ce/state/`, required forbidden surfaces for
  tmux/SSH/git-push/ACP/TUI/runtime-socket/private-key/root-token exposure, and
  request-handle names for Max auth, OpenBao `ce-root-v1` signing, and GitHub
  App installation tokens.
- The validator registers `RV1-020-CONTAINMENT` and enforces contained posture
  predicates beyond the schema.
- The DGX Controller runsc artifact adds an image, wrapper, dry-run argv tests,
  refusal behavior for known-bad DGX runtime/network paths, and build docs.
- The packaged validator app wheel is rebuilt on the rebased source so it
  includes both the merged ce-ops#120 `reviewer_triage.py` source and this PR's
  `controller_runtime_contract.py` source.
- The ratified design doc is retained in-branch as implementation context.
- Gates 3-7 supervisor/runtime/fan-in work is not implemented.

Per-file purpose (the closed path-set - 17 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce115-wave1-controller-containment.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce115-wave1-controller-containment.md`** *(A)* - this carrier.
- **`.ce/state/research/DESIGN_ce115_controller_containment_20260619T043931Z.md`** *(A)* - adopted design blueprint retained in branch.
- **`deploy/dgx-controller-runsc/Dockerfile`** *(A)* - minimal seat-matched DGX Controller image.
- **`deploy/dgx-controller-runsc/README.md`** *(A)* - DGX image-build, runtime, dry-run, and scope docs.
- **`deploy/dgx-controller-runsc/run-controller-runsc.sh`** *(A)* - dry-runable Claude Controller wrapper under `runsc-gvproxy-ptrace`.
- **`docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`** *(M)* - protocol update for role and contained posture.
- **`examples/malformed/controller-runtime-contract/misclassified-hosted-authority.yaml`** *(M)* - add required `role`.
- **`examples/malformed/controller-runtime-contract/secret-value.yaml`** *(M)* - add required `role`.
- **`examples/well-formed/controller-runtime-contract/contained.yaml`** *(A)* - contained contract fixture.
- **`examples/well-formed/controller-runtime-contract/minimal.yaml`** *(M)* - add required `role`.
- **`schemas/controller-runtime-contract.schema.yaml`** *(M)* - schema support for role and contained posture fields.
- **`validators/creator_engine_validator/checks/controller_runtime_contract.py`** *(M)* - containment predicate enforcement.
- **`validators/tests/unit/test_controller_runtime_contract.py`** *(M)* - Gate 1 TDD coverage.
- **`validators/tests/unit/test_dgx_controller_runsc.py`** *(A)* - Gate 2 dry-run argv/refusal coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refresh only the app-wheel checksum line.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt validator app wheel from rebased source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=6125ceb513a57c825a3cbe4355d2648d60efed3b22ea9bd7f42f2cf7dd06b785

```text
.ce/changelog/ce115-wave1-controller-containment.md
.ce/pr-manifests/ce115-wave1-controller-containment.md
.ce/state/research/DESIGN_ce115_controller_containment_20260619T043931Z.md
deploy/dgx-controller-runsc/Dockerfile
deploy/dgx-controller-runsc/README.md
deploy/dgx-controller-runsc/run-controller-runsc.sh
docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md
examples/malformed/controller-runtime-contract/misclassified-hosted-authority.yaml
examples/malformed/controller-runtime-contract/secret-value.yaml
examples/well-formed/controller-runtime-contract/contained.yaml
examples/well-formed/controller-runtime-contract/minimal.yaml
schemas/controller-runtime-contract.schema.yaml
validators/creator_engine_validator/checks/controller_runtime_contract.py
validators/tests/unit/test_controller_runtime_contract.py
validators/tests/unit/test_dgx_controller_runsc.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
