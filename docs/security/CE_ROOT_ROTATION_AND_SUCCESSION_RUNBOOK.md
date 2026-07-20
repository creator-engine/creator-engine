# CE Root Rotation And Succession Runbook

## Purpose And Authority

This runbook governs replacement of the public release-signing trust root. It
covers a normal planned rotation or loss of the old signing capability, and a
separate compromise or revocation response. It is an operational procedure, not
authority to sign, publish, alter a release, or change a consumer.

The current public identity is:

| Field | Value |
|---|---|
| Key ID | `ce-root-v1` |
| Algorithm | `ssh-ed25519` |
| Public fingerprint | `SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ` |
| Created | 2026-07-09 |

Only a controller performs signing and release actions. Workers do not sign and
must never receive, read, copy, or handle private-key material or passphrases.
The new private component stays in approved offline custody; its passphrase is
unique, kept separately, and never recorded in the repository, a work item, a
command transcript, or a release artifact.

## Public Consumer Inventory

The following are the actual tracked public consumers and root-pin surfaces at
the time this runbook was written. Update every applicable surface in one
authorized rotation change; do not infer additional consumers from historical
mentions alone.

| Consumer or surface | Current binding | Rotation responsibility |
|---|---|---|
| `docs/keys/ce-root-v1` | Public OpenSSH `allowed_signers` trust-root file | Publish the successor public key under the chosen current endpoint and retain the old public key only for the declared compatibility window. |
| `docs/security/trust-anchors.md` | Public fingerprint record | Publish the successor fingerprint and explicit transition or revocation status that matches the DNS TXT anchor. |
| `docs/llms-install.md` | Embedded key ID, SSHSIG metadata, canonical bytes, and public verification recipe | Reissue its canonical form and detached signature under the successor key; change the recipe and default identity to the successor. |
| `docs/install.sh` | Fetches the root and the out-of-band DNS TXT fingerprint anchor; refuses missing, mismatched, or same-origin anchors before installation | Point the bootstrap at the successor root and the matching DNS TXT record, while preserving an intentional legacy path only when it remains trusted. |
| `docs/downloads/0.2.0/install.sh` through `docs/downloads/0.3.6/install.sh` | Versioned public bootstrap snapshots | Treat as historical consumers. Preserve their old verification behavior or publish a clearly versioned successor bootstrap; do not silently rewrite a released snapshot. |
| `docs/llms.txt` | Public entry point that names the root, fingerprint, and anchor model | Update the public discovery text and successor fingerprint only after the DNS TXT anchor is available. |
| `validators/creator_engine_validator/v3_installer.py` and `v3_cli.py` | Distributed validator pin set plus verify-before-execute and out-of-band-anchor checks | Add the successor pin, choose the current default key, and keep old-key acceptance only for the approved transition window. |
| `validators/creator_engine_validator/update.py` | Update path fetches the install spec, root endpoint, and DNS TXT anchor | Re-anchor its endpoint and anchor defaults to the successor. |
| `validators/creator_engine_validator/release_publish.py` and `release_orchestrator.py` | Staging identity, permitted release-signing IDs, public-root artifact, and ratification packet | Select the successor identity, stage the successor public root, and regenerate the affected public release package. |
| `.github/workflows/release.yml` | Release-finalize seam verifies a supplied public SSHSIG before producing publishable bytes | Change the expected successor identity only with the corresponding gate and artifact update. Finalization verifies; it does not sign. |
| `validators/creator_engine_validator/release_smoke_evidence.py` and `checks/release_smoke_evidence.py` | Release-smoke artifact set and fail-closed evidence policy bind the release key ID and namespace | Re-anchor the root artifact, key ID, namespace policy when required, and the evidence schema expectations together. |

Tests, changelog fragments, path manifests, and release-staging history are
evidence of these contracts, not additional production consumers. A rotation
must still inspect them for required coverage before changing an implementation.

## Out-Of-Band DNS TXT Anchor

The single independent anchor for the current installer is the DNS TXT record
`_ce-root-v1.creator-engine.dev`, queried through the repository resolver
endpoint `https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT`
and passed to consumers as `dns-txt:_ce-root-v1.creator-engine.dev`. Its public
content is a key-ID-to-fingerprint assertion, not a key: the current expected
TXT content is `ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ`.
For a successor, publish the corresponding `ce-root-v2=SHA256:<successor-public-fingerprint>`
assertion in that record before re-anchoring the consumer; do not copy any key
material into the record or this runbook.

DNS registrar and zone access are held out of band from repository and release
access. TXT publication and removal can take time to propagate through the
configured resolver and its caches, so DNS confirmation is a separate
operational step in addition to repository consumer re-anchoring. On the
compromise path this anchor is especially load-bearing: dual trust is forbidden,
so the revoked identity cannot remain as a fallback while the successor record
or its propagation is incomplete.

## Normal Rotation Or Succession

Use this path only when there is no evidence that `ce-root-v1` was compromised.
Loss of availability, retirement, or planned custodial succession is not a
revocation event by itself.

1. Record the reason, whether the prior signer can still sign, the successor
   authority, the compatibility window, and the planned old-key retirement date.
   Do not classify uncertainty as a normal rotation; use the emergency path
   until compromise has been ruled out.
2. The controller mints `ce-root-v2` as an `ssh-ed25519` signing identity in
   approved offline custody. Create and retain only its public identity in the
   repository. Keep the private component and its passphrase outside all worker
   and repository surfaces.
