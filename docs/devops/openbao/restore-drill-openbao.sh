#!/usr/bin/env bash
set -euo pipefail

BAO_BIN="${BAO_BIN:-bao}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OPENBAO_ENCRYPTED_SNAPSHOT="${OPENBAO_ENCRYPTED_SNAPSHOT:?set the encrypted .snap.age artifact to drill}"
OPENBAO_AGE_IDENTITY="${OPENBAO_AGE_IDENTITY:?set the age identity file for the drill key}"
OPENBAO_RESTORE_DRILL_ADDR="${OPENBAO_RESTORE_DRILL_ADDR:?set the throwaway OpenBao address; never point this at production}"
OPENBAO_RESTORE_CANARY_PATH="${OPENBAO_RESTORE_CANARY_PATH:-secret/data/ce-openbao-restore-canary}"
OPENBAO_RESTORE_CANARY_FIELD="${OPENBAO_RESTORE_CANARY_FIELD:-ok}"
RESTORE_DRILL_PROOF="${RESTORE_DRILL_PROOF:-restore-drill-proof.json}"
OPENBAO_RESTORE_TOKEN="${OPENBAO_RESTORE_TOKEN:-${BAO_TOKEN:-}}"
OPENBAO_VERIFY_TOKEN="${OPENBAO_VERIFY_TOKEN:-$OPENBAO_RESTORE_TOKEN}"

if [[ "${OPENBAO_RESTORE_DRILL_CONFIRM:-}" != "throwaway" ]]; then
  echo "refusing restore drill without OPENBAO_RESTORE_DRILL_CONFIRM=throwaway" >&2
  exit 78
fi
if [[ -z "$OPENBAO_RESTORE_TOKEN" || -z "$OPENBAO_VERIFY_TOKEN" ]]; then
  echo "set OPENBAO_RESTORE_TOKEN for the target drill instance and OPENBAO_VERIFY_TOKEN for the restored snapshot canary read" >&2
  exit 78
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
raw="$workdir/restore.snap"

age -d -i "$OPENBAO_AGE_IDENTITY" -o "$raw" "$OPENBAO_ENCRYPTED_SNAPSHOT"

BAO_ADDR="$OPENBAO_RESTORE_DRILL_ADDR" BAO_TOKEN="$OPENBAO_RESTORE_TOKEN" "$BAO_BIN" operator raft snapshot restore -force "$raw"

if [[ -n "${OPENBAO_RESTORE_DRILL_UNSEAL_KEY_FILE:-}" ]]; then
  BAO_ADDR="$OPENBAO_RESTORE_DRILL_ADDR" "$BAO_BIN" operator unseal "$(cat "$OPENBAO_RESTORE_DRILL_UNSEAL_KEY_FILE")" >/dev/null
fi

canary_json="$workdir/canary.json"
BAO_ADDR="$OPENBAO_RESTORE_DRILL_ADDR" BAO_TOKEN="$OPENBAO_VERIFY_TOKEN" "$BAO_BIN" read -format=json "$OPENBAO_RESTORE_CANARY_PATH" > "$canary_json"

"$PYTHON_BIN" - "$canary_json" "$OPENBAO_RESTORE_CANARY_FIELD" "$RESTORE_DRILL_PROOF" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

canary_path = Path(sys.argv[1])
field = sys.argv[2]
proof_path = Path(sys.argv[3])
payload = json.loads(canary_path.read_text(encoding="utf-8"))
data = payload.get("data", {})
if isinstance(data.get("data"), dict):
    data = data["data"]
if data.get(field) in (None, ""):
    raise SystemExit(f"restore canary field missing: {field}")
proof = {
    "ok": True,
    "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "canary_path": str(canary_path),
    "canary_field": field,
}
proof_path.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8")
PY

echo "restore drill passed; proof written to $RESTORE_DRILL_PROOF"
