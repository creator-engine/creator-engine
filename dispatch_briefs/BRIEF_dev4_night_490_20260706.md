# BRIEF — dev-4 NIGHT addition — 2026-07-06 ~17:3xZ — U3 (queue AFTER batch5 U1/U2)

## U3 — ce-ops#490: contained-default launch lane plan-time validation — branch `ce-490-launch-plan-time-validation`
Commit-only, signal READY|BLOCKED-ENV <branch> <sha> <evidence>. Base FRESH origin/main.
Ticket embedded (you cannot read ce-ops):
SYMPTOM: `ce launch` (contained default) on a fresh 0.3.3 tenant refuses
G6-LAUNCH-RUNTIME-POLICY-REFUSED ("no launch-owned runtime probe pid") — fail-closed is CORRECT
but all three root causes are invisible; two exist in EVERY fresh onboarded repo:
(a) onboard emits runtime-policy.yaml with a placeholder all-zeros image digest (runtime_posture
    leg HELD per ce-ops#71) — passes form validation, only fails at container start;
(b) policy unconditionally bind-mounts ~/.config/claude (+3 dotfile dirs) — docker hard-fails
    rc=125 pre-create when any source dir is absent on the host;
(c) container command = sentinel wrapper at a HOST path under repo root, not in the mount
    manifest unless repo lives under the onboarded workspace_root — exec fails even after a+b.
Plus: the launcher's 2s probe swallows docker stderr — diagnosing (b) required manual argv
reconstruction via translate_to_docker_plan. Evidence: /var/tmp/ce-canary-c3/stage4_launch_smoke/
(controller host): leg3b_real_launch.json, leg5c_argv_reconstruction.txt, manual_probe_stderr.txt.
BUILD (plan-time refusal slice — refusal-that-teaches pattern, mirror today's takeover refusal):
1. PLAN-TIME validation in the contained-launch path, each with a NAMED refusal BEFORE spawn:
   - placeholder/all-zeros digest → refuse naming the digest + the fix (pin real digest /
     rerun the runtime_posture leg);
   - each bind-mount source checked for existence → refuse naming the missing path;
   - container command path checked against the mount manifest → refuse naming the uncovered path.
2. Surface docker stderr: when the spawn fails anyway, the refusal carries the captured docker
   stderr verbatim (bounded), never just "no probe pid".
3. Failure-direction tests per cause: crafted policy with zero-digest → named refusal pre-spawn;
   absent dotfile dir → named refusal; repo outside workspace_root → named refusal; real docker
   failure → stderr present in the refusal output. The existing fail-closed behavior must be
   PRESERVED (no weakening — these ADD earlier, clearer refusals).
Do NOT touch the onboard placeholder-digest emission itself (that is ce-ops#71 territory) —
this slice makes the launch side diagnose and teach. Work class: story.
