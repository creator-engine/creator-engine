# PR path manifest — ce-republish-020-rootv1 · re-publish signed 0.2.0 (ce-root-v1)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-republish-020-rootv1
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

- **Declared work class:** feature

Scope:
Re-publishes the signed `0.2.0` release mirror built from current `main` (HEAD includes
`ce brain init` #206, the launch-leg `LAUNCHED_STATE` fix #205, and `--signing-key-id`
#352). `docs/llms-install.md` is re-signed with the **ce-root-v1** trust anchor
(`signature.key_id: ce-root-v1`, namespace `ce-spec-v1`); the staged spec/canonical/
manifest were produced reproducibly by `release-stage --signing-key-id ce-root-v1` from
this same `main`. The brownfield scanner mirror (`downloads/0.2.0/scanners/`, ce-ops#123)
is independent of the install manifest and is preserved untouched. First step of the
fleet-retirement clean-install program (dev-4 installs this release).

Verification (pre-push, on cedev2 which holds ce-root-v1):
`ssh-keygen -Y verify -f docs/keys/ce-root-v1 -I ce-root-v1 -n ce-spec-v1 -s <sig>` over the
canonical re-derived from the published `llms-install.md` returns
`Good "ce-spec-v1" signature for ce-root-v1`. Published app-wheel sha256 equals its
`SHA256SUMS` entry (`709547f7…`).

Per-file purpose (closed path-set — 6 paths):
- **`.ce/pr-manifests/ce-republish-020-rootv1.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce-republish-020-rootv1.md`** *(A)* — per-PR changelog fragment.
- **`docs/llms-install.md`** *(M)* — re-signed install spec (ce-root-v1).
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — app wheel rebuilt from current main (now carries `ce brain init` etc.).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* — updated manifest hashes for the new app wheel + install.sh.
- **`docs/downloads/0.2.0/install.sh`** *(A)* — per-version installer copy (already referenced by SHA256SUMS; previously missing from the versioned dir).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=f8e3221bab603cf0b4c9afad2ab453c9061a1bc19b82223147425a86b871988d

```text
.ce/changelog/ce-republish-020-rootv1.md
.ce/pr-manifests/ce-republish-020-rootv1.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/downloads/0.2.0/install.sh
docs/llms-install.md
```
