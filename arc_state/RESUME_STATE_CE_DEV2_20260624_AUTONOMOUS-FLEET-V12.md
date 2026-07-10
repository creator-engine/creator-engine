# RESUME STATE — CE-DEV-2 · 2026-06-24 · 🏭 PHASE-1 HERDR WAVE-A LANDED → WAVE-B NEXT · V12

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V11.** READ THIS + MEMORY.md FIRST. Discipline: **verify-don't-trust** every seat "done"/CI-green/SHA; **inline-only seat dispatch**; **codify don't rediscover**.

## 🟢 HEADLINE: #227 de-risked to ALL-IN-REPO; two PRs landing; Wave-B staged
- **herdr-ce probe (DONE):** #227 criteria 4 (keystroke-commit) + 6 (sha256 delivery) are **CE-Python-only — NO Rust PR**. herdr binary already has `pane send-keys <id> Enter` (encodes `\r`, commits) and `pane read` (read-back). `send-text` deliberately does NOT commit (= the b′ bug). Memory [[herdr-cli-commit-and-readback]]. The whole #227 DoD is now this-repo work in 2 dev-4 waves.

## ✅ THIS SESSION — built→verified→PR'd→latched (Phase-1 pre-authorized, ce-dev-2 reviews dev-authored)
- **#416** (#219 codex PreToolUse redact) — **MERGED** `953fb98` (= main tip).
- **#419** Wave-A (`ce227-wave-a`): register Ring-1 `[[hooks.PreToolUse]]` in generated contained-codex config (BOTH runsc launchers) + crit1/2/3 test-hardening. dev-4 built `5f41286`; 44/44 unit pass host-side; carriers fixed → head `bc8e9ff0`; ce-dev-2 approved + **auto-merge latched**. Crit-5 mirrors `.codex/requirements.toml` managed-hooks pattern (allow_managed_hooks_only + inline hook + matcher), container-abs path + PYTHONPATH. ⚠️ per-call BLOCK proof = #227 canary, not unit tests.
- **#420** #229 (`ce229-live-action-scope-guard`): new SHARED `pickup_search.py` chokepoint — every live-action GH query MUST pass explicit `scope=` or fail closed. dev-3 built `444d150`; 71/71 + 17/17 version-boundary pass; carriers fixed → head `ec2c4795`; ce-dev-2 approved + **auto-merge latched**.
- ⚠️ BOTH carrier gates FAILED first time (missing changelog row in manifest) → FIXED. New memory [[ce-carrier-verify-require-carrier-gap]]: verify with `--require-carrier`; run gen-manifest AFTER carriers committed; obey STALE-REF TRAP. **fresh-me: confirm #419+#420 went green & merged** (`gh pr view 419/420`); main should advance past `953fb98`.

## 🚀 IMMEDIATE NEXT (fresh-me, in order)
1. **Confirm #419 + #420 merged.** When **#419 merges → fire Wave-B on dev-4** (brief STAGED at `/home/cedev2/creator-engine/tmp/brief-dev4-227wave-b.md`): crit4 (`herdr_session.py send` → add `send-keys Enter` + port `v3_seat_bridge.py:773-808` submit cadence) + crit6 (sha256 verify-after-render via `pane read`, marker-line approach). Sequential on dev-4 (one-instance-per-worktree). Dispatch = same pipeline below.
2. **#227 CANARY probe** (the real DoD): relaunch a seat via canonical `ce launch` with the new config, attempt a denied tool call → confirm BLOCKED per-call + logged (proves crit5). This is criterion 5's only true proof.
3. **#228 design** (cred-injection/OneCLI) — convergence pin; now ALSO absorbs #222's remaining EGRESS-ENFORCEMENT scope (#222 attestation already merged via #397/#402; issue stays open for actual egress confinement). Run as a worker/design pass.
4. **#174** (path-manifest stale-base-SHA after rebase→force-push) re-queued → give to a contained seat (dev-3 after #229, or dev-4 after waves). NOT dev-1.

