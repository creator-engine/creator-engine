# PR path manifest - ce-l3-triage-ready-queue-p0

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-L3-triage-ready-queue-p0 --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
Adds the P0 advisory ce-ops inbound triage queue: a hidden `ce triage queue`
scan/inspect surface, a queue runtime that reuses existing forge triage
classification primitives, an offline unit test suite, and a fail-open scheduled
workflow that defaults to dry-run.

Non-authority posture:
The queue does not ratify, approve, review, merge, authorize dispatch, or block
CI. `--apply` patches an existing sentinel comment only; it does not create the
ce-ops#67 sentinel comment.

Per-file purpose:
- **`.ce/changelog/ce-l3-triage-ready-queue-p0.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-l3-triage-ready-queue-p0.md`** *(A)* - this closed path-set carrier.
- **`.ce/reference/cli.generated.md`** *(M)* - regenerated CLI reference after adding the internal `triage` group.
- **`.github/workflows/ce-ops-triage-queue.yml`** *(A)* - fail-open scheduled/manual advisory triage queue workflow.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - hidden `ce triage queue scan|inspect` parser and dispatch handlers.
- **`validators/creator_engine_validator/ce_ops_triage_queue.py`** *(A)* - advisory queue runtime and GitHub I/O seam.
- **`validators/tests/unit/test_ce_ops_triage_queue.py`** *(A)* - offline unit coverage for queue parsing, rendering, scan, apply, audit, CLI help, and forge-triage coupling.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* - register the new internal `triage` command group in the as-built CE inventory guard.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=00540c8a10e7ac05ba2c780d74a24eabe879b1173967de9c52799d0fc5a67aad

```text
.ce/changelog/ce-l3-triage-ready-queue-p0.md
.ce/pr-manifests/ce-l3-triage-ready-queue-p0.md
.ce/reference/cli.generated.md
.github/workflows/ce-ops-triage-queue.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/ce_ops_triage_queue.py
validators/tests/unit/test_ce_ops_triage_queue.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
