# Surface Update Runbook

Use this procedure when updating a rented surface version or digest in `surfaces/manifest.yaml`.

## Carrier Naming

Surface-bump carriers live in `carriers/` and use this filename format:

`carriers/surface-bump-<surface-name>-<to_version>.md`

For example, a Codex update to `0.142.0` uses `carriers/surface-bump-codex-0.142.0.md`.

## Procedure

1. Detect

   Run `ce surfaces check-updates` to identify available rented-surface updates.

2. Evaluate

   Review the upstream changelog, perform a CVE check, and ground any vendor capability claims per [[verify-vendor-capability-vs-our-wiring]]. Capability claims must be tied to current vendor documentation and compared against our actual wiring.

3. Draft Carrier

   Copy `carriers/surface-bump-TEMPLATE.md` to the required carrier filename and fill every field, including changelog summary, CVE status and notes, vendor capability grounding, canary seat, ratifier, and ratification time.

4. Open Manifest-Bump PR

   Update `surfaces/manifest.yaml` with the new version and digest or commit. Include the filled carrier file named `carriers/surface-bump-<surface-name>-<to_version>.md` in the same PR.

5. Canary Seat Validation

   Run the updated surface through the named canary seat and record the validation outcome in the PR.

6. Gate

   Ensure the `surfaces_bump_has_carrier` validator check passes. A PR that touches `surfaces/manifest.yaml` must include at least one `carriers/surface-bump-*.md` file.

7. Fleet Rollout

   Roll out the accepted update with `ce surfaces fleet-rollout`. This rollout command is planned and not yet available, so keep rollout tracking explicit until the command ships.
