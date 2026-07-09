# PR path manifest — ce-p3-rehearsal-s1 · Fresh-Tenant Rehearsal harness slice 1

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-p3-rehearsal-s1
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

The change:
Fresh-Tenant Rehearsal harness slice 1 under `deploy/rehearsal/`. The harness runs
fail-closed unless `--live` is supplied, installs CE from the public signed-release
installer in a clean Docker container with no host checkout mount, walks the documented
Solo + CEO first-hour stage list, stubs live model/GitHub/PR/completed-run phases with
explicit `CE_REHEARSAL_STUB:` markers, and emits a schema-versioned JSON evidence bundle.

Per-file purpose (closed path-set — 6 paths):
- **`.ce/changelog/ce-p3-rehearsal-s1.md`** *(A)* — changelog fragment, work class story.
- **`.ce/pr-manifests/ce-p3-rehearsal-s1.md`** *(A)* — this carrier (self-inclusive).
- **`deploy/rehearsal/README.md`** *(A)* — public usage, environment, container, stage, and stub inventory docs.
- **`deploy/rehearsal/evidence-format.md`** *(A)* — authoritative JSON evidence schema and versioning policy.
- **`deploy/rehearsal/run-rehearsal.sh`** *(A)* — main CLI entrypoint for dry-run/live/list/help and stage execution.
- **`deploy/rehearsal/test_rehearsal_smoke.sh`** *(A)* — Docker-free targeted smoke test for dry-run behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d90c54840efa37f4c6c34015571e891160af0853771f1deccdb0d9a38d98915b

```text
.ce/changelog/ce-p3-rehearsal-s1.md
.ce/pr-manifests/ce-p3-rehearsal-s1.md
deploy/rehearsal/README.md
deploy/rehearsal/evidence-format.md
deploy/rehearsal/run-rehearsal.sh
deploy/rehearsal/test_rehearsal_smoke.sh
```