## 🖥️ FLEET (verify before dispatch)
- **dev-4** (DGX, contained `ce-dgx-codex`): repo IN-CONTAINER `/workspace/creator-engine` = HOST bind-mount `/home/cedev4/ce-workspaces/creator-engine`; CODEX_HOME `/home/cedev4/.codex`; has git network. #227 long-pole builder, clean for Wave-B.
- **dev-3** (VPS, contained `ce-vps-codex`): in-container `/workspace/creator-engine` = HOST `/home/ce-dev-3/creator-engine`; CODEX_HOME `/home/ce-dev-3/.codex`. Built #229. Phase-1 canary subject.
- **dev-1** (VPS, NON-contained tmux codex `ce-dev1-orchestrator:2.0`): sole credentialed reviewer, **THIN ~23% ctx → reserve as reviewer, do NOT load build work**. Compacts and drops directives ([[ce-codex-foreman-directive-durable]]). #222 was a false alarm (stale narration; already merged).
- Tokens: `~/.ce-keys/ce-dev-2.pat` (my reviewer id), overwatch (`set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`). Repo `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`.

## 🛠️ CONTAINED-SEAT DISPATCH PIPELINE (validated this session — reuse verbatim)
1. Write self-contained brief to `tmp/brief-*.md` (contained seats can't read tickets — EMBED everything; end with `BUILT_SHA=<sha>` gate; "do NOT push").
2. Reset container to clean main + branch: `sudo docker exec <ctr> bash -lc 'cd /workspace/creator-engine && git fetch origin main && git checkout -q main && git reset --hard origin/main && git checkout -qB <branch>'` (dev-3 via `ssh dev3 'sudo docker exec ...'`).
3. Deliver brief + **md5-verify**: `cat brief | [ssh dev3] sudo docker exec -i <ctr> tee /tmp/brief.md` then compare md5 both sides.
4. Build (background): `sudo docker exec <ctr> bash -lc 'cd /workspace/creator-engine && CODEX_HOME=<ch> codex exec --dangerously-bypass-approvals-and-sandbox "$(cat /tmp/brief.md)" 2>&1 | tee /tmp/codex-*.log'`.
5. On done: VERIFY commit in container (`git log/diff --stat`, grep BUILT_SHA) — NOT narration.
6. **Model-B push from seat HOST** (NOT container): dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519 'cd ~/ce-workspaces/creator-engine && git push origin <branch>'`; dev-3 `ssh dev3 'cd /home/ce-dev-3/creator-engine && git push origin <branch>'`.
7. Fetch to my repo (STALE-REF TRAP: `git fetch origin 'refs/heads/X:refs/remotes/origin/X' --force`); worktree under `TMPDIR=/home/cedev2/cetmp`; host-side pytest (seats have no venv) w/ `.venv/bin/python`.
8. Carriers: write `.ce/changelog/<slug>.md` → commit code+changelog → `/tmp/gen-manifest.py <slug> <issue> <title>` (AFTER commit!) → commit manifest → **`verify-path-manifest --require-carrier`** (PASS) → push.
9. `gh pr create` (body needs `- **Declared work class:** story` BULLET). ce-dev-2 `--approve` (dev-authored→I review; ce-dev-2-authored→dev-1). `gh pr merge --auto` (NO --squash; queue sets strategy; "already queued to merge" = it's in; autoMergeRequest!=null confirms latch).

## 📌 STANDING (carry from V11)
- Phase-1 merges PRE-AUTHORIZED (verify-green + carrier-pass + independent review). Drive batch-ratified arcs autonomously; ping only for genuine ratification.
- Containment sequencing: workers(dev-3/4)→reviewer(dev-1)→controller(me) LAST; all gated on #228.
- DGX host tests under `TMPDIR=/home/cedev2/cetmp`; host python `/home/cedev2/creator-engine/.venv/bin/python`.
- Open ce-ops: #227(active)/#228/#219(landing via #416)/#229(landing via #420)/#222(enforcement-remaining)/#174/#206/#208/#223(pilot-critical install)/#226/#216.
