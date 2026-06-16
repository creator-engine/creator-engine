# PR path manifest — ce80-republish-233 · republish the 0.2.0 download mirror to match main's post-#233 wheel

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce80-republish-233
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

> ⚠️ Carrier filename is locked to `branch_slug(head_ref)`. This file is named for branch
> `ce80-republish-233` (`branch_slug("ce80-republish-233") == "ce80-republish-233"`). If this
> branch is pushed/PR'd under a DIFFERENT name, rename this carrier to
> `branch_slug(<that-branch>).md` or `verify-path-manifest` emits
> `path_manifest_carrier_slug_mismatch`.

Ratified:
Operator-ratified (2026-06-16, ce-ops#80 release-process gap — "scope A"): republish the frozen
`docs/downloads/0.2.0/` mirror IN PLACE so a fresh `curl … | install.sh` installs main's
post-#233 onboarder (the brownfield live-forge `ApplyDriver`). Version STAYS `0.2.0`.

Base:
`f379219` (`origin/main` after #235: `fix(ce-ops#89): cev3 review --spawn out-of-repo --repo-root … (#235)`).

The change (packaging-surface only — no source/behaviour change):
Tonight's merges through #233 (`feat(creator-engine#88): production live-forge ApplyDriver
(Phase 1)`) rebuilt the in-repo 0.2.0 validator wheel (new sha `de40b62f…`, adding
`onboard_apply_live.py` — the brownfield plain-join apply legs), leaving the published mirror +
signed spec pinned to the pre-#233 wheel (`588eeca0…`, no `onboard_apply_live`). A fresh install
therefore dead-ended the team-mode brownfield `onboard --apply` at `e2_brownfield_seam_unavailable`.
This syncs the mirror `creator_engine_validator-0.2.0-py3-none-any.whl` to be **byte-identical** to
the CI-verified `validators/wheelhouse/` wheel (`de40b62f…`), re-pins the mirror `SHA256SUMS` (CE
wheel line only), and updates + **re-signs** the install trust-root manifest `docs/llms-install.md`
(`sha256s_sha256` → `e346f52f…`, app-wheel `sha256` → `de40b62f…`, `content_sha256` → `416179a7…`).
The manifest is re-signed with the **`ce-root-v1`** root key (Operator-laptop-held, offline,
namespace `ce-spec-v1`) — required because `onboard_apply` pins the apply-spec `key_id` to
`ce-root-v1`. `install.sh` is byte-unchanged (it reads the wheel hash from the served `SHA256SUMS`
at runtime). The 6 dependency wheels and the `install.sh` SHA256SUMS entry are byte-unchanged. The
frozen mirror's INTERNAL self-consistency (ce-ops#69 re-scope) is preserved.

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/ce80-republish-233.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce80-republish-233.md`** *(A)* — ce-ops#65 release-surface fragment.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — the
  republished 0.2.0 app wheel, byte-identical to the in-repo wheelhouse wheel (same version).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* — re-pinned CE wheel line (deps + install.sh entry unchanged).
- **`docs/llms-install.md`** *(M)* — signed artifact manifest: new `sha256s_sha256` + app-wheel
  `sha256` + re-issued SSHSIG (`ce-root-v1`, namespace `ce-spec-v1`) + `content_sha256` floor.

Posture: Controller-authored + signed (offline `ce-root-v1`, CE-DEV-2); independent review by the
`cedev1vps-cmd` reviewer venue (cross-review, dev-2 authoring); merge Operator-authorized once
reviewed-green (2026-06-16); Pages republishes.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=bfef4ecf2061fb02a2fc248913b87b2653a5af59665ef250bd2e014198c27101

```text
.ce/changelog/ce80-republish-233.md
.ce/pr-manifests/ce80-republish-233.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
