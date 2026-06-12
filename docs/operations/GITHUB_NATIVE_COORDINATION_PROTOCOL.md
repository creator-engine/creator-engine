# GitHub-native coordination protocol (v3 G-iii)

> Status: v3 evolve gate **G-iii**. Defensive: this hardens *our own*
> repository's merge gate and packages that hardening as the reusable platform
> seam. No offensive surface.

## a. Purpose

CE v3 **rents coordination, review, and merge to a forge** (GitHub first)
rather than building a bespoke coordinator (Brief plane A; the v2 reviewer-venue
authority machinery is retired). G-iii stands up the thin, reusable seam that
makes a repository's GitHub configuration *be* that coordination plane, and
makes scope-containment (plane B, the `path_manifest_fidelity` diff-gate) a
**machine-enforced** merge gate instead of post-hoc verification by the
authoring Controller.

It is the first slice of the platform's auto-config: the same two functions the
(future, thin) orchestrator calls once per user repo —
`configure_repo()` and `install_required_checks()` — live in
`creator_engine_validator/forge/github_repo_config.py`.

## b. The two operations

Both are **idempotent**, **desired-state**, and **plan-by-default**. Every
GitHub call goes through an injectable `GhRunner` (`gh api` by default) so they
are unit-tested with a fake runner and perform zero live network at import or
in tests.

- `install_required_checks(repo, contexts, *, branch="main", apply=False, gh_runner=None)`
  — read the branch's current required status-check contexts, compute the
  **sorted union** with `contexts` (non-destructive — never drops a check
  someone else registered), and `PATCH` only when that union differs.

- `configure_repo(repo, policy=DEFAULT_MAIN_PROTECTION, *, branch="main", apply=False, gh_runner=None)`
  — read the branch's current *classic* protection, union the policy's required
  contexts with any already present, and `PUT` the full classic-protection body
  only when the policy-relevant observation differs; then re-read to **verify**
  the live state matches the policy.

With `apply=False` (the default) each operation reads, diffs, and returns a
`ConfigResult` describing what *would* change — it mutates nothing. A live
mutation happens only when a caller passes `apply=True` with a real runner.

## c. Desired-state policy (`DEFAULT_MAIN_PROTECTION`)

The classic branch-protection CE applies to its own `main`:

| Field | Value | Why |
| --- | --- | --- |
| required status check | `Validate governance artifacts` (strict / up-to-date) | the one required job runs **both** the pytest suite and the `verify-path-manifest` diff-gate, so scope-containment is enforced when a PR carries its per-PR carrier `.ce/pr-manifests/<branch-slug>.md` |
| required approving reviews | `1`, last-push-approval on, dismiss-stale on | an independent, current approval is always required |
| **require Code Owner review** | **on** | pins the required non-author approval to the CE-managed reviewer identity in `.github/CODEOWNERS` |
| linear history | on | squash + linear keeps history auditable |
| `enforce_admins` | **on** | no admin/bypass actor can merge past the gate (closes the silent-bypass risk) |
| force-pushes / deletions | off | protected branch integrity |
| conversation resolution | on | nothing merges with unresolved review threads |

### Authority is a *config* fact, not a *credential* fact (OD-04′)

Branch confinement and "cannot self-merge" are **branch-protection facts**, not
token facts: there is no branch-scoped token and no separable merge permission.
So this configuration — not any credential — is what enforces the no-self-merge
guarantee. Author-cannot-approve-own-PR is GitHub-intrinsic;
`require_code_owner_reviews` + CODEOWNERS pins the approver to the CE-managed
reviewer identity. CE owns getting this configuration right so the user never
touches it, *and* validates its own config (the desired-state re-read in
`configure_repo`).

## d. Reviewer identity

The non-author approver is the **CE-managed reviewer identity** (`ubuntuaws745-cmyk`
today, distinct from the author `chmod735`), declared in `.github/CODEOWNERS`.
A `@creator-engine/ce-reviewers` *team* is the recommended future hardening
(robust to single-account unavailability); CODEOWNERS is the only native way to
require an individual identity, so the individual is used for the MVP.

## e. Classic protection vs rulesets

G-iii targets **classic branch protection** (`.../branches/{branch}/protection`)
— it is what `main` already uses and what prior PRs merged through, and
`enforce_admins=true` removes any bypass-list concern. A migration to the newer
**rulesets** API (more expressive, team-based required reviewers, bypass lists)
is a deliberate later gate, not part of G-iii.

## f. Live-apply procedure (run in the merge batch, post-merge)

To avoid a bootstrap deadlock (tightening protection before this PR merges would
block this very PR), the **live** application of the policy is deferred to the
G-iii **merge batch**, after the squash-merge, and is itself Operator-ratified:

1. Record the current protection as the rollback:
   `gh api repos/creator-engine/creator-engine/branches/main/protection > rollback.json`.
2. Dogfood the just-merged seam on `main` (real runner, `apply=True`):
   `configure_repo("creator-engine/creator-engine", apply=True)`.
3. Confirm `ConfigResult.verified is True` and that `require_code_owner_reviews`
   is now on and `enforce_admins` keeps admins on-gate (no bypass).
4. **Rollback** (only if needed): `PUT` the recorded `rollback.json` back.

`install_required_checks` need not change the required context set (the single
`Validate governance artifacts` job is already required and already runs both
checks); splitting the diff-gate into its own required context is an optional
future refinement.

## g. Carrier convention (the enforcement that makes plane B real)

Every gate PR carries its ratified closed manifest as its own per-PR carrier
`.ce/pr-manifests/<branch-slug>.md` (see `PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
Because the diff-gate runs inside the required `Validate governance artifacts`
check, a gate PR whose `base..HEAD` diff drifts from its carried manifest
**cannot merge**. This converts scope-containment from post-hoc verification by
the Controller into a machine gate. Because each PR's carrier has a distinct
path, two concurrently-open gate PRs never conflict on the carrier file (the
ce-ops#21 migration from the single shared `.ce/pr-path-manifest.md`).

## h. How the orchestrator uses this

The future thin orchestrator calls `configure_repo()` once at install time
(against the *user's* repo, with a scoped GitHub App installation token) and
`install_required_checks()` to register the CI contexts. Both are idempotent, so
re-running install is safe. This module may later be extracted into a standalone
`ce_orchestrator` package on the architect's pre-committed extraction trigger;
until then it ships in the validator package so the existing CI pytest job
covers it (it registers no validator check and leaves `--list-checks`
unchanged).
