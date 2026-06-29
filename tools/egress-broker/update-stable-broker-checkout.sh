#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: update-stable-broker-checkout.sh --pin SHA [--checkout PATH] [--remote NAME] [--branch NAME]

Fail-closed controller helper for the Surface-B self-review broker stable
checkout. The checkout must already exist and be clean. The script fetches the
remote branch, verifies the requested full commit SHA exists on origin/main (or
the configured remote/branch), checks it out detached, and verifies the final
HEAD exactly matches the pin.

Environment:
  CE_BROKER_HOME       Default checkout path (/opt/ce-broker/creator-engine)
  CE_BROKER_PIN        Pin used when --pin is omitted
  CE_BROKER_REMOTE     Remote used when --remote is omitted (origin)
  CE_BROKER_BRANCH     Branch used when --branch is omitted (main)
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

checkout="${CE_BROKER_HOME:-/opt/ce-broker/creator-engine}"
pin="${CE_BROKER_PIN:-}"
remote="${CE_BROKER_REMOTE:-origin}"
branch="${CE_BROKER_BRANCH:-main}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --checkout)
      checkout="${2:?--checkout requires a path}"
      shift 2
      ;;
    --pin)
      pin="${2:?--pin requires a commit SHA}"
      shift 2
      ;;
    --remote)
      remote="${2:?--remote requires a remote name}"
      shift 2
      ;;
    --branch)
      branch="${2:?--branch requires a branch name}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -n "$pin" ]] || fail "missing required pinned commit SHA (--pin or CE_BROKER_PIN)"
[[ "$pin" =~ ^[0-9a-fA-F]{40}$ ]] || fail "pin must be a full 40-character commit SHA"

case "$checkout" in
  /workspace/creator-engine|/workspace/creator-engine/*|/home/ce-dev-*|/home/ce-dev-*/*|/home/cedev*|/home/cedev*/*)
    fail "target looks like a seat working tree, not a stable broker checkout: $checkout"
    ;;
esac

[[ -d "$checkout" ]] || fail "stable broker checkout is missing: $checkout"
[[ -d "$checkout/.git" || -f "$checkout/.git" ]] || fail "target is not a git checkout: $checkout"

git -C "$checkout" rev-parse --is-inside-work-tree >/dev/null ||
  fail "target is not a valid git worktree: $checkout"

if [[ -n "$(git -C "$checkout" status --porcelain=v1)" ]]; then
  fail "stable broker checkout is dirty; refusing to update: $checkout"
fi

git -C "$checkout" fetch --prune "$remote" "$branch" ||
  fail "could not fetch $remote $branch"

git -C "$checkout" cat-file -e "$pin^{commit}" ||
  fail "pinned commit cannot be verified in checkout: $pin"

remote_ref="refs/remotes/$remote/$branch"
git -C "$checkout" show-ref --verify --quiet "$remote_ref" ||
  fail "remote tracking ref is missing after fetch: $remote_ref"

git -C "$checkout" merge-base --is-ancestor "$pin" "$remote_ref" ||
  fail "pinned commit is not reachable from $remote/$branch: $pin"

git -C "$checkout" checkout --detach "$pin" ||
  fail "could not check out pinned commit: $pin"

head_sha="$(git -C "$checkout" rev-parse HEAD)"
[[ "$head_sha" == "$pin" ]] || fail "checkout HEAD $head_sha does not match pin $pin"

if [[ -n "$(git -C "$checkout" status --porcelain=v1)" ]]; then
  fail "stable broker checkout became dirty after checkout: $checkout"
fi

printf 'stable broker checkout ready: %s @ %s\n' "$checkout" "$head_sha"
