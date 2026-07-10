# SEED BRIEF — CE-410 slice 8b: production validation-sandbox runner (receipt-emitting)

Ticket: ce-ops#410 slice 8b. Design SSOT: /var/tmp/CE410_SLICE8_SPIKE_DESIGN_20260704.md
(transferred alongside this brief — READ IT FULLY FIRST; it is Operator-ratified as written).
Role: implementer. Seat: dev-1 (self-push). Branch: ce-410-s8b-sandbox-runner off FRESH origin/main.
PRECONDITION (verify before starting): PR #773 (slice 8a shared container-launcher) is MERGED to
main — `git fetch origin main && git log origin/main --oneline -5` must show it. If not merged,
wait/re-check; do not build on the PR branch.

Ratified engine decision (Risk 1 resolved 2026-07-04): validation/PCO tier = ROOTLESS PODMAN
(DGX-proven). Build for `podman-rootless` per the policy schema enum. No Docker path in this slice.

## Scope (design §8b, S/M)
1. Promote examples/well-formed/worker-container-policies/podman-verification.yaml →
   governance/policies/worker-container/podman-verification-v1.yaml (Source-ratified record with
   real policy_sha; follow the existing governance-record promotion pattern in the repo).
2. NEW validators/creator_engine_validator/validation_sandbox_runner.py — production runner
   BEHIND THE UNCHANGED validation_sandbox.py seam (ValidationSandboxSpec/Result are FROZEN, PR
   #768 — zero modifications):
   - Uses slice-8a's container_launcher foreground `--rm` mode (run_foreground_podman /
     build_podman_run_argv) — the launcher stays the ONLY engine-argv construction site. Do NOT
     modify container_launcher.py; if an additive extension is truly unavoidable, isolate it in
     one minimal commit and flag it in your report.
   - Spec→run mapping per design §1: verification policy selected+asserted; command = trailing
     argv; cwd = allocator workspace bind-mounted READ-ONLY at the identical absolute path; env =
     repeated --env from already-scrubbed spec.env (no broker inject); timeout host-side AND
     engine-side (--timeout).
   - Ephemeral per-run: --rm + container-local tmpfs TMPDIR. NO warm-container reuse (rejected in
     design — reintroduces cross-lane contamination).
3. NEW ValidationSandboxReceipt (ADDITIVE — Spec/Result untouched): nonce+HMAC signed following
   the existing DaemonPathReceipt pattern; binds tree_sha (not branch), command_sha256,
   policy_sha, image_sha, applied mount/egress/secret shape, returncode. Minted ONLY by the
   function that observed the container exit. Persist via existing
   side_effect_ledger_runtime.record(effect_kind="validation_sandbox_run") — append-only, never
   update-in-place. NO new tracked-schema predicate in this slice.
4. Tests (unit, no podman required at test time — injected runner seam): spec→argv mapping
   incl. read-only mount + identical-path assertion; receipt minted only on observed exit +
   binds all listed fields; receipt NOT minted on launcher failure/timeout; tamper check (HMAC
   verify fails on any field change); ledger record appended with correct effect_kind; timeout
   propagation both layers.
5. Changelog fragment .ce/changelog/ce-410-s8b-sandbox-runner.md.

## Stop line (allowed paths)
governance/policies/worker-container/** (new) · validators/creator_engine_validator/validation_sandbox_runner.py (new)
· receipt module file (new, name per repo convention) · validators/tests/unit/test_validation_sandbox_runner.py (new)
· .ce/changelog/ce-410-s8b-sandbox-runner.md
FORBIDDEN: validation_sandbox.py (frozen seam) · container_launcher.py / worker_runtime.py (8a —
additive-only escape hatch above) · conveyor_daemon.py, conveyor_discovery.py, daemon_lease (dev-4
territory) · ce_cli.py/v3_cli.py (dev-3 territory) · checks/** · docs/install.sh · docs/downloads/**
· 8c wiring (conveyor armed-mode) is the NEXT slice — do not wire the daemon here.

## Obligations
- FULL `ce validate-pr` GREEN locally in ONE pass before push (CI parity; never discover gates in CI).
- PR body: exactly one `- **Declared work class:** <XS|S|M|L>` line sized to the diff; changelog +
  carrier (regen via carrier_gen API, stem == branch slug); reference "Part of creator-engine/ce-ops#410".
- Self-push + open PR; report PR number + head SHA. Controller runs the independent review leg.
- This is parallel-safe with your #775 test task (disjoint files) — run both via your worktree fan-out.
