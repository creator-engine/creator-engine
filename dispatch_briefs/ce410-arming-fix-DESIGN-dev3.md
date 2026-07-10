# DISPATCH BRIEF — dev-3 — ce-ops#410 ARCHITECT SLICE: conveyor-arming fix design
Date: 2026-07-03 · Role: architect (READ-ONLY design output; you write NOTHING except your report file) · Work class: design (no code)
Deliver: write your COMPLETE design doc to /var/tmp/CE410_ARMING_FIX_DESIGN.md in the container, report DESIGN-READY + its sha256. No branch, no commits, no code changes.

## Mandate
Design the fixes for the three structural blockers that keep the conveyor/integrator belt UNARMED
(found by dev-1's independent security review 2026-07-02; belt stays unarmed until these are FIXED,
not waived). Ground every design decision in the actual code in your checkout (fetch origin/main
first — it moved today: automerge Tier A + pin-migration slices merged).

## The three blockers (from the security review + ticket, embedded since you cannot read ce-ops)
1. NO DAEMON-OWNED PATH ALLOCATION: worktree/staging paths used during validation are caller-influenced;
   the daemon must own and allocate its working paths itself (predictable, collision-free, tenant-safe).
2. VALIDATION SUBPROCESS INHERITS DAEMON SECRETS: the validation run inherits os.environ from the daemon,
   leaking approval-wall/forge tokens into code-under-validation's reach. Needs a credentialless
   validation sandbox (scrubbed env, minimal PATH, no network creds).
3. NO TRANSPORT/VALIDATION CREDENTIAL SEPARATION: the same credential context both fetches PRs and
   validates them; fetching (transport) and validating (execution of untrusted diff) need separated
   privilege domains.

## Design requirements
- Study: validators/creator_engine_validator/forge/integrator_belt.py (the belt/daemon),
  the queue-daemon wiring in v3_cli.py, conveyor.py if present, and the worker-container
  protocol (docs/operations/WORKER_CONTAINER_PROTOCOL.md) — the credentialless sandbox should
  reuse the existing container/policy primitives where possible, not invent a parallel mechanism.
- For each blocker: current-state evidence (file:line), proposed fix, blast radius, test plan,
  and whether it is XS/S/M sized as an implementation ticket.
- Fail-closed bias throughout; no fix may weaken an existing gate.
- Sequencing: which fix first, and what the re-arming evidence bundle must show before the
  Operator can ratify arming.

## Evidence: DESIGN-READY + sha256 of /var/tmp/CE410_ARMING_FIX_DESIGN.md + one-paragraph summary.
## Root cause (from dev-1 independent security review, 2026-07-02)

The conveyor daemon's execution model — running git/gh in payload-specified directories, trusting ambient `.git/config`, and merging daemon secrets into validation subprocess env — is structurally unsafe to arm without three foundational fixes.

See ce-ops#388 comment for full dev-1 review outcome and evidence chain.

## Blockers (must close before arming)

- [ ] **daemon-owned allocation:** Wire real daemon-owned allocation/receipt for worktree, repo, and bundle paths. Direct `ConveyorDaemonItem` objects must carry an unforgeable daemon allocation/provenance check, or armed mode must only consume allocation records created by the daemon. (Currently defaults to `daemon_owned_paths_allocated=True` with no verification.)

- [ ] **credentialless validation sandbox:** Run validation in a credentialless sandbox with a scrubbed allowlist environment. Do not merge `os.environ`; do not run attacker-controlled validator code with daemon secrets, forge token (`GH_TOKEN`), SSH agent, credential helper, or privileged network. (Currently: `conveyor.py:484-502` merges `{**os.environ, **env}` → full credential exposure class if harvest branch lands malicious validator code.)

- [ ] **transport-credential separation:** Keep git/gh transport authority separate from validation. Only push/PR subprocesses should receive the forge credential, and only after validation completes in the unprivileged environment. (Currently: credentials flow through the validation phase.)

- [ ] **daemon-private restrictive roots:** Require daemon-private, restrictive roots rather than broad writable roots. The current `_confine_path()` check is useful defense-in-depth but not a substitute for daemon-owned allocation.

## Related

- ce-ops#388 (security design review tracking issue)
- ce-ops#383 (argv hardening, approved; root-trust boundary remains)
- creator-engine#740 (conveyor go-live PR, approved but disarmed-pending-fixes)
