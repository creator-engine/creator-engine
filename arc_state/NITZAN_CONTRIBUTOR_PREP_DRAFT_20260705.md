# Nitzan Contributor-Onboarding Prep — Draft (internal)

Status: **DRAFT ONLY**. Not sent anywhere, no repo pushed, no PR opened.
Prepared: 2026-07-05. Subject: Nitzan, announced 2026-07-04 as Creator
Engine's first external contributor. Scope/employment/agreement status
with Nitzan is still TBD with the Operator (see Open Questions, §4).

This document is internal working material. Where a subsection is marked
**[QUOTE-READY]**, its prose is written so it could be copy-pasted into a
public-facing file (e.g. `CONTRIBUTING.md`, `docs/guide/contributing-to-ce.md`)
with zero edits for confidentiality — it carries no `ce-ops#` references, no
internal seat/fleet vocabulary, no controller/dispatch mechanics. Everything
else is internal-only framing and should NOT be copied verbatim into a public
surface.

---

## 0. What already exists (read this before drafting anything new)

Before writing new contributor-facing content, note that Creator Engine
already ships a mature contributor on-ramp. Don't duplicate it — reference it.

- **`CONTRIBUTING.md`** (repo root, also present on the forge at
  `github.com/creator-engine/creator-engine/blob/main/CONTRIBUTING.md`,
  last touched by commit `5cadbdc7`) — the canonical public contributing
  doc. Covers: how work is organized (constitution → specs → README →
  GOVERNANCE.md), what kinds of changes are welcome (issues, small scoped
  PRs, "discuss first" for larger changes), ratification boundaries and
  privileged mutation classes, PR expectations (scope, no instance-local
  state, no secrets), local validation commands (`check-examples`,
  `scan-no-limitless`, full `check`), the developer install path (uv +
  editable install, three console scripts `ce` / `cev3` /
  `creator-engine-validator`), the v1↔v3 version-boundary rule, and
  license/DCO (Apache-2.0, `Signed-off-by:` trailer required).
