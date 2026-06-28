# Author A CE-Valid PR

Use this playbook before handing a branch to a controller for commit, push, or review.

> **Standing directive: full local preflight before every self-push / commit-for-harvest.**
> Run the FULL local validator preflight (`ce validate-pr`, CI-parity) before
> every self-push or commit-for-harvest. Do not discover gates via CI. The full
> suite is what must pass before push. For fast iteration once the test-tier
> split lands on main, use `pytest -m "not slow"` — that is for iteration only;
> the full suite still gates the push.

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

3. Add the PR carriers for the same branch slug:

   - `.ce/changelog/<branch-slug>.md`
   - `.ce/pr-manifests/<branch-slug>.md`

   The PR manifest must list the closed `origin/main..HEAD` path set, include itself, and include exactly one PR-body line:

   ```md
   - **Declared work class:** <tiny|story|feature|epic>
   ```

   These are CE ceremony tiers, not Agile work item types. The declaration
   states the PR's minimum governance ceremony, not whether the change is a
   Scrum story, product feature, or roadmap epic. The work-sizing gate derives
   a minimum tier from the diff and rejects declarations below that floor.

4. Run the local preflight before push:

   ```sh
   PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr
   ```

   The preflight's default test gate mirrors the CI offline invocation exactly — the whole `validators/tests/` tree (unit + integration), excluding `wheel_bake_gate`, run in parallel (`python -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup`). This is true CI parity, so it is slower (~1-4 min) than a unit-only run; that cost is intentional to avoid CI false-greens.

   For uncommitted worker handoff checks, add `--allow-dirty` only to inspect deterministic gates before the foreman commit. The authoritative carrier and diff gates validate committed `base..HEAD` state.

5. Fix every failed per-check line until the final summary is `PASS: PR preflight`.

6. Hand off the branch evidence to the foreman/controller. Do not self-merge.
