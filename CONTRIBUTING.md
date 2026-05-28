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
  example, anything under `.hermes/` that is intended to be ignored,
  filled-in copies of `templates/hermes/session-state/STATE.template.md`,
  generated logs, local credentials, or per-machine paths). The
  constitution (Principle II) requires upstream content to remain
  reusable across deployments; instance-local state stays in ignored
  local files.
- Not contain secrets, credentials, tenant-identifying data, or any
  content that the redaction gate would reject. If you are unsure
  whether content is sensitive, see [`SECURITY.md`](./SECURITY.md) and
  use the private reporting channel for vulnerability-shaped findings.
- Include or update tests/examples when changing the validator or
  schema/template behavior.

## Local validation

Before opening a PR, please run the checks that CI also runs locally.
These are offline and require only Python 3 and the bundled
wheelhouse (see [`validators/README.md`](./validators/README.md) for
the install quickstart). From the repo root:

```bash
# Catch whitespace defects and merge-conflict markers.
git diff --check

# Validate bundled well-formed and malformed examples against schemas.
PYTHONPATH=validators python3 -m creator_engine_validator check-examples

# Run the no-LIMITLESS generic-path scan (LIMITLESS is the named
# dogfood tenant; generic paths must not hardcode it).
PYTHONPATH=validators python3 -m creator_engine_validator scan-no-limitless
```

If you change the validator, schemas, or examples, also run the full
check suite:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator check
```

A PR whose changes do not pass these checks locally will not pass CI.

## Code of conduct, security, license

- All participation is subject to the
  [Code of Conduct](./CODE_OF_CONDUCT.md).
- Security-sensitive issues must be reported privately per
  [`SECURITY.md`](./SECURITY.md), not in public issues or PRs.
- By contributing, you agree that your contributions are licensed
  under the project's Apache License, Version 2.0
  (see [`LICENSE`](./LICENSE)).

Thanks for helping keep Creator Engine governed, auditable, and
useful.
