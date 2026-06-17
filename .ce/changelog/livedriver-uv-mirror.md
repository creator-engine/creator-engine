---
slug: livedriver-uv-mirror
date: 2026-06-17
kind: fixed
scope: install / onboard --apply / live-forge driver / mirror
issue: ce-ops#90
---

**`LiveForgeApplyDriver` now installs userspace deps (`uv`) by fetching the pinned
wheel from CE's own 0.2.0 mirror and detects an already-installed App — a plain-join
`onboard --apply` no longer dead-ends at `host_dependencies` or `github_app_install`,
and a fresh EXTERNAL onboard can self-serve `uv` with no extra env.**

This is the **2nd live-forge driver gap of the same class** surfaced by the dev-3
brownfield dogfood (the 1st was the already-CE detector, ce-ops#90 #241):
`LiveForgeApplyDriver` overrode only the forge legs and inherited two conservative
base `ApplyDriver` legs that refuse-and-are-reached in an already-CE plain-join. The
dogfood ran `cev3 onboard --apply` and stopped at
`host_dependencies: no_userspace_installer_configured`.

- **`install_dependencies`** — installs userspace tools (e.g. `uv`) WITHOUT sudo by
  fetching the pinned wheel from CE's own mirror (`docs/downloads/0.2.0/`, **not**
  `astral.sh` / a live index), sha256-verifying the bytes against the in-code pin
  (`MIRROR_USERSPACE_WHEELS`, bound to the SIGNED `required_wheels` entry) BEFORE
  install, then installing OFFLINE via `pip install --no-index --find-links <dir>
  <tool>`; `verify_tool` must pass after. A pre-seeded `CE_FORGE_WHEELHOUSE` dir is an
  optional no-egress fallback. `sudo_tools` keep the base refusal (a §7 governed seat
  has no host package installer). Fails closed on every fetch / hash-mismatch /
  install / verify failure; the staged temp dir is always cleaned.
- **`wait_for_app_installation`** — read-only already-installed-App detect via the
  driver's configured `installation_id` + a `GET /installation/repositories` coverage
  read; no click, no mutation; fails closed if unconfigured / not covered.

The `uv` 0.11.21 wheel (matching the manifest's `python_acquisition` pin) is **served
from the mirror** (`docs/downloads/0.2.0/` + `SHA256SUMS`) and added to `required_wheels`
in `docs/llms-install.md`, so its integrity is rooted in the ce-root-v1 signature — the
clean self-serve path the dogfood validates (design A, Operator-ratified, superseding the
earlier vendored-wheelhouse design B). The validator wheel is rebuilt from post-#242
source (carries the git-grammar classifier fix). The `docs/llms-install.md` signature is
left at the canonical placeholder for the dev-2 in-PR `ce-root-v1` re-sign (the
`required_wheels` edit forces it, by design — the #243 republish shape).
