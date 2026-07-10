#!/usr/bin/env bash
# reap-scratch.sh — F-1.3 slice 1: deterministic scratch reaper
#
# Sweeps age-policy scratch paths and reclaims disk space.  Idempotent.
# Refuses nothing: every category is attempted independently; failures in
# one category do not block others.
#
# Age policies (per VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710 §C/F-1.1):
#   /var/tmp/wt-*   48h   (worktree scratch)
#   /var/tmp/pt-*   24h   (pytest-tmp scratch)
#   docker images   untagged only (docker image prune --filter "dangling=true")
#
# All reclaimed-bytes totals are logged to stdout (captured by journald
# when run under systemd).
#
# Usage:
#   reap-scratch.sh [--dry-run]
#
# Flags:
#   --dry-run   Print what would be removed without removing anything.
#               Exits 0.  Idempotent; safe to run at any time.
#
# Design notes:
#   - Pure mechanics; no judgment or lease-awareness (that belongs in a future
#     daemon layer, per ce-daemon-vs-agent-rubric).
#   - Shellcheck-clean (SC version 0.8+).
#   - Does NOT remove docker images by name/tag — only dangling/untagged
#     images are pruned to avoid clobbering pinned digests.
#   - containerd gVisor GC is out of scope for slice 1 (requires crictl or
#     nerdctl and additional privilege; tracked separately).
#
# Exit codes:
#   0  All categories completed (or --dry-run).
#   1  One or more categories encountered a non-fatal error (partial success).

set -euo pipefail

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
DRY_RUN=0
ERRORS=0

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=1
            ;;
        *)
            echo "ERROR: unknown argument: $arg" >&2
            echo "Usage: $0 [--dry-run]" >&2
            exit 1
            ;;
    esac
done

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "reap-scratch: --dry-run mode; nothing will be deleted"
fi

# ---------------------------------------------------------------------------
# Helper: log a reclaim summary line
# ---------------------------------------------------------------------------
_log_reclaim() {
    local category="$1"
    local bytes="$2"
    if [[ "$bytes" -gt 0 ]]; then
        local human
        human=$(numfmt --to=iec-i --suffix=B "$bytes" 2>/dev/null || echo "${bytes}B")
        echo "reap-scratch: reclaimed ${human} (${bytes} bytes) from ${category}"
    else
        echo "reap-scratch: reclaimed 0 bytes from ${category}"
    fi
}

# ---------------------------------------------------------------------------
# Helper: sum disk usage of a list of paths
# ---------------------------------------------------------------------------
_disk_usage_bytes() {
    local total=0
    local path
    for path in "$@"; do
        if [[ -e "$path" ]]; then
            local size
            size=$(du -sb "$path" 2>/dev/null | awk '{print $1}') || true
            total=$(( total + ${size:-0} ))
        fi
    done
    echo "$total"
}

