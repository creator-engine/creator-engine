#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

export PYTHONPATH="${repo_root}/validators${PYTHONPATH:+:${PYTHONPATH}}"
if command -v python >/dev/null 2>&1; then
  python_bin=python
elif command -v python3 >/dev/null 2>&1; then
  python_bin=python3
else
  echo "FAIL: python or python3 is required" >&2
  exit 1
fi

exec "${python_bin}" -m creator_engine_validator.pr_preflight --repo-root "${repo_root}" "$@"
