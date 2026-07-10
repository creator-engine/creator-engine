# BRIEF — ce-s1b-seat-image — canonical seat image with coding agents baked in (PARALLEL UNIT, dev-1)

Role: implementer (dev-1, self-push, foreman mode). PARALLEL thread — file-disjoint from your
#414/#417 docs units; run it concurrently in its own worktree. Branch `ce-s1b-seat-image` off
freshly-fetched origin/main.

## Why (Operator-ratified day-arc)
Tenant `ce launch` must start the coding agent CONTAINED. The canonical runtime image
(deploy/runtime-image, published to ghcr as ce-runtime, manifest-list digest pins per its README)
deliberately contains NO coding agent; the fleet's gvisor path bind-mounts a host codex binary —
wrong for tenants. Ratified design: agents BAKED into a derived seat image; tenant auth/config
travels only via explicitly enumerated mounts (that part is another unit's job).

## Deliverable: `deploy/seat-image/`
1. `deploy/seat-image/Dockerfile`: `FROM` the digest-pinned ce-runtime image per
   deploy/runtime-image/README.md's consumption contract (ARG CE_CANONICAL_RUNTIME_IMAGE,
   manifest-LIST digest only — never a child arch digest; the README documents the exec-format
   footgun). Layer in BOTH agent CLIs, version-pinned: codex CLI and claude-code CLI, installed
   the way our existing seat Dockerfiles do (consult deploy/dgx-runsc/Dockerfile +
   deploy/vps-runsc/Dockerfile for the proven install patterns — reuse, don't reinvent; but NO
   herdr, NO broker, NO runsc toolchain — those are fleet-specific, not tenant surface).
   Non-root `ce` user preserved; agents runnable by uid 10001.
2. `deploy/seat-image/README.md`: consumption contract (what it is, digest-pin rule, what is
   deliberately NOT inside: no credentials, no herdr, auth arrives via mounts), product lens,
   ZERO ce-ops references.
3. Publish workflow: extend .github/workflows/publish-runtime-image.yml or add
   publish-seat-image.yml (mirror its structure: workflow_dispatch version input + release tags,
   multi-arch buildx amd64+arm64, pushes ghcr.io/creator-engine/creator-engine/ce-seat:<version>,
   surfaces the manifest-list digest in the step summary).
4. surfaces/manifest.yaml: add the seat image entry following the existing image-pin conventions
   (look at how ce-runtime/base pins are recorded; keep UNSET-until-published digest convention if
   that is the pattern).
5. Tests: static Dockerfile-content assertions in validators/tests/unit/ (mirror
   test_runtime_image.py style): FROM-arg digest-pin discipline, both agent installs present +
   version-pinned, no herdr/broker/runsc artifacts, workflow file sanity if cheaply assertable.

SEMANTIC NOVELTY CHECK FIRST: confirm no deploy/seat-image (or equivalent tenant seat image)
exists on fresh main; if one does, signal BLOCKED already-resolved with evidence.

## STOP lines
- ⛔ Do NOT modify deploy/runtime-image/, deploy/dgx-runsc/, deploy/vps-runsc/ (read them, reuse
  patterns, change nothing there).
- ⛔ Do NOT publish/push any image and do NOT run the workflow — publish is a controller act.
- ⛔ Do NOT touch docs/install.sh or docs/downloads/**. Never sign anything.
- ⛔ No review/approve/merge/enqueue.

## Evidence bar
Full `ce validate-pr` GREEN one pass before push. Changelog + carrier. Declared work class: story.
Local `docker build` proof NOT required (builder may lack base digest access) — static tests are
the bar; say in the PR body whether you build-verified locally or not.
Report: `READY ce-s1b-seat-image <40-hex sha> PR=<url>`.
