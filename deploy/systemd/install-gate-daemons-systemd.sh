#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: install-gate-daemons-systemd.sh [--system] [--repo-root PATH] [--env-file PATH] [--egress-broker-env-file PATH] [--egress-self-review-env-file PATH] [--unit-dir PATH] [--no-start]

Installs Creator Engine gate daemon systemd units from this source checkout.

Defaults:
  user units:   ~/.config/systemd/user
  system units: /etc/systemd/system
  gate env file:
    ~/.config/creator-engine/gate-daemons.env (user)
    /etc/creator-engine/gate-daemons.env (--system)
  egress broker env file:
    ~/.config/creator-engine/ce-egress-broker.env (user)
    /etc/creator-engine/ce-egress-broker.env (--system)
  egress self-review env file:
    ~/.config/creator-engine/ce-egress-self-review.env (user)
    /etc/creator-engine/ce-egress-self-review.env (--system)

The script copies rendered units, runs daemon-reload, enables the services, and
starts them unless --no-start is supplied. It does not create or overwrite the
secret env file; create it first with CE_GATE_REPO, CE_GATE_AUTHORIZED_REVIEWERS,
plus GH_TOKEN and/or CE_PICKUP_TOKEN as needed.
USAGE
}

scope="user"
repo_root=""
unit_dir=""
env_file=""
egress_broker_env_file=""
egress_self_review_env_file=""
start_services=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --system)
      scope="system"
      shift
      ;;
    --repo-root)
      repo_root="${2:?--repo-root requires a path}"
      shift 2
      ;;
    --unit-dir)
      unit_dir="${2:?--unit-dir requires a path}"
      shift 2
      ;;
    --env-file)
      env_file="${2:?--env-file requires a path}"
      shift 2
      ;;
    --egress-broker-env-file)
      egress_broker_env_file="${2:?--egress-broker-env-file requires a path}"
      shift 2
      ;;
    --egress-self-review-env-file)
      egress_self_review_env_file="${2:?--egress-self-review-env-file requires a path}"
      shift 2
      ;;
    --no-start)
      start_services=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$repo_root" ]]; then
  repo_root="$(cd -- "$script_dir/../.." && pwd)"
else
  repo_root="$(cd -- "$repo_root" && pwd)"
fi

if [[ "$scope" == "system" ]]; then
  unit_dir="${unit_dir:-/etc/systemd/system}"
  env_file="${env_file:-/etc/creator-engine/gate-daemons.env}"
  egress_broker_env_file="${egress_broker_env_file:-/etc/creator-engine/ce-egress-broker.env}"
  egress_self_review_env_file="${egress_self_review_env_file:-/etc/creator-engine/ce-egress-self-review.env}"
  systemctl_cmd=(systemctl)
else
  unit_dir="${unit_dir:-$HOME/.config/systemd/user}"
  env_file="${env_file:-$HOME/.config/creator-engine/gate-daemons.env}"
  egress_broker_env_file="${egress_broker_env_file:-$HOME/.config/creator-engine/ce-egress-broker.env}"
  egress_self_review_env_file="${egress_self_review_env_file:-$HOME/.config/creator-engine/ce-egress-self-review.env}"
  systemctl_cmd=(systemctl --user)
fi

services=(
  ce-belt-daemon.service
  ce-integrator-daemon.service
  ce-review-pickup-daemon.service
  # ce-egress-broker.service uses its own EnvironmentFile (ce-egress-broker.env) which must
  # include BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT, BROKER_APPROLE_ROLE_ID, and
  # BROKER_APPROLE_SECRET_ID for vault-backed seats; create that file before starting.
  ce-egress-broker.socket
  ce-egress-broker.service
  # ce-egress-self-review.service uses its own EnvironmentFile (ce-egress-self-review.env)
  # which must include the same BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT,
  # BROKER_APPROLE_ROLE_ID, and BROKER_APPROLE_SECRET_ID for vault-backed seats; create that
  # file before starting.
  ce-egress-self-review.socket
  ce-egress-self-review.service
)

echo "scope: $scope"
echo "repo root: $repo_root"
echo "unit dir: $unit_dir"
echo "gate env file: $env_file"
echo "egress broker env file: $egress_broker_env_file"
echo "egress self-review env file: $egress_self_review_env_file"

if [[ ! -d "$repo_root/.git" ]]; then
  echo "ERROR: repo root does not look like a git checkout: $repo_root" >&2
  exit 1
