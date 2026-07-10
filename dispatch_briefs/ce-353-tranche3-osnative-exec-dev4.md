# BRIEF — dev-4 — #353 Tranche-3: enforceable sandbox contract → enable os-native execution (DESIGN-then-BUILD, build-OR-blocker)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-353-tranche3-osnative-exec` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report HEAD SHA. **OR**, if a provably-enforceable sandbox contract cannot be built safely, return a clear FAIL-CLOSED BLOCKER REPORT (as Tranche-2 correctly did) — both outcomes are acceptable. NEVER produce a weaker/unsandboxed launch path.

## Context (EMBEDDED — you cannot read the ticket; this IS the scope)
Tranche-2 (PR #653, now MERGED) implemented the os-native backend PROBE + PROVISION path in `validators/creator_engine_validator/runner/os_native_backend.py` but kept it **unconditionally FAIL-CLOSED** — `_provision` raises `BackendUnavailable(_EXECUTION_CONTRACT_UNAVAILABLE_REASON)` even when all primitives (bwrap, Landlock, seccomp) are present, because **no concrete deny-by-default egress-proxy enforcement contract or restrictive seccomp helper was available**. Read that file FIRST to see exactly where it refuses.

Tranche-3 builds those two missing pieces so the backend can ACTUALLY launch a command sandboxed — but ONLY when the full contract is provably in force.

## CARDINAL INVARIANT (non-negotiable — this is a security boundary)
Never run a command unless ALL of these are simultaneously enforced and VERIFIED at launch: bwrap namespace isolation + Landlock filesystem restriction + a RESTRICTIVE seccomp filter (deny-by-default syscalls) + a DENY-BY-DEFAULT egress proxy (no network except an explicit allowlist). If ANY cannot be established/verified for a given command, the backend MUST refuse (fail-closed) — never degrade to a weaker sandbox, never launch unconfined. There must be NO code path that launches a command with a partial/absent sandbox.

## DESIGN FIRST (write your design into the PR description / a docstring before building)
1. **Restrictive seccomp helper**: how the deny-by-default syscall filter is constructed + applied to the child (e.g. via bwrap's seccomp support or a libseccomp BPF program). Define the allowlist conservatively.
2. **Deny-by-default egress-proxy enforcement contract**: how network is forced through CE's egress proxy with default-deny + explicit allowlist, and how the backend VERIFIES the proxy is actually enforcing before it lets a command run (a contract that is asserted but not verified = not acceptable).
Match CE's existing egress-proxy / broker architecture — read the relevant modules under `validators/` and `tools/egress-broker/` to align, do not invent a parallel mechanism.

## BUILD (only what the design supports; stay fail-closed where it doesn't)
- Implement the seccomp helper + the proxy enforcement-contract verification as the design specifies (new helper module(s) + wiring into `os_native_backend.py`'s `_provision`/`run`).
- Replace the UNCONDITIONAL refusal with a CONDITIONAL one: launch sandboxed ONLY when the full contract is established+verified; otherwise raise `BackendUnavailable` with a precise reason (fail-closed).
- **Update the latent test** the Tranche-2 review flagged: `test_os_native_non_empty_egress_also_refuses_before_runner_probe` currently matches `"restrictive seccomp policy"` (the old unconditional raise); now that the egress branch is reachable, fix its match string to the egress-specific error text and add a distinct test for the execution-contract path.
- Tests must prove: (a) full-contract-present → command runs sandboxed (assert it actually ran inside the sandbox, e.g. egress blocked / fs restricted); (b) EACH missing primitive (no seccomp helper, no proxy enforcement, no Landlock, no bwrap) → refuses before any side effect / before any launch; (c) NO fallback/partial-sandbox launch path exists.

## Do NOT
- Do NOT touch `install.sh`, `support_runtime.py`, support files, or the broker decouple files (`tools/egress-broker/*`, `deploy/systemd/*` — ce-ops#357 is harvesting now).
- Do NOT weaken the cardinal invariant for test convenience (use proper test doubles that still prove the invariant).
- Do NOT launch ANYTHING unsandboxed, ever.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`; on this DGX host you may need `LD_LIBRARY_PATH` for libsodium as before). Carriers via `carrier_gen.write_carriers(base=<merge-base>)` (rm build/egg-info first; VERIFY the `- **Declared work class:** <x>` line is present — the API omits it; likely `feature`) + `.ce/changelog/<slug>.md`. Carrier slug == branch `ce-353-tranche3-osnative-exec`. STOP at green; report SHA. Do NOT push. If blocked on the invariant → fail-closed blocker report instead.
