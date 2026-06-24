### security — fail-closed App-grant minimum (Phase-1 security quick-win 2/3)

- The mint-broker now rejects any token request whose permissions exceed a DECLARED MINIMUM grant **before** any binding or GitHub mint call (`config.within_declared_minimum()` gate) → `403 requested_permissions_exceed_declared_minimum`, no mint. The declared minimum — not the broader installation grant — is the operative ceiling.
- Audit record emitted on every decision (allow or deny). Lineage: installation-grant-as-mint-ceiling (ce-ops#88).
