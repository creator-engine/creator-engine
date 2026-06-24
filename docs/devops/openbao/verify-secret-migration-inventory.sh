#!/usr/bin/env bash
set -euo pipefail

INVENTORY_PATH="${1:-}"
EXPECTED_HEADER=$'record_id\tsecret_class\tsource_ref\ttarget_ref\towner_ref\trotation_ref\trollback_ref\tevidence_ref\tstatus\tnotes'

usage() {
  cat >&2 <<'EOF'
usage: verify-secret-migration-inventory.sh <inventory.tsv>

Validates the value-free OpenBao migration inventory shape. The inventory is
allowed to contain refs, owners, rollback handles, and evidence handles only.
It must not contain secret values, PEM blocks, raw tokens, passwords, or private
keys.
EOF
}

if [[ -z "$INVENTORY_PATH" || "$INVENTORY_PATH" == "-h" || "$INVENTORY_PATH" == "--help" ]]; then
  usage
  exit 64
fi
if [[ ! -f "$INVENTORY_PATH" ]]; then
  echo "inventory not found: $INVENTORY_PATH" >&2
  exit 66
fi

header="$(head -n 1 "$INVENTORY_PATH")"
if [[ "$header" != "$EXPECTED_HEADER" ]]; then
  echo "invalid inventory header; use docs/devops/openbao/secret-migration-inventory.tsv as the template" >&2
  exit 78
fi

awk -F '\t' '
BEGIN {
  allowed_secret_class["github_app_pem"] = 1
  allowed_secret_class["model_provider_key"] = 1
  allowed_secret_class["bootstrap_token"] = 1
  allowed_secret_class["reviewer_token"] = 1
  allowed_secret_class["signing_key"] = 1
  allowed_secret_class["runtime_secret"] = 1
  allowed_secret_class["other"] = 1

  allowed_status["planned"] = 1
  allowed_status["imported"] = 1
  allowed_status["verified"] = 1
  allowed_status["cutover"] = 1
  allowed_status["rolled-back"] = 1
  allowed_status["decommissioned"] = 1
}
NR == 1 { next }
/^[[:space:]]*$/ { next }
{
  data_rows++
  if (NF != 10) {
    printf("line %d: expected 10 tab-separated fields, got %d\n", NR, NF) > "/dev/stderr"
    bad = 1
    next
  }
  if ($1 !~ /^[a-z0-9][a-z0-9._-]*$/) {
    printf("line %d: invalid record_id %s\n", NR, $1) > "/dev/stderr"
    bad = 1
  }
  if (!($2 in allowed_secret_class)) {
    printf("line %d: invalid secret_class %s\n", NR, $2) > "/dev/stderr"
    bad = 1
  }
  if ($3 !~ /^source-ref:[A-Za-z0-9._\/:-]+$/) {
    printf("line %d: source_ref must be source-ref:<value-free-handle>\n", NR) > "/dev/stderr"
    bad = 1
  }
  if ($4 !~ /^openbao-ref:ce-(kv|transit)\/[A-Za-z0-9._\/:-]+$/) {
    printf("line %d: target_ref must be openbao-ref:ce-kv/... or openbao-ref:ce-transit/...\n", NR) > "/dev/stderr"
    bad = 1
  }
  if ($5 !~ /^owner-ref:[A-Za-z0-9._\/:-]+$/) {
    printf("line %d: owner_ref must be owner-ref:<value-free-handle>\n", NR) > "/dev/stderr"
    bad = 1
  }
  if ($6 !~ /^rotation-ref:[A-Za-z0-9._\/:-]+$/) {
    printf("line %d: rotation_ref must be rotation-ref:<value-free-handle>\n", NR) > "/dev/stderr"
    bad = 1
  }
  if ($7 !~ /^rollback-ref:[A-Za-z0-9._\/:-]+$/) {
    printf("line %d: rollback_ref must be rollback-ref:<value-free-handle>\n", NR) > "/dev/stderr"
    bad = 1
  }
  if ($8 !~ /^evidence-ref:[A-Za-z0-9._\/:-]+$/) {
    printf("line %d: evidence_ref must be evidence-ref:<value-free-handle>\n", NR) > "/dev/stderr"
    bad = 1
  }
  if (!($9 in allowed_status)) {
    printf("line %d: invalid status %s\n", NR, $9) > "/dev/stderr"
    bad = 1
  }

  lower = tolower($0)
  possible_secret = 0
  if (lower ~ /-----begin.*private key-----/) possible_secret = 1
  if (lower ~ /-----begin certificate-----/) possible_secret = 1
  if (lower ~ /github_pat_/) possible_secret = 1
  if (lower ~ /gh[pousr]_[a-z0-9_][a-z0-9_]+/) possible_secret = 1
  if (lower ~ /glpat-/) possible_secret = 1
  if (lower ~ /xox[baprs]-/) possible_secret = 1
  if (lower ~ /sk-[a-z0-9]/) possible_secret = 1
  if (lower ~ /akia[0-9a-z][0-9a-z][0-9a-z][0-9a-z]/) possible_secret = 1
  if (lower ~ /age-secret-key-/) possible_secret = 1
  if (lower ~ /(password|passwd|passphrase|secret|token|api[_-]?key|private[_-]?key|client[_-]?secret)[[:space:]]*[=:]/) possible_secret = 1
  if (lower ~ /(value|credential)[[:space:]]*[=:][[:space:]]*[^[:space:]]{4,}/) possible_secret = 1
  if (possible_secret) {
    printf("line %d: possible secret material detected; inventory must contain refs only\n", NR) > "/dev/stderr"
    bad = 1
  }
}
END {
  if (data_rows < 1) {
    print "inventory has no data rows" > "/dev/stderr"
    bad = 1
  }
  exit bad
}
' "$INVENTORY_PATH"

echo "PASS value-free OpenBao migration inventory: $INVENTORY_PATH"
