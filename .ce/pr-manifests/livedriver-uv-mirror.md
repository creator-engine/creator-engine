# PR path manifest — livedriver-uv-mirror · live-driver uv-from-mirror + app-install overrides (design A)

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref livedriver-uv-mirror

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

> Carrier filename is locked to `branch_slug(head_ref)`. This file is named for branch
> `livedriver-uv-mirror` (`branch_slug("livedriver-uv-mirror") == "livedriver-uv-mirror"`).

Ratified:
Operator-RATIFIED **design A** (uv from CE's own mirror, sha256-pinned, `pip --no-index --find-links`),
2026-06-17, superseding the seat's earlier design-B (vendored `validators/wheelhouse/`). Authoritative:
`DECISION_uv_RATIFIED_driveA_20260617.md` + `SEAT_MANDATE_uv_designA_20260617T0345Z.md`. Built by a §7
governed CE seat on base `9890ee8`; push/merge + the dev-2 ce-root-v1 re-sign are Operator/dev-2-gated.

Base:
`9890ee8` (`main` = #242, runner-owned Ring-1 increment 1 + git-grammar-aware deploy classifier).

GREEN-EXCEPT-THE-SIG (by design): `docs/llms-install.md` carries a PLACEHOLDER signature
(`value` + `content_sha256` = `<published-with-this-spec>`). dev-2 re-signs `ce-root-v1` IN THIS PR (the
`required_wheels` edit forces the re-sign — the #243 republish shape). Every other content field is set
correct + reproduced (the served-mirror `sha256s_sha256`, the rebuilt validator `required_wheels` sha, and
the new uv `required_wheels` entry), so the full unit suite is green and the real-SSHSIG verify test
SKIPS on the placeholder (it flips to PASS once dev-2 signs).

The change (design A — redirect the uv SOURCE from a vendored wheelhouse to CE's mirror):
2nd live-forge driver gap of the #241 class, surfaced by the dev-3 brownfield dogfood. The driver's
`install_dependencies` fetches the pinned `uv` wheel from CE's own mirror (`docs/downloads/0.2.0/`, NOT
astral.sh / a live index), sha256-verifies it against the in-code pin (`MIRROR_USERSPACE_WHEELS`, bound to
the SIGNED `required_wheels` entry + the served wheel by a parity test), then installs OFFLINE via
`pip --no-index --find-links`; `CE_FORGE_WHEELHOUSE` remains an optional no-egress fallback. The uv wheel
is now SERVED on the mirror + listed in `required_wheels` so a fresh external onboard self-serves it with
no extra env. `wait_for_app_installation` is a read-only already-installed-App detect. The validator wheel
is rebuilt from post-#242 source (carries the #242 classifier fix) into BOTH the dev wheelhouse and the
mirror copy. No `validators/wheelhouse/` uv vendoring (design A sources from the mirror).

Per-file purpose (the closed path-set — 10 paths):
- **`.ce/changelog/livedriver-uv-mirror.md`** *(A)* — ce-ops#65 release-surface fragment (kind: fixed).
- **`.ce/pr-manifests/livedriver-uv-mirror.md`** *(A)* — this carrier (self-inclusive).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* — added the served uv wheel line + re-pinned the rebuilt
  validator-wheel line (other lines byte-unchanged).
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — mirror copy of the
  rebuilt validator wheel (byte-identical to the dev wheelhouse copy).
- **`docs/downloads/0.2.0/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`** *(A)* — the
  pinned uv 0.11.21 linux x86_64 wheel SERVED from the mirror, the apply-time fetch source (sha256 `b9ecdefa…`).
- **`docs/llms-install.md`** *(M)* — added uv to `required_wheels`; updated `sha256s_sha256` (served-mirror
  SHA256SUMS hash) + the validator `required_wheels` sha (rebuilt wheel); RESET `value` + `content_sha256`
  to the canonical placeholder for the dev-2 `ce-root-v1` re-sign (NOT signed by the seat).
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* — both leg overrides +
  `MirrorUserspaceWheel`/`MIRROR_USERSPACE_WHEELS`, mirror-fetch/sha-verify/offline-pip helpers,
  `mirror_fetch`/`pip_spawn` config seams, `CE_FORGE_WHEELHOUSE` fallback.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* — offline tests for BOTH overrides:
  mirror-fetch+install success; fail-closed (fetched-sha-mismatch, fetch-failure, sudo-refusal, pip-fail,
  verify-fail, unpinned-tool, fallback tamper); `CE_FORGE_WHEELHOUSE` fallback; pin↔served-wheel↔SHA256SUMS↔
  `required_wheels` parity; app detect + not-covered + unconfigured-id. Injected `mirror_fetch` + `pip_spawn`
  → ZERO network / pip.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned the rebuilt validator-wheel line (design A does
  NOT vendor uv here; no uv line).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt 0.2.0 app
  wheel from post-#242 source (source parity: `verify_wheel_matches_source`). Clean rebuild, no `build/`
  leak; `_version.py` unchanged.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=782201bd9948a6cb0848d3286cc151ffb6c1d0c76836caff43584931f0213063

```text
.ce/changelog/livedriver-uv-mirror.md
.ce/pr-manifests/livedriver-uv-mirror.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/downloads/0.2.0/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/llms-install.md
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
