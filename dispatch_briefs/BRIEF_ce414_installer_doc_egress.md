# BRIEF — ce-414-installer-doc-egress — installer contract: version-symbolic paths + egress allowlist (UNIT 5)

Role: implementer (dev-1, self-push, foreman mode). UNIT 5 — start immediately (your ce-435
unit stopped correctly at the novelty check; that ticket is being closed as already-resolved).
Branch `ce-414-installer-doc-egress` off freshly-fetched origin/main.

## Mandate
Read ce-ops#414 directly (gh read). Two doc gaps found by the 2026-07-03 D1a install canary:
1. `docs/contracts/installer.md` §"E1 real bootstrap" step 4 + the "Pages mirror" line still cite
   `downloads/0.3.0/...`; live is 0.3.1. Fix by referencing the version SYMBOLICALLY (preferred —
   e.g. `downloads/<current-release>/`, with one line saying the manifest is the authority) so the
   doc never lags again; hardcode 0.3.1 only where a concrete example genuinely helps.
2. Document the full REQUIRED EGRESS ALLOWLIST for the default one-liner flow, in the installer
   contract AND the pilot runbook: (a) creator-engine.dev (spec+wheels), (b) https://dns.google
   (DoH out-of-band trust anchor, CE_TRUST_ANCHOR_URL default), (c) github.com (astral-sh/uv
   releases → manifest-pinned uv + CPython 3.14 when no local >=3.14). State plainly that
   egress-restricted environments must allow all three or the install fails non-obviously.

SEMANTIC NOVELTY CHECK FIRST: confirm the stale 0.3.0 citations + missing egress section still
exist on your fresh checkout; if already fixed, signal `BLOCKED ce-414-installer-doc-egress
already-resolved` with evidence and pull your next unit.

## Allowed paths
docs/contracts/installer.md · docs/guide/pilot-runbook.md (egress section only in this unit) ·
.ce/changelog/ce-414-installer-doc-egress.md · .ce/pr-manifests/ce-414-installer-doc-egress.md

## STOP lines
- ⛔ Do NOT touch `docs/install.sh` or anything under `docs/downloads/` — those are SIGNED
  release surfaces; editing them breaks the signed install and is a release op, not a doc fix.
  If the fix seems to require it → STOP and signal BLOCKED with the reason.
- ⛔ Public-docs product lens: ZERO ce-ops#N references or internal-fleet vocabulary in the
  public docs; write for a product user.
- ⛔ Never sign anything with any key; if a step appears to need a signature → STOP, controller signs.

## ADDENDUM 2026-07-05 — TERRITORY EXTENSION (controller-authorized, after your BLOCKED report)
Your closed-set stop was correct. The write set is EXTENDED to include the public-docs
confidentiality ratchet allowlist and its test expectations — exactly and only the files your two
failing tests point at. Direction constraint: you may only REMOVE/shrink allowlist entries (the
docs/contracts/installer.md entry that the stale-reference removal obsoletes); you may NOT add or
loosen any entry. Resume from your local commit 9614c0c9ccbbde128e3d64ff8f6765af4343e74c, make the
ratchet edit, regen the carrier to include the new paths, re-run full validate-pr to GREEN in one
pass, then push and open the PR per the original evidence bar.

## Evidence bar
Full `ce validate-pr` GREEN locally in ONE pass before push (CI-parity; do not discover gates via
CI). Changelog fragment + path-manifest carrier matching base..HEAD. PR body carries exactly one
`- **Declared work class:** tiny` (bump to story only if the diff exceeds the tiny floor).
Commit and report: `READY ce-414-installer-doc-egress <40-hex sha> PR=<url>`.
