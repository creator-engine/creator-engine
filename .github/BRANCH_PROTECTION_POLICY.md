# Branch Protection Policy

> **Invariant:** CI verifies; CI does not ratify.
>
> A passing CI run is validation evidence. It is not governance authorization.
> Ratification of governed or privileged changes requires a separate, explicit
> Source ratification envelope, independent of CI outcome.

## Protected Branches

The following branches are treated as protected under this policy:

- `main`

Feature and sprint branches (`sprint-*/`, `feature/*`) are not protected under
this policy but MUST be merged to `main` only via pull request.

## Required Checks / Review Policy

For all pull requests targeting `main`:

1. **CI validation must pass.** The `Validate / Validate governance artifacts` check
   must succeed before merge is permitted.

2. **At least one reviewer approval is required.** Self-review (author == approver)
   is not sufficient for any PR.

3. **Author/approver separation is required.** The person who authored the PR must
   not be the sole approver. For governed or privileged mutation classes, author and
   approver must be distinct identities.

4. **Direct push to `main` is prohibited.** All changes must arrive via pull request.

5. **Force-push to `main` is prohibited.**

6. **Branch deletion of `main` is prohibited.**

## Governed and Privileged Changes

For PRs carrying governed or privileged mutation classes (as defined in
`docs/contracts/mutation-class-taxonomy.md` and `docs/contracts/authority-matrix.md`):

- A valid Source ratification envelope reference must appear in the PR description.
- The authorized scope (files/paths) must be explicitly stated and verified.
- CI evidence alone does not satisfy the ratification requirement.
- Additional human review by an authorized ratifier is required.

## Author/Approver Separation

| Mutation class | Minimum approvers | Author == Approver? |
|----------------|-------------------|---------------------|
| Standard       | 1                 | Not permitted        |
| Governed       | 1 + ratifier      | Not permitted        |
| Privileged     | Source ratifier   | Not permitted        |

## Live GitHub Settings and Branch-Protection Application

> **This document is policy documentation only.**
>
> Live GitHub branch-protection settings, repository settings mutation, and
> branch-protection rule application are NOT performed by CI, are NOT performed
> by opening a PR, and are NOT performed by merging this or any other PR.
>
> Applying live GitHub branch-protection rules or repository settings requires
> a **separate, explicit Source ratification envelope** authorizing that specific
> action. No automated process, CI workflow, or agent action in this repository
> is authorized to mutate live GitHub settings without such an envelope.

This separation ensures:

- CI cannot accidentally apply or remove branch protection.
- A compromised workflow cannot escalate its own permissions.
- All live-settings mutations are traceable to an explicit human authorization act.

## CI Evidence vs. Ratification

CI validation evidence confirms that:

- Artifacts parse as valid YAML.
- Governance artifacts pass schema and rule checks.
- No write permissions or deploy/merge/approve actions are present in workflow files.

CI validation evidence does **not** confirm that:

- The change is authorized under the governance authority matrix.
- A Source ratification envelope covers the mutation.
- The change is safe to deploy, release, or activate in a live environment.
- Live branch-protection settings match this policy document.

The human review and ratification process is the authoritative gate for those
determinations.

## Policy Maintenance

Changes to this document are governed changes. Any modification requires:

- A PR with scope/boundary documentation.
- CI validation passing.
- At least one reviewer approval with author/approver separation.
- For changes that alter the ratification model: a Source ratification envelope.
