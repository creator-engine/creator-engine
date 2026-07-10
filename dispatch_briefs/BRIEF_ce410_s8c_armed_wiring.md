# BRIEF — ce-ops#410 slice 8c: wire conveyor armed-mode validation to the 8b sandbox runner
Role: implementer. Claim: ce-410-s8c-armed-wiring. Branch: `ce-410-s8c-armed-wiring` off origin/main (fetch first — main now contains 8b #777, S3 #778, and shortly S2 #774).

## Goal
Conveyor armed-mode validation must execute through the slice-8b production ValidationSandboxRunner (rootless-podman, ephemeral per-run container, receipt minted and ledger-recorded) instead of the direct env-scrub-only path from slice 7. Slice 9 will make "refuse without receipt" a hard gate; 8c's job is the wiring so a receipt EXISTS for every armed validation run.

## Design SSOT
The ratified slice-8 design you already hold at /var/tmp (CE410_SLICE8_SPIKE_DESIGN co-transferred with your 8b brief): ValidationSandboxSpec/Result seam unchanged; ValidationSandboxReceipt via the additive side-effect-ledger effect_kind (landed in 8b as `validation_sandbox_run`); ephemeral per-run containers. Read your merged 8b code (validation_sandbox_runner.py, validation_sandbox_receipt.py) as the implementation contract — note the rework-hardened requirements: receipt_issuer is REQUIRED (no default), tree_sha is derived+verified from the mounted tree, issued_at is inside the keyed payload.

## Requirements
1. In the conveyor armed path (conveyor.py / conveyor_daemon.py validate-runner seam from slices 6-7): construct ValidationSandboxSpec from the allocation-receipt-backed paths, run via the 8b runner, thread the resulting receipt into the run record/ledger. Disarmed/shadow paths unchanged.
2. Receipt signing-secret sourcing: follow the production sourcing path documented in 8b (explicit issuer construction at daemon startup, material sourced outside the validation environment per the slice-7 scrub seam — the secret must never enter the sandboxed process env).
3. Preserve the S3 lease semantics that just merged: the per-item heartbeat now fires before each item — your sandbox call happens inside an item; do not add heartbeat regressions and do not modify daemon_lease.py internals.
4. Extend-don't-weaken: every armed-mode refusal seam stays intact (missing-seam list incl. path_allocator, daemon_lease, git/gh runners); if the runner needs a new required seam (receipt_issuer), ADD it to the armed refusal list — construction without it must refuse, tested.
5. Tests: armed validate path produces a ledger-recorded receipt bound to the validated tree; missing receipt_issuer refuses at construction; disarmed path untouched (no receipt, no sandbox); no weakened existing tests.
6. Changelog fragment .ce/changelog/ce-410-s8c-armed-wiring.md + carrier via carrier_gen API. Work-class S or M by diff size.

## Stop lines
Do NOT touch: daemon_lease.py, deploy/**, conveyor_discovery.py, forge/automerge*, portability_plane.py, v3_cli.py/ce_cli.py, docs/install.sh, schemas/side-effect-ledger.schema.yaml (the effect_kind already exists — no new kinds). The refuse-without-receipt HARD gate is slice 9, not yours — do not implement it beyond the construction-seam refusal in req 4.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` GREEN one pass, then self-push and open the PR yourself (you have push+PR authority): title "ce-ops#410 slice 8c: conveyor armed-mode validation via sandbox runner", body with "Refs creator-engine/ce-ops#410" (mention-only, NO Closes) + exactly one `- **Declared work class:** <S|M>` line. Then signal: `READY-FOR-HARVEST ce-410-s8c-armed-wiring <full-40-hex-sha>` with the PR number.
