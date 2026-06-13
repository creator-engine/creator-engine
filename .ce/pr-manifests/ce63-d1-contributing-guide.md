# PR path manifest — ce63-d1-contributing-guide · ce-ops#63 Tier-A docs lane

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce63-d1-contributing-guide
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED D1 draft (ce-ops#63, ratified 2026-06-13) + M2-approved DCO
requirement. Scope `ce63-d1-contributing-guide`; approver_ref ratified D1 sha256
`a5b317f8dac9ea17869efaa5f64fa4c68255c2ca1fffb81f74f3c986001c563d`.

Base:
`f8d1c25` (`main`, #219 — benign base refresh from #218; the #219 test-only change is disjoint from this PR's path-set).

The change:
Publish the ratified contributor guide under `docs/guide/`, add the DCO requirement
line to the root contributing on-ramp, and carry the self-inclusive closed path-set
for the PR diff gate. Change-type: `docs`.

Per-file purpose (the closed path-set — 3 paths):
- **`.ce/pr-manifests/ce63-d1-contributing-guide.md`** *(A)* — this carrier (self-inclusive).
- **`CONTRIBUTING.md`** *(M)* — adds the ratified DCO sign-off requirement bullet after
  the Apache-2.0 inbound license bullet.
- **`docs/guide/contributing-to-ce.md`** *(A)* — publishes the ratified D1 contributor
  guide with the mandated preamble drop and two citation tightenings.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=a9e5d1db82b81555434b620cda11a3bcb5d072405bd2e2b371003320ff1f21dd

```text
.ce/pr-manifests/ce63-d1-contributing-guide.md
CONTRIBUTING.md
docs/guide/contributing-to-ce.md
```
