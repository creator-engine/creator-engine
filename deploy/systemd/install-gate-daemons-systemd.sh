#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: install-gate-daemons-systemd.sh [--system] [--repo-root PATH] [--env-file PATH] [--unit-dir PATH] [--no-start]

Installs Creator Engine gate daemon systemd units from this source checkout.

Defaults:
  user units:   ~/.config/systemd/user
  system units: /etc/systemd/system
  env file:     ~/.config/creator-engine/gate-daemons.env (user)
                /etc/creator-engine/gate-daemons.env (--system)

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
  systemctl_cmd=(systemctl)
else
  unit_dir="${unit_dir:-$HOME/.config/systemd/user}"
  env_file="${env_file:-$HOME/.config/creator-engine/gate-daemons.env}"
  systemctl_cmd=(systemctl --user)
fi

services=(
  ce-integrator-daemon.service
  ce-review-pickup-daemon.service
)

echo "scope: $scope"
echo "repo root: $repo_root"
echo "unit dir: $unit_dir"
echo "env file: $env_file"

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
  GH_TOKEN=...
Optional for review pickup:
  CE_PICKUP_TOKEN=...
EOF
  exit 1
fi

mkdir -p "$unit_dir"

render_unit() {
  local src="$1"
  local dst="$2"
  local tmp
  local rendered_repo_root
  local rendered_env_file
  rendered_repo_root="$(printf '%s' "$repo_root" | sed 's/[&#]/\\&/g')"
  rendered_env_file="$(printf '%s' "$env_file" | sed 's/[&#]/\\&/g')"
  tmp="$(mktemp)"
  sed \
    -e "s#^WorkingDirectory=.*#WorkingDirectory=$rendered_repo_root#g" \
    -e "s#^EnvironmentFile=.*#EnvironmentFile=$rendered_env_file#g" \
    "$src" > "$tmp"
  if [[ -f "$dst" ]] && cmp -s "$tmp" "$dst"; then
    echo "unchanged: $dst"
    rm -f "$tmp"
  else
    install -m 0644 "$tmp" "$dst"
    echo "installed: $dst"
    rm -f "$tmp"
  fi
}

for service in "${services[@]}"; do
  render_unit "$script_dir/$service" "$unit_dir/$service"
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
