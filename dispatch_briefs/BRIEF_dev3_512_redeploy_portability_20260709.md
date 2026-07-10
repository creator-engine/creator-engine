# BRIEF — dev-3 — 2026-07-09 — P1: singleton-redeploy host-portability fixes (STRANGELOOP-1 pool)

Role: **implementer**. Contained COMMIT-ONLY seat (controller harvests — self-push infra is down).
Fresh worktree /var/tmp/wt-512-portability off origin/main (fetch first). Branch
`ce-512-redeploy-portability`. Declared work class: **story**.
Signal: `READY ce-512-redeploy-portability <sha> .ce/pr-manifests/ce-512-redeploy-portability.md`
or `BLOCKED ce-512-redeploy-portability <reason>`.
NO .ce/brain/assertions.yaml edits. FULL `ce validate-pr` before READY.

## U1 — deploy/singleton-redeploy + deploy/queue-daemon portability (work class: story)

CONTEXT (from the 2026-07-08 first real deployment of this surface, DGX gate-outage recovery —
all four gaps required manual workarounds):
(a) `deploy/queue-daemon/ce-queue-daemon.service` hardcodes `User=ce-dev-1`;
    `redeploy-singleton.sh` renders paths but NOT the user → DGX needed a hand-written drop-in.
(b) `validate_repo_root()` requires `.git` to be a DIRECTORY → rejects git worktrees (the DGX
    deployment base was a linked worktree; had to be converted to a standalone clone).
(c) The post-deploy health probe sources ONLY the env file → misses vars pinned via unit
    `Environment=` (BAO_ADDR) and needs BAO_CACERT; both had to be duplicated into the env file.
(d) `deploy/queue-daemon/RELOCATION.md` is written for the VPS cutover only.

FIXES (all four, one branch):
1. Render the unit user: `redeploy-singleton.sh` gains `--service-user NAME` (default: current
   `id -un` at deploy time) and renders `User=` in the unit the same way it renders paths.
2. `validate_repo_root`: accept a `.git` FILE (worktree) as valid — or if worktrees are genuinely
   unsupported by the ro-mount model, `die` with an explicit "linked worktrees unsupported —
   clone standalone" message instead of the misleading "does not look like a git checkout".
   Ground your choice in how run-daemon-container.sh mounts the checkout; state it in the PR body.
3. Health probe env parity: probe composes env from BOTH the env file AND the unit's pinned
   `Environment=` values (parse the rendered unit, or accept a documented `--probe-env` extension);
   BAO_CACERT handling documented.
4. RELOCATION.md: host-agnostic rewrite (parameterized user/paths; DGX + VPS examples; state-root
   override via drop-in documented; env file template gains BAO_ADDR + BAO_CACERT keys).
Tests: extend validators/tests/unit/test_* coverage for redeploy-singleton rendering (there is an
existing smoke-singleton-redeploy.sh — keep it green; add unit coverage for the sed/render logic
if a test harness for it exists, else the smoke script must exercise --service-user).
Carrier + changelog fragment. Public lens: no internal hostnames beyond generic examples
(use placeholders like <deploy-host>, not machine names).
