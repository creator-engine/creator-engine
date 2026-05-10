# LIMITLESS Dogfood Tenant Fixture

This directory will hold the concrete LIMITLESS tenant mapping for the Creator Engine v0.1 governance substrate.

Planned files:

- `limitless-identifiers.yml` — canonical non-secret identifier list used by the no-LIMITLESS generic-contract scan.
- `identity-record.yml` — populated tenant identity record.
- `repositories.yml` — allowed repository list.
- `mutation-classes.yml` — tenant extension classes, if any.
- `authority-matrix-overlay.yml` — tenant-specific role names overlaying the generic authority matrix.
- `ratification-flow.yml` — tenant ratification surfaces and evidence expectations.
- `attestations/`, `ratifications/`, `redactions/` — tenant-declared storage roots.

LIMITLESS-specific identifiers belong under `tenants/limitless/`, not under the generic contract paths `docs/contracts/`, `schemas/`, `validators/`, or `templates/`.
