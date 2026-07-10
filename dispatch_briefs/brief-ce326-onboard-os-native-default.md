# WORK CLAIM — ce-ops#326 onboard: default to os-native (not gvisor-proxy) for no-profile/solo

**Seat:** dev-3 (VPS contained). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-326-onboard-os-native-default origin/main
```

## Why (self-contained)
`cev3 onboard` run WITHOUT a `profile` resolves the isolation backend to the schema-level `DEFAULT_ISOLATION_BACKEND = "gvisor-proxy"` (Tier 2, privileged) — promising gVisor runsc + egress proxy and demanding **sudo**, pushing a first-time solo pilot onto the heavy privileged runtime. The code already maps `PROFILE_DEFAULT_BACKEND['solo-pilot'] = 'os-native'` and a comment says "solo-pilot → os-native is clear", but the **no-profile path still falls through to gvisor-proxy**.

## Expected / Task
Make the **no-profile / unspecified-profile** onboarding path default to **os-native** (Tier 1: governance + unprivileged OS-native sandbox, no sudo, no container runtime) for solo pilots. Preserve explicit-profile behavior — an explicitly chosen `gvisor-proxy`/team profile still gets Tier 2. Safety posture: default = least-privilege.

**Repro to satisfy:** `cev3 onboard --spec … --plan` (no answers) should show os-native (`install —`, `sudo no`), matching the `--answers <profile: solo-pilot>` path.

## Allowed paths (nothing else)
The onboarding/profile-resolution code under `validators/creator_engine_validator/` (the profile→backend resolution: e.g. `ce_profile_path.py`, the onboard orchestration, the schema default), `validators/tests/**` (a test proving the default), `.ce/changelog/**`, `.ce/pr-manifests/**`.
**Do NOT touch:** `.github/workflows/validate.yml`, the reviewer-authority PreToolUse hook, `.claude/**`, `AGENTS.md`, release/_version files — other seats own those (avoid merge collisions).

## Evidence (DoD)
Full `ce validate-pr` GREEN + a test proving no-profile → os-native (Tier 1, `sudo no`). Declare the G5-derived work-class.

## Stop-line
- Green + self-push works → push + open PR referencing ce-ops#326. Do NOT approve/merge.
- Green but push FAILS (#337) → STOP + report `READY-FOR-HARVEST: branch ce-326-onboard-os-native-default, <N> commits, preflight GREEN`.
- Preflight RED → STOP + report the failing gate.
