# DISPATCH — ce-ops#377: per-arch base-image digests — dev-1

LANE: `surfaces/manifest.yaml` pins ONE digest per base image, but the fleet builds TWO arches (VPS=amd64, DGX=aarch64). A single amd64 digest silently broke DGX builds (`exec format error`). Make base-image digests per-arch + guard it. Self-contained code lane; disjoint from in-flight work (L7=.github/workflows, N1d=install.sh).

WORKTREE off origin/main (you self-push). Branch **ce-377-per-arch-base-digests**. Run `ce validate-pr` GREEN. You MAY push + open the PR as your own identity; do NOT merge (controller gates).

## Known-correct digests (from the issue)
- `debian:bookworm-slim`: amd64 `sha256:1def178…` (current), arm64 `sha256:60eac759…`
- `rust:1-bookworm`: amd64 `sha256:c993d32d…` (current), arm64 `sha256:05f85ef6…`
(Resolve the FULL digests yourself via `docker buildx imagetools inspect <tag>` or the registry; the issue gives prefixes. Pin the real full sha256 for each arch.)

## Asks (implement 1–3; #4 needs DGX → defer to dev-4, note it)
1. **Schema**: base-image surfaces in `surfaces/manifest.yaml` carry per-arch digests, e.g. `commit_or_digest: {amd64: sha256:…, arm64: sha256:…}` (keep backward-compat for single-digest non-base surfaces — don't break other surface types). Update `surfaces/render.py` so it emits the digest matching the build-target arch (derive arch from the Dockerfile/build context or an explicit arch param).
2. **Guard/test**: extend the `surfaces_manifest` check (find it under validators/creator_engine_validator/checks/ or surfaces/) so a base image used by BOTH the VPS (amd64) and DGX (aarch64) Dockerfiles MUST declare both arch digests — fail CI if an arch is missing. Add a unit test.
3. Update any Dockerfile/render call sites that consume the base-image digest to pass/select the target arch.
4. (DEFER) Reconcile the live DGX `codex-runsc` image (built off-manifest arm64) back onto the manifest — needs DGX; note as a follow-up for dev-4.

## Evidence
- `surfaces_manifest` (or equivalent) check passes with per-arch coverage; new test proves single-arch-for-dual-arch-base FAILS.
- `ce validate-pr` GREEN. Carrier+changelog (carrier_gen.write_carriers, head_ref=ce-377-per-arch-base-digests, issue=ce-ops#377, kind=fix, scope=surfaces) + `- **Declared work class:** story` in the carrier.
- ⚠️ Verify against origin/main; do NOT base on ce-release-0.3.1-rc2.
Report: branch, commit SHA, PR # (if opened), validate-pr PASS line.
