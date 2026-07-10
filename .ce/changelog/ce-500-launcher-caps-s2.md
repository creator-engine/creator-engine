## ce-500-launcher-caps-s2

- fix(contained-seat): add cgroup memory cap to DGX and VPS runsc launchers

  Adds `CE_DGX_MEMORY_LIMIT` (default `8g`) and `CE_VPS_MEMORY_LIMIT` (default `8g`)
  env-configurable docker `--memory` flags to the runsc seat launchers. Seats now OOM
  inside the container (pytest dies, work survives in the durable bind-mount worktree)
  rather than triggering a host OOM-kill that evaporates the gVisor sentry and all in-
  progress work. Disable by setting the env var to empty string.

- fix(preflight): add governed TMPDIR + parallelism cap wrapper for host preflight runs

  Adds `tools/preflight-caps.sh`: a thin bash wrapper that exports TMPDIR to a disk-backed
  path (default `$HOME/tmp`), warns if the resolved TMPDIR is on tmpfs, caps `-n auto` to
  `-n 4` (configurable via CE_PREFLIGHT_MAX_WORKERS), forwards all argv to the wrapped
  command, and cleans up `pytest-of-*` tmpdirs post-run. Prevents host-tmpfs RAM
  competition with contained-seat sentry processes during concurrent preflight runs.

**Declared work class: story**
