#!/usr/bin/env bash
set -euo pipefail

VERSION="2.5.5"
BASE_URL="${OPENBAO_RELEASE_BASE_URL:-https://github.com/openbao/openbao/releases/download/v$VERSION}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -m)" in
  x86_64|amd64)
    ARCH="x86_64"
    EXPECTED_SHA256="2c5577707e97fc95c2086950f39880ead5e45b356c94388e5cb606f5a5c2b697"
    ;;
  aarch64|arm64)
    ARCH="arm64"
    EXPECTED_SHA256="9b133729e503ecf4d52f1d4e062954b9fd3798f14335ad8af5f7435f5b8ebd16"
    ;;
  *)
    echo "unsupported OpenBao smoke-test architecture: $(uname -m)" >&2
    exit 78
    ;;
esac

if [[ -n "${OPENBAO_VERIFY_WORKDIR:-}" ]]; then
  WORKDIR="$OPENBAO_VERIFY_WORKDIR"
  mkdir -p "$WORKDIR"
  CLEANUP=0
else
  WORKDIR="$(mktemp -d)"
  CLEANUP=1
fi

cleanup() {
  if [[ "${SERVER_PID:-}" != "" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [[ "$CLEANUP" == "1" ]]; then
    rm -rf "$WORKDIR"
  fi
}
trap cleanup EXIT

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required tool for OpenBao production config smoke: $1" >&2
    exit 69
  fi
}

free_port() {
  "$PYTHON_BIN" - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
}

wait_tcp() {
  local port="$1"
  local log_path="$2"
  for _ in $(seq 1 120); do
    if "$PYTHON_BIN" - "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

sock = socket.socket()
sock.settimeout(0.1)
sock.connect(("127.0.0.1", int(sys.argv[1])))
sock.close()
PY
    then
      return 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "OpenBao exited before accepting the rendered production config:" >&2
      cat "$log_path" >&2
      return 1
    fi
    sleep 0.1
  done
  echo "OpenBao did not listen after loading the rendered production config:" >&2
  cat "$log_path" >&2
  return 1
}

require_tool curl
require_tool openssl
require_tool sha256sum
require_tool tar
require_tool "$PYTHON_BIN"

ASSET="bao_${VERSION}_Linux_${ARCH}.tar.gz"
ARCHIVE="$WORKDIR/$ASSET"
EXTRACT_DIR="$WORKDIR/extract"
TLS_DIR="$WORKDIR/tls"
RAFT_DIR="$WORKDIR/raft"
AUDIT_DIR="$WORKDIR/audit"
CONFIG_PATH="$WORKDIR/openbao-production.hcl"
LOG_PATH="$WORKDIR/openbao-production.log"

mkdir -p "$EXTRACT_DIR" "$TLS_DIR" "$RAFT_DIR" "$AUDIT_DIR"
curl -fsSL -o "$ARCHIVE" "$BASE_URL/$ASSET"
printf '%s  %s\n' "$EXPECTED_SHA256" "$ARCHIVE" | sha256sum -c -
tar -xzf "$ARCHIVE" -C "$EXTRACT_DIR"
BAO_BIN="$(find "$EXTRACT_DIR" -type f -name bao -perm -u+x | head -n 1)"
if [[ -z "$BAO_BIN" ]]; then
  echo "downloaded OpenBao archive did not contain an executable bao binary" >&2
  exit 70
fi

API_PORT="$(free_port)"
CLUSTER_PORT="$(free_port)"
openssl req \
  -x509 \
  -newkey rsa:2048 \
  -nodes \
  -days 1 \
  -subj "/CN=127.0.0.1" \
  -addext "subjectAltName=IP:127.0.0.1,DNS:localhost" \
  -keyout "$TLS_DIR/openbao.key" \
  -out "$TLS_DIR/openbao.crt" >/dev/null 2>&1

OPENBAO_ALLOW_NON_TAILNET_FOR_TEST=1 \
OPENBAO_CLUSTER_NAME="ce-openbao-prod-config-smoke" \
OPENBAO_NODE_ID="ce-openbao-prod-config-smoke" \
OPENBAO_RAFT_PATH="$RAFT_DIR" \
OPENBAO_AUDIT_LOG="$AUDIT_DIR/audit.log" \
OPENBAO_TLS_CERT_FILE="$TLS_DIR/openbao.crt" \
OPENBAO_TLS_KEY_FILE="$TLS_DIR/openbao.key" \
OPENBAO_TLS_CLIENT_CA_FILE="$TLS_DIR/openbao.crt" \
OPENBAO_TAILNET_HOSTNAME="127.0.0.1" \
OPENBAO_TAILNET_BIND_ADDR="127.0.0.1" \
OPENBAO_API_PORT="$API_PORT" \
OPENBAO_CLUSTER_PORT="$CLUSTER_PORT" \
  "$SCRIPT_DIR/provision-openbao.sh" --render-config > "$CONFIG_PATH"

if grep -q "disable_mlock" "$CONFIG_PATH"; then
  echo "rendered production config still contains unsupported disable_mlock" >&2
  exit 1
fi

"$BAO_BIN" server -config="$CONFIG_PATH" > "$LOG_PATH" 2>&1 &
SERVER_PID="$!"
wait_tcp "$API_PORT" "$LOG_PATH"

if grep -qi "disable_mlock" "$LOG_PATH"; then
  echo "OpenBao reported the removed mlock setting while loading production config" >&2
  cat "$LOG_PATH" >&2
  exit 1
fi

kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
SERVER_PID=""

echo "PASS openbao $VERSION accepted rendered production config"
