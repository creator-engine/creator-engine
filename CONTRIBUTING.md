# Contributing to Creator Engine

Thanks for your interest in Creator Engine. This document is the
public on-ramp for contributors. Creator Engine is a pre-1.0,
spec-driven, ratification-governed substrate, so the contribution
workflow is more structured than for many open-source projects:
contributions are expected to follow the spec/plan/tasks model and
to respect the project's ratification boundaries.

By participating in this project you agree to abide by the
[Code of Conduct](./CODE_OF_CONDUCT.md).

## How Creator Engine work is organized

Creator Engine work is driven by:

- The constitution at
  [`.specify/memory/constitution.md`](./.specify/memory/constitution.md)
  — highest-authority governance document.
- Feature specifications under [`specs/`](./specs/) — each feature is
  defined by a `spec.md`, `plan.md`, `tasks.md`, and supporting
  artifacts (see [`specs/001-v0-1-governance-substrate/plan.md`](./specs/001-v0-1-governance-substrate/plan.md)
  for an example).
- The canonical document set indexed in [`README.md`](./README.md).
- The governance and authority on-ramp in
  [`GOVERNANCE.md`](./GOVERNANCE.md).

If you are unfamiliar with the model, read the README, GOVERNANCE,
and at least one feature's `spec.md` / `plan.md` / `tasks.md` triple
before opening a change.

## What kinds of changes are welcome

External contributors are welcome to:

- Open issues that describe a defect, ambiguity, or improvement
  suggestion. Reference the affected file paths and, where relevant,
  the canonical document or feature spec.
- Propose small, well-scoped pull requests that fix typos, clarify
  prose, fix validator bugs, or add tests inside an existing feature
  scope.
- Discuss potential larger changes in an issue first, so that any
  required spec/plan/tasks updates and ratifier expectations can be
  identified before code is written.

Large architectural changes, new mutation classes, modifications to
the constitution, the Feature 001 governance substrate, the Feature 002
operating model, or anything that crosses a privileged-class boundary
require explicit Operator/maintainer authorization before
implementation. These changes are themselves Creator-Engine-governed
mutations, not ordinary pull requests, and will not be merged from
unsolicited PRs.

## Ratification boundaries and privileged operations

Creator Engine distinguishes between work that CI verifies and work
that humans ratify. Contributors should not attempt privileged
operations without explicit Operator/maintainer authorization. The full
taxonomy is in
[`docs/governance/MUTATION_CLASS_MODEL.md`](./docs/governance/MUTATION_CLASS_MODEL.md);
the privileged classes that require Operator ratification include:

- `deploy`
- `governance`
- `identity`
- `security`
- `attestation`
- `redaction`

Examples of operations a contributor must **not** perform without
explicit authorization:

- Repo-visibility or repo-settings changes.
- Branch-protection rule changes.
- Git history rewrites (`push --force`, history surgery on shared
  branches).
- Changes to the constitution
  (`.specify/memory/constitution.md`) or to canonical governance
  documents under `docs/governance/`.
- Changes that would broaden the redaction surface or weaken the
  no-LIMITLESS generic-path scan.
- Mutating external trackers, deploying, or otherwise reaching outside
  the repository on behalf of the project.

When in doubt, open an issue and ask before sending a PR.

## Pull request expectations

Pull requests should:

- Reference the relevant spec/feature where applicable.
- Keep a clean changed-file boundary — touch only what the change
  requires, and avoid sweeping unrelated reformatting or churn.
- Avoid checking in instance-local runtime or session state (for
  example, anything under `.ce/state/`, legacy `.hermes/` runtime
  state kept ignored for backward compatibility, filled-in copies of
  `templates/hermes/session-state/STATE.template.md`, generated logs,
  local credentials, or per-machine paths). The
  constitution (Principle II) requires upstream content to remain
  reusable across deployments; instance-local state stays in ignored
  local files.
- Not contain secrets, credentials, tenant-identifying data, or any
  content that the redaction gate would reject. If you are unsure
  whether content is sensitive, see [`SECURITY.md`](./SECURITY.md) and
  use the private reporting channel for vulnerability-shaped findings.
- Include or update tests/examples when changing the validator or
  schema/template behavior.

## Optional local diagnostics

