# ce-ops#128 SUB-B - Docker runsc renderer

- Changed the gVisor proxy backend's pure `RunscPlan` renderer from a direct
  `runsc` argv to the DGX Docker shape using the registered
  `runsc-gvproxy-ptrace` runtime.
- Added explicit plan inputs and fail-closed validation for Docker runtime name,
  uid/gid user rendering, host `CODEX_HOME`, host Codex binary, absolute policy
  mounts, digest-pinned image references, and omitted Docker networking.
- Extended focused backend tests to cover rendered Docker argv, CODEX_HOME/bin
  mount handling, uid-only and uid:gid users, runtime selection, and unsafe
  input refusals.
