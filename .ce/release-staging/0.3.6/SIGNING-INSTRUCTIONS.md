# Signing record for ce-root-v1 — v0.3.6

The install spec (`llms-install.md` and its staging mirror) carries the embedded
ce-root-v1 signature. Controller-verified:

```
Good "ce-spec-v1" signature for ce-root-v1
ED25519 SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ
```

- Canonical bytes: `INSTALL_SPEC_TO_SIGN` (byte-identical to `llms-install.canonical`)
- Detached SSHSIG: `INSTALL_SPEC_TO_SIGN.sig` (also at `llms-install.canonical.sig`)
- content_sha256: `1d3f9a7d65e1a003667b59ff179f3492513c1ccabf2bf6bfa06d5931bb54edaf`
- Signing namespace: `ce-spec-v1`
- Key identity: `ce-root-v1`

To re-verify:

```bash
ssh-keygen -Y verify -f keys/ce-root-v1 -I ce-root-v1 -n ce-spec-v1 \
  -s INSTALL_SPEC_TO_SIGN.sig < INSTALL_SPEC_TO_SIGN
```
