# Author A CE-Valid PR

Use this playbook before handing a branch to a controller for push or review.

> **Standing directive: commit the candidate before local preflight.** Create a
> named exact-path candidate commit, then run the FULL local validator preflight
> (`ce validate-pr`, CI-parity) only on that clean committed tree before every
> self-push or handoff. A required correction is a new appended commit followed
> by another preflight; never amend, rewrite, or discard the candidate.

> **MANDATORY before EVERY push — no exemptions.** `ce validate-pr` (the full
> CI-parity offline suite, whole tree, run on a CLEAN working tree) MUST go green
> locally before pushing ANY PR — feature PRs, release / publish PRs, AND
> controller-authored PRs alike. There is no "it's just a release / signature
> ceremony" exemption: a release-publish PR is still a code change to the install
> spec and MUST pass the offline suite first. The offline suite mirrors
> `.github/workflows/validate.yml` exactly, so a local green ≈ CI green; pushing
> without it wastes a forge round-trip and surfaces failures publicly. Cautionary
> example: a release-publish PR (0.2.0 → 0.3.0) was pushed after verifying only
> the release signature, and 6 version-pinned install-spec tests still expecting
> `0.2.0` went RED at CI — every one of them would have been caught by running the
> offline suite locally first (see
> [`../delivery/VERSIONING_AND_RELEASE_POLICY.md`](../delivery/VERSIONING_AND_RELEASE_POLICY.md)
> "Release-publish preflight"). The durable fix — making those install-spec tests
> read the version dynamically from `version.py` so a release bump no longer breaks
> them — is tracked on the internal roadmap under the autonomous-release work
> (W2 release-bump).

1. Start from current main.

   ```sh
   git fetch origin
   git switch -c <branch-slug> origin/main
   ```

2. Make the scoped change and keep the tree focused on the ticket.

3. Create the named exact-path candidate commit before preflight. For a
   contained seat, commit the scoped files named by the brief; the controller
   generates and commits the required carrier later. For a non-contained
   author, include the PR carriers for the same branch slug:

   - `.ce/changelog/<branch-slug>.md`
   - `.ce/pr-manifests/<branch-slug>.md`

   The PR manifest must list the closed `origin/main..HEAD` path set, include itself, and include exactly one current PR-body work-class line:

   ```md
   - **Declared work class:** <XS|S|M|L>
   ```

   Use only `XS`, `S`, `M`, or `L`. These are CE ceremony tiers, not Agile work
   item types. The declaration states the PR's minimum governance ceremony, not
   whether the change is a Scrum story, product feature, or roadmap epic. The
   work-sizing gate derives a minimum tier from the diff and rejects declarations
   below that floor.

4. Run the local preflight on the clean candidate commit before push:

   ```sh
   PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr
   ```

   The preflight's default test gate mirrors the CI offline invocation exactly — the whole `validators/tests/` tree (unit + integration), excluding `wheel_bake_gate`, run in parallel (`python -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup`). This is true CI parity, so it is slower (~1-4 min) than a unit-only run; that cost is intentional to avoid CI false-greens.

   Do not use `--allow-dirty` as candidate or handoff evidence: it validates old
   committed state rather than an uncommitted candidate. A dirty tree must be
   committed before authoritative validation.

5. Fix every failed per-check line with a new appended commit, then rerun until
   the final summary is `PASS: PR preflight`.

6. Hand off the branch evidence to the foreman/controller. The controller
   generates and commits any contained-seat carrier and runs full unprofiled
   validation before attestation or merge-gate handling. Independent review,
   green checks, ratification, and merge-gate requirements still apply. Do not
   self-merge.
