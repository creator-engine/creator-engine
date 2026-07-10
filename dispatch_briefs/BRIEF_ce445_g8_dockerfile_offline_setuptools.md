# BRIEF — ce-445-g8 — make canonical-image Dockerfiles buildable on clean pull (offline setuptools)

Role: implementer (dev-4, contained). Branch: `ce-445-g8-dockerfile-offline-setuptools` off
freshly-fetched origin/main. Worktree under /var/tmp. venv: `.venv/bin/python -m pytest`.

## Problem (controller-verified during the C1 image build, 2026-07-04 — full context embedded)
deploy/runtime-image/Dockerfile (canonical, from #781) and deploy/oci/Dockerfile both run
`python -m pip wheel --no-deps --no-build-isolation --wheel-dir /out /src/validators` in their
wheel-builder stage. validators/pyproject.toml declares build-backend setuptools.build_meta, but
the base python:3.14-slim-bookworm ships WITHOUT setuptools and --no-build-isolation prevents pip
from fetching it → both Dockerfiles are unbuildable on a clean pull, and the
.github/workflows/publish-runtime-image.yml workflow would fail if triggered. A local build
succeeded only via a workaround Dockerfile.

## Deliverable (Option A — offline-safe, preserves hermetic build)
In BOTH Dockerfiles' wheel-builder stage, BEFORE the `pip wheel` RUN:
1. `COPY validators/wheelhouse-dev /opt/build-tools` (the setuptools-82.0.1-py3-none-any.whl is
   already tracked there — verify the exact filename in your worktree).
2. `RUN python -m pip install --no-index --find-links=/opt/build-tools setuptools`
Keep --no-build-isolation and --no-deps exactly as-is. Do not change base image digests, ARGs,
labels, or any other stage. If the two Dockerfiles' wheel-builder stages differ structurally,
adapt minimally per file and note the difference in the changelog.

## Verification (behavioral — you cannot run docker in the container; verify by construction + tests)
- Confirm the wheelhouse-dev wheel exists and covers setuptools' own deps (it's a py3-none-any
  single wheel; pip install with --no-index must resolve from /opt/build-tools alone — if
  setuptools needs `wheel` too, check wheelhouse-dev for it and include it in the install list;
  report if something required is missing rather than adding new tracked binaries).
- If any CI test asserts Dockerfile content (grep validators/tests for 'Dockerfile', 'runtime-image',
  'wheel-builder'), update assertions consistently.
- Full `ce validate-pr` GREEN one pass. (The controller will rebuild the image from your branch on
  the host as post-merge verification.)

## Constraints
- Files (closed set): deploy/runtime-image/Dockerfile · deploy/oci/Dockerfile · any test file that
  directly asserts those Dockerfiles' content (name it in the carrier) · .ce/changelog/ce-445-g8-dockerfile-offline-setuptools.md ·
  .ce/pr-manifests/ce-445-g8-dockerfile-offline-setuptools.md. Nothing else — no workflow edits,
  no wheelhouse additions without reporting first.
- ⛔ Signed-artifact stop-line: signature-gate failure → STOP + report bytes; never sign.
- Work class: tiny (bump minimally only if the sizing floor demands).

## Evidence + signal (no push auth — controller harvests)
Commit `deploy: offline setuptools in canonical-image wheel-builder stages`, emit:
`READY-FOR-HARVEST ce-445-g8-dockerfile-offline-setuptools <40-hex sha>`.

## Stop line
No push/PR/review/signing. Controller harvests on signal.
