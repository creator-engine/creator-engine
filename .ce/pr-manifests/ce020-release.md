# PR path manifest — ce020-release · republish the 0.2.0 download mirror to match main's post-#85 wheel

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce020-release
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

> ⚠️ Carrier filename is locked to `branch_slug(head_ref)`. This file is named for branch
> `ce020-release` (`branch_slug("ce020-release") == "ce020-release"`). If this branch is
> pushed/PR'd under a DIFFERENT name, rename this carrier to `branch_slug(<that-branch>).md`
> or `verify-path-manifest` emits `path_manifest_carrier_slug_mismatch`.

Ratified:
Operator-mandated (relayed via the CE-DEV-2 Controller, 2026-06-15, ce-ops#48 0.2.0 cut +
ce-ops#80 release-process step): republish the frozen `docs/downloads/0.2.0/` mirror IN
PLACE so a fresh `curl … | install.sh` installs main's post-#85 onboarder. Version STAYS
`0.2.0`. STAGE-ONLY.

Base:
`27c04b0` (`origin/main` after #229: `feat(ce-ops#85): onboard --apply plain-join path … (#229)`).

The change (packaging-surface only — no source/behaviour change):
PR #229 rebuilt the in-repo 0.2.0 validator wheel (new sha `588eeca0…`), leaving the
published mirror + signed spec pinned to the OLD wheel (`539be5fa…`). This syncs the mirror
`creator_engine_validator-0.2.0-py3-none-any.whl` to be **byte-identical** to the CI-verified
`validators/wheelhouse/` wheel (`588eeca0…`), re-pins the mirror `SHA256SUMS` (CE wheel line
only), and updates + **re-signs** the install trust-root manifest `docs/llms-install.md`
(`sha256s_sha256` → `fde81151…`, app-wheel `sha256` → `588eeca0…`, `content_sha256` →
`88c2fbca…`). The manifest is re-signed with the **`ce-root-v1`** root key (Operator-laptop-held,
offline, namespace `ce-spec-v1`) — required because `onboard_apply` pins the apply-spec
`key_id` to `ce-root-v1`. `install.sh` is byte-unchanged (it reads the wheel hash from the
served `SHA256SUMS` at runtime). The 6 dependency wheels and the `install.sh` SHA256SUMS entry
are byte-unchanged. The frozen mirror's INTERNAL self-consistency (ce-ops#69 re-scope) is
preserved.

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/ce020-release.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce-republish-020-with85.md`** *(A)* — ce-ops#65 release-surface fragment.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — the
  republished 0.2.0 app wheel, byte-identical to the in-repo wheelhouse wheel (same version).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* — re-pinned CE wheel line (deps + install.sh entry unchanged).
- **`docs/llms-install.md`** *(M)* — signed artifact manifest: new `sha256s_sha256` + app-wheel
  `sha256` + re-issued SSHSIG (`ce-root-v1`, namespace `ce-spec-v1`) + `content_sha256` floor.

Posture: STAGE-ONLY — NO push / NO PR / NO merge / NO signing by the seat. The seat stages and
emits the canonical bytes; the Controller/Operator signs (offline `ce-root-v1`), reviews, pushes,
and merges; ubuntuaws745-cmyk reviews; Pages republishes.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b56d119780e0aae1d72133d121932c1fc64a985cb8fa95919eae48dd7b155f11

```text
.ce/changelog/ce-republish-020-with85.md
.ce/pr-manifests/ce020-release.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
