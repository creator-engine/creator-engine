# BRIEF — dev-1 — ce-ops#364 follow-up: import install-sig guard's pinned-key material from the single source

Non-contained, SELF-PUSH as ce-dev-1. Fresh branch `ce-364-guard-single-source` off CURRENT origin/main (`git fetch origin main` first — #663 the guard is now merged). Drive to a GREEN PR; self-push, do NOT merge.

## Why (flagged in the #663 review)
The merged install-spec signature guard `validators/creator_engine_validator/checks/install_spec_signature_guard.py` carries its OWN copies of `PINNED_KEYS`, `content_digest()`, and `canonical_spec_bytes()` rather than importing them from `v3_installer`. Drift risk: if a new root key is later added to `v3_installer.PINNED_KEYS` but forgotten in the guard, the guard would SILENTLY miss it (a security gap in a security guard). Eliminate the duplication.

## Deliverable
1. Refactor the guard to IMPORT `PINNED_KEYS` (and `content_digest`/`canonical_spec_bytes` if they are equivalently defined) from the single source `v3_installer` (read both first; confirm the definitions are truly equivalent before collapsing — if they intentionally differ, keep them separate and instead add a test asserting they stay in sync). Behavior must be UNCHANGED (the guard still detects placeholder/invalid-base64/non-verifying signatures exactly as before; it stays ADVISORY/non-blocking until the controller re-signs).
2. Add/keep a test asserting the guard's pinned-key set == `v3_installer.PINNED_KEYS` (so future key additions can't drift). The existing `test_validate_file_accepts_mocked_good_ssh_signature` already cross-asserts the ce-root-v1 material — extend to assert the FULL set is shared/imported, not just one key.

## Do NOT
- Do NOT change the guard's detection logic, its advisory wiring, or flip it to blocking (the flip happens after the controller re-signs — separate step).
- Do NOT modify `docs/llms-install.md`. Do NOT touch support/os_native/broker files.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Note the advisory guard will (correctly) still warn on main's placeholder — that must stay non-blocking (your PR must be green). Carriers (slug == branch `ce-364-guard-single-source`, work-class line) + changelog. Report PR # + head SHA.
