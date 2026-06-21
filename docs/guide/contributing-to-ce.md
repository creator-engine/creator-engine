# Contributing to Creator Engine

## 1. Who This Is For

This guide is for human contributors who want to move from a fresh clone to a well-scoped pull request in the Creator Engine repository. It is written for people who can work inside a ratification-governed project without assuming that a green CI run, a comment, or an opened PR gives them authority. External PRs carry proposed change only; issues carry information; envelopes carry authority; CI verifies but never ratifies (`docs/governance/EXTERNAL_CONTRIBUTOR_INTAKE_BOUNDARY.md:38-56`).

Creator Engine is pre-1.0 and ratification-governed. The public contributing on-ramp already says contributors should follow the spec/plan/tasks model and respect ratification boundaries (`CONTRIBUTING.md:3-8`).

### Trust-Tier Table

The baseline authority matrix has exactly seven `role_category` values (`schemas/authority-matrix.schema.yaml:7-12`, `schemas/authority-matrix.schema.yaml:37-40`). The prose contract describes the same seven categories (`docs/contracts/authority-matrix.md:24-37`).

| Trust tier / `role_category` | Can do | Cannot do without ratification or delegation |
| --- | --- | --- |
| `source` / Operator | Approve governance direction and ratify privileged mutations (`docs/contracts/authority-matrix.md:29-32`). | Cannot bypass author/approver separation; single-actor approval of a privileged mutation is invalid (`GOVERNANCE.md:116-118`, `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md:121-123`). |
| `ratifier` | Accept a mutation after reviewing evidence when Source has authorized that role (`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md:99-109`). | Cannot become the author of the same mutation they ratify; cannot grant themselves privileged authority. |
| `architect` | Author spec/plan/contract and docs/code/schema design artifacts (`docs/contracts/authority-matrix.yml:62-77`). | Cannot ratify; cannot deploy, mutate identity, or change governance without a human ratifier. |
| `implementer` | Author docs/code/schema work from spec/plan/tasks (`docs/contracts/authority-matrix.yml:78-92`). | Cannot review or ratify their own PR; cannot expand mutation class or path scope. |
| `reviewer` | Provide review evidence on PRs and artifacts (`docs/contracts/authority-matrix.yml:94-106`). | Review text is not privileged ratification (`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md:111-119`). |
| `verifier` | Author tests, validators, and verification artifacts (`docs/contracts/authority-matrix.yml:108-121`, `docs/contracts/authority-matrix.md:36`). | Cannot treat passing tests as authority; CI/verifier evidence does not ratify. |
| `observer` | Write notes, issues, observations, and handoff material (`docs/contracts/authority-matrix.yml:123-133`). | Cannot author tracked implementation, approve, merge, or ratify. |

### Governed Seat Hard Denials

A governed seat does not get ambient forge authority.

- `git push` is classified as the restricted `deploy` mechanic (`validators/creator_engine_validator/hook_check.py:198-204`). Under governed posture, restricted mechanics that are not covered are hard-denied (`validators/creator_engine_validator/hook_check.py:318-327`, `validators/creator_engine_validator/hook_check.py:551-563`).
- `gh pr review` is classified as the restricted `pr_review` mechanic (`validators/creator_engine_validator/hook_check.py:210-214`). A reviewer-authority envelope can authorize exactly one `pr_review` mechanic on exactly one PR, and everything else fails closed (`docs/operations/REVIEWER_VENUE_AUTHORITY.md:23-35`).
- Secret-looking reads are denied. The hook recognizes `.env`, key files, PEM/key suffixes, `.ssh`, `.gnupg`, `.aws`, and credential-like names (`validators/creator_engine_validator/hook_check.py:160-190`), and returns a credential-path denial without reading secret bytes (`validators/creator_engine_validator/hook_check.py:330-334`).
- Branch-protection settings, repository settings, and constitution changes remain privileged. Live branch-protection mutation requires a separate Source ratification envelope and is not performed by CI, PR, merge, or agent action (`.github/BRANCH_PROTECTION_POLICY.md:56-67`). `CONTRIBUTING.md` tells contributors not to change branch protection, history, the constitution, or canonical governance docs without explicit authorization (`CONTRIBUTING.md:70-83`).

## 2. Governance In Five Minutes

Creator Engine separates verification from authority. The CI workflow itself states that it verifies only and does not deploy, publish, merge, approve, or ratify (`.github/workflows/validate.yml:1-5`). `GOVERNANCE.md` repeats the invariant: automated checks prove artifacts are well formed and policies are followed; they do not authorize privileged action (`GOVERNANCE.md:120-125`).

