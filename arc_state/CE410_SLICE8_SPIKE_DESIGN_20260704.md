# CE-410 Slice-8 SPIKE — Production Validation Sandbox Design (for Operator ratification)
> Authored 2026-07-04 by architect_research (read-only). Answers the five SPIKE questions in
> CE410_SLICE8_SPIKE_RATIFICATION_PACKAGE_20260704.md. No implementation performed.
> Design SSOT input: CE410_ARMING_FIX_DESIGN_20260703.md. Frozen contract: validation_sandbox.py
> (ValidationSandboxSpec/Result, PR #768) — NOT modified by this design.

## Executive summary
Run the SAME `ValidationSandboxSpec` (today a bare host subprocess) inside the EXISTING
worker-container-policy `verification` role (empty egress + empty secret allowlists, read-only
worktree), emit an unforgeable `ValidationSandboxReceipt` bound to `tree_sha`, and gate slices
9/10 on that receipt. One shared container-launcher (generalize
`worker_runtime.build_podman_run_argv` to a foreground `--rm` + trailing-command mode) is the
ONLY place allowed to invoke the engine — satisfying #437's single-privileged-launcher intent
and avoiding a fourth independent podman/docker call site.

## The five answers (condensed)
1. **Substrate**: promote `examples/well-formed/worker-container-policies/podman-verification.yaml`
   to a Source-ratified `governance/policies/worker-container/podman-verification-v1.yaml` (real
   `policy_sha`). Map Spec→config: context selects+asserts the verification policy; command →
   trailing argv of a foreground `podman run --rm <image>@<sha>`; cwd → daemon-allocator workspace
   bind-mounted read-only at the IDENTICAL absolute path; env → repeated `--env` from the
   already-scrubbed `spec.env` (no broker inject — secret_allowlist is empty by design);
   timeout enforced both host-side (`subprocess.run timeout`) and engine-side (`--timeout`).
2. **Filesystem**: allocator-issued workspace ONLY, read-only, from CE-410 slice-1
   `DaemonPathAllocation`; container-local tmpfs for TMPDIR (—`--rm` guarantees artifact
   destruction even on crash, strictly better than today's post-hoc `_remove_validator_artifacts`);
   bake the pinned validators install into the canonical image (run-time `pip install` would need
   egress the verification role forbids).
3. **Evidence**: NEW additive `ValidationSandboxReceipt` (Spec/Result unchanged) — nonce+HMAC
   signed like `DaemonPathReceipt`, minted ONLY by the function that observed the container exit.
   Binds `tree_sha` (not branch), `command_sha256`, `policy_sha`, `image_sha`, applied
   mount/egress/secret shape, `returncode`. Replay-resistant via tree_sha binding + per-run nonce
   (append-only, never update-in-place). Store via existing `side_effect_ledger_runtime.record(
   effect_kind="validation_sandbox_run")` for v1 (avoids a new tracked-schema predicate; PCO-046
   is already taken).
4. **Cost/latency**: baseline validate-pr ~6-7 min. Cache by image digest + baked venv. REJECT
   warm-container reuse for v1 (reintroduces the cross-lane-contamination class CE-410 exists to
   kill) → ephemeral-per-run `--rm` + tmpfs; target ≤~60s container overhead ceiling; fallback =
   single-use pre-staged containers, never reuse across two runs.
5. **#437 integration**: one shared launcher module (the single place permitted to build
   podman/docker argv), generalized from `build_podman_run_argv`; conveyor daemon calls it
   in-process today; if the daemon itself becomes contained, the call becomes an RPC to a
   host-side process and the daemon container NEVER gets an engine socket (mirrors
   deploy/dgx-controller-runsc/DESIGN.md C1). Rootless-Podman-CLI needs NO socket = best per the
   scoping order. One canonical image for all roles, parameterized by the policy record.

## ⚠️ Risk 1 — RUNTIME-ENGINE DECISION (cross-cutting, elevate to Operator)
The worker-container-policy schema enum is `podman-rootless` | `docker-rootless`. But the only
PROVEN-LIVE containment on the DGX is Docker + the custom `runsc-gvproxy-ptrace` OCI runtime
(gVisor) — a different axis than "rootless Docker daemon". `PodmanCommandRunner` has never been
proven live (fails closed when podman absent). This decision affects #437, the harvest daemon,
AND every future PCO worker container — not just validation. MUST be an explicit recorded
decision: (a) prove rootless Podman on the DGX before slice 8b, OR (b) extend the enum/OSD-I-1 to
name "Docker + gVisor/runsc" and update worker_runtime.py.

## Other risks (SPIKE recommendations)
- R2: `run_command`/ephemeral run-one-capture primitive is unbuilt (only allocate/terminate/gc
  exist) → build a narrow `run --rm` foreground primitive, don't route validation through the
  full PCO claim/lease lifecycle.
- R3: receipt via side-effect-ledger additive effect_kind for v1 (not a new schema predicate).
- R4: build the shared launcher (slice 8a) BEFORE the container-exec code, else validation
  becomes a 4th engine-invocation site (the "two substrates" problem #437 warns against).
- R5: measure ephemeral overhead vs ~60s ceiling; fall back to single-use pre-staged, never reuse.

## Proposed slicing (9/10 alignment)
- **8a (S)**: extract shared container-launcher (foreground `--rm` + trailing-command) from
  `build_podman_run_argv` — #437 single-privileged-launcher precursor.
- **8b (S/M)**: production validation-sandbox runner behind the UNCHANGED seam, using 8a +
  promoted governance policy record; emits `ValidationSandboxReceipt` via side-effect ledger.
- **8c (S)**: wire conveyor armed-mode validate-runner to require 8b's runner (preserves slice-7
  floor; not yet gating on receipt at publish).
- **9 (S)**: armed-construction refusal without matching receipt (tree_sha == head, policy/image
  sha == currently-ratified, empty egress/secrets, rc==0).
- **10 (S)**: publish-reverify — re-derive tree_sha immediately before push/PR, confirm ==
  receipt's bound tree_sha; per-phase audit trail.
- Then: Re-Arming Evidence Bundle → SEPARATE Operator ratification.

## Access caveat
ce-ops#437 returned 404 to the read-only role (private org, no auth) — design relied on the
mandate package's restatement + MEMORY doctrine. Route a follow-up to an authenticated role if
direct issue-thread citation fidelity is needed.
