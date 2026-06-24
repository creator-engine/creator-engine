# Seat ce-ops Read-Only Checkout

Seat hosts can expose durable private `ce-ops` artifacts to seats through a
local read-only checkout. The checkout is for reading design and research
artifacts only; seats must not receive write credentials for `ce-ops`.

## Provisioning

Run the provisioner from a `creator-engine` checkout on the seat host:

```bash
sudo CE_OPS_SEAT_GROUP=ce-seat ./tools/provision-ce-ops-readonly.sh
```

Defaults:

- `CE_OPS_REPO_URL=git@github.com:creator-engine/ce-ops.git`
- `CE_OPS_READONLY_CHECKOUT=/opt/creator-engine/ce-ops-readonly`
- `CE_OPS_REF=main`

The script is safe to re-run. It clones the checkout when absent, otherwise it
fetches and fast-forwards the configured ref. After each run it sets the
checkout read-only for seat users and sets the git remote push URL to an inert
value.

Access to the private repository must be configured outside this repository,
for example with a host-managed read-only deploy key or read-only GitHub App
credential. Do not put tokens, private keys, or credential-bearing URLs in this
repository or in briefs.

When `CE_OPS_SEAT_GROUP` is set, only root and members of that group can read
the checkout. If it is unset, the checkout is world-readable on that host.

## Brief References

Briefs may reference private `ce-ops` artifacts by path once the checkout
exists. Use the compact form:

```text
ce-ops:designs/example-design.md
ce-ops:mandates/example-mandate.md
```

A seat resolves that form against `CE_OPS_READONLY_CHECKOUT`, or against the
default checkout path when the environment variable is unset:

```bash
artifact="${CE_OPS_READONLY_CHECKOUT:-/opt/creator-engine/ce-ops-readonly}/designs/example-design.md"
```

References must be relative paths inside the checkout. Briefs should not embed
private artifact contents when a `ce-ops:` reference is sufficient, and should
not include credentials or host-specific absolute paths.
