# PR path manifest - ce259-worker-run

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce259-worker-run --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#259 adds a discoverable `ce worker run --role <role> --brief <file>`
command that resolves `.claude/agents/<role>.md`, launches through the existing
governed worker-spawn primitive, seeds the launched pane with a pointer-only
prompt/findings instruction, and returns structured findings through an
offline-testable collector seam.

Per-file purpose:
- **`.ce/changelog/ce259-worker-run.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce259-worker-run.md`** *(A)* - this closed path-set
  carrier.
- **`docs/operations/WORKER_CONTAINER_PROTOCOL.md`** *(M)* - documents
  `ce worker run` as the sanctioned role-brief path and enumerates deferrals.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classifies the
  new worker-run module as v1 kernel runtime beside `worker_spawn`.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - exposes
  `ce worker run`, JSON output, and testable launcher/seeder/collector
  factories.
- **`validators/creator_engine_validator/worker_run.py`** *(A)* - implements
  role resolution, prompt materialization, worker-spawn composition, pointer-only
  prompt seeding, and findings normalization/collection.
- **`validators/creator_engine_validator/worker_spawn.py`** *(M)* - recognizes
  `architect_research` as a read-only worker-spawn role.
- **`validators/tests/unit/test_ce_worker_cli.py`** *(M)* - covers CLI
  discoverability, mocked run round trip, and unknown-role fail-closed behavior.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - updates the v1
  runtime count/classification expectation for `worker_run`.
- **`validators/tests/unit/test_worker_run.py`** *(A)* - covers role resolution,
  missing/unknown role refusal, mocked launch-to-findings behavior, and
  seed-phase fail-closed behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=3f4d140728f384d90ef731f380c472a5b11b62b607630ae721d6fc3ba8172374

```text
.ce/changelog/ce259-worker-run.md
.ce/pr-manifests/ce259-worker-run.md
docs/operations/WORKER_CONTAINER_PROTOCOL.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/worker_run.py
validators/creator_engine_validator/worker_spawn.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_worker_run.py
```
