#!/usr/bin/env bash
#
# switch-openai-account.sh — mechanical helper for switching the codex fleet
# between two OpenAI Pro subscriptions.
#
# SSOT runbook: docs/operations/SWITCH_OPENAI_ACCOUNT.md (read it first).
#
# This automates ONLY the safe, mechanical parts:
#   pre-stage <acctB-codex-home>          device-auth login acct B into a
#                                         parallel CODEX_HOME (non-disruptive).
#   swap <target-codex-home> <acctB-home> back up the current auth.json, then
#                                         copy acct B's auth.json in (host-side).
#   plan <dev-1|dev-3|dev-4>              print the exact relaunch + resume
#                                         commands (does NOT execute a contained
#                                         relaunch — operator/controller-gated).
#
# Invariants:
#   * Never prints auth.json / token contents.
#   * Idempotent + fail-safe: refuses if a required auth.json is missing; always
#     backs up before overwrite.
#   * Contained-seat relaunch is NEVER executed here (breaks bwrap; must go
#     through the canonical launcher). We only print the command.
#
set -euo pipefail

PROG="$(basename "$0")"

err()  { printf '%s: error: %s\n' "$PROG" "$*" >&2; }
info() { printf '%s: %s\n' "$PROG" "$*" >&2; }

usage() {
  cat <<EOF
Usage:
  $PROG pre-stage <acctB-codex-home>
  $PROG swap <target-codex-home> <acctB-codex-home>
  $PROG plan <dev-1|dev-3|dev-4>
  $PROG -h | --help

See docs/operations/SWITCH_OPENAI_ACCOUNT.md for the full procedure, order,
and the contained-seat canonical-relaunch rule.
EOF
}

# Resolve the codex binary without assuming a path.
codex_bin() {
  if [ -n "${CODEX_BIN:-}" ]; then
    printf '%s' "$CODEX_BIN"
    return 0
  fi
  if command -v codex >/dev/null 2>&1; then
    command -v codex
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# pre-stage: device-auth login acct B into a parallel CODEX_HOME.
# Non-disruptive: running seats already hold their token in memory.
# ---------------------------------------------------------------------------
cmd_pre_stage() {
  local home="${1:-}"
  if [ -z "$home" ]; then
    err "pre-stage requires <acctB-codex-home>"
    usage; exit 2
  fi
  local bin
  if ! bin="$(codex_bin)"; then
    err "codex binary not found (set CODEX_BIN or put codex on PATH)"
    exit 1
  fi

  if [ -f "$home/auth.json" ]; then
    info "acct B already staged: $home/auth.json exists."
    info "re-run 'codex login' manually only if acct B credentials rolled."
    info "nothing to do (idempotent)."
    return 0
  fi

  mkdir -p "$home"
  info "launching device-auth login into CODEX_HOME=$home"
  info "complete the printed device-auth flow with ACCT B credentials."
  # The device-auth flow prints its own URL/code (OpenAI UX, not a token leak).
  CODEX_HOME="$home" "$bin" login

  if [ -f "$home/auth.json" ]; then
    info "staged OK: $home/auth.json is ready (contents not shown)."
  else
    err "login finished but $home/auth.json was not created — check the flow."
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# swap: back up current auth.json, then copy acct B's in. Host-side.
# Fail-safe: refuses if either auth.json is missing; always backs up first.
# ---------------------------------------------------------------------------
cmd_swap() {
  local target="${1:-}" src="${2:-}"
  if [ -z "$target" ] || [ -z "$src" ]; then
    err "swap requires <target-codex-home> <acctB-codex-home>"
    usage; exit 2
  fi

  local target_auth="$target/auth.json"
  local src_auth="$src/auth.json"

  if [ ! -f "$target_auth" ]; then
    err "target auth.json missing: $target_auth (refusing — nothing to back up)"
    exit 1
  fi
  if [ ! -f "$src_auth" ]; then
    err "acct B auth.json missing: $src_auth (run 'pre-stage $src' first)"
    exit 1
  fi

  # Idempotent: if target already equals acct B, do nothing (no needless backup).
  if cmp -s "$target_auth" "$src_auth"; then
    info "target already matches acct B ($target_auth) — no swap needed."
    return 0
  fi

  local ts backup
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="$target_auth.bak.$ts"
  cp -p "$target_auth" "$backup"
  info "backed up current auth.json -> $backup"

  # Copy via temp + atomic mv so a partial copy can't leave a broken auth.json.
  local tmp
  tmp="$(mktemp "$target/.auth.json.new.XXXXXX")"
  cp -p "$src_auth" "$tmp"
  chmod 600 "$tmp" 2>/dev/null || true
  mv -f "$tmp" "$target_auth"
  info "swapped acct B auth.json into $target_auth (contents not shown)."
  info "to revert: $PROG swap accepts the backup's home, or restore $backup"
}

# ---------------------------------------------------------------------------
# plan: print the exact relaunch + resume commands for a seat.
# Does NOT execute a contained relaunch (operator/controller-gated).
# ---------------------------------------------------------------------------
cmd_plan() {
  local seat="${1:-}"
  if [ -z "$seat" ]; then
    err "plan requires <dev-1|dev-3|dev-4>"
    usage; exit 2
  fi
  case "$seat" in
    dev-1|dev1)
      cat <<'EOF'
# dev-1 — Hetzner VPS (ce-dev-1), NON-contained.
# Relaunch inline in its tmux pane (ce-dev1-orchestrator %0):
#   1. stop the running `codex` cleanly (let it exit; do not C-c mid-op)
#   2. relaunch:
codex
#   3. then: codex resume <SESSION_ID>   (or re-seed from handoff)
#   4. verify: /status (new account) + /usage (fresh pool)
EOF
      ;;
    dev-3|dev3)
      cat <<'EOF'
# dev-3 — Hetzner VPS (ce-dev-3), CONTAINED.
# Relaunch via the CANONICAL launcher ONLY. NEVER raw codex / ssh+tmux
# (breaks bwrap). The command below is OPERATOR/CONTROLLER-GATED — run it
# through the governed launch path, not from this helper:
deploy/vps-runsc/run-vps-runsc.sh --harness codex
#   then: codex resume <SESSION_ID>   (or re-seed from handoff)
#   verify: /status (new account) + /usage (fresh pool)
# See docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
EOF
      ;;
    dev-4|dev4)
      cat <<'EOF'
# dev-4 — DGX Spark (cedev4), CONTAINED.
# Relaunch via the CANONICAL launcher ONLY. NEVER raw codex / ssh+tmux
# (breaks bwrap). The command below is OPERATOR/CONTROLLER-GATED — run it
# through the governed launch path, not from this helper:
deploy/dgx-runsc/run-codex-runsc.sh
#   then: codex resume <SESSION_ID>   (or re-seed from handoff)
#   verify: /status (new account) + /usage (fresh pool)
# See docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
EOF
      ;;
    *)
      err "unknown seat: $seat (expected dev-1, dev-3, or dev-4)"
      exit 2
      ;;
  esac
  info "plan printed for $seat — contained relaunch is NOT executed here."
}

main() {
  local sub="${1:-}"
  case "$sub" in
    pre-stage) shift; cmd_pre_stage "$@" ;;
    swap)      shift; cmd_swap "$@" ;;
    plan)      shift; cmd_plan "$@" ;;
    -h|--help|help|"") usage ;;
    *) err "unknown subcommand: $sub"; usage; exit 2 ;;
  esac
}

main "$@"