The six privileged mutation classes are `deploy`, `governance`, `identity`, `security`, `attestation`, and `redaction` (`GOVERNANCE.md:101-108`). The mutation-class model describes the nine baseline classes and marks those six as privileged (`docs/governance/MUTATION_CLASS_MODEL.md:18-37`). Privileged classes require human ratification and cannot be ratified by agent-authored review text or CI (`docs/governance/MUTATION_CLASS_MODEL.md:92-127`).

In practical terms:

- CI verifies.
- Humans ratify.
- PRs carry change.
- Envelopes carry authority.
- Reviewers produce evidence unless they are explicitly acting as ratifiers under the authority model.

## 3. Environment Setup

Clone the repository and work from the repository root:

```bash
git clone <repo-url>
cd creator-engine
git rev-parse --short=7 HEAD
```

Install the validator runtime dependencies using the uv-first offline path. The
validator README defines Python 3.14 as the current floor, source-checkout
execution, and the checked-in dependency wheelhouse contract
(`validators/README.md:7-17`):

```bash
uv venv --python 3.14
UV_PYTHON_DOWNLOADS=never uv pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
PYTHONPATH=validators python -m creator_engine_validator --list-checks
```

If you need the full pytest gate, install the dev/test dependency set from the checked-in dev wheelhouse (`validators/README.md:41-55`):

```bash
python -m venv .venv-test
.venv-test/bin/pip install --no-index \
  --find-links validators/wheelhouse \
  --find-links validators/wheelhouse-dev \
  -r validators/requirements.txt \
  -r validators/requirements-dev.txt
```

Run these three named CI checks locally before asking for review:

```bash
# Creator Engine validator - pytest suite (offline)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=validators \
  python -m pytest -p no:cacheprovider validators/tests/ -q -n auto --dist loadgroup

# Creator Engine validator - well-formed examples
PYTHONPATH=validators python -m creator_engine_validator check examples/well-formed/

# Creator Engine validator - malformed examples (expect failures)
if PYTHONPATH=validators python -m creator_engine_validator check examples/malformed/; then
  echo "FAIL: malformed examples unexpectedly passed"
  exit 1
else
  echo "OK: malformed examples correctly rejected"
fi
```

Those names and commands mirror the workflow steps in `.github/workflows/validate.yml:43-46`, `.github/workflows/validate.yml:83-94`. For smaller documentation PRs, the existing `CONTRIBUTING.md` also asks contributors to run `git diff --check`, `check-examples`, and `scan-no-limitless` locally (`CONTRIBUTING.md:108-125`).

