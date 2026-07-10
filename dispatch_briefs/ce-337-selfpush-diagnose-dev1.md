# SEED BRIEF — ce-ops#337: dev-3 contained self-push broken — diagnose live + smoke canary — SEAT: dev-1

**Context:** The contained seat dev-3 (container `ce-vps-codex` on THIS VPS) completes work but
cannot self-push: `gh auth status` = not logged in, `git push` falls back to plain HTTPS →
"could not read Username for 'https://github.com': terminal prompts disabled". The entire
self-push spine is already BUILT and deployed (transport-deputy injected credential, egress
self-push broker daemon + vault signer AppRole login, VPS launcher socket mount, SO_PEERCRED
socket-origin attestation, systemd socket-activation for broker restart-staleness). Yet the live
container doesn't engage it. Likely: (a) broker daemon/socket down or stale on this seat
(ECONNREFUSED — the old restart-staleness mode recurring), (b) launcher mount / git remote-helper
routing absent in the container's actual launch, or (c) seat git/gh flow never pointed at the broker.

**Task:**
1. DIAGNOSE on this host: broker service liveness (systemd unit state, socket inode inside vs
   outside the container), whether the container has the broker socket mounted, and how the seat's
   git push is routed (git config, remote-helper, credential helper inside `ce-vps-codex` — read-only
   probes only, do NOT restart the seat).
2. REPO-SIDE FIX for whatever you find that is fixable in-repo (launcher mount wiring, remote-helper
   config baked into the seat image/launch, etc.).
3. Add a **self-push smoke canary**: a script/check that proves a contained seat can push a no-op
   ref end-to-end, failing LOUDLY — so trapped work never goes silent again.

**Stop line:** if the root cause needs host root actions you can't perform, or a container relaunch,
STOP after the diagnosis + repo-side fix and report exactly what privileged step remains.

**Branch:** `ce-337-selfpush-canary` (off `origin/main`). **Role:** implementer. **Work class:** by floor (likely S/M).
**Repo:** creator-engine/creator-engine. Non-contained: self-push + open PR (body needs exactly one
`- **Declared work class:** <tiny|story|feature|epic>` line). `Refs ce-ops#337` in the body.
**Obligations:** `.ce/changelog/ce-337-selfpush-canary.md` fragment + `.ce/pr-manifests/ce-337-selfpush-canary.md`
carrier matching base..HEAD (slug == branch). Run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before self-push; do not discover gates via CI. Commit and echo the SHA. Report your
diagnosis findings in the PR body — the diagnosis is a first-class deliverable even if the fix is partial.
