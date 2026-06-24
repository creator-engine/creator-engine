---
slug: feat-runsc-detached-launch-mode
date: 2026-06-24
kind: added
scope: deploy/runsc launchers (vps + dgx-controller)
issue: ce-ops#207-adjacent (detached launch); review fix per ce-ops#408
---

**Detached (named-persistent) launch mode for the runsc launchers — kill the tmux
crutch — with a fail-closed secret-retention guard for token-bearing harnesses.**

- Adds `--detach` / `CE_VPS_DETACH` / `CE_DGX_CONTROLLER_DETACH` to launch contained
  seats via `docker run -d --name` (named-persistent, no `--rm`) and poll herdr for
  readiness, instead of a foreground tmux-held `docker run --rm`. A crashed/stopped seat
  stays inspectable (docker logs/exit code) for forensics.
- **Secret-retention guard (review fix):** in detached/named-persistent mode a
  token-bearing `--env CLAUDE_CODE_OAUTH_TOKEN` lands in the container's inspectable
  metadata (`docker inspect` `Config.Env`) and survives until an explicit `docker rm` —
  foreground `--rm` previously scrubbed it on exit, so detached mode silently extended the
  credential's lifetime into readiness-failure/forensics state. The launchers now **fail
  closed**: detached launch of a token-bearing harness (Claude / `--harness controller`)
  is REFUSED unless the operator explicitly accepts the tradeoff via
  `CE_VPS_ALLOW_DETACHED_TOKEN_ENV=1` / `CE_DGX_CONTROLLER_ALLOW_DETACHED_TOKEN_ENV=1`
  (which also prints a retention warning). Codex detached carries no token and is
  unaffected. Foreground (`--rm`) is unaffected.
- Follow-up (tracked separately): move the credential through a non-inspectable path
  (tmpfs secret-file consumed by the image entrypoint) so detached token-bearing seats
  never retain the secret in metadata even when opted in — the controller image
  (`ENTRYPOINT tini --`) supports a wrapper; the VPS image's harness entrypoint needs the
  read-from-file change.
