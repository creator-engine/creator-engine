#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Provision or refresh a local read-only checkout of the private ce-ops repo.

Environment:
  CE_OPS_REPO_URL            Git URL for ce-ops.
                             Default: git@github.com:creator-engine/ce-ops.git
  CE_OPS_READONLY_CHECKOUT   Destination path.
                             Default: /opt/creator-engine/ce-ops-readonly
  CE_OPS_REF                 Branch to track.
                             Default: main
  CE_OPS_SEAT_GROUP          Optional local group allowed to read the checkout.
                             When unset, the checkout is world-readable.

Examples:
  sudo CE_OPS_SEAT_GROUP=ce-seat ./tools/provision-ce-ops-readonly.sh
  CE_OPS_READONLY_CHECKOUT=$HOME/.cache/ce-ops-readonly ./tools/provision-ce-ops-readonly.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

repo_url="${CE_OPS_REPO_URL:-git@github.com:creator-engine/ce-ops.git}"
checkout="${CE_OPS_READONLY_CHECKOUT:-/opt/creator-engine/ce-ops-readonly}"
ref="${CE_OPS_REF:-main}"
seat_group="${CE_OPS_SEAT_GROUP:-}"

case "$repo_url" in
  http://*:*@*|https://*:*@*)
    printf 'refusing credential-bearing CE_OPS_REPO_URL; configure read-only git credentials outside the repo\n' >&2
    exit 2
    ;;
esac

if ! command -v git >/dev/null 2>&1; then
  printf 'git is required\n' >&2
  exit 127
fi

if [[ -n "$seat_group" ]] && ! getent group "$seat_group" >/dev/null 2>&1; then
  printf 'CE_OPS_SEAT_GROUP does not exist: %s\n' "$seat_group" >&2
  exit 2
fi

parent="$(dirname "$checkout")"
mkdir -p "$parent"

if [[ -e "$checkout" && ! -d "$checkout/.git" ]]; then
  printf 'destination exists but is not a git checkout: %s\n' "$checkout" >&2
  exit 2
fi

export GIT_TERMINAL_PROMPT="${GIT_TERMINAL_PROMPT:-0}"

if [[ ! -d "$checkout/.git" ]]; then
  git clone --branch "$ref" --single-branch --no-tags "$repo_url" "$checkout"
else
  chmod -R u+rwX "$checkout"
  current_origin="$(git -C "$checkout" remote get-url origin)"
  if [[ "$current_origin" != "$repo_url" ]]; then
    printf 'destination origin mismatch: expected %s, found %s\n' "$repo_url" "$current_origin" >&2
    exit 2
  fi
  git -C "$checkout" fetch --prune origin "$ref"
  git -C "$checkout" checkout "$ref"
  git -C "$checkout" pull --ff-only origin "$ref"
fi

git -C "$checkout" remote set-url --push origin DISABLED_READ_ONLY_CE_OPS_CHECKOUT
git -C "$checkout" config advice.detachedHead false
git -C "$checkout" config pull.ff only

if [[ -n "$seat_group" ]]; then
  chgrp -R "$seat_group" "$checkout"
  find "$checkout" -type d -exec chmod 0550 {} +
  find "$checkout" -type f -exec chmod 0440 {} +
else
  find "$checkout" -type d -exec chmod 0555 {} +
  find "$checkout" -type f -exec chmod 0444 {} +
fi

printf 'ce-ops read-only checkout ready: %s\n' "$checkout"
printf 'tracked ref: %s\n' "$ref"
