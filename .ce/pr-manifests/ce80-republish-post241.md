# PR path manifest - ce80-republish-post241 - republish the 0.2.0 download mirror to match post-#241 wheel

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce80-republish-post241
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

> Carrier filename is locked to `branch_slug(head_ref)`. This file is named for branch
> `ce80-republish-post241` (`branch_slug("ce80-republish-post241") == "ce80-republish-post241"`).

Ratified:
Operator-approved republish (2026-06-16, ce-ops#80 / ce-ops#90 batch): after PR #241 merged
(loosened brownfield detector), republish the frozen `docs/downloads/0.2.0/` mirror in place so
a fresh install provisions main's current post-#241 validator wheel. Version stays `0.2.0`.

Base:
`0935e12` (main after #241).

The change (packaging-surface only - no source/behaviour change):
The in-repo 0.2.0 validator wheel is now `ac8117d3...` (post-#241 detector), but the published
mirror and signed spec were still pinned to the post-#240 wheel (`3554a293...`, OLD detector).
This syncs the mirror `creator_engine_validator-0.2.0-py3-none-any.whl` byte-identical to
`validators/wheelhouse/`, re-pins the mirror `SHA256SUMS` (CE wheel line only), and updates
and re-signs `docs/llms-install.md` (`sha256s_sha256` -> `a2f6a701...`, app-wheel `sha256`
-> `ac8117d3...`, `content_sha256` -> `5820a9f8...`). The detached SSHSIG was issued by the
Controller-held offline `ce-root-v1` root key under namespace `ce-spec-v1`; local verification
returns `Good "ce-spec-v1" signature for ce-root-v1`.

Per-file purpose (the closed path-set - 5 paths):
- **`.ce/changelog/ce80-republish-post241.md`** *(A)* - ce-ops#65 release-surface fragment.
- **`.ce/pr-manifests/ce80-republish-post241.md`** *(A)* - this carrier (self-inclusive).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - re-pinned CE wheel line; deps and install.sh unchanged.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - the
  republished 0.2.0 app wheel, byte-identical to the in-repo wheelhouse wheel.
- **`docs/llms-install.md`** *(M)* - re-pinned `sha256s_sha256` + app-wheel `sha256`, re-signed
  `content_sha256` + SSHSIG `value` under `ce-root-v1` / `ce-spec-v1`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b02575dcbfc16d8abcfef0360ad906763a34001dfb22780df2193180eec9a7d6

```text
.ce/changelog/ce80-republish-post241.md
.ce/pr-manifests/ce80-republish-post241.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
