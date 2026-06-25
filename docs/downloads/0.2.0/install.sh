#!/usr/bin/env bash
# Creator Engine (CE) v3 real installer bootstrap.
#
#   curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
#
# E1 boundary: verify the signed install spec before persistent mutation, install
# the validator wheel offline from signed-manifest-pinned artifacts, and execute
# authenticated onboard inventory. No sudo, runtime provisioning, GitHub mutation,
# or first-project apply happens in this bootstrap.
set -euo pipefail

CE_SITE="${CE_SITE:-https://creator-engine.dev}"
CE_ANSWERS="${CE_ANSWERS:-}"
CE_INSTALL_ROOT="${CE_INSTALL_ROOT:-}"
CE_TRUST_ANCHOR_URL="${CE_TRUST_ANCHOR_URL:-https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT}"
CE_TRUST_ANCHOR_SOURCE="${CE_TRUST_ANCHOR_SOURCE:-dns-txt:_ce-root-v1.creator-engine.dev}"
CE_JSON=0
CE_INVENTORY_ONLY=1

downloaded=0
reused=0
verified=0
installed=0
skipped_already_current=0
failed=0

TMPDIR_CE=""
LOCK_DIR=""

say() { printf '◆ CE · %s\n' "$*" >&2; }

cleanup() {
  if [ -n "${LOCK_DIR:-}" ] && [ -d "$LOCK_DIR" ]; then
    rm -f "$LOCK_DIR/pid" 2>/dev/null || true
    rmdir "$LOCK_DIR" 2>/dev/null || true
  fi
  if [ -n "${TMPDIR_CE:-}" ] && [ -d "$TMPDIR_CE" ]; then
    rm -rf "$TMPDIR_CE"
  fi
}
trap cleanup EXIT

fail() {
  class="$1"
  shift
  failed=$((failed + 1))
  printf '◆ CE · INSTALL_REFUSED %s: %s\n' "$class" "$*" >&2
  exit 1
}

single_line() {
  printf '%s' "$*" | sed -E 's/[[:cntrl:]]+/ /g; s/[[:space:]]+/ /g; s/^ //; s/ $//'
}

onboard_refusal_detail() {
  class="$1"
  combined="$2"
  code="$3"
  if [ "$class" = "missing_bootstrap_dependency" ]; then
    line="$(grep -m1 'missing_bootstrap_dependency' "$combined" 2>/dev/null || true)"
    line="$(printf '%s' "$line" | sed -E 's/.*missing_bootstrap_dependency[: ]*//; s/[{}"\\]//g; s/^[[:space:]]+//; s/[[:space:]]+/ /g')"
    if [ -n "$line" ]; then
      single_line "$line"
      return
    fi
    single_line "required bootstrap dependency missing. Remediation: install the missing command and re-run this installer."
    return
  fi
  single_line "cev3 onboard --inventory exited ${code}. Remediation: fix the onboard inventory refusal and re-run this installer."
}

usage() {
  cat >&2 <<'EOF'
Usage: install.sh [--answers PATH] [--inventory-only] [--json] [--install-root PATH] [--site URL]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --answers)
      [ "$#" -ge 2 ] || fail missing_bootstrap_dependency "--answers requires a path"
      CE_ANSWERS="$2"
      shift 2
      ;;
    --inventory-only)
      CE_INVENTORY_ONLY=1
      shift
      ;;
    --json)
      CE_JSON=1
      shift
      ;;
    --install-root)
      [ "$#" -ge 2 ] || fail missing_bootstrap_dependency "--install-root requires a path"
      CE_INSTALL_ROOT="$2"
      shift 2
      ;;
    --site)
      [ "$#" -ge 2 ] || fail missing_bootstrap_dependency "--site requires a URL"
      CE_SITE="${2%/}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail missing_bootstrap_dependency "unknown installer argument: $1"
      ;;
  esac
done

if { [ -n "${CE_TEST_UNAME_S:-}" ] || [ -n "${CE_TEST_UNAME_M:-}" ]; } \
  && [ "${CE_INSTALLER_TEST_MODE:-}" != "1" ]; then
  fail test_override_refused "CE_TEST_UNAME_S/CE_TEST_UNAME_M require CE_INSTALLER_TEST_MODE=1; refusing test platform override in real install"
fi

SPEC_URL="${CE_SITE}/llms-install.md"
TRUST_ROOT_URL="${CE_SITE}/keys/ce-root-v1"
CURL_FLAGS=(--proto '=https' --tlsv1.2 -fsSL)

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail missing_bootstrap_dependency "required command missing: $1"
  fi
}

