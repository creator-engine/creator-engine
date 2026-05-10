# Contract: Validator CLI

**Source FRs**: FR-025, FR-026, FR-027, FR-027a

## Purpose

The substrate's machine-checkable validator. Runs from a fresh `git
clone` with no external service calls. Reports violations with
contract-referenced errors citing the specific field or rule violated.

## Implementation surface

- `validators/creator_engine_validator/` — Python 3.11 package.
- `validators/requirements.txt` — `PyYAML`, `jsonschema`.
- `validators/pyproject.toml` — package metadata, console_script
  entrypoint.
- `validators/README.md` — invocation guide.

## Invocation

`python -m creator_engine_validator <subcommand> [paths…] [flags]`

## Subcommands

- `check [paths…]` — runs all enabled checks against the given paths
  (default: repository root). Default subcommand for CI-style use.
- `check-examples` — runs `check` against `examples/well-formed/` and
  `examples/malformed/`, asserting the documented outcomes per
  FR-028 / FR-029 / SC-006. It exits `0` when the well-formed fixtures
  pass and every malformed fixture fails with the expected FR citation;
  it exits `1` when those expectations are not met.
- `scan-no-limitless` — runs only the FR-024 / FR-024a no-LIMITLESS
  exact-string scan against the four generic-contract paths.
- `--list-checks` — prints the enabled checks and the FRs each one
  enforces (audit support for FR-027).

## Flags

- `--json` — machine-readable output suitable for inclusion in
  Verification Evidence references (FR-014).
- `--tenant <name>` — restricts cross-artifact checks to one tenant
  (e.g. `tenants/limitless/`).

## Exit codes

- `0` — all enabled checks passed.
- `1` — at least one check failed (validation failure).
- `2` — invocation error (missing path, malformed CLI args).

## Required checks (one-to-one with checks/ module)

- `identity.py` (FR-001..FR-005)
- `sidecar_conformance.py` (FR-009/012a/012b)
- `mutation_class.py` (FR-006..FR-008, FR-027a class/action mismatch)
- `lifecycle.py` (FR-013a transitions and ordering)
- `definition_of_ready.py` (FR-013)
- `definition_of_done.py` (FR-014, attestation linkage)
- `duplicate_spec_id.py` (FR-027a)
- `attestation_linkage.py` (FR-004, FR-020a)
- `ratification.py` (FR-007, FR-016..FR-018)
- `redaction_gate.py` (FR-019..FR-021)
- `no_limitless_strings.py` (FR-024, FR-024a, SC-004)

## Performance and isolation

- Runs offline. No HTTP, no DNS, no external service calls (FR-026,
  FR-027a v0.1 exclusion list).
- Completes a full pass on the bundled examples in under 60 seconds
  on a developer workstation (SC-007).

## Error message contract (FR-027)

Every validator failure cites:
- The FR or contract clause violated (e.g. `FR-007`, `FR-013a`).
- The specific field or path that violated it (e.g.
  `examples/malformed/identity-record.missing-fields.yml:
  human_ratifier_roles`).
- The contract document the reader can consult
  (e.g. `docs/contracts/identity-record.md`).

## Acceptance evidence

- Spec User Story 7, Acceptance Scenarios 1–3.
- SC-006: every well-formed example passes; every malformed example
  fails with a specific field-level or rule-level error.
- SC-007: full pass under 60 seconds on a fresh `git clone`, no
  network.