3. Before using the successor for a release, publish its public key and
   fingerprint in the trust-root file and the DNS TXT anchor. Confirm that the
   configured DNS resolver returns the successor fingerprint from
   `_ce-root-v1.creator-engine.dev`. A same-origin record is not an
   out-of-band DNS TXT anchor.
4. Prepare one authorized implementation change that re-anchors every current
   consumer in the inventory. Current installers and validator pins may accept
   both identities during the declared window, but the current install spec,
   bootstrap defaults, update path, release staging, finalization gate, and
   smoke-evidence policy must agree on which identity is current.
5. Regenerate the current public release package. The controller alone signs
   the new canonical install spec and performs release actions after the
   public-root, DNS TXT anchor, and consumer changes have been verified.
6. Reissue previous releases as versioned successor records. Each reissue
   preserves the prior release's artifact hashes and identifies the original
   release, then supplies a successor-key signature over its new canonical
   release record. Publish the matching successor public key and DNS TXT anchor
   evidence with that record. Do not overwrite old release bytes or claim that
   an old signature changed signers.
7. After the stated compatibility window and successful reissue audit, remove
   normal acceptance of `ce-root-v1` from current consumers and retire its
   public record only if this is still a normal succession. Retain public
   historical evidence necessary to explain already-published releases.

### Users During The Planned Transition

New installs should verify the current spec against `ce-root-v2` and a matching
DNS TXT fingerprint anchor. Existing `ce-root-v1`-only installers can keep
verifying the old release material they already understand during the declared
compatibility window. They cannot automatically authenticate a successor key
unless an already-trusted, signed handoff was made available while the old key
was usable. Current consumer code has no automatic root-handover mechanism.

For a planned rotation while `ce-root-v1` remains available, the controller may
publish a signed, public transition record binding the successor identity and
fingerprint before changing the default. That record improves user migration,
but it does not replace the required DNS TXT fingerprint anchor.

## Compromise Or Revocation: Fail Closed

Use this path for suspected or confirmed private-key exposure, unauthorized
signing, anchor-control compromise, or any case where the old key cannot remain
trusted. Do not keep a compromised key in a dual-trust window.

1. Declare the old identity revoked and freeze release finalization, publication,
   and automated update promotion that would accept it. Preserve evidence without
   reproducing secret material.
2. Publish the revocation in `_ce-root-v1.creator-engine.dev` through its
   out-of-band registrar-controlled DNS TXT record and remove the old
   fingerprint from the record that `install.sh` consults through the configured
   DNS resolver endpoint. Change the current trust-root endpoint and pin set so
   current consumers reject the old identity. A missing, mismatched, or unpinned
   root must refuse before any installation or release finalization proceeds.
3. Mint `ce-root-v2` under the custody rules above and publish its expected
   `ce-root-v2=SHA256:<successor-public-fingerprint>` TXT assertion. Wait for
   the configured DNS resolver to return it, then re-anchor every current
   consumer in the inventory, including the bootstrap, embedded pins, update
   path, release staging, release-finalize expectation, and release-smoke
   policy.
4. Treat all artifacts whose authenticity depends on the revoked key as
   untrusted until independently assessed. Withdraw or quarantine affected
   current artifacts and issue successor releases with new signatures and
   explicit replacement records. Do not represent a reissued artifact as proof
   that the revoked signature was safe.
5. Verify that stale bootstrap attempts fail closed: the old identity must no
   longer satisfy both a current public root and the DNS TXT anchor. Verify that
   the successor path succeeds only with the successor key, expected namespace,
   canonical bytes, and an agreeing DNS TXT anchor.
6. Keep the revoked public identity and incident record available as historical
   evidence where appropriate, but never as an accepted signer in a current
   install, update, or release gate.

### Users From Revocation Through Re-Anchoring

This is a compromise response, not the planned transition described above. From
revocation until `install.sh` has been re-anchored to the successor root and
the successor TXT assertion has propagated through the configured DNS resolver,
a user running the current `install.sh` must not receive a successful install.
It exits before installation: a revoked or replaced root causes signature or
root verification to fail, while a removed, stale, or mismatched TXT
fingerprint causes the out-of-band-anchor check to fail closed. Users must not
override that failure, fall back to `ce-root-v1`, or treat DNS propagation delay
as permission to use dual trust. Only after the DNS TXT response and the
re-anchored installer agree on `ce-root-v2` can installation resume.

## Unrecoverable Limits

- A lost private key or forgotten passphrase cannot be reconstructed from the
  public key, a signature, the repository, or an existing release.
- After compromise, no procedure can prove that a historical signature was not
  produced by an unauthorized holder of the old key.
- A client that trusts only `ce-root-v1` cannot cryptographically discover and
  trust `ce-root-v2` without a handoff authenticated before loss or compromise,
  or an explicit user decision based on an independent successor anchor.
- Cached or mirrored historical artifacts cannot be silently made trustworthy by
  editing current public records. They need a distinct successor record or must
  fail closed.
- Re-signing a previous release creates a new signed record. It cannot alter the
  bytes, provenance, or security properties of the already-published release.

## Completion Record

For either path, retain a public, non-secret record of the old and successor key
IDs, public fingerprints, effective dates, DNS TXT anchor confirmation,
affected consumer inventory, release reissue mapping, compatibility decision,
and verification results. The controller records the signing and publication
evidence. Workers may prepare documentation and public consumer changes only;
they do not sign, publish, revoke, or operate release tooling.
