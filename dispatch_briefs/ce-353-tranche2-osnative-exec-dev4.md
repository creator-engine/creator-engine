# BRIEF — dev-4 — #353 Tranche-2: real os-native sandboxed execution (bwrap+Landlock+seccomp+egress-proxy)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-353-tranche2-osnative-exec` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report `git rev-parse HEAD`.

## Context — OQ-1 Option A ratified; #648 (Tranche-1) merged
`validators/creator_engine_validator/runner/os_native_backend.py` today implements ONLY the capability PROBE + fail-closed refusal:
- `probe_os_native_capability()` checks `bwrap` (shutil.which), Landlock ABI (`landlock_abi_version`), seccomp (`/proc/sys/kernel/seccomp/actions_avail`).
- `_provision` refuses with `BackendUnavailable` when primitives absent.
- `run()` STILL REFUSES even when the probe passes (the "follow-on" message: "...full bwrap + Landlock + seccomp + deny-by-default proxy command execution is a follow-on; refusing to run a command rather than launching unsandboxed").

You implement that follow-on.

## Mission — Tranche-2
Wire the ACTUAL sandboxed command execution for the os-native (Tier-1) backend: when the capability probe passes and provisioning succeeds, `run()` launches the command INSIDE a `bwrap` sandbox with Landlock filesystem mediation + a seccomp filter + a deny-by-default egress proxy — a true peer of the gvisor-proxy backend.

## CARDINAL INVARIANT (non-negotiable, security-critical)
- **NEVER fall back to unsandboxed execution.** If ANY primitive (bwrap/Landlock/seccomp/proxy) is missing or provisioning fails at run time → REFUSE (fail-closed), exactly as today. There is NO `--no-sandbox` path and you must not add one.
- Refuse BEFORE any side effect. A command must never run outside the sandbox.

## Build
1. Study the existing **gvisor-proxy backend** (find it under `validators/creator_engine_validator/runner/`) as the reference peer — mirror its security contract: how it wires the deny-by-default egress proxy, the FS-mediation/allowed-path model, and command launch/IO. os-native must be an equal-strength backend, not a weaker one.
2. In `os_native_backend.py`, replace the refusal in `run()` with the real launch path, gated on `capability.available()` + a valid provisioned sandbox:
   - `bwrap` rootless invocation (user/mount/pid/net namespaces as the gvisor peer does), binding ONLY the task-allocated read/write paths.
   - Landlock ruleset enforcing the allowed filesystem set (use the imported `landlock_abi_version`; honor ABI differences).
   - seccomp filter applied to the child.
   - egress routed through the deny-by-default proxy (reuse the same proxy primitive the gvisor backend uses; the `"proxy"` primitive is already in `LINUX_SANDBOX_PRIMITIVES`).
3. Keep the probe + `_unavailable_reason` + fail-closed refusal paths intact for the unavailable case.

## Tests (required — prove isolation AND fail-closed)
- Primitives present: a command runs INSIDE the sandbox and is actually isolated — assert it CANNOT read a path outside the allowed set and CANNOT egress to a non-allowlisted host (mirror the gvisor backend's isolation tests).
- Any primitive absent / provision fails: `run()` REFUSES (fail-closed), no unsandboxed execution — regression guard.
- No code path runs a command without the sandbox.
- Address the 2 probe-hardening follow-on notes recorded on ce-ops#353 if they fall in this scope; otherwise note them.

## Gates
- FULL `ce validate-pr` GREEN in one pass (TMPDIR=/var/tmp). Carriers: `.ce/pr-manifests/<slug>.md` (regen via carrier_gen API; rm build/egg-info first) + `.ce/changelog/<slug>.md`. One work-class line (likely `feature`). PR-body context references ce-ops#353 + OQ-1 Option A. STOP at green; report SHA. Do NOT push.