fi

if [[ ! -x "$repo_root/.venv/bin/python" ]]; then
  echo "ERROR: expected executable virtualenv python at $repo_root/.venv/bin/python" >&2
  exit 1
fi

if [[ ! -f "$env_file" ]]; then
  cat >&2 <<EOF
ERROR: env file is missing: $env_file
Create it before starting the services. Required:
  CE_GATE_REPO=owner/name
  CE_GATE_AUTHORIZED_REVIEWERS=reviewer-login[,reviewer-login...]
  CE_BELT_IDENTITY=ce-dev-4
  GH_TOKEN=...
Optional for review pickup:
  CE_PICKUP_TOKEN=...
Optional for work-pickup belt:
  CE_BELT_INTERVAL_SECONDS=120
  CE_BELT_LABELS=enhancement
  CE_PICKUP_TOKEN=...
EOF
  exit 1
fi

if [[ ! -f "$egress_broker_env_file" ]]; then
  cat >&2 <<EOF
ERROR: egress broker env file is missing: $egress_broker_env_file
Create it before starting the services. Required:
  CE_EGRESS_BROKER_SOCKET=...
  CE_EGRESS_BROKER_SEAT=...
  CE_EGRESS_BROKER_REPO=...
  CE_EGRESS_BROKER_CONFIG=...
For vault-backed seats also include BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT,
BROKER_APPROLE_ROLE_ID, and BROKER_APPROLE_SECRET_ID.
EOF
  exit 1
fi

if [[ ! -f "$egress_self_review_env_file" ]]; then
  cat >&2 <<EOF
ERROR: egress self-review env file is missing: $egress_self_review_env_file
Create it before starting the services. Required:
  CE_EGRESS_SELF_REVIEW_SOCKET=...
  CE_EGRESS_SELF_REVIEW_CONFIG=...
  CE_EGRESS_RUN_MODE=dev
For vault-backed seats also include BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT,
BROKER_APPROLE_ROLE_ID, and BROKER_APPROLE_SECRET_ID.
EOF
  exit 1
fi

mkdir -p "$unit_dir"

render_unit() {
  local src="$1"
  local dst="$2"
  local env_path="${3:-}"
  local tmp
  local rendered_repo_root
  local rendered_env_file
  rendered_repo_root="$(printf '%s' "$repo_root" | sed 's/[&#]/\\&/g')"
  rendered_env_file="$(printf '%s' "$env_path" | sed 's/[&#]/\\&/g')"
  tmp="$(mktemp)"
  if [[ -n "$rendered_env_file" ]]; then
    sed \
      -e "s#^WorkingDirectory=.*#WorkingDirectory=$rendered_repo_root#g" \
      -e "s#^EnvironmentFile=.*#EnvironmentFile=$rendered_env_file#g" \
      "$src" > "$tmp"
  else
    sed \
      -e "s#^WorkingDirectory=.*#WorkingDirectory=$rendered_repo_root#g" \
      "$src" > "$tmp"
  fi
  if [[ -f "$dst" ]] && cmp -s "$tmp" "$dst"; then
    echo "unchanged: $dst"
    rm -f "$tmp"
  else
    install -m 0644 "$tmp" "$dst"
    echo "installed: $dst"
    rm -f "$tmp"
  fi
}

env_file_for_service() {
  case "$1" in
    ce-egress-broker.service)
      printf '%s\n' "$egress_broker_env_file"
      ;;
    ce-egress-self-review.service)
      printf '%s\n' "$egress_self_review_env_file"
      ;;
    *.service)
      printf '%s\n' "$env_file"
      ;;
    *)
      printf '\n'
      ;;
  esac
}

for service in "${services[@]}"; do
  render_unit "$script_dir/$service" "$unit_dir/$service" "$(env_file_for_service "$service")"
done

echo "running: ${systemctl_cmd[*]} daemon-reload"
"${systemctl_cmd[@]}" daemon-reload

for service in "${services[@]}"; do
  echo "running: ${systemctl_cmd[*]} enable $service"
  "${systemctl_cmd[@]}" enable "$service"
done

if [[ "$start_services" -eq 1 ]]; then
  for service in "${services[@]}"; do
    echo "running: ${systemctl_cmd[*]} start $service"
    "${systemctl_cmd[@]}" start "$service"
  done
else
  echo "skipped service start (--no-start)"
fi
