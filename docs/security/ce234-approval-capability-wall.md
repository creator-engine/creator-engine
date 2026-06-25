# ce-ops#234 Approval Capability Wall

GitHub approval remains a necessary signal for the integrator daemon, but it is
no longer sufficient authority to enqueue or auto-merge a pull request. A raw
`reviewDecision == APPROVED` can be produced by any process that inherits a
controller credential, including controller-launched forks. The integrator must
therefore require a second proof that is not available inside contained seats.

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

The integrator verifies in this order:

1. The PR is not draft and GitHub says the review decision is approved.
2. At least one approval is attached to the current head commit.
3. The PR body contains exactly one approval capability marker.
4. The marker signature validates with the injected verifier secret.
5. The claims match the live PR identity and current approval policy, have not
   expired, and name an actual approving reviewer when reviewer identity is
   available.
6. Only then do mergeability, changed-file completeness, governance checks,
   test checks, carrier validity, path overlap, and merge-queue enqueue run.

Durable records and logs must remain value-free. They may record that a marker
was present and may record public claims or failure reasons, but they must never
persist the verifier secret or any live credential. The capability text itself is
public PR metadata and contains no secret; its authority comes only from the
controller-side signature key. If the verifier or secret supplier is absent, the
daemon fails closed and treats the wall capability as invalid.
