#!/usr/bin/env bash
set -euo pipefail

BAO_BIN="${BAO_BIN:-bao}"
SNAPSHOT_DIR="${OPENBAO_SNAPSHOT_WORKDIR:-/var/backups/openbao}"
OPENBAO_AGE_RECIPIENT="${OPENBAO_AGE_RECIPIENT:?set the age recipient for off-host encrypted snapshots}"
OPENBAO_SNAPSHOT_REMOTE_URI="${OPENBAO_SNAPSHOT_REMOTE_URI:?set rclone:, scp:, or file: URI for encrypted off-host storage}"
OPENBAO_SNAPSHOT_LABEL="${OPENBAO_SNAPSHOT_LABEL:-ce-openbao-raft}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
raw="$SNAPSHOT_DIR/$OPENBAO_SNAPSHOT_LABEL-$timestamp.snap"
encrypted="$raw.age"

mkdir -p "$SNAPSHOT_DIR"
chmod 0700 "$SNAPSHOT_DIR"

"$BAO_BIN" operator raft snapshot save "$raw"
age -r "$OPENBAO_AGE_RECIPIENT" -o "$encrypted" "$raw"
sha256sum "$encrypted" > "$encrypted.sha256"
rm -f "$raw"

copy_offhost() {
  local src="$1"
  local dst="$2"
  case "$dst" in
    rclone:*)
      rclone copyto "$src" "${dst#rclone:}/$(basename "$src")"
      ;;
    scp:*)
      scp "$src" "${dst#scp:}/$(basename "$src")"
      ;;
    file:*)
      if [[ "${OPENBAO_SNAPSHOT_ALLOW_LOCAL:-}" != "1" ]]; then
        echo "file: destinations are allowed only for local restore drills; production snapshots must leave the host" >&2
        exit 78
      fi
      install -m 0600 "$src" "${dst#file:}/$(basename "$src")"
      ;;
    *)
      echo "unsupported OPENBAO_SNAPSHOT_REMOTE_URI: $dst" >&2
      exit 64
      ;;
  esac
}

copy_offhost "$encrypted" "$OPENBAO_SNAPSHOT_REMOTE_URI"
copy_offhost "$encrypted.sha256" "$OPENBAO_SNAPSHOT_REMOTE_URI"
echo "encrypted OpenBao raft snapshot copied off-host: $(basename "$encrypted")"
