#!/usr/bin/env bash
set -euo pipefail

stub_status="stub-ce-ops-239-no-secret-injection"
ready_status="ready-ce-ops-239-credential-injection"
stub_injection="SEAM-STUB"
ready_injection="TRANSPORT-DEPUTY"

status="${CE_TRANSPORT_DEPUTY_SEAM_STATUS:-${stub_status}}"
injection="${CE_DGX_CREDENTIAL_INJECTION:-${stub_injection}}"
real_gh="${CE_TRANSPORT_DEPUTY_GH_REAL:-/usr/bin/gh}"

refuse() {
  cat >&2 <<EOF
Refusing controller gh action: transport-deputy credential delivery is not live.

The contained Controller has no credential material while the seam is stubbed,
so gate/source-host actions fail closed. ce-ops#239 must provide scoped
credential delivery before this wrapper may delegate to gh.

Current seam status: ${status}
Current injection mode: ${injection}

Future ready interface:
  CE_TRANSPORT_DEPUTY_SEAM_STATUS=${ready_status}
  CE_DGX_CREDENTIAL_INJECTION=${ready_injection}
  CE_TRANSPORT_DEPUTY_GH_REAL=/usr/bin/gh
EOF
  exit 78
}

if [ "${status}" != "${ready_status}" ] || [ "${injection}" != "${ready_injection}" ]; then
  refuse
fi

case "${real_gh}" in
  /*) ;;
  *)
    printf 'Refusing controller gh action: CE_TRANSPORT_DEPUTY_GH_REAL must be an absolute path.\n' >&2
    exit 78
    ;;
esac

case "${real_gh}" in
  /usr/local/bin/gh|/usr/local/bin/ce-controller-gh-guard)
    printf 'Refusing controller gh action: CE_TRANSPORT_DEPUTY_GH_REAL points back at the guard.\n' >&2
    exit 78
    ;;
esac

if [ ! -x "${real_gh}" ]; then
  printf 'Refusing controller gh action: CE_TRANSPORT_DEPUTY_GH_REAL is not executable.\n' >&2
  exit 78
fi

exec "${real_gh}" "$@"
