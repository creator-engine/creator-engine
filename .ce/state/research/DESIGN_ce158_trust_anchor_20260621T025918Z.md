# ce-ops#158 - Out-of-Band Trust Anchor for ce-root-v1

Status: implementation-ready design plus local verifier mechanics.
Branch: ce158-trust-anchor.
Base: d6ba7ee291c882aa865af7e0e32972b3223b5532.

## Problem

The authentic install path already verifies the install spec before planning or
applying, but the served spec, served signature, and served trust root can all be
obtained from the same web origin. That proves self-consistency, not independent
authenticity, if the origin or delivery path is compromised.

The verifier must therefore require at least one out-of-band fingerprint anchor
for the public key it is about to trust. If no independent anchor is supplied,
the result is not "verified"; it is refused as same-origin-only.

## Recommendation

Primary anchor: DNS TXT.

Use DNS TXT as the first production binding because it is separate from the web
content origin, easy to query from a shell or agent wrapper, and operationally
simple. The proposed record is:

```text
_ce-root-v1.creator-engine.dev TXT "ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ"
```

Defense in depth:

- GitHub org/profile or pinned repository text should publish the same line on a
  different origin/TLS chain.
- Sigstore/Rekor should be added as the strongest later anchor once the signing
  identity and bundle publication policy are ratified.

The verifier accepts any supplied anchor source name and reports which sources
agreed. One agreeing source is enough to verify; any mismatching source for the
same key id refuses the install.

## Record Format

Canonical line:

```text
ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ
```

Accepted alternate line:

```text
ce-root-v1 SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ
```

The fingerprint is OpenSSH's SHA256 public-key fingerprint for the
`allowed_signers` key material, computed from the base64 key blob and encoded as
unpadded base64. The full key line is not duplicated into the anchor.

## Verifier Contract

Authentic onboarding now has two gates:

1. Verify the spec SSHSIG against the fetched `allowed_signers` trust root.
2. Verify the fetched trust-root key fingerprint against one or more
   out-of-band anchor records supplied as `--trust-anchor SOURCE=PATH`.

Example:

```bash
ce onboard \
  --require-authentic \
  --spec /tmp/llms-install.md \
  --trust-root /tmp/ce-root-v1.allowed-signers \
  --trust-anchor dns-txt=/tmp/ce-root-v1.dns.txt \
  --inventory
```

Machine-readable evidence is attached under `verified.trust_anchors`, including
`status`, `agreed`, and `mismatched` source labels only. The
same-origin-only case fails closed with `status: same_origin_only`; a
fingerprint disagreement fails closed with `status: mismatch`.

## External Binding Still Required

This branch does not bind production DNS, GitHub profile text, or Sigstore
identity. Those are external control-plane actions and must be performed by the
Operator/controller before the public §0 path can rely on them. The repo change
only defines the record format and makes the verifier refuse false-positive
"verified" states when no supplied independent anchor agrees.
