# PR path manifest — ce-republish-020-with71 · republish the 0.2.0 download mirror with ce-ops#71 os-native `--apply`

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-republish-020-with71
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified:
Operator-approved (relayed via the CE-DEV-2 Controller, 2026-06-14): rebuild-IN-PLACE the
published `docs/downloads/0.2.0/` CE wheel from merged main so a fresh install gets the
user-level os-native `--apply` (ce-ops#71 / #226). Version STAYS `0.2.0`. STAGE-ONLY.

Base:
`106792df` (`origin/main` after #226 collapsed-merge: `feat(ce-ops#71,#34) … (#226)`).

The change (packaging-surface only — no source/behaviour change):
The published 0.2.0 app wheel predated #226 (old gVisor `--apply`). This rebuilds it from
the `106792df` source (content-identical to the CI-verified in-repo wheel; new container
sha `539be5fa…`), re-pins the mirror `SHA256SUMS` (CE wheel line only), and updates +
**re-signs** the install trust-root manifest `docs/llms-install.md` (`sha256s_sha256` +
the app-wheel `sha256`). The manifest is re-signed with the **`ce-root-v1`** root key
(Operator-laptop-held, offline) — required because `onboard_apply` pins the apply-spec
`key_id` to `ce-root-v1`. `install.sh` is byte-unchanged (it reads the wheel hash from the
served `SHA256SUMS` at runtime). The 6 dependency wheels are byte-unchanged.

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/ce-republish-020-with71.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce-republish-020-with71.md`** *(A)* — ce-ops#65 release-surface fragment.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — the rebuilt
  os-native 0.2.0 app wheel (republished in place; same version).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* — re-pinned CE wheel line (deps + install.sh entry unchanged).
- **`docs/llms-install.md`** *(M)* — signed artifact manifest: new `sha256s_sha256` + app-wheel
  `sha256`, re-signed (SSHSIG, `ce-root-v1`, namespace `ce-spec-v1`).

Posture: STAGE-ONLY — NO push / NO PR / NO merge by the seat-or-orchestrator beyond staging.
The orchestrator stages; the Operator/dev-2 reviews, pushes, and merges; Pages republishes.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=8d6f9fe35c68f4a5900343e1e3526183ca04407c97b8ea656cc14550ac521859

```text
.ce/changelog/ce-republish-020-with71.md
.ce/pr-manifests/ce-republish-020-with71.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
