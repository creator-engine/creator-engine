# BRIEF — ce-ops#437 slice 4: published canonical runtime image (multi-arch)
Role: implementer (design-forward: read the referenced artifacts before writing). Claim: ce-437-s4-runtime-image. Branch: `ce-437-s4-runtime-image` (worktree under /var/tmp, off origin/main — fetch first; main should contain #778's deploy/daemons/ artifacts. If your origin/main lacks deploy/daemons/Dockerfile, STOP and signal BLOCKED stale-main).

## Goal
The two-plane architecture (ADR-0014, docs/adr/) requires ONE canonical Linux container runtime image that all CE container forms are born from (daemons, validation sandbox, seats eventually). Slices 1-3 landed the consumers; slice 4 makes the image REAL AND PUBLISHED: a reproducible multi-arch build + publish pipeline with digest-pinned references consumers can adopt.

## Embedded context (you cannot read ce-ops)
- #778 (merged today) added deploy/daemons/Dockerfile which builds FROM a ce-validator base — study it and deploy/daemons/run-daemon-container.sh for the consumption pattern, plus governance/policies/worker-container/podman-verification-v1.yaml (the 8b sandbox pins image identity by sha).
- KNOWN DEFECT to solve in the publish design (fleet ticket, embedded): the current image manifest reference used for the DGX seat rebuild pins an amd64 digest → exec-format-error on the aarch64 DGX (GB10). The published image MUST be a multi-arch manifest list (linux/amd64 + linux/arm64) and every in-repo digest-pin reference must pin the MANIFEST LIST digest, not a single-arch digest.
- Engine posture (ratified): image must be ENGINE-AGNOSTIC — buildable/runnable by both Docker and rootless podman; validation/PCO tier runs rootless podman, seats run Docker+runsc. No engine-specific features baked in.

## Deliverables
1. deploy/runtime-image/Dockerfile (or clearly-named location under deploy/): the canonical image definition — base OS + pinned Python + the validator package install seam (wheel or source-install arg), non-root default user, OCI labels (source repo, version, revision).
2. Build+publish workflow: .github/workflows/publish-runtime-image.yml — buildx (or equivalent) multi-arch build (amd64+arm64), pushed to GHCR under the repo's namespace, tagged {version} + {git-sha}, MANIFEST LIST digest surfaced in the job output/summary. Trigger: manual workflow_dispatch + on release tags — NOT on every push. Follow the repo's existing workflow-permissions conventions (the workflow-permissions audit gate will check least-privilege; look at existing workflows for the pattern; packages:write only where needed).
3. A short consumer contract doc: deploy/runtime-image/README.md — how daemons/sandbox/seat images derive FROM the canonical image, the digest-pin rule (manifest-list digest only, with the arm64/amd64 defect above as the recorded rationale), and how to bump pins.
4. Tests: whatever the repo's existing deploy-file test conventions support (e.g. workflow YAML parse/permissions tests, Dockerfile lint-style checks if precedent exists — search validators/tests for how #778's deploy files were tested and match that pattern; do not invent a new test framework).
5. Changelog fragment .ce/changelog/ce-437-s4-runtime-image.md + carrier via carrier_gen API. Work-class: S or M per diff size (~400-line rule).

## Stop lines (hard)
Do NOT touch: conveyor_daemon.py / conveyor.py / daemon_lease.py (8c wiring incoming on dev-1), validation_sandbox_*.py, forge/automerge*, portability_plane.py, v3_cli.py/ce_cli.py, docs/install.sh, docs/downloads/**, deploy/dgx-runsc/** (host WIP exists), existing deploy/daemons/* CONTENT (you may REFERENCE the image from your README; if deploy/daemons/Dockerfile's FROM line must change to consume the canonical image, note it as a follow-up in the done-report instead of editing). No registry credentials in any file — the workflow uses the standard GITHUB_TOKEN/GHCR pattern.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` GREEN one pass before commit-for-harvest; if environmentally impossible in-container, run the focused set (workflow/deploy tests + path manifest) green and signal BLOCKED with the exact failure class (controller re-runs authoritative preflight at harvest). Signal exactly:
`READY-FOR-HARVEST ce-437-s4-runtime-image <full-40-hex-sha>` (or `BLOCKED ce-437-s4-runtime-image <reason>`).