The following offline checks are optional iteration diagnostics; see
[`validators/README.md`](./validators/README.md) for setup. They cannot
substitute for required CI on the pushed current head.

```bash
# Catch whitespace defects and merge-conflict markers.
git diff --check

CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"

# Validate bundled well-formed and malformed examples against schemas.
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator check-examples

# Run the no-LIMITLESS generic-path scan (LIMITLESS is the named
# dogfood tenant; generic paths must not hardcode it).
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator scan-no-limitless
```

If you change the validator, schemas, or examples, you may also run the full
local diagnostic suite:

```bash
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator check
```

Commit the complete carrier set, push that final head, open or update the PR,
and wait for the required Validate run bound to that exact head. Record its
URL/status together with independent review and ratification evidence.

> **Running from an isolated worktree (creator-engine#82)?** CE lane worktrees under
> `ce-worktrees/*` have no local `.venv`; set `CE_VALIDATOR_PYTHON` to a known
> interpreter before invoking source-backed validator commands from that worktree.
> See [`validators/README.md`](./validators/README.md).

## Developer install (from source, editable)

Use this path when you want the installed Creator Engine command-line tools to
run directly from your local checkout while you edit files under `validators/`.
It requires Python 3.14 and `uv`.

For a fresh contributor checkout:

```bash
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/creator-engine/creator-engine.git
cd creator-engine
git switch main
git pull
```

Then create the validator virtual environment and install the package in
editable mode:

```bash
uv venv --python 3.14 validators/.venv
CE_VALIDATOR_PYTHON=validators/.venv/bin/python
uv pip install --python "$CE_VALIDATOR_PYTHON" -e validators/
```

Verify that the expected console scripts were installed:

```bash
validators/.venv/bin/ce --version
validators/.venv/bin/cev3 --help
validators/.venv/bin/creator-engine-validator --list-checks
```

Depending on the change you are making, you may only need one of `ce`, `cev3`,
or `creator-engine-validator`, but all three are installed by the same
`creator-engine-validator` Python distribution.

Editable installs use the package build backend declared in
`validators/pyproject.toml` (`setuptools.build_meta`). If your environment
already has the needed build backend available through an online index or local
package cache, the command above is sufficient.

For a fully offline editable install, install from the checked-in wheelhouses so
both runtime dependencies and the build backend are available:

```bash
UV_PYTHON_DOWNLOADS=never uv pip install \
  --python "$CE_VALIDATOR_PYTHON" \
  --offline \
  --no-index \
  --find-links validators/wheelhouse \
  --find-links validators/wheelhouse-dev \
  -r validators/requirements.txt \
  -e validators/
```

The runtime wheelhouse alone is intentionally runtime-only; it may not contain
`setuptools`, so an offline editable install can fail while resolving
`build-system.requires`. If you only need the runtime or test dependency setup
without an editable install, use the offline runtime or dev/test install paths
in [`validators/README.md`](./validators/README.md).

## Version boundary (v1 ↔ v3)

Creator Engine v1.0 and v3.x coexist in this repository on a shared base, and
the two execution runtimes are kept import-disjoint. The `version_boundary`
check (run by `check` above) enforces this: a `v1` module must not import a `v3`
module or vice-versa, and a `shared` (validator-engine / durable-infra) module
must not import a version-specific module except via the small baselined
allowlist. When you add code, classify any new runtime module in
`creator_engine_validator/_versions.py`, do not cross the v1⊥v3 boundary, and do
not introduce a new `shared`→version import. See
[`docs/architecture/VERSION_BOUNDARY.md`](./docs/architecture/VERSION_BOUNDARY.md).
Removing v1.0 code is governed, not routine — propose it as an orphaned-only
change proven unused by both versions.

## Code of conduct, security, license

- All participation is subject to the
  [Code of Conduct](./CODE_OF_CONDUCT.md).
- Security-sensitive issues must be reported privately per
  [`SECURITY.md`](./SECURITY.md), not in public issues or PRs.
- By contributing, you agree that your contributions are licensed
  under the project's Apache License, Version 2.0
  (see [`LICENSE`](./LICENSE)).
- By contributing, you certify the Developer Certificate of Origin for each commit by adding a `Signed-off-by: Name <email>` trailer, usually with `git commit -s`.

Thanks for helping keep Creator Engine governed, auditable, and
useful.
