# Creator Engine Validator

Offline, repository-local validator for the Creator Engine v0.1 governance substrate.

## Offline runtime install

From a fresh clone, create a virtualenv and install only the validator runtime dependencies from the checked-in runtime wheelhouse:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
```

The validator must not call external services during installation from `validators/wheelhouse/` or during validation. Runtime installs intentionally do not include pytest or other test-only dependencies.

## Offline dev/test install

To run the validator test suite from a fresh clone without network access, install the runtime and test-only dependency sets from their separate checked-in wheelhouses:

```bash
python -m venv .venv-test
.venv-test/bin/pip install --no-index \
  --find-links validators/wheelhouse \
  --find-links validators/wheelhouse-dev \
  -r validators/requirements.txt \
  -r validators/requirements-dev.txt
PYTHONPATH=validators .venv-test/bin/python -m pytest validators/tests -q
```

`validators/requirements-dev.txt` and `validators/wheelhouse-dev/` are for developer/test tooling only. Keep `validators/requirements.txt` and `validators/wheelhouse/` runtime-only.

## Invocation

```bash
python -m creator_engine_validator --list-checks
python -m creator_engine_validator check examples/well-formed/
python -m creator_engine_validator check-examples
python -m creator_engine_validator scan-no-limitless
```

## Exit codes

- `0`: all enabled checks passed.
- `1`: at least one validation failure.
- `2`: invocation error.

Each validation failure cites the violated FR or contract clause, the specific field/path, and the contract document to consult.

## `role_boundary_attribution` scope and limitations

The `role_boundary_attribution` check (contract: `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`) is a Phase-1 audit aid for R-011 controller-seat-edit pressure. It runs in two distinct modes, and its limitations matter when reading its output:

- **Default whole-tree mode (advisory, not a hard failure).** Invoked through `python -m creator_engine_validator check <paths>` (and `check-examples`). It scans documents whose front matter declares `kind: hermes-handoff` or `kind: hermes-recommended-prompt` and emits *warnings* — never errors — when a `role: controller` document also carries a fenced path manifest. Whole-tree mode is intentionally conservative: it gives the verifier a starting point and MUST NOT be relied on as a hard governance gate. A clean default run does not by itself prove that no boundary breach occurred; conversely, a warning is a signal to investigate, not a CI-blocking error.
- **`verify-attribution --base <commit>` mode (best-effort, fresh-clone limited).** Compares the changed files between `<base>..HEAD` against the active handoff manifests under `.hermes/handoffs/` and emits errors for any changed file not covered by an active handoff. This mode REQUIRES `.hermes/handoffs/` to be present and readable in the worktree. A fresh clone of the upstream public repository does NOT carry `.hermes/` and so this mode is unavailable there; the check emits `role_boundary_no_active_handoff` rather than silently passing. Operators relying on attribution evidence outside of an environment with `.hermes/` populated must use an alternative attribution record.

Both modes are verifier evidence. Neither ratifies a batch.
