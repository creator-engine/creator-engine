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

1. Before every diff, re-derive and record the comparison base. Do this before
   creating the branch and again before each commit-for-harvest or PR-ready
   diff; a previously observed `origin/main` is not evidence for a later diff.

   ```sh
   git fetch --prune origin
   BASE_SHA="$(git rev-parse origin/main)"
   printf 'derived base: %s\n' "$BASE_SHA"
   git switch -c <branch-slug> origin/main
   ```

   The handoff report names this derived base SHA.

2. Make the scoped change and keep the tree focused on the ticket. Stage only
   the named, authorized paths: never use `git add -A`. Before committing,
   record and verify the exact staged set with `git diff --cached --name-only`.

3. Add the PR carriers for the same branch slug:

   - `.ce/changelog/<branch-slug>.md`
   - `.ce/pr-manifests/<branch-slug>.md`

   Derive the slug programmatically by invoking `branch_slug(head_ref)` (or the
   existing `write_carriers` recipe); never hand-predict a carrier slug. That
   canonical invocation owns slash collapse, long-slug truncation with hash
   disambiguation, short-slug hash padding, and future normalization changes.
   Before commit and before PR, report the supplied head ref, the derived slug,
   and the matching carrier filenames. The PR manifest must list the closed
   `origin/main..HEAD` path set, include itself, and include exactly one current
   PR-body work-class line:

   ```md
   - **Declared work class:** <XS|S|M|L>
   ```

   Use only `XS`, `S`, `M`, or `L`. These are CE ceremony tiers, not Agile work
   item types. Before PR, compute and report the diff's floor and the declared
   class. Legacy inputs normalize as `tiny` → `XS`, `story` → `S`, `feature` →
   `M`, and `epic` → `L`; a declared class above the computed floor clears the
   floor, while one below it does not.

   When an edited document is the evidence reference of an active brain
   assertion, identify that pinned document in the carrier result and append its
   same-carrier correction through `ce brain correct`. Pass the predecessor
   `--statement` explicitly, report the predecessor and successor ids, preserved
   statement, and asserted shipped hash, and never edit `claim.sha256` in place.

4. Run the local preflight before push:

   ```sh
   PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr
   ```

   The preflight's default test gate mirrors the CI offline invocation exactly — the whole `validators/tests/` tree (unit + integration), excluding `wheel_bake_gate`, run in parallel (`python -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup`). This is true CI parity, so it is slower (~1-4 min) than a unit-only run; that cost is intentional to avoid CI false-greens.

   For uncommitted worker handoff checks, add `--allow-dirty` only to inspect deterministic gates before the foreman commit. The authoritative carrier and diff gates validate committed `base..HEAD` state.

5. Fix every failed per-check line until the final summary is `PASS: PR preflight`.
   A result is ready for handoff only after a commit exists: report the committed
   `HEAD` and a clean worktree. A clean worktree alone never substitutes for a
   committed head.

6. Hand off the branch evidence to the foreman/controller. Do not self-merge.
