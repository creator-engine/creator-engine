# BRIEF — dev-3 — os-native OQ-1 decision package (ce-ops#353)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. DESIGN/DECISION doc only — no implementation.

## Why design-first
ce-ops#353 (the bug: os-native backend raises BackendUnavailable unconditionally → users can't elect the unprivileged isolation path) is GATED on OQ-1 — the held decision of WHICH unprivileged-sandbox mechanism CE uses. Building the wrong mechanism wastes effort, so the fastest path to the fix is a crisp, ratifiable OQ-1 decision package the Operator can approve. That's this slice.

## Goal
Produce a decision doc that resolves OQ-1: recommend the unprivileged-sandbox mechanism(s) for the os-native (Tier-1) backend, scope the Tranche-2 adapter, and make it one-tap ratifiable.

## Branch
`ce-oq1-os-native-mechanism` off CURRENT origin/main (git fetch origin main first). Fresh worktree.

## Scope (study first: validators/creator_engine_validator/runner/os_native_backend.py — the HELD scaffold, its LINUX_SANDBOX_PRIMITIVES and _HELD_REASON; fs_mediation.py — the existing Landlock wiring; ce-ops#71 the Tranche-1 scaffold; ce-ops#353 the bug; ce-ops#82 OpenShell A.2b for contrast)
Write `docs/design/oq1-os-native-sandbox-mechanism.md` covering:
1. The problem: os-native must be a real, user-elected Tier-1 backend (unprivileged, no container/sudo), with contained (gvisor-proxy) staying the DEFAULT. The governance posture is preserved either way — os-native is still governed, just unprivileged.
2. Mechanism options, each with pros/cons/blast-radius/portability:
   - Linux: bwrap (bubblewrap) + Landlock (LSM) + seccomp — note Landlock is already partially wired (fs_mediation.py) and is Linux 5.13+.
   - macOS: Seatbelt / sandbox-exec (couples to ce-ops#352 native-macOS lane — the os-native start there).
   - Alternative: a CE-native jail (more control, more build cost).
3. A RECOMMENDATION (your best engineering call) with rationale, expressed as the default option.
4. The Tranche-2 adapter scope: what `_provision` would do per-OS once the mechanism is chosen; the user-election path (how a user opts into os-native and how the choice is honored end-to-end); what stays fail-closed.
5. A short "Ratification ask" section: the precise decision the Operator taps to approve (the recommended mechanism), and what unblocks on approval (the adapter build slices).

## Allowed paths (HARD limit)
- `docs/design/oq1-os-native-sandbox-mechanism.md` (NEW)
- `.ce/changelog/ce-oq1-os-native-mechanism.md`, `.ce/pr-manifests/ce-oq1-os-native-mechanism.md`
Design doc only. Do NOT touch any .py/schema/backend code.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-oq1-os-native-mechanism`
- Carriers via carrier_gen (dashed slug); single carrier; manifest `- **Declared work class:** story`.
- STOP and emit: `READY-FOR-HARVEST: branch ce-oq1-os-native-mechanism, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- ZERO internal identities/IPs/host-paths in the doc body (carrier ce-ops# OK). No push. Stay in allowed paths.