> **Running from an isolated worktree (creator-engine#82)?** CE lane worktrees under
> `ce-worktrees/*` have no local `.venv` — it is gitignored and lives only in the
> canonical checkout. When no virtualenv is active, set `CE_VALIDATOR_PYTHON` to a
> known interpreter (e.g. the canonical checkout's venv) and invoke the validator as
> `${CE_VALIDATOR_PYTHON:-python}`. See [`../../validators/README.md`](../../validators/README.md).

## 4. The Governed Cycle

The user-facing cycle is:

```text
Frame -> Shape -> Build -> Review -> Ship
```

`docs/architecture/stage-vocabulary.md` is the canon for these words (`docs/architecture/stage-vocabulary.md:1-11`). The short version:

- Frame: understand and bound the problem.
- Shape: turn it into a ratifiable bet: acceptance criteria, budget, mutation class, and plan.
- Build: execute the ratified bet in a governed run.
- Review: grade the result against acceptance criteria.
- Ship: land the governed terminal result (`docs/architecture/stage-vocabulary.md:13-17`).

Under the words is a conserved state machine. Shape-to-Build is the front gate, and Ship is the back gate with mutation-class-tiered ratification plus branch-protected merge (`docs/architecture/stage-vocabulary.md:27-38`). The mechanical spec lifecycle remains `draft -> ready -> in_progress -> verified -> ratified -> done` (`docs/architecture/stage-vocabulary.md:40-48`).

For a contributor, the practical loop is:

1. Compose: frame the request, scope it, and name the mutation class.
2. Verify: run the local validator/pytest checks and collect evidence.
3. Ratify: obtain the required human ratification for governed or privileged scope.
4. Implement: produce the bounded diff and PR.
5. Review/Ship: obtain independent review, then a maintainer/Operator lands what is authorized.

## 5. Your First PR

Keep the PR boring and bounded.

Use the PR template's scope section to state what changed, what did not change, and the mutation class (`.github/pull_request_template.md:3-12`). The privileged mutation section asks for the Source ratification envelope reference, authorized scope, dominant mutation class, and confirmation that no deploy, live branch-protection mutation, merge, or secrets action occurred (`.github/pull_request_template.md:29-49`).

Path scope is not informal. The live CI path-manifest gate uses per-PR carriers under `.ce/pr-manifests/<branch-slug>.md`, discovered from the PR diff, and enforces that the PR diff equals the carrier path set (`.github/workflows/validate.yml:100-118`). Do not invent a different carrier name for live PRs unless a ratified change updates the validator and workflow.

Checklist for the first PR:

- Reference the issue/spec/Scope that authorizes the change.
- Declare mutation class: `docs`, `code`, `schema`, or another baseline class from the mutation taxonomy.
- Keep the changed-file boundary tight.
- Add the path-manifest carrier when the PR is governed by a manifest.
- Paste validation evidence, including the three local checks above when they apply.
- Do not include secrets, local session state, generated logs, or machine-local paths. `CONTRIBUTING.md` explicitly excludes instance-local state and credentials (`CONTRIBUTING.md:91-106`).

## 6. Review And Independence

You cannot self-approve.

The CODEOWNERS file says the non-author approver is a CE-managed reviewer identity, and GitHub's author-cannot-approve-own-PR rule is part of the enforcement model (`.github/CODEOWNERS:1-9`). Branch-protection policy requires at least one reviewer approval and author/approver separation for every PR targeting `main` (`.github/BRANCH_PROTECTION_POLICY.md:18-36`).

Peer authority also enforces this at the governance-data level. The `peer_authority` check says the author's or running seat's human never counts as a ratifier (`validators/creator_engine_validator/checks/peer_authority.py:173-181`), and the implementation skips any approver resolving to the author/seat human (`validators/creator_engine_validator/checks/peer_authority.py:204-219`).

Reviewer venues are distinct seats. A reviewer authority ref is valid only for a distinct reviewer venue, launched as role `reviewer` and lane kind `review` (`validators/creator_engine_validator/lane_runtime.py:361-372`, `validators/creator_engine_validator/lane_runtime.py:620-630`). The reviewer venue gets only the envelope-authorized `pr_review` mechanic for one PR; it cannot push or merge (`validators/creator_engine_validator/v3_seat_bridge.py:952-984`).

## 7. Boundaries

Ask before you cross a boundary. Stop before you mutate a privileged surface.

These require explicit Operator/maintainer authorization before implementation:

- Large architecture changes.
- New mutation classes.
- Changes to the constitution.
- Changes to Feature 001 governance substrate or Feature 002 operating model.
- Anything crossing a privileged-class boundary (`CONTRIBUTING.md:46-52`).

Never-touch list for ordinary contributor PRs:

- Branch-protection rules and repository settings.
- Git history rewrites on shared branches.
- `.specify/memory/constitution.md`.
- Canonical governance docs under `docs/governance/`.
- Identity records, credentials, signing keys, App PEMs, tokens, and secret-shaped files.
- Redaction/security/attestation gate weakening.
- Deploy, publish, merge, or live external-tracker mutation on behalf of the project.

The governance on-ramp lists these privileged repo/platform operations and says PRs attempting them without authorization are closed pending the appropriate spec/plan/tasks triple and Operator ratification (`GOVERNANCE.md:135-155`).

## 8. Legal: Apache-2.0 And DCO

Current `CONTRIBUTING.md` says contributions are licensed under Apache License, Version 2.0 (`CONTRIBUTING.md:150-158`). ce-ops#63 M2 is Operator-approved for DCO, so this D1 guide should add the DCO mechanics rather than pretending they already exist in the live file.

Contributor rule:

```text
Every commit must carry a Developer Certificate of Origin sign-off.
Use `git commit -s`, or include this line in the commit message:

Signed-off-by: Name <email>
```

Exact CONTRIBUTING.md DCO requirement line for ratification:

```markdown
- By contributing, you certify the Developer Certificate of Origin for each commit by adding a `Signed-off-by: Name <email>` trailer, usually with `git commit -s`.
```

Example:

```bash
git commit -s -m "docs: clarify contributor setup"
```

The email in the sign-off must identify the human contributor. Do not sign off for another person.

## 9. Growth Path

The default contributor path is:

```text
contributor -> trusted implementer/reviewer -> area owner -> peer ratifier
```

The authority matrix already has least-privilege role categories for implementer, reviewer, verifier, ratifier, and source (`docs/contracts/authority-matrix.md:24-37`). Peer authority extends this with per-area ownership and risk-tiered quorum rather than a new authority engine (`docs/contracts/peer-authority.md:10-24`).

To become an area owner or peer ratifier, a contributor needs a ratified identity/authority update, not just more merged PRs. The repo coordination policy is self-classified as `governance`, and changing its authority map requires the privileged ratification bar (`.ce/coordination.yml:1-12`, `schemas/coordination-policy.schema.yaml:17-20`). For privileged decisions in team mode, peer authority requires at least two distinct humans (`docs/contracts/peer-authority.md:15-20`, `schemas/coordination-policy.schema.yaml:85-97`).

Until that update is ratified, keep working as a contributor: propose small, scoped changes; provide evidence; and let independent reviewers and ratifiers carry authority.
