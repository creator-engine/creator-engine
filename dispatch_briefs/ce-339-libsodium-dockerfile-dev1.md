# SEED BRIEF — ce-ops#339: add system libsodium to DGX seat image — SEAT: dev-1

**Context:** The dev-4 container (ce-dgx-codex) has no SYSTEM libsodium (only pynacl's
bundled copy); `ldconfig -p | grep sodium` = 0, no `libsodium` apt package. This makes the
`check-examples` gate fail on unrelated fixtures inside contained seats, blocking clean
auto-gating. Fix: install system libsodium in the DGX seat image so the gate passes.
(The image rebuild + relaunch is a separate controller step — this PR just fixes the Dockerfile.)

**Branch:** `ce-339-libsodium-dockerfile` (off `origin/main`). **Role:** implementer. **Work class:** by floor (likely XS).
**Repo:** creator-engine/creator-engine. Non-contained: self-push + open PR.

## Goal
In `deploy/dgx-runsc/Dockerfile`, add `libsodium23` (the Debian/Ubuntu runtime package;
use `libsodium-dev` only if a header is actually needed — prefer the runtime lib) to the
apt-get install list (there are two apt install blocks — add it to the one that installs
runtime libs for the seat environment; match the existing `--no-install-recommends` style
and alphabetical/logical ordering). Verify the package name is correct for the base image's
distro (check the FROM line's distro). Do NOT change anything else in the Dockerfile.

## Scope — exactly these
- `deploy/dgx-runsc/Dockerfile`
- `.ce/pr-manifests/ce-339-libsodium-dockerfile.md` + `.ce/changelog/ce-339-libsodium-dockerfile.md`
Infra/config diff → if the test-coupling gate fires, use `CE-TEST-COUPLING-EXEMPT` in the PR body (legitimate — Dockerfile only, no testable app logic).

## Evidence / DoD
- FULL `ce validate-pr` GREEN one pass (TMPDIR=/var/tmp PYTHONPATH=validators; brain-drift reconcile if false-RED: `git show origin/main:.ce/brain/assertions.yaml > .ce/state/brain/assertions.yaml`).
- Note in the PR body that the image rebuild + dev-4 relaunch is a follow-on controller step (this PR only lands the Dockerfile change).
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; push; open PR w/ declared-work-class line. Do NOT approve/merge.
