# BRIEF — ce-446-base-resolve-robust — governance workflow: robust moved-base comparison-base resolution (ce-ops#446)

Role: implementer (dev-1, self-push). Branch: `ce-446-base-resolve-robust` off freshly-fetched origin/main.

## Mandate
Read ce-ops#446 directly (you have gh read on creator-engine/ce-ops). The "Validate governance
artifacts" workflow's "Resolve live comparison base" step crashes with object-traversal errors
whenever a PR's recorded base has moved behind origin/main (observed on PR #789 run 28717576182:
`fatal: Failed to traverse parents` / `remote did not send all necessary objects`). The daemon
does not retry infra failures, so the PR silently stalls (~1h cost on #789).

## Semantic novelty check FIRST
On your fresh origin/main, verify the step still has the fragile local-traversal fallback. If it
has already been hardened (server-side merge-base or bounded deepen present), signal
`BLOCKED ce-446-base-resolve-robust already-resolved` and stop.

## Deliverable
Harden the fallback so a moved base never produces an object-traversal failure:
- PREFERRED: resolve the merge-base server-side via the GitHub compare API
  (`GET /repos/{owner}/{repo}/compare/{base}...{head}` → merge_base_commit.sha) — eliminates the
  local ancestor-graph requirement entirely; fetch exactly the resolved SHA afterward if needed.
- Keep (or add) a bounded `git fetch --deepen=<N>` retry (N doubling to a cap) ONLY as a fallback
  if you judge the API path insufficient in some case — justify in the PR body if you keep both.
- On genuine infra failure the step must fail with a message that clearly distinguishes
  infrastructure-vs-content failure (so a human/daemon knows re-run is the remedy).
- The workflow-permissions audit gate is live: use the default GITHUB_TOKEN with existing
  permissions; do NOT add write scopes.

## Constraints
- Files (closed set): the workflow file under .github/workflows/ containing the step + any helper
  script it already invokes + .ce/changelog/ce-446-base-resolve-robust.md +
  .ce/pr-manifests/ce-446-base-resolve-robust.md. NOTHING else (esp. not validators/, deploy/).
  Anything else needed → BLOCKED signal, don't widen.
- ⛔ Signed-artifact stop-line: any gate failure on a signed artifact (SSHSIG/SHA256SUMS/
  content_sha256) → STOP and report the bytes; never sign; ce-root-v1 is controller-only.

## Preflight (standing ce-ops#303)
FULL `ce validate-pr` GREEN in ONE pass before push. Work class: minimal compliant
(tiny|story|feature|epic). Changelog required; carrier via carrier_gen API
`write_carriers(base=<merge-base vs origin/main>)`, stem == branch name.

## Deliver
Self-push PR titled `ce-ops#446: robust moved-base comparison-base resolution in governance
workflow`; body: exactly one `- **Declared work class:** <class>` line, a `Closes
creator-engine/ce-ops#446` line, and a short before/after of the failure mode.

## Stop line
No review, no approve, no merge, no enqueue. Report PR URL.
