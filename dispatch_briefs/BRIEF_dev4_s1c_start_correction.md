# CORRECTION — dev-4 — s1c START CONDITION SATISFIED (controller-verified)

1. **Unit 5 (s1c) starts NOW.** Your poll greps origin/main for branch-name tokens
   (`ce-s1a-docker-runner-backend` / `s1a.*docker.*runner`), but merge commits carry the PR
   TITLE, which contains none of those tokens. The s1a work IS merged:
   `635e1424c9a15aac7b8c16e40380e7a02f32beaf` — "runner: plain-Docker backend for tenant
   contained launch (ce-ops#447 unit A) (#809)". `git fetch origin && git show --stat 635e1424`
   to confirm (you will see runner/docker_backend.py etc.). Treat the start condition as MET and
   begin Unit 5 per BRIEF_ce_s1c_launch_default_policy.md unchanged. Unit 6 stays queued behind it.
   Lesson for your future polls: match merge-commit TITLES (or `git log --grep '#<PR>'`), not
   branch slugs.

2. **didyoumean tiny is SHIPPED.** Merged to main as #812 (`fa7d7c68`). Do not re-signal, do not
   rebase that branch again; delete the local branch when convenient.

3. **Fresh canary intel for s1c design** (from today's credentialed brownfield canary on live
   0.3.1): a real `ce launch --backend gvisor --runtime-policy ...` on a tenant box refuses
   FAIL-CLOSED pre-container with `G6-LAUNCH-RUNTIME-POLICY-REFUSED ... no allowlist enforcement
   primitive is proven` — it does NOT silently fall back to os-native. Your fail-closed default
   (D-i) must compose with that existing G6 refusal seam, not duplicate or shadow it; check
   whether part of the S1 surface is already covered by G6 before writing new refusal paths.

Standing preflight directive unchanged: full local validator preflight green in one pass before
commit-for-harvest. Signal shape unchanged.
