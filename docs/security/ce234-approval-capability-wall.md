# ce-ops#234 Approval Capability Wall

GitHub approval remains a necessary signal for the integrator daemon. Once the
approval wall is armed, it is no longer sufficient authority to enqueue or
auto-merge a pull request. A raw `reviewDecision == APPROVED` can be produced by
any process that inherits a controller credential, including controller-launched
forks. An armed integrator therefore requires a second proof that is not
available inside contained seats.

The approval wall is a controller-minted capability marker:

```text
ce-approval-capability: v1.<payload-b64>.<signature>
```

The signed payload is value-only and binds the authorization to one exact merge
candidate: `repo`, `pr_number`, `head_sha`, `approved_by`, `issued_at`,
`expires_at`, and `policy_sha`. The signature is produced with a controller-only
capability secret. Production minting should use the existing credential spine:
`SecretIdentityBackend` backed by OpenBao, with the live secret exposed only to a
trusted controller/integrator mint or verify process. Forks and contained seats
may still submit GitHub reviews, but they cannot mint a valid marker because they
do not receive that controller-only capability.

The wall is enforce-when-armed:

1. With no configured wall secret and no durable armed state, the wall is
   dormant. The daemon falls back to the pre-wall behavior: GitHub APPROVED on
   the current head is enough to continue to mergeability, checks, carrier, path
   overlap, and enqueue. Decisions carry `approval_wall: not armed` evidence.
2. When the controller/integrator sees a configured wall secret, it persists
   `.ce/state/approval-capability-wall/state.json` with `armed: true` and
   enforces markers from then on.
3. If that durable armed state exists later but the secret is unavailable, the
   daemon fails closed as `approval_wall_misconfigured`; it must not silently
   downgrade back to dormant mode.

When armed, the integrator verifies in this order:

1. The PR is not draft and GitHub says the review decision is approved.
2. At least one approval is attached to the current head commit.
3. The PR body contains exactly one approval capability marker.
4. The marker signature validates with the configured verifier secret.
5. The claims match the live PR identity and current approval policy, have not
   expired, and name an actual approving reviewer when reviewer identity is
   available.
6. Only then do mergeability, changed-file completeness, governance checks,
   test checks, carrier validity, path overlap, and merge-queue enqueue run.

Durable records and logs must remain value-free. They may record that a marker
was present and may record public claims or failure reasons, but they must never
persist the verifier secret or any live credential. The capability text itself is
public PR metadata and contains no secret; its authority comes only from the
controller-side signature key. The bootstrap secret source is
`CE_APPROVAL_CAPABILITY_SECRET`; production wiring should replace or wrap that
supplier with `approval_wall_secret_supplier_from_secret_identity_backend`, which
uses a `SecretIdentityBackend`/OpenBao grant plus an injected materialized-value
reader.

Controllers mint markers with:

```text
ce approval-capability mint --repo OWNER/REPO --pr NUMBER --head-sha SHA --approved-by LOGIN --policy-sha SHA_OR_ID
```

The command prints only the public marker. It refuses if the wall secret is not
configured.