for cmd in curl ssh-keygen sed awk grep base64 mktemp chmod uname date mkdir rm cp mv ln; do
  need_cmd "$cmd"
done

HASH_TOOL=""
if command -v sha256sum >/dev/null 2>&1; then
  HASH_TOOL="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  HASH_TOOL="shasum"
else
  fail missing_bootstrap_dependency "required command missing: sha256sum or shasum -a 256"
fi

hash_file() {
  if [ "$HASH_TOOL" = "sha256sum" ]; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

normalized_url_origin() {
  printf '%s\n' "$1" | awk '
    {
      url = $0
      if (match(url, /^[A-Za-z][A-Za-z0-9+.-]*:\/\//) == 0) {
        print url
        exit
      }
      scheme = tolower(substr(url, 1, RLENGTH - 3))
      authority = substr(url, RLENGTH + 1)
      sub(/[\/?#].*$/, "", authority)
      n = split(authority, userinfo_parts, "@")
      authority = userinfo_parts[n]
      host = authority
      port = ""
      if (authority ~ /^\[[^]]+\]/) {
        rb = index(authority, "]")
        host = substr(authority, 1, rb)
        suffix = substr(authority, rb + 1)
        if (suffix ~ /^:[0-9]+$/) {
          port = substr(suffix, 2)
        }
      } else if (authority ~ /:[0-9]+$/) {
        host = authority
        sub(/:[0-9]+$/, "", host)
        port = authority
        sub(/^.*:/, "", port)
      }
      host = tolower(host)
      if ((scheme == "https" && port == "443") || (scheme == "http" && port == "80")) {
        port = ""
      }
      printf "%s://%s%s\n", scheme, host, port == "" ? "" : ":" port
    }
  '
}

refuse_same_origin_trust_anchor() {
  site_origin="$(normalized_url_origin "$CE_SITE")"
  anchor_origin="$(normalized_url_origin "$CE_TRUST_ANCHOR_URL")"
  if [ "$site_origin" = "$anchor_origin" ]; then
    fail trust_anchor_refused "trust anchor URL must be out-of-band; ${CE_TRUST_ANCHOR_URL} shares origin with ${CE_SITE}"
  fi
}

base64_decode_to() {
  input="$1"
  output="$2"
  if printf '%s' "$input" | base64 -d >"$output" 2>/dev/null; then
    return 0
  fi
  printf '%s' "$input" | base64 -D >"$output" 2>/dev/null
}

fetch_url() {
  url="$1"
  output="$2"
  failure_class="${3:-network_fetch_failed}"
  err="${TMPDIR_CE}/curl.err"
  rm -f "$err"
  set +e
  curl "${CURL_FLAGS[@]}" "$url" -o "$output" 2>"$err"
  status="$?"
  set -e
  if [ "$status" -ne 0 ]; then
    detail="$(tr '\n' ' ' <"$err" | sed 's/[[:space:]]\+/ /g')"
    if [[ "$url" == *"/downloads/"* ]] && printf '%s' "$detail" | grep -q '404'; then
      fail pages_mirror_not_ready "$url returned 404 while GitHub Pages may still be deploying; retry after the mirror is ready"
    fi
    fail "$failure_class" "url=$url curl_status=$status retry_count=0 detail=${detail:-curl failed}"
  fi
  downloaded=$((downloaded + 1))
}

verify_hash() {
  expected="$1"
  path="$2"
  name="$3"
  actual="$(hash_file "$path")"
  if [ "$actual" != "$expected" ]; then
    fail artifact_hash_mismatch "$name expected=$expected actual=$actual"
  fi
  verified=$((verified + 1))
}

sig_field() {
  key="$1"
  awk -v key="$key" '
    $0 == "signature:" { in_sig = 1; next }
    in_sig && $0 !~ /^  / && NF { exit }
    in_sig {
      prefix = "  " key ": "
      if (index($0, prefix) == 1) {
        print substr($0, length(prefix) + 1)
        exit
      }
    }
  ' "$SPEC_FILE"
}

manifest_value() {
  key="$1"
  awk -v key="$key" '
    $0 == "artifact_manifest:" { in_manifest = 1; next }
    in_manifest && $0 !~ /^  / && NF { exit }
    in_manifest {
      prefix = "  " key ": "
      if (index($0, prefix) == 1) {
        print substr($0, length(prefix) + 1)
        exit
      }
    }
  ' "$SPEC_FILE"
}

manifest_wheels_tsv() {
  platform="$1"
  awk -v platform="$platform" '
    function platform_match(list, parts, n, i) {
      if (list == "" || list == "all" || list == "*") return 1
      gsub(/,/, " ", list)
      n = split(list, parts, /[[:space:]]+/)
      for (i = 1; i <= n; i++) {
        if (parts[i] == "all" || parts[i] == platform) return 1
      }
      return 0
    }
    function emit() {
      if (filename != "" && url != "" && sha != "" && platform_match(platforms)) {
        print filename "\t" url "\t" sha
      }
    }
    $0 == "  required_wheels:" { in_wheels = 1; next }
    in_wheels && $0 == "  python_acquisition:" {
      emit()
      filename = ""
      in_wheels = 0
      exit
    }
    in_wheels && $0 ~ /^    - filename: / {
      emit()
      filename = substr($0, length("    - filename: ") + 1)
      url = ""
      sha = ""
      platforms = "all"
      next
    }
    in_wheels && $0 ~ /^      url: / { url = substr($0, length("      url: ") + 1); next }
    in_wheels && $0 ~ /^      sha256: / { sha = substr($0, length("      sha256: ") + 1); next }
    in_wheels && $0 ~ /^      platforms: / { platforms = substr($0, length("      platforms: ") + 1); next }
    END {
      if (in_wheels) emit()
    }
  ' "$SPEC_FILE"
}

manifest_python_acquisition_tsv() {
  platform="$1"
  awk -v platform="$platform" '
    function reset_entry() {
      tool = ""
      version = ""
      url = ""
      sha = ""
      command = ""
      emitted_current = 0
    }
    function emit() {
      if (emitted_current) return
      if (entry_platform == platform && tool != "" && version != "" && url != "" && sha != "" && command != "") {
        print tool "\t" version "\t" url "\t" sha "\t" command
        found = 1
        emitted_current = 1
      }
    }
    $0 == "  python_acquisition:" { in_python = 1; next }
    in_python && $0 !~ /^    / && NF { emit(); exit }
    in_python && $0 ~ /^    - platform: / {
      emit()
      entry_platform = substr($0, length("    - platform: ") + 1)
      reset_entry()
      next
    }
    in_python && $0 ~ /^      tool: / { tool = substr($0, length("      tool: ") + 1); next }
    in_python && $0 ~ /^      version: / { version = substr($0, length("      version: ") + 1); next }
    in_python && $0 ~ /^      url: / { url = substr($0, length("      url: ") + 1); next }
    in_python && $0 ~ /^      sha256: / { sha = substr($0, length("      sha256: ") + 1); next }
    in_python && $0 ~ /^      command: / { command = substr($0, length("      command: ") + 1); next }
    in_python && $0 ~ /^    tool: / { if (entry_platform == "") entry_platform = "linux-x86_64-cp314"; tool = substr($0, length("    tool: ") + 1); next }
    in_python && $0 ~ /^    version: / { if (entry_platform == "") entry_platform = "linux-x86_64-cp314"; version = substr($0, length("    version: ") + 1); next }
    in_python && $0 ~ /^    url: / { if (entry_platform == "") entry_platform = "linux-x86_64-cp314"; url = substr($0, length("    url: ") + 1); next }
    in_python && $0 ~ /^    sha256: / { if (entry_platform == "") entry_platform = "linux-x86_64-cp314"; sha = substr($0, length("    sha256: ") + 1); next }
    in_python && $0 ~ /^    command: / { if (entry_platform == "") entry_platform = "linux-x86_64-cp314"; command = substr($0, length("    command: ") + 1); next }
    END {
      if (in_python) emit()
      if (!found) exit 1
    }
  ' "$SPEC_FILE"
}

sha256s_entry() {
  file="$1"
  awk -v file="$file" '
    $2 == file || $2 == "*" file { print $1; found = 1; exit }
    END { if (!found) exit 1 }
  ' "$SHA256S_FILE"
}

trust_root_fingerprint() {
  key_id="$1"
  ssh-keygen -l -f "$TRUST_ROOT_FILE" -E sha256 | awk -v key="$key_id" '
    $3 == key {
      print $2
      found = 1
      exit
    }
    END { if (!found) exit 1 }
  '
}

anchor_record() {
  key_id="$1"
  raw_path="$2"
  awk -v key="$key_id" '
    {
      line = $0
      gsub(/["{}\\,]/, " ", line)
      n = split(line, fields, /[[:space:]]+/)
      for (i = 1; i <= n; i++) {
        token = fields[i]
        if (index(token, key "=") == 1) {
          fp = substr(token, length(key) + 2)
          if (fp ~ /^SHA256:[A-Za-z0-9+\/]{43}$/) {
            print key "=" fp
            found = 1
            exit
          }
        }
        if ((token == key || token == key ":") && i < n && fields[i + 1] ~ /^SHA256:[A-Za-z0-9+\/]{43}$/) {
          print key "=" fields[i + 1]
          found = 1
          exit
        }
      }
    }
    END { if (!found) exit 1 }
  ' "$raw_path"
}

compatible_python() {
  candidate="$1"
  "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 14) else 1)
PY
}

find_host_python() {
  for candidate in "${CE_PYTHON:-}" python3.14 python3 python; do
    [ -n "$candidate" ] || continue
    if command -v "$candidate" >/dev/null 2>&1 && compatible_python "$candidate"; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

state_value() {
  key="$1"
  [ -f "$STATE_FILE" ] || return 1
  awk -F= -v key="$key" '$1 == key { print substr($0, length(key) + 2); found = 1; exit } END { if (!found) exit 1 }' "$STATE_FILE"
}

acquire_lock() {
  mkdir -p "$BOOTSTRAP_ROOT"
  lock="$BOOTSTRAP_ROOT/install.lock"
  if mkdir "$lock" 2>/dev/null; then
    LOCK_DIR="$lock"
    printf '%s\n' "$$" >"$lock/pid"
    return 0
  fi
  holder="$(cat "$lock/pid" 2>/dev/null || true)"
  if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
    fail install_lock_held "another install is active (pid $holder, lock $lock)"
  fi
  fail stale_install_lock "stale lock at $lock; remove it after confirming no installer is running"
}

write_state() {
  tmp_state="${STATE_FILE}.tmp.$$"
  {
    printf 'spec_canonical_sha256=%s\n' "$SPEC_CANONICAL_SHA"
    printf 'trust_root_sha256=%s\n' "$TRUST_ROOT_SHA"
    printf 'trust_anchor_source=%s\n' "$CE_TRUST_ANCHOR_SOURCE"
    printf 'trust_anchor_sha256=%s\n' "$TRUST_ANCHOR_SHA"
    printf 'sha256s_sha256=%s\n' "$SHA256S_SHA"
    printf 'package_version=%s\n' "$PACKAGE_VERSION"
    printf 'python_executable=%s\n' "$PYTHON_BIN"
    printf 'platform=%s/%s\n' "$OS_NAME" "$MACHINE"
    printf 'venv_path=%s\n' "$VENV_DIR"
    printf 'venv_target=%s\n' "$VENV_TARGET"
    printf 'timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$tmp_state"
  mv "$tmp_state" "$STATE_FILE"
}

install_cli_shim() {
  name="$1"
  target="$2"
  shim="${LOCAL_BIN}/${name}"
  tmp_shim="${shim}.tmp.$$"

  [ -x "$target" ] \
    || fail entrypoint_missing "cannot expose $name: target $target is absent or not executable"
  if [ -e "$shim" ] && [ ! -L "$shim" ]; then
    fail cli_exposure_failed "refusing to overwrite non-symlink CLI path $shim"
  fi
  rm -f "$tmp_shim"
  ln -s "$target" "$tmp_shim" \
    || fail cli_exposure_failed "failed to prepare CLI shim $tmp_shim -> $target"
  if ! mv -Tf "$tmp_shim" "$shim"; then
    rm -f "$tmp_shim"
    fail cli_exposure_failed "failed to install CLI shim $shim -> $target"
  fi
  [ -x "$shim" ] \
    || fail cli_exposure_failed "CLI shim $shim does not resolve to executable $target"
}

install_cli_shims() {
  [ -n "${HOME:-}" ] || fail cli_exposure_failed "HOME is not set; cannot create ~/.local/bin CLI shims"
  LOCAL_BIN="${HOME}/.local/bin"
  mkdir -p "$LOCAL_BIN" \
    || fail cli_exposure_failed "failed to create user-local bin directory $LOCAL_BIN"

  install_cli_shim cev3 "${VENV_DIR}/bin/cev3"
  install_cli_shim ce "${VENV_DIR}/bin/ce"
  say "exposed CLI shims: ${LOCAL_BIN}/cev3 and ${LOCAL_BIN}/ce"
  case ":${PATH:-}:" in
    *":${LOCAL_BIN}:"*) ;;
    *) say "warning: ${LOCAL_BIN} is not on PATH; add it to run ce/cev3 without an absolute path" ;;
  esac
}

TMPDIR_CE="$(mktemp -d)"
chmod 700 "$TMPDIR_CE"
SPEC_FILE="$TMPDIR_CE/llms-install.md"
TRUST_ROOT_FILE="$TMPDIR_CE/ce-root-v1"
TRUST_ANCHOR_RAW_FILE="$TMPDIR_CE/ce-root-v1.anchor.raw"
TRUST_ANCHOR_FILE="$TMPDIR_CE/ce-root-v1.anchor"
CANONICAL_FILE="$TMPDIR_CE/ce-spec.canonical"
SIG_FILE="$TMPDIR_CE/ce-spec.sig"
SCHEMA_FILE="$TMPDIR_CE/install-answers.schema.yaml"
SHA256S_FILE="$TMPDIR_CE/SHA256SUMS"
WHEELHOUSE_DIR="$TMPDIR_CE/wheelhouse"
mkdir "$WHEELHOUSE_DIR"

say "fetching signed install spec from ${SPEC_URL}"
fetch_url "$SPEC_URL" "$SPEC_FILE" network_fetch_failed
say "fetching trust root from ${TRUST_ROOT_URL}"
fetch_url "$TRUST_ROOT_URL" "$TRUST_ROOT_FILE" trust_root_unreadable

KEY_ID="$(sig_field key_id)"
ALGO="$(sig_field algo)"
NAMESPACE="$(sig_field namespace)"
SIG_VALUE="$(sig_field value)"
CONTENT_SHA="$(sig_field content_sha256)"

[ -n "$KEY_ID" ] || fail signature_refused "missing key_id"
[ "$ALGO" = "ssh-ed25519" ] || fail signature_refused "unsupported algo $ALGO"
[ "$NAMESPACE" = "ce-spec-v1" ] || fail signature_refused "unsupported namespace $NAMESPACE"
printf '%s\n' "$CONTENT_SHA" | awk '/^[0-9a-f]{64}$/ { ok = 1 } END { exit ok ? 0 : 1 }' \
  || fail signature_refused "content_sha256 is not 64-hex"
grep -Eq "^${KEY_ID}([[:space:],]|$)" "$TRUST_ROOT_FILE" \
  || fail signature_refused "key_id $KEY_ID is not present in fetched trust root"

sed -E 's#^(  value: ).*#\1<published-with-this-spec>#; s#^(  content_sha256: ).*#\1<published-with-this-spec>#' \
  "$SPEC_FILE" >"$CANONICAL_FILE"
SPEC_CANONICAL_SHA="$(hash_file "$CANONICAL_FILE")"
[ "$SPEC_CANONICAL_SHA" = "$CONTENT_SHA" ] \
  || fail signature_refused "content_sha256 mismatch expected=$CONTENT_SHA actual=$SPEC_CANONICAL_SHA"
base64_decode_to "$SIG_VALUE" "$SIG_FILE" \
  || fail signature_refused "signature value is not valid base64"
if ! ssh-keygen -Y verify -f "$TRUST_ROOT_FILE" -I "$KEY_ID" -n "$NAMESPACE" -s "$SIG_FILE" <"$CANONICAL_FILE" >/dev/null 2>&1; then
  fail signature_refused "stock ssh-keygen refused the install spec"
fi
verified=$((verified + 1))
TRUST_ROOT_SHA="$(hash_file "$TRUST_ROOT_FILE")"
say "signed spec verified: canonical sha256 ${SPEC_CANONICAL_SHA}"

refuse_same_origin_trust_anchor
say "fetching out-of-band trust anchor from ${CE_TRUST_ANCHOR_URL}"
fetch_url "$CE_TRUST_ANCHOR_URL" "$TRUST_ANCHOR_RAW_FILE" trust_anchor_unreadable
TRUST_ANCHOR_RECORD="$(anchor_record "$KEY_ID" "$TRUST_ANCHOR_RAW_FILE" || true)"
[ -n "$TRUST_ANCHOR_RECORD" ] \
  || fail trust_anchor_refused "no out-of-band anchor for $KEY_ID found at ${CE_TRUST_ANCHOR_URL}"
TRUST_ANCHOR_FINGERPRINT="${TRUST_ANCHOR_RECORD#*=}"
TRUST_ROOT_FINGERPRINT="$(trust_root_fingerprint "$KEY_ID" || true)"
[ -n "$TRUST_ROOT_FINGERPRINT" ] \
  || fail trust_anchor_refused "could not derive fingerprint for $KEY_ID from fetched trust root"
[ "$TRUST_ANCHOR_FINGERPRINT" = "$TRUST_ROOT_FINGERPRINT" ] \
  || fail trust_anchor_refused "out-of-band anchor mismatch for $KEY_ID"
printf '%s\n' "$TRUST_ANCHOR_RECORD" >"$TRUST_ANCHOR_FILE"
TRUST_ANCHOR_SHA="$(hash_file "$TRUST_ANCHOR_FILE")"
verified=$((verified + 1))
say "out-of-band trust anchor accepted from ${CE_TRUST_ANCHOR_SOURCE}"

MANIFEST_VERSION="$(manifest_value artifact_manifest_version)"
PACKAGE_NAME="$(manifest_value package_name)"
PACKAGE_VERSION="$(manifest_value package_version)"
PYTHON_REQUIRES="$(manifest_value python_requires)"
ARTIFACT_BASE_URL="$(manifest_value artifact_base_url)"
SHA256S_URL="$(manifest_value sha256s_url)"
SHA256S_SHA="$(manifest_value sha256s_sha256)"
INSTALL_SH_ENTRY="$(manifest_value install_sh_sha256s_entry)"
ANSWERS_SCHEMA_URL="$(manifest_value answers_schema_url)"
ANSWERS_SCHEMA_SHA="$(manifest_value answers_schema_sha256)"
APP_WHEEL="$(manifest_value app_wheel)"

[ "$MANIFEST_VERSION" = "1" ] || fail signature_refused "unsupported artifact_manifest_version $MANIFEST_VERSION"
[ "$PACKAGE_NAME" = "creator-engine-validator" ] || fail signature_refused "unexpected package_name $PACKAGE_NAME"
[ "$PYTHON_REQUIRES" = ">=3.14" ] || fail signature_refused "unexpected python_requires $PYTHON_REQUIRES"
[ -n "$ARTIFACT_BASE_URL" ] || fail signature_refused "artifact_base_url missing"

if [ "${CE_INSTALLER_TEST_MODE:-}" = "1" ]; then
  OS_NAME="${CE_TEST_UNAME_S:-$(uname -s)}"
  MACHINE="${CE_TEST_UNAME_M:-$(uname -m)}"
else
  OS_NAME="$(uname -s)"
  MACHINE="$(uname -m)"
fi
case "${OS_NAME}/${MACHINE}" in
  Linux/x86_64|Linux/amd64)
    PLATFORM_TAG="linux-x86_64-cp314"
    UV_BIN_REL="uv-x86_64-unknown-linux-gnu/uv"
    ;;
  Linux/aarch64|Linux/arm64)
    PLATFORM_TAG="linux-aarch64-cp314"
    UV_BIN_REL="uv-aarch64-unknown-linux-gnu/uv"
    ;;
  *) fail unsupported_platform "no signed wheelhouse for ${OS_NAME}/${MACHINE}; E1 supports Linux x86_64/amd64 and Linux aarch64/arm64 CPython 3.14" ;;
esac

PYTHON_ACQ_TSV="$(manifest_python_acquisition_tsv "$PLATFORM_TAG" || true)"
[ -n "$PYTHON_ACQ_TSV" ] || fail signature_refused "python_acquisition missing for ${PLATFORM_TAG}"
OLDIFS="$IFS"
IFS=$'\t'
read -r UV_TOOL UV_VERSION UV_URL UV_SHA UV_COMMAND <<EOF
$PYTHON_ACQ_TSV
EOF
IFS="$OLDIFS"
printf '%s\n' "$SHA256S_SHA" "$ANSWERS_SCHEMA_SHA" "$UV_SHA" | awk '/^[0-9a-f]{64}$/ { next } { bad = 1 } END { exit bad ? 1 : 0 }' \
  || fail signature_refused "artifact manifest contains a non-hex sha256"

if [ -n "$CE_INSTALL_ROOT" ]; then
  BOOTSTRAP_ROOT="$CE_INSTALL_ROOT"
else
  CE_BASE="${CE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/creator-engine}"
  BOOTSTRAP_ROOT="${CE_BASE}/bootstrap"
fi
VENV_DIR="${BOOTSTRAP_ROOT}/venv"
VENV_TARGET="${BOOTSTRAP_ROOT}/venv-${PACKAGE_VERSION}-${SHA256S_SHA}"
STATE_FILE="${BOOTSTRAP_ROOT}/install-state"
ARTIFACT_CACHE="${BOOTSTRAP_ROOT}/artifacts/${SHA256S_SHA}"

PYTHON_BIN="$(find_host_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  [ "$UV_TOOL" = "uv" ] || fail missing_bootstrap_dependency "no compatible Python and signed manifest does not permit uv acquisition"
  need_cmd tar
  UV_TARBALL="$TMPDIR_CE/uv.tar.gz"
  UV_EXTRACT="$TMPDIR_CE/uv"
  mkdir "$UV_EXTRACT"
  say "no CPython >=3.14 found; acquiring uv ${UV_VERSION} from signed manifest"
  fetch_url "$UV_URL" "$UV_TARBALL" python_acquisition_failed
  verify_hash "$UV_SHA" "$UV_TARBALL" "uv-${UV_VERSION}"
  tar -xzf "$UV_TARBALL" -C "$UV_EXTRACT" || fail python_acquisition_failed "uv extraction failed"
  UV_BIN="$UV_EXTRACT/$UV_BIN_REL"
  [ -x "$UV_BIN" ] || fail python_acquisition_failed "uv executable missing after extraction"
  "$UV_BIN" python install 3.14 >/dev/null 2>&1 \
    || fail python_acquisition_failed "uv python install 3.14 failed (${UV_COMMAND})"
  PYTHON_BIN="$("$UV_BIN" python find 3.14 2>/dev/null || true)"
  [ -n "$PYTHON_BIN" ] && compatible_python "$PYTHON_BIN" \
    || fail python_acquisition_failed "uv installed Python but no compatible interpreter was found"
fi
say "using Python: ${PYTHON_BIN}"

fetch_url "$SHA256S_URL" "$SHA256S_FILE" network_fetch_failed
verify_hash "$SHA256S_SHA" "$SHA256S_FILE" "SHA256SUMS"

if ! sha256s_entry "$INSTALL_SH_ENTRY" >/dev/null 2>&1; then
  fail artifact_hash_mismatch "SHA256SUMS is missing published install.sh entry ${INSTALL_SH_ENTRY}"
fi

fetch_url "$ANSWERS_SCHEMA_URL" "$SCHEMA_FILE" network_fetch_failed
verify_hash "$ANSWERS_SCHEMA_SHA" "$SCHEMA_FILE" "install-answers.schema.yaml"

mkdir -p "$ARTIFACT_CACHE"
WHEELS_TSV="$TMPDIR_CE/wheels.tsv"
manifest_wheels_tsv "$PLATFORM_TAG" >"$WHEELS_TSV"
app_wheel_seen=0
while IFS=$'\t' read -r filename url expected; do
  [ -n "$filename" ] || continue
  [ "$filename" != "$APP_WHEEL" ] || app_wheel_seen=1
  printf '%s\n' "$expected" | awk '/^[0-9a-f]{64}$/ { ok = 1 } END { exit ok ? 0 : 1 }' \
    || fail signature_refused "wheel $filename has non-hex sha256 in signed manifest"
  entry_hash="$(sha256s_entry "$filename" || true)"
  [ "$entry_hash" = "$expected" ] \
    || fail artifact_hash_mismatch "$filename SHA256SUMS entry=${entry_hash:-missing} manifest=$expected"
  cached="$ARTIFACT_CACHE/$filename"
  target="$WHEELHOUSE_DIR/$filename"
  if [ -f "$cached" ] && [ "$(hash_file "$cached")" = "$expected" ]; then
    cp "$cached" "$target"
    reused=$((reused + 1))
    verified=$((verified + 1))
  else
    fetch_url "$url" "$target" network_fetch_failed
    verify_hash "$expected" "$target" "$filename"
    cp "$target" "$cached"
  fi
done <"$WHEELS_TSV"
[ "$app_wheel_seen" = "1" ] || fail signature_refused "app_wheel $APP_WHEEL is not listed in required_wheels"

acquire_lock

current=0
if [ -x "${VENV_DIR}/bin/cev3" ] && [ -f "$STATE_FILE" ]; then
  if [ "$(state_value spec_canonical_sha256 || true)" = "$SPEC_CANONICAL_SHA" ] \
    && [ "$(state_value sha256s_sha256 || true)" = "$SHA256S_SHA" ] \
    && [ "$(state_value package_version || true)" = "$PACKAGE_VERSION" ] \
    && "${VENV_DIR}/bin/cev3" --help >/dev/null 2>&1; then
    current=1
  fi
fi

if [ "$current" = "1" ]; then
  skipped_already_current=$((skipped_already_current + 1))
  say "reusing verified venv: ${VENV_DIR}"
else
  backup="${BOOTSTRAP_ROOT}/venv.previous.$$"
  link_tmp="${BOOTSTRAP_ROOT}/venv.link.$$"
  rm -rf "$backup"
  rm -f "$link_tmp"
  target_current=0
  if [ -x "${VENV_TARGET}/bin/cev3" ] && "${VENV_TARGET}/bin/cev3" --help >/dev/null 2>&1; then
    target_current=1
  fi
  if [ "$target_current" = "1" ]; then
    say "reusing verified venv target: ${VENV_TARGET}"
  else
    rm -rf "$VENV_TARGET"
    say "building verified venv target: ${VENV_TARGET}"
    if ! "$PYTHON_BIN" -m venv "$VENV_TARGET" >/dev/null 2>&1; then
      rm -rf "$VENV_TARGET"
      fail python_venv_unavailable "Python cannot create venv at $VENV_TARGET"
    fi
    if ! PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_TARGET/bin/python" -m pip install \
      --no-index --find-links "$WHEELHOUSE_DIR" "${PACKAGE_NAME}==${PACKAGE_VERSION}" >/dev/null 2>&1; then
      rm -rf "$VENV_TARGET"
      fail venv_install_failed "offline pip install failed in venv target $VENV_TARGET"
    fi
    if ! "$VENV_TARGET/bin/cev3" --help >/dev/null 2>&1; then
      rm -rf "$VENV_TARGET"
      fail entrypoint_missing "venv target installed but cev3 is absent or not runnable"
    fi
    installed=$((installed + 1))
  fi
  ln -s "$(basename "$VENV_TARGET")" "$link_tmp" \
    || fail venv_install_failed "failed to prepare venv symlink"
  if [ -e "$VENV_DIR" ] && [ ! -L "$VENV_DIR" ]; then
    mv "$VENV_DIR" "$backup" \
      || fail venv_install_failed "failed to preserve previous venv directory"
  fi
  if ! mv -Tf "$link_tmp" "$VENV_DIR"; then
    rm -f "$link_tmp"
    if [ -d "$backup" ]; then
      mv "$backup" "$VENV_DIR" 2>/dev/null || true
    fi
    fail venv_install_failed "failed to promote verified venv link atomically"
  fi
  rm -rf "$backup"
  say "installed verified venv: ${VENV_DIR}"
fi

"${VENV_DIR}/bin/cev3" --help >/dev/null 2>&1 \
  || fail entrypoint_missing "verified venv exists but cev3 no longer runs"
install_cli_shims
write_state

ONBOARD_ARGS=(
  "${VENV_DIR}/bin/cev3"
  onboard
  --spec "$SPEC_FILE"
  --trust-root "$TRUST_ROOT_FILE"
  --trust-anchor "${CE_TRUST_ANCHOR_SOURCE}=${TRUST_ANCHOR_FILE}"
  --answers-schema "$SCHEMA_FILE"
  --inventory
)
if [ -n "$CE_ANSWERS" ]; then
  ONBOARD_ARGS+=(--answers "$CE_ANSWERS")
fi
if [ "$CE_JSON" = "1" ]; then
  ONBOARD_ARGS+=(--json)
fi

say "running authenticated onboard inventory"
ONBOARD_STDOUT="${TMPDIR_CE}/onboard.stdout"
ONBOARD_STDERR="${TMPDIR_CE}/onboard.stderr"
ONBOARD_COMBINED="${TMPDIR_CE}/onboard.combined"
set +e
"${ONBOARD_ARGS[@]}" >"$ONBOARD_STDOUT" 2>"$ONBOARD_STDERR"
onboard_code="$?"
set -e
if [ "$onboard_code" -ne 0 ]; then
  failed=$((failed + 1))
  cat "$ONBOARD_STDOUT" "$ONBOARD_STDERR" >"$ONBOARD_COMBINED"
  onboard_class="onboard_inventory_failed"
  if grep -q 'missing_bootstrap_dependency' "$ONBOARD_COMBINED" 2>/dev/null; then
    onboard_class="missing_bootstrap_dependency"
  fi
  onboard_detail="$(onboard_refusal_detail "$onboard_class" "$ONBOARD_COMBINED" "$onboard_code")"
  printf '◆ CE · INSTALL_REFUSED %s: %s\n' "$onboard_class" "$onboard_detail" >&2
  exit "$onboard_code"
fi
cat "$ONBOARD_STDOUT"
cat "$ONBOARD_STDERR" >&2

say "state file: ${STATE_FILE}"
say "summary: downloaded=${downloaded} reused=${reused} verified=${verified} installed=${installed} skipped_already_current=${skipped_already_current} failed=${failed}"
say "next: prepare ce-install.answers.yaml, then run ${VENV_DIR}/bin/cev3 onboard --spec <verified-spec> --trust-root <verified-trust-root> --trust-anchor <source>=<verified-trust-anchor> --answers-schema <verified-schema> --answers <file> --plan"