- **`docs/guide/contributing-to-ce.md`** (242 lines) — a longer,
  product-lens companion guide already written for external humans. It
  covers a trust-tier table, governed hard-denials (why a contributor's
  `git push` / `gh pr review` don't carry ambient authority), the
  Frame→Shape→Build→Review→Ship cycle, first-PR checklist, review
  independence (CODEOWNERS + peer-authority, no self-approval), a
  "never touch without authorization" list, DCO mechanics, and a
  trust-tier graduation ladder (contributor → trusted implementer/reviewer
  → area owner → peer ratifier) with concrete merged-PR/review-count
  thresholds. It already cites files, not internal tickets — it is
  product-lens compliant as written.
- **`GOVERNANCE.md`** — the public governance index: roles (Operator,
  Maintainers, Contributors, Agents), the six privileged mutation classes
  (`deploy`, `governance`, `identity`, `security`, `attestation`,
  `redaction`), the CI-verifies/humans-ratify invariant, and the list of
  privileged repo/platform operations a PR must not attempt unsolicited.
- **`docs/governance/EXTERNAL_CONTRIBUTOR_INTAKE_BOUNDARY.md`** — the
  governance note that already fixes the external-contributor boundary
  model: issues carry information, envelopes carry authority, PRs carry
  change, CI verifies but never ratifies; privileged surfaces need a
  Source ratification envelope regardless of CI/reviewer status; and —
  important for Nitzan specifically — it explicitly says **public
  visibility/discoverability is out of scope** and deferred to a later,
  separately-gated OSS-readiness effort. Onboarding one named external
  contributor is not the same decision as making the repo publicly
  discoverable; don't conflate the two.
- **`.github/BRANCH_PROTECTION_POLICY.md`** — policy doc for `main`:
  required CI check, ≥1 reviewer approval, author/approver separation,
  no direct push, no force-push, no branch deletion. Notes live
  GitHub branch-protection application is itself a privileged,
  separately-ratified act — not something CI or a merge does.
  (Live-settings state should be spot-checked against this doc before
  Nitzan's first PR — see §4.)
- **`.github/CODEOWNERS`** and the PR template
  (`.github/pull_request_template.md`) — enforce non-author review and
  ask for mutation class + (for privileged mutations) ratification
  envelope reference in the PR body.

**Implication for this task:** the "CONTRIBUTING.md outline" asked for in
§1 below is mostly a *gap list against existing docs*, not a from-scratch
draft. The existing docs already do the heavy lifting; what's missing is
(a) an access-model decision for a specific named contributor, and (b) a
short "gate troubleshooting" companion aimed at someone hitting CI gates
for the first time without fleet/controller context.

---

## 1. CONTRIBUTING.md outline, contributor lens — gap list against existing docs

Skeleton below marks each item **[COVERED]** (already documented, cite the
file) or **[GAP]** (needs new content or an explicit decision).

1. **How to propose work** — [COVERED] `CONTRIBUTING.md` §"What kinds of
   changes are welcome"; `docs/guide/contributing-to-ce.md` §4 (the
   governed cycle) and §5 (first PR checklist).
2. **Branch/PR conventions** — [COVERED] `docs/guide/contributing-to-ce.md`
   §5; PR template. **[GAP]** neither doc states a required branch-naming
   convention for external forks (internal branches use a `ce-<ticket>`
   convention that is fleet-internal and should NOT be pushed on
   contributors — a fork contributor's branch name is their own fork's
   business). Confirm there is no naming requirement to give Nitzan, or
   state one explicitly if there is.
3. **Carrier (path manifest) + changelog + declared-work-class, in plain
   language** — [PARTIALLY COVERED, GAP on plain-language framing].
   `docs/guide/contributing-to-ce.md` §5 explains the path-manifest carrier
   mechanically (per-PR file at `.ce/pr-manifests/<branch-slug>.md`,
   diff must equal the carrier's path set) and points at the PR template's
   mutation-class field. It does **not** currently explain, in a first-timer's
   plain language:
   - *why* this exists (prevents scope creep / silent unrelated changes,
     makes every PR's blast radius auditable) — worth one sentence, no
     internal jargon.
   - the **changelog fragment** obligation
     (`.ce/changelog/<branch-slug>.md`) is not mentioned in either public
     doc at all. **[GAP — real]**: a contributor who reads only
     `CONTRIBUTING.md` / `docs/guide/contributing-to-ce.md` today will not
     know a changelog fragment is required and will fail the carrier gate
     without understanding why. Suggested addition (plain language,
     quote-ready):
     > Every pull request needs two small bookkeeping files alongside your
     > change: a path manifest at `.ce/pr-manifests/<your-branch-slug>.md`
     > listing every file your PR touches, and a one-paragraph changelog
     > fragment at `.ce/changelog/<your-branch-slug>.md` describing what
     > changed and why. CI checks that your manifest's path list exactly
     > matches your PR's actual diff — this catches unrelated files sneaking
     > into a PR. Generate the manifest with the repo's carrier-generation
     > tool rather than writing it by hand (see `validators/README.md`);
     > regenerate it any time your diff changes.
   - the "declared work class" line — [GAP]: no public doc currently
     tells a contributor they must add a line like
     `- **Declared work class:** tiny` to their PR body, what the four
     values (`tiny`/`story`/`feature`/`epic`) mean, or that editing the PR
     body alone won't re-trigger the check (needs close+reopen or a new
     push). Suggested addition (quote-ready):
     > Your PR description must contain exactly one line of the form
     > `- **Declared work class:** <tiny|story|feature|epic>`. This tells
     > CI what size of change to expect and lets it flag PRs whose diff
     > looks bigger than declared. Pick the smallest class that honestly
     > describes your change; when in doubt, ask in the PR or issue first.
4. **Preflight bar: "green before you push"** — [COVERED, mechanically]
   `docs/guide/contributing-to-ce.md` §3 lists the exact local commands
   (pytest suite, well-formed/malformed examples). **[GAP]**: neither doc
   currently bundles these into one named "run this one command before you
   push" entry point the way the internal `ce validate-pr` preflight does
   for maintainers. If a single consolidated contributor-facing preflight
   command is wanted, that's a real product decision (does a
   contributor-safe subset of `ce validate-pr` exist / should one be built?)
   rather than a docs-only fix — flag as an open question (§4) rather than
   assuming it should be built now.

**Bottom line for §1**: the two real content gaps are the changelog
fragment obligation and the declared-work-class line. Both are small,
self-contained additions to `docs/guide/contributing-to-ce.md` §5 and
would very likely resolve the confusion Nitzan is most likely to hit on a
first PR (a green-looking local run that still fails CI on carrier/gate
checks). Recommend filing this as a small, ordinary `docs` PR through the
normal contributor flow once reviewed — it is not itself privileged.

---

## 2. Access model options (least-privilege first)

**No decision has been made here — this section lays out options for the
Operator, it does not recommend one over the others without more
information about Nitzan's role (see §4).**

### Option A — Fork-and-PR (no repo access granted)

Nitzan forks the repository on the forge, works on a branch in their own
fork, and opens PRs against `main` from the fork.

- What Nitzan can trigger: opening PRs, pushing to their own fork,
  commenting on issues/PRs.
- What Nitzan cannot trigger: pushing to any branch in the upstream repo,
  approving/merging PRs, triggering workflows that need `write` (CI here
  is entirely `contents: read` / `pull-requests: read` per
  `.github/workflows/validate.yml`, so a fork PR's CI run has no elevated
  permissions regardless).
- Merge gate from outside: identical to any other external PR under
  `docs/governance/EXTERNAL_CONTRIBUTOR_INTAKE_BOUNDARY.md` — CI verifies,
  a distinct human reviewer/maintainer reviews and approves (never the
  author), and for privileged mutation classes a Source ratification
  envelope is required regardless of CI/review state. No self-merge is
  possible in any case: branch protection requires ≥1 non-author approval
  before merge and the merge queue/queue-daemon owns actual merge
  sequencing.
- Lowest-privilege option; standard OSS pattern; requires no repo-settings
  change and no new collaborator entry. Recommended default absent a
  specific reason Nitzan needs more.

### Option B — Collaborator with branch protection (push access, no bypass)

Nitzan is added as a repo collaborator (read/triage/write, scoped by
GitHub role) and pushes branches directly to the upstream repo rather than
a fork, still opening PRs against `main`.

- What changes vs. Option A: Nitzan can push branches directly (skips the
  fork step), may be able to see/triage issues with elevated visibility
  depending on the GitHub role granted (`triage` vs `write`).
- What stays the same: `main` is still protected — no direct push, no
  force-push, no self-approval, no bypass of the ≥1-reviewer /
  author-approver-separation rule; a `write`-scoped collaborator does not
  get branch-protection-admin rights (that stays privileged, per
  `.github/BRANCH_PROTECTION_POLICY.md`, and is not implied by any
  collaborator role).
- Granting collaborator access is itself a privileged, Operator-gated act
  ("Repository settings changes" is on the explicit privileged-operations
  list in `GOVERNANCE.md`) — this is not a maintainer-level call to make
  unilaterally.
- Consider only if Nitzan needs to push directly for a specific reason
  (e.g. sustained high-frequency contribution, or tooling that assumes
  push access); otherwise Option A achieves the same governed outcome with
  strictly less standing access.

### What a contributor can/cannot trigger, either option

- **Can trigger:** CI validation run (read-only checks), a review request,
  a merge-queue entry once approved+green (queue sequencing is automatic,
  not contributor-triggered).
- **Cannot trigger, ever, regardless of access level:** merge to `main`
  without independent human review; any branch-protection or
  repo-settings change; any privileged mutation-class merge without a
  Source ratification envelope; live deploy/release actions; history
  rewrites on shared branches.
- **Not yet decided:** whether Nitzan gets any tooling beyond a plain git/PR
  workflow (see §4, contained-seat tooling question) — that is a separate
  axis from repo access level and should not be bundled into the same
  decision.

---

## 3. Gate interactions: what a contributor's PR will hit, and who fixes what

From `.github/workflows/validate.yml` (the only required check on PRs and
the merge queue), a contributor's PR runs, in order:

1. Offline validator pytest suite (`validators/tests/`).
2. YAML parse checks (workflows, schemas/templates/contracts/examples/playbooks).
3. Identity-registry schema check.
4. Well-formed example check, playbook-format check, malformed-example
   check (expects rejection).
5. `--list-checks` audit-evidence dump, install-spec signature scan, brain
   drift check.
6. **G5 — work-sizing floor gate**: reads the PR body for exactly one
   `- **Declared work class:** <tiny|story|feature|epic>` line and checks
   the diff size against that declared class.
7. **Test-coupling gate**: checks the PR body + diff for expected
   test coverage coupling.
8. **G-ii — path-manifest / carrier gate**: discovers the PR's own carrier
   file at `.ce/pr-manifests/<branch-slug>.md` from the diff and requires
   the PR's changed-file set to exactly equal the carrier's declared path
   set, plus a matching `.ce/changelog/<branch-slug>.md` fragment. Runs in
   `--require-carrier` (fail-closed) mode.
9. Workflow-permissions audit (asserts no workflow declares `write`
   permissions) — this is a repo-hygiene check, not something a
   contributor's PR could trip either way.

### Self-service (contributor can fix without maintainer help)

- Pytest/example/YAML failures: standard code-review-style fixes; the
  failure output is the same locally and in CI (`docs/guide/contributing-to-ce.md`
  §3 gives the exact local commands to reproduce before pushing).
- G5 missing/malformed declared-work-class line: add or correct the PR
  body line.
- Test-coupling gate: add the coupled test the gate is asking for.
- Carrier/changelog gate: generate/update
  `.ce/pr-manifests/<branch-slug>.md` and `.ce/changelog/<branch-slug>.md`
  to match the current diff. **Caveat**: the carrier-generation tool
  (`validators/creator_engine_validator/carrier_gen.py`) is currently
  documented as an internal maintainer workflow entry point
  (`write_carriers(base=...)`); whether a first-time external contributor
  can run it standalone from a fresh clone with no other context is
  untested from a true "cold start" contributor position. **[GAP — worth
  a dry run before Nitzan's first PR]**: have someone simulate a fresh
  clone + carrier generation with zero prior repo knowledge to confirm
  the documented path actually works end-to-end, or fix it if not.

### Needs maintainer/Operator help (not contributor self-service)

- Anything the G5/carrier gates flag as touching a **privileged mutation
  class** (`deploy`, `governance`, `identity`, `security`, `attestation`,
  `redaction`) — these need a Source ratification envelope referenced in
  the PR body; a contributor cannot self-authorize this regardless of how
  green their local run is.
- Branch-protection / repo-settings requests surfaced by a contributor
  (e.g. "can I get write access") — Operator-gated per `GOVERNANCE.md`'s
  privileged-operations list.
- Stuck merge-queue entries, stale approval-capability markers, or gate
  false-positives (e.g. a stale-base carrier mismatch) — these are
  maintainer-side operational issues, not something to ask a contributor
  to work around.
- Any request to bypass a check (never appropriate) vs. a genuine gate bug
  (file an issue; do not work around it in the PR).

---

## 4. Open questions for the Operator

These need an explicit decision before Nitzan's onboarding proceeds beyond
"read the public docs":

1. **Scope of Nitzan's contribution area.** Is this open-ended ("whatever
   they want to work on") or a specific area (docs? validator bugs? a
   named feature)? The existing `CONTRIBUTING.md` already asks for
   "discuss potential larger changes in an issue first" — is there a
   starter area/issue list to point Nitzan at, or is triage itself the
   first task?
2. **Employment/agreement status.** Is Nitzan a paid contractor, an
   unpaid open-source-style volunteer, or something else (e.g. evaluation
   period before a role)? This affects which access model (§2) and which
   graduation-ladder expectations (`docs/guide/contributing-to-ce.md` §9)
   apply, and whether a separate contributor agreement / CLA-equivalent
   is needed beyond the DCO sign-off already required by `CONTRIBUTING.md`.
3. **Contained-seat tooling.** Is Nitzan expected/offered any of the
   fleet's own contained-agent tooling (e.g. governed agent seats), or is
   this a plain human-with-git-and-editor contributor with no fleet
   tooling exposure? This is a separate axis from repo access level (§2)
   and should be decided independently — bundling them risks either
   over- or under-provisioning.
4. **Credential boundaries.** Confirm explicitly what Nitzan does and does
   not get: no GitHub App/PAT tokens used by the fleet, no OpenBao
   access, no signing key access (`ce-root-v1` stays controller-only per
   existing doctrine), and no access to any internal ticket tracker
   (`ce-ops`) if that tracker itself remains internal-only. If Nitzan needs
   to file issues, confirm which tracker they use — the code repository's
   own issue tracker, presumably, not `ce-ops`.
5. **Public-visibility conflation check.** `docs/governance/EXTERNAL_CONTRIBUTOR_INTAKE_BOUNDARY.md`
   is explicit that public visibility/discoverability of the repo is a
   *separate, later, explicitly-gated* decision from accepting external
   PRs. Confirm the Operator is deciding "onboard Nitzan as a named
   external contributor to a repo that stays otherwise non-public" and
   not implicitly also deciding to make the repo publicly discoverable —
   these should not be the same ratification act.
6. **Who reviews Nitzan's first PR.** Given author/approver separation and
   no-self-review rules, confirm which maintainer identity is the intended
   independent reviewer for Nitzan's PRs, and whether that reviewer is
   expected to also handle any privileged-class escalation, or whether
   escalation routes straight to the Operator.
7. **Live branch-protection state check.** Before Nitzan's first PR, worth
   a maintainer confirming the *live* GitHub branch-protection settings on
   `main` actually match `.github/BRANCH_PROTECTION_POLICY.md` (the policy
   doc itself notes CI evidence does not confirm live settings match
   policy) — a stale live setting could either block or fail to block
   something the docs promise a first-time contributor.

---

## Summary for hand-off

Two existing public docs (`CONTRIBUTING.md`, `docs/guide/contributing-to-ce.md`)
already give Nitzan a strong contributor on-ramp; the concrete content gaps
are narrow (changelog-fragment + declared-work-class explanations) and are
themselves ordinary, non-privileged `docs` PRs. The harder open items are
not documentation gaps but decisions only the Operator can make: which
access model to grant, what Nitzan's agreement/scope actually is, whether
fleet tooling is in scope, and confirming the public-visibility boundary
isn't being accidentally widened by this one onboarding. Recommend
resolving the seven open questions above before doing anything
Nitzan-facing beyond pointing them at the two existing public docs.
