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
capability secret. Production minting uses the existing credential spine:
`SecretIdentityBackend` backed by OpenBao, with the live secret exposed only to a
trusted controller/integrator mint or verify process. The canonical SecretRef is
backend `openbao`, mount `ce-kv`, path `forge/approval-capability/wall`, field
`signing_secret`, purpose `approval-capability-wall`, and owner-ref
`controller:integrator`. Forks and contained seats may still submit GitHub
reviews, but they cannot mint a valid wall-capable marker because they do not
receive that controller-only capability.

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

ce-ops#247 adds controller/integrator-only mint-on-approval on the same path.
If the armed wall refuses only because the marker is missing, and a trusted
controller/integrator issuer is available, the daemon may mint a marker before
enqueue. That mint is permitted only after current-head approval, approval
settle, authorized-reviewer matching, path manifest gating, and live approval
reverify all pass. The marker is written into the PR body as public metadata and
the daemon defers; the armed verifier must verify that PR-body marker on a later
pass before enqueue is eligible. Contained seats never receive the OpenBao wall
secret and do not mint wall-capable approvals.

Durable records and logs must remain value-free. They may record that a marker
was present and may record public claims or failure reasons, but they must never
persist the verifier secret or any live credential. The capability text itself is
public PR metadata and contains no secret; its authority comes only from the
controller-side signature key.

The daemon's primary production secret source is a configured
`SecretIdentityBackend`/OpenBao supplier. `ce queue-daemon` builds a regular
`SecretRequest` from the approval-wall SecretRef flags, materializes it to a
file-backed target, and reads the materialized value through the injected reader
used by `approval_wall_secret_supplier_from_secret_identity_backend`. The
OpenBao request must use backend `openbao`, mount `ce-kv`, path
`forge/approval-capability/wall`, field `signing_secret`, purpose
`approval-capability-wall`, and owner-ref `controller:integrator`.

When the wall is armed, the daemon fails closed on missing backend
configuration, unavailable or empty secret material, and invalid existing
markers. If a SecretIdentityBackend is configured, backend refusal or empty
materialization is not allowed to fall back to environment variables. Automatic
mint-on-approval uses the configured controller/integrator backend supplier; it
has no env fallback. The standalone `ce approval-capability mint` command is a
manual bootstrap/controller utility and is not the automatic mint path.

The daemon's bootstrap secret source, `CE_APPROVAL_CAPABILITY_SECRET`, remains
available only when no SecretIdentityBackend supplier is configured. If backend
flags are present, partial configuration, `env:` target refs, backend refusal,
or an empty/falsy materialized value are treated as misconfiguration and the
daemon fails closed instead of consulting the env fallback. Backend delivery must
be file-backed so controller-minted verifier material is not placed in
`os.environ`. With neither source configured and no durable armed state, the
wall remains dormant.

For manual controller/bootstrap operations, controllers can mint markers with:

```text
ce approval-capability mint --repo OWNER/REPO --pr NUMBER --head-sha SHA --approved-by LOGIN --policy-sha SHA_OR_ID
```

The command prints only the public marker. It refuses if the wall secret is not
configured. This command is not the queue-daemon automatic mint-on-approval
path.
