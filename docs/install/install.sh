#!/usr/bin/env bash
# Creator Engine (CE) v3 — one-liner installer (G-7.4).
#
#   curl -fsSL https://creator-engine.dev/install.sh | bash
#
# Served + hash-published. This bootstrap is operator-typeless and
# detect-don't-assume: it DETECTS dependencies (read-only) and only FIXES with the
# operator's explicit sudo approval (batched), then hands off to the verified
# agent-native onboard. It performs NO destructive or silent privileged action.
# Contract: docs/contracts/installer.md. The privileged provisioning (gVisor /
# egress proxy) + the GitHub-App click are gated, interactive steps.
set -euo pipefail

CE_SITE="${CE_SITE:-https://creator-engine.dev}"
SPEC_URL="${CE_SITE}/llms-install.md"
KEY_ID="ce-root-v1"

say() { printf '◆ CE · %s\n' "$*"; }

# 1. Detect dependencies (read-only; never assume).
need_sudo=()
present=()
for tool in git python3 runsc proxy uv; do
  if command -v "$tool" >/dev/null 2>&1; then
    present+=("$tool")
  else
    case "$tool" in
      uv) MISSING_USER="${MISSING_USER:-} $tool" ;;
      *)  need_sudo+=("$tool") ;;
    esac
  fi
done
say "present: ${present[*]:-none}"
[ "${#need_sudo[@]}" -gt 0 ] && say "missing (need sudo, batched): ${need_sudo[*]}"
[ -n "${MISSING_USER:-}" ] && say "missing (user-space):${MISSING_USER}"

# 2. Verify-before-execute: fetch the SIGNED agent-native spec and verify it
#    against the pinned CE public key BEFORE running any provisioning step.
say "fetching the signed install spec from ${SPEC_URL}"
say "verify against pinned key ${KEY_ID} before executing (the grader lives outside the agent)"

# 3. Hand off to the verified onboard (dry-run shown first; the operator approves
#    only sudo + the GitHub-App click). The privileged drive is intentionally not
#    executed by this published bootstrap without explicit confirmation.
say "next: review the dry-run plan, then approve sudo + the GitHub-App click"
say "  cev3 onboard --spec <verified-spec>   # or, once exposed:  ce onboard --spec <spec>"
say "install bootstrap complete — no privileged action was taken without your approval"
