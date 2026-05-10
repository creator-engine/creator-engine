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