# ---------------------------------------------------------------------------
# Helper: find paths older than N hours under a glob pattern
#
# Arguments:
#   $1  base directory (e.g. /var/tmp)
#   $2  glob pattern (e.g. wt-*)
#   $3  max age in hours
# ---------------------------------------------------------------------------
_find_aged() {
    local base_dir="$1"
    local pattern="$2"
    local max_age_hours="$3"
    local max_age_minutes=$(( max_age_hours * 60 ))

    # find emits one path per line; callers use mapfile
    find "$base_dir" -maxdepth 1 -name "$pattern" \
        -mmin "+${max_age_minutes}" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Category 1: /var/tmp/wt-*  (worktrees older than 48h)
# ---------------------------------------------------------------------------
_reap_worktrees() {
    local category="wt-scratch (/var/tmp/wt-* older than 48h)"
    echo "reap-scratch: scanning ${category}"

    mapfile -t targets < <(_find_aged /var/tmp "wt-*" 48)

    if [[ "${#targets[@]}" -eq 0 ]]; then
        echo "reap-scratch: no aged entries found for ${category}"
        _log_reclaim "$category" 0
        return 0
    fi

    local total_bytes=0
    local path
    for path in "${targets[@]}"; do
        local size
        size=$(_disk_usage_bytes "$path")
        if [[ "$DRY_RUN" -eq 1 ]]; then
            echo "reap-scratch: [dry-run] would remove: ${path} (${size} bytes)"
        else
            rm -rf -- "$path" 2>/dev/null || {
                echo "reap-scratch: WARNING: failed to remove ${path}" >&2
                ERRORS=$(( ERRORS + 1 ))
                size=0
            }
        fi
        total_bytes=$(( total_bytes + size ))
    done

    _log_reclaim "$category" "$total_bytes"
}

# ---------------------------------------------------------------------------
# Category 2: /var/tmp/pt-*  (pytest scratch older than 24h)
# ---------------------------------------------------------------------------
_reap_pytest_scratch() {
    local category="pytest-scratch (/var/tmp/pt-* older than 24h)"
    echo "reap-scratch: scanning ${category}"

    mapfile -t targets < <(_find_aged /var/tmp "pt-*" 24)

    if [[ "${#targets[@]}" -eq 0 ]]; then
        echo "reap-scratch: no aged entries found for ${category}"
        _log_reclaim "$category" 0
        return 0
    fi

    local total_bytes=0
    local path
    for path in "${targets[@]}"; do
        local size
        size=$(_disk_usage_bytes "$path")
        if [[ "$DRY_RUN" -eq 1 ]]; then
            echo "reap-scratch: [dry-run] would remove: ${path} (${size} bytes)"
        else
            rm -rf -- "$path" 2>/dev/null || {
                echo "reap-scratch: WARNING: failed to remove ${path}" >&2
                ERRORS=$(( ERRORS + 1 ))
                size=0
            }
        fi
        total_bytes=$(( total_bytes + size ))
    done

    _log_reclaim "$category" "$total_bytes"
}

# ---------------------------------------------------------------------------
# Category 3: docker image prune (untagged/dangling only)
# ---------------------------------------------------------------------------
_reap_docker_images() {
    local category="docker-images (dangling/untagged)"
    echo "reap-scratch: scanning ${category}"

    if ! command -v docker &>/dev/null; then
        echo "reap-scratch: docker not found; skipping ${category}"
        _log_reclaim "$category" 0
        return 0
    fi

    if ! docker info &>/dev/null 2>&1; then
        echo "reap-scratch: docker daemon unreachable; skipping ${category}"
        _log_reclaim "$category" 0
        return 0
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        local dry_output
        dry_output=$(docker image prune --filter "dangling=true" --no-prune 2>/dev/null \
            || docker images --filter "dangling=true" --format "{{.ID}} {{.Size}}" 2>/dev/null \
            || true)
        echo "reap-scratch: [dry-run] dangling images that would be pruned:"
        if [[ -n "$dry_output" ]]; then
            echo "$dry_output"
        else
            echo "  (none or unable to enumerate)"
        fi
        _log_reclaim "$category" 0
        return 0
    fi

    local prune_output
    prune_output=$(docker image prune --filter "dangling=true" --force 2>/dev/null || true)
    if [[ -n "$prune_output" ]]; then
        echo "$prune_output"
    fi

    # Parse reclaimed bytes from docker output: "Total reclaimed space: 1.23GB"
    local reclaimed_bytes=0
    if echo "$prune_output" | grep -qi "Total reclaimed space"; then
        local size_str
        size_str=$(echo "$prune_output" | grep -i "Total reclaimed space" | grep -oP '[\d.]+\s*\w+' | tail -1 || true)
        # Convert via numfmt if possible
        if command -v numfmt &>/dev/null && [[ -n "$size_str" ]]; then
            reclaimed_bytes=$(numfmt --from=iec "$size_str" 2>/dev/null || echo 0)
        fi
    fi

    _log_reclaim "$category" "$reclaimed_bytes"
}

# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------
echo "reap-scratch: starting sweep at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

_reap_worktrees    || ERRORS=$(( ERRORS + 1 ))
_reap_pytest_scratch || ERRORS=$(( ERRORS + 1 ))
_reap_docker_images  || ERRORS=$(( ERRORS + 1 ))

echo "reap-scratch: sweep complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$ERRORS" -gt 0 ]]; then
    echo "reap-scratch: WARNING: ${ERRORS} non-fatal error(s) during sweep" >&2
    exit 1
fi

exit 0
