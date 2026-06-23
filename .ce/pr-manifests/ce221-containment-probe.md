# PR path manifest - ce221-containment-probe

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce221-containment-probe

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#221 Fix-1 — the CE containment-attestation probe, rebased on
`origin/main` `e75c9ab220b49488c1fd9ca5818bf8e725114477`. Containment must be
PROBED from the live kernel runtime, never self-reported. Build a `ce
containment-probe` subcommand that reads `/proc/<pid>` and emits a fail-closed
structured verdict (`{contained, backend, isolation, gaps, reason}`), plus pure
unit tests over fixture `/proc` trees.

The changes:
- New `containment_probe.py` runtime: a `ProcReader` seam over `/proc`, pure
  verdict logic comparing namespaces (mnt/pid/net/user) against pid 1, cgroup
  scope (runsc/docker/containerd vs host `user.slice`), backend classification
  (gvisor/bwrap/none), capability drop (`CapEff`/`CapBnd` vs full host mask),
  `NoNewPrivs`, and the `/proc/<pid>/root` mount-root target.
- Fail-closed decision: `contained=true` ONLY with positive kernel-isolation
  evidence (distinct mnt namespace AND non-host cgroup scope AND dropped caps);
  any undeterminable signal forces `contained=false` with a reason.
- `ce_cli.py` registers the `containment-probe` subcommand (pid arg defaulting
  to the current process, `--proc-root`, `--host-pid`, `--json`) and a handler
  that exits non-zero unless containment is positively proven.
- README/docs inventory and the v1 docs reconciliation guard list the new
  `ce containment-probe` command group so command docs stay in sync with the
  as-built parser surface.
- Unit tests cover the raw-host (not contained), gVisor-isolated
  (contained/backend=gvisor), bwrap-container, partial-isolation (not
  contained), undeterminable (fail-closed), purity, and CLI cases.

Per-file purpose (the closed path-set - 7 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce221-containment-probe.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce221-containment-probe.md`** *(A)* - this carrier.
- **`README.md`** *(M)* - document `ce containment-probe` in the v1 command inventory.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - register the `containment-probe` subcommand + handler.
- **`validators/creator_engine_validator/containment_probe.py`** *(A)* - live-runtime containment probe runtime.
- **`validators/tests/unit/test_containment_probe.py`** *(A)* - fail-closed/raw-host/gVisor TDD coverage.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* - expected inventory includes `containment-probe`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=8a4cceb4700730c629b0eff06aaddade543d283b795d1b04a48b0747b2a49488

```text
.ce/changelog/ce221-containment-probe.md
.ce/pr-manifests/ce221-containment-probe.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/containment_probe.py
validators/tests/unit/test_containment_probe.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
