# Creator Engine — Trust Anchor Publication

**Status:** Canonical. This file is the **in-repo out-of-band trust anchor** for
the CE signing keys. Agents and operators MUST verify the served key fingerprint
against this record (or another independent channel) before trusting the install
spec's detached signature. Same-origin anchors (anything served by
`creator-engine.dev`) do **not** count as independent.

**Rationale:** The §0 install ceremony (`ssh-keygen -Y verify … < llms-install.md`)
proves integrity — the served spec matches what was signed. It does **not** prove
authenticity unless the signing-key fingerprint is pinned via a channel independent
of the serving origin. This file, published in the GitHub repository
(`creator-engine/creator-engine`), constitutes that independent channel: GitHub
serves a different origin and trust path than the Pages mirror, so a compromise of
`creator-engine.dev` alone cannot forge an agreeing record here.

Related: [SECURITY_MODEL.md](./SECURITY_MODEL.md)

---

## Signing keys

### `ce-root-v1` (primary signing key)

| Field       | Value |
|-------------|-------|
| Key type    | `ssh-ed25519` |
| Principal   | `ce-root-v1` |
| Fingerprint | `SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ` |
| Namespace   | `ce-spec-v1` |
| Custody     | Operator-held private key, offline; never enters the repo or any governed seat |
| Ratified    | 2026-06-10 |

### `ce-dev1-root-v1` (escalation / secondary key)

| Field       | Value |
|-------------|-------|
| Key type    | `ssh-ed25519` |
| Principal   | `ce-dev1-root-v1` |
| Fingerprint | `SHA256:tqPyyLJiJSJA3gdujT2tPv7MiJvdAevxHZSQCdPHC+s` |
| Namespace   | `ce-spec-v1` |
| Custody     | Secondary operator-held private key, encrypted at rest; never enters the repo or any governed seat |
| Ratified    | 2026-06-11 |

---

## Published anchor channels

The fingerprints above are published via multiple independent channels. Any one
agreeing independent channel satisfies the §0 anchor requirement.

| Channel | Record | Authority |
|---------|--------|-----------|
| **This file** (`docs/security/trust-anchors.md`, `creator-engine/creator-engine` on GitHub) | Both fingerprints above | GitHub (separate origin from `creator-engine.dev`) |
| **DNS TXT** (`_ce-root-v1.creator-engine.dev`) | `ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ ce-dev1-root-v1=SHA256:tqPyyLJiJSJA3gdujT2tPv7MiJvdAevxHZSQCdPHC+s` | DNS control-plane (separate from Pages web content) |

### Verify via DNS TXT

```bash
curl -fsSL 'https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT' \
  | grep -Eo 'ce-root-v1[= ]SHA256:[A-Za-z0-9+/]{43}'
# Expected: ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ
```

### Verify via this file (GitHub raw)

```bash
# Fetch this file from the GitHub raw URL (independent of creator-engine.dev)
curl -fsSL https://raw.githubusercontent.com/creator-engine/creator-engine/main/docs/security/trust-anchors.md \
  | grep -A1 'ce-root-v1 (primary'
# Visually confirm the Fingerprint row matches the key you fetched.
```

### Cross-check the served key

```bash
# Fetch the served allowed_signers file
curl -fsSL https://creator-engine.dev/keys/ce-root-v1 -o ce-root-v1
# Compute its fingerprint
ssh-keygen -l -f ce-root-v1 -E sha256
# 256 SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ ce-root-v1 (ED25519)
# Must match the record in this file and the DNS TXT value above.
```

---

## Trust model

The §0 ceremony proves:
- **Integrity:** the served `llms-install.md` byte-for-byte matches what was signed
  with a key whose public half lives in `docs/keys/ce-root-v1`; any tampering
  changes the canonical bytes and the `ssh-keygen -Y verify` step fails.
- **Authenticity (with anchor):** if the fingerprint of the fetched `ce-root-v1`
  public key matches an agreed-upon record in an independent channel (this file,
  the DNS TXT record, or another equivalent), the signing key has been confirmed as
  the Creator Engine root key by that independent authority path.

Without a matching independent anchor, the ceremony proves only self-consistency —
a compromised or MITM'd `creator-engine.dev` origin could serve a matching
key + signature pair. The install ceremony is designed to enforce this: same-origin
anchor URLs are refused before fetch; the anchor check must come from a distinct
origin.

---

## Key lifecycle

New signing keys are:
1. Generated offline on an air-gapped or appropriately isolated host.
2. Added to `docs/keys/ce-root-v1` (the allowed_signers file) via a PR that itself
   passes the gate.
3. Recorded in this file with fingerprint, custody, and ratification date.
4. Published to the DNS TXT record by the Operator before any spec is signed with
   the new key.

A key is revoked by removing it from `docs/keys/ce-root-v1` and this file via a
signed PR, and by removing it from the DNS TXT record. Any spec signed with a
revoked key produces an `ssh-keygen -Y verify` failure once the allowed_signers
file no longer contains that principal.
