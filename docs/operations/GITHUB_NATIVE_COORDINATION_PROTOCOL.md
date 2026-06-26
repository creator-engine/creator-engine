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

The non-author approver is the **CE-managed reviewer identity** (distinct from
the author identity), declared in `.github/CODEOWNERS`.
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
migration from the single shared `.ce/pr-path-manifest.md`).

## h. How the orchestrator uses this

The future thin orchestrator calls `configure_repo()` once at install time
(against the *user's* repo, with a scoped GitHub App installation token) and
`install_required_checks()` to register the CI contexts. Both are idempotent, so
re-running install is safe. This module may later be extracted into a standalone
`ce_orchestrator` package on the architect's pre-committed extraction trigger;
until then it ships in the validator package so the existing CI pytest job
covers it (it registers no validator check and leaves `--list-checks`
unchanged).

## i. Known limitation — the JIT App push leg cannot ship `.github/workflows/**`

**The limitation.** The `cev3 pr --apply` ship leg pushes the seat's authored head
under a JIT least-privilege installation token whose mint request is a FIXED,
in-repo least-privilege set — `contents: write` + `pull_requests: write`
(`v3_forge_join.PR_TOKEN_PERMISSIONS`, doc comment "never broader"). It carries
**no `workflows` permission**. An installation token's effective permissions are the
requested subset, so the minted token lacks `workflows` *regardless of the App's
installed grant*. GitHub therefore **rejects** the App push for any diff that
creates or updates a file under `.github/workflows/**`.

**The signature.** The operator sees the remote-rejected line verbatim (it survives
`forge/_redact.py` redaction — it carries no credential):

> `refusing to allow a GitHub App to create or update workflow ... without `workflows` permission`

The failure is LATE (post-mint, at push) but NOT opaque — it names the exact missing
scope, so a CI-touching gate is diagnosable in-run (this is how PR #206 was diagnosed).

**The procedure (the declared orchestrator pre-push).** For a gate whose manifest
touches `.github/workflows/**`, the ORCHESTRATOR/Operator session pushes the authored
head FIRST, with an ambient `workflow`-scoped identity (the same HTTPS identity used
for other orchestrator pushes), and **DECLARES that pre-push on the gate's forge
trail** (the #206 precedent wording). Then `cev3 pr --apply` runs unchanged: with the
head already on the remote, the App push leg verifies an idempotent no-op
(`up_to_date=True`, nothing pushed — `forge/change_push.py`) and the PR-open stays
App-authored. This composes BY DESIGN; it is not a governance bypass — the binding
gate (review + merge) is untouched.

**The deferred durable fix.** The right fix is CONDITIONAL, not an unconditional
broadening (which would violate the module's "never broader" doctrine for the
overwhelming majority of PRs touching no workflow file): request `workflows: write`
**iff** the run's manifest path-set touches `.github/workflows/**` (the path-set is
already in `open_change_for_run`'s hands; the mint module accepts the scope unchanged).
It is sequenced behind an ops act — verifying the live `workflows: write` grant on both
per-dev Apps — and is tracked as a named follow-up micro-gate in an internal tracking issue. Until it
lands, use the declared pre-push above.

## g. Concurrent-merge throughput (F6 Phase-0: two-tier change-block re-stamp)

Strict up-to-date protection (§c) means **every merge moves `main`**, leaving other
open PRs behind base. A rebase/branch-update then changes a PR's head after its run
opened, so the locally-pinned `pr_opened.head_sha` goes stale and a head-pinned squash
of that SHA is correctly rejected by the server. Per-PR carriers removed the file-carrier
conflict; they do **not** address this stale head-pin.

F6 Phase-0 resolves it WITHOUT a queue and WITHOUT a head-override, conserving the
invariant **what-was-TESTED == what-MERGES**. The authority question is not "who may
override a stale pin?" — **override authority is rejected as a category** (there is no
`--head-override` and no override parameter on `forge.merge` / `merge_for_run`). The pin
is redefined as a ratified **change-block identity** plus a machine proof the integrated
state was tested. Two tiers:

| Tier | Trigger | CE action |
| --- | --- | --- |
| **Content change** | any changed diff identity / path-set / content pin / re-targeted branch-base, or an unprovable chain | **REFUSE** before any merge PUT (`content_drift_requires_reratification` / `restamp_legacy_unprovable`); route through the existing fresh ratification / adopt path — never a silent accept |
| **Base-only motion** | only the base moved; CE machine-proves unchanged branch/base/PR identity + unchanged carrier path-set + unchanged normalized non-mechanical diff identity + unchanged stable patch-id, with the live head green + review-satisfied | **auto re-stamp**: append `runtime_change_restamp` (`authority: machine_rebase_equivalence`), then squash-merge the NEW head |

`cev3 merge` (plan-by-default) reports `head_status` as `unchanged`,
`base_only_restamp_available`, `content_drift_refused`, or `legacy_unprovable`, and the
old/new SHAs; `--apply` re-stamps (if proven) and merges, then appends `pr_merged` + a
`runtime_merge_audit`. The audit makes squash honest: with squash-only the merged commit
is not the reviewed head, so CE records the conserved **tree-equivalence** invariant
(tested head tree == merged tree); a mismatch is an operator-visible alarm
(`merge_audit_tree_mismatch`), never a silent pass. The change-identity anchor (`base_sha`
+ content/patch identity) is stamped at PR-open onto the dispatch `change` block and
propagated into the chain's `pr_opened.change_set` by `cev3 collect`; a pre-F6 chain that
lacks `base_sha` is **legacy-unprovable** and is refused, never overridden. The merge still
mints **no** per-run token and rides the Operator's ambient `gh` identity (§e).

### Phase-1: GitHub native merge queue (F6 — the trigger is now being hit live)

Enable the GitHub native **merge queue** when CE sees **3 or more concurrent ratified PRs
more than once per week**, or a **third authoring host** is onboarded. That trigger is being
hit live: the serial train's per-step re-review tax blocked #297/#296. At this volume the
queue's tested-`gh-readonly-queue/{base}` integrator earns its integration cost; below it,
serial direct merge under the Phase-0 re-stamp is cheaper. Phase-1 does not change the
authority semantics — it only changes the trusted integrator (the queue owns final
integration; CE verifies the queued result is tree-equivalent to the ratified change-block).

**Enablement is a gated controller/Operator action — see
`MERGE_QUEUE_ENABLEMENT_RUNBOOK.md`.** The CI
prerequisite ships ahead of it as ordinary code.

What Phase-1 changes:

- **`merge_group` required-CI trigger (the load-bearing change).**
  `validate.yml` triggers on `merge_group: { types: [checks_requested] }`; without it the
  required check never reports on `gh-readonly-queue/{base}` and the queue stalls forever.
  Guarded by `validators/tests/unit/test_workflow_merge_group_trigger.py`.
- **The flip** is one `merge_queue` rule on the `ce-reference-protection-floor` repository
  ruleset. `RulesetPolicy(require_merge_queue=True, merge_queue_merge_method="SQUASH", …)`
  emits it through the existing `upsert_ruleset` adapter (plan-by-default, idempotent,
  verify-on-apply). Classic branch protection cannot express a merge queue; the queue is
  ruleset-only.
- `cev3 merge --apply` switches from direct squash PUT to **enqueue** (supplying the current
  ratified/re-stamped head), appending `pr_enqueued` then `pr_merged` only after GitHub
  reports the queue merge.
- Required review / dismiss-stale / last-push-approval / code-owner / `enforce_admins` /
  conversation-resolution **all stay**; the queue runs *after* the independent approval and
  its server-side rebase does not dismiss it.

#### F6 — the "re-sign the merged head" question, adjudicated

The merge-queue head (the `merge_group` synthetic commit, then the squash on `main`) differs
from the reviewed head. The question is: *who re-signs the merged head
under `ce-root-v1` so the conserved head-pin survives the queue's rebase?*

**The premise dissolves on inspection of what CE actually conserves.** CE does **not** hold a
`ce-root-v1` ed25519 signature over any merged commit head today. The offline `ce-root-v1`
(`ce-spec-v1` namespace) key signs exactly one thing — the install spec
(`docs/llms-install.md`) via detached SSHSIG, verified offline by the installer. The **merge
head-pin is not a cryptographic signature at all**: it is (1) the server-side
`--match-head-commit` guard on the squash PUT, plus (2) the F6 Phase-0 machine proof
(`runtime_change_restamp`, `authority: machine_rebase_equivalence`) and the post-merge
`runtime_merge_audit` tree-equivalence record in the hash-chained evidence spine. The
conserved invariant is **what-was-TESTED == what-MERGES**, carried by machine proof +
append-only evidence — *not* by an asymmetric signature over the head.

Therefore F6 needs **no new key, no delegated/sub-queue-signer, and no signing step in CI.**
The merge queue is simply the **trusted integrator** that performs the base-only motion the
Phase-0 re-stamp already models; CE re-binds review to the change-block and re-validates the
integrated state — exactly what every surveyed system (GitHub MQ, bors, Zuul, SubmitQueue)
does. Putting any private key in CI to "re-sign" the queue head would be a regression: it
would move custody of a trust root into the most-exposed surface to defend a property CE
never asserted with a key.

**Recommended F6 approach (no key custody change):**

1. Keep `ce-root-v1` exactly where it is — offline, controller/Operator-held, signing the
   install spec only. **Never in CI.**
2. The queue's merged head is governed by the **existing** evidence machinery, retargeted:
   - `pr_enqueued` records the ratified/re-stamped head handed to the queue (the
     change-block anchor `base_sha` + content/patch identity already stamped at PR-open).
   - After GitHub reports the queue merge, append `pr_merged` + a **post-merge**
     `runtime_merge_audit` proving the merged-commit tree is equivalent to the
     ratified/tested change-block tree. A mismatch is an operator-visible alarm
     (`merge_audit_tree_mismatch`), never a silent pass.
   - Because the queue is a GitHub black box, this audit is **post-hoc** (GitHub integrated;
     CE verifies after the fact) rather than the pre-merge gate of the direct path. That is
     the one genuine loosening — recorded, bounded, and the same trade every consumer of a
     native queue accepts.
3. The independent forge-side auditor (separate from the merge spine) re-confirms the
   tree/patch equivalence out-of-band, preserving small-blast-radius separation.

> **THE KEY-CUSTODY DECISION THAT NEEDS OPERATOR RATIFICATION** is therefore *narrow and
> negative*: ratify that **F6 introduces no new signing key and no CI-resident key** — the
> merged head is conserved by machine tree-equivalence + the append-only evidence chain, not
> by a `ce-root-v1` (or delegated) signature over the head. The only authority change to
> ratify is accepting the **post-hoc** (rather than pre-merge) tree-equivalence audit as the
> integrity gate for queue-merged heads. If the Operator instead wants a cryptographic
> signature over merged heads, that is a *new* requirement (not a conservation of an existing
> one) and would need: a delegated signer key trust-rooted under `ce-root-v1`, a custody home
> for it (OpenBao, **not** CI secrets), and a controller-side post-merge
> signing step — none of which is built or should be invented here without that explicit
> decision.
