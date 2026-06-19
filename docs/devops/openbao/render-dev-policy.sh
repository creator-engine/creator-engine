#!/usr/bin/env bash
set -euo pipefail

CE_DEV_ID="${CE_DEV_ID:?set CE_DEV_ID, for example dev-1}"
TEMPLATE="${OPENBAO_DEV_POLICY_TEMPLATE:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ce-dev-policy.hcl.tmpl}"

if [[ ! "$CE_DEV_ID" =~ ^dev-[A-Za-z0-9_-]+$ ]]; then
  echo "refusing invalid CE_DEV_ID: $CE_DEV_ID" >&2
  echo "expected a per-dev id such as dev-1 or dev-alice_1" >&2
  exit 78
fi

if [[ "$CE_DEV_ID" == *"/"* || "$CE_DEV_ID" == *".."* || "$CE_DEV_ID" == *"+"* || "$CE_DEV_ID" == *"*"* ]]; then
  echo "refusing unsafe CE_DEV_ID path component: $CE_DEV_ID" >&2
  exit 78
fi

sed "s/__CE_DEV_ID__/$CE_DEV_ID/g" "$TEMPLATE"
