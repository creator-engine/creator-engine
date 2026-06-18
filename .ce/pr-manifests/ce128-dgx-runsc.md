# PR path manifest - ce128-dgx-runsc

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce128-dgx-runsc

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#128 on 2026-06-18: author DGX-side runsc/gVisor
Codex containment artifacts, then revise the wrapper to avoid the nested DGX
root-netns failure by mirroring CE runner networking through the Stage-1
`gvproxy`/`gvisor-tap-vsock` path. Follow-up DGX testing confirmed that
`runsc --platform=systrap --network=host` fixed networking for a basic
container but Codex panicked in Rust alternate signal stack guard-page setup, so
the Codex runtime default moves to the `ptrace` platform.

The changes:
- The DGX wrapper defaults to a dedicated `runsc-gvproxy-ptrace` Docker runtime
  rather than the plain `runsc` runtime.
- The wrapper does not pass Docker `--network` by default and refuses the old
  plain `runsc` / Docker network path unless explicitly overridden for
  diagnostics.
- The README documents the CE runner evidence (`runsc`, mediated egress), the
  required DGX runtime registration, the ptrace-over-systrap rationale for
  Codex, and an HTTPS egress check.
- The image remains a minimal seat-matched runtime with CA certificates, `git`,
  and no baked Codex auth/config/binary.

Per-file purpose (the closed path-set - 5 paths; `(A)` add):
- **`.ce/changelog/ce128-dgx-runsc.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce128-dgx-runsc.md`** *(A)* - this carrier.
- **`deploy/dgx-runsc/Dockerfile`** *(A)* - minimal seat-matched Codex runtime
  image.
- **`deploy/dgx-runsc/README.md`** *(A)* - DGX apply and validation steps.
- **`deploy/dgx-runsc/run-codex-runsc.sh`** *(A)* - parameterized Codex TUI /
  `codex exec` wrapper.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a3b59fd29602e8b1ef2ebbb284b555c62cf1e3eba282b80a7d130295fdcd2e45

```text
.ce/changelog/ce128-dgx-runsc.md
.ce/pr-manifests/ce128-dgx-runsc.md
deploy/dgx-runsc/Dockerfile
deploy/dgx-runsc/README.md
deploy/dgx-runsc/run-codex-runsc.sh
```
