# Claude Code Hook-Pack (CC-G-C)

The committed Claude Code hook-pack is the **Ring 1** layer of the three-ring
governance model in
[`CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`](CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md)
(§8). It consists of:

- `.claude/settings.json` — registers the hooks (PreToolUse for
  `Edit|Write|MultiEdit|Read|Bash`, plus an advisory Stop hook);
- `.claude/hooks/ce-hook-common.sh` — shared root-resolution + validator
  invocation helpers (POSIX sh);
- `.claude/hooks/ce-pretooluse.sh` — the PreToolUse wrapper;
- `.claude/hooks/ce-stop.sh` — the advisory/observability-only Stop wrapper.

The hooks are thin wrappers. All decision logic lives in **Ring 2**, the
`creator_engine_validator hook-check` bridge (CC-G-B), which the hooks call
in-band so that real-time enforcement and post-hoc verification share one
source of scope / mechanics / secret / posture truth. CC-G-C adds only an
*additive presentation seam* on top of CC-G-B — `hook-check --format claude`
and `HookDecision.to_claude_hook_dict()` — and changes **no** CC-G-B decision
semantics.

## Ring 1 is RUNTIME (launch-pinned) and DEFEASIBLE — not HARD

This hook-pack is **RUNTIME (launch-pinned) enforcement: in-band and
defeasible.** It is strong while it runs, but it is *not* a hard, non-overridable
boundary. It can be bypassed by any of:

- `--bare` (skips hooks, plugin sync, auto-memory, `CLAUDE.md` discovery);
- `settings.local.json` or `--setting-sources` excluding `project`;
- `disableAllHooks`;
- launching outside the governed `ce` launcher entirely.

It must therefore **never** be described as HARD or non-overridable on its own.
The HARD repo-native floor is **Ring 0** — the `ce launch` / `ce lane launch`
kernel (CC-G-D, not yet built). The optional non-defeasible host lock is
managed settings (a v1.1 FUTURE SEAM). If any later artifact claims the
committed hook-pack is non-overridable without managed settings, that is a
defect to halt and correct (seat contract §8).

## Fail-open is intentional Ring 1 behavior

The hooks **fail open** by contract. On a missing or broken validator, an
unresolvable validator interpreter, or malformed hook input, the PreToolUse
wrapper prints no blocking decision and exits 0; the session is never blocked
by a broken Ring 1.

This is deliberate. A defeasible, in-band runtime gate that hard-failed the
session on its own breakage would be both unsafe (easy self-inflicted denial of
service) and dishonest about its strength. The cost is real: if the validator
cannot run, Ring 1 enforces nothing. Two consequences follow, both resolved at
Ring 0:

1. **Validator reachability is a launch precondition, not a hook concern.** The
   wrapper invokes the validator with a fixed fallback order —
   `creator-engine-validator` console script, else `python3 -m
   creator_engine_validator`, else `python -m …`, with
   `PYTHONPATH=<repo>/validators`. Whether the resolved interpreter actually has
   the validator and its dependencies (`pyyaml`, `jsonschema`) installed is an
   environment property. A governed launch (Ring 0) must guarantee a
   deps-complete validator entrypoint on `PATH`; an ad-hoc shell where bare
   `python3` lacks those dependencies will silently fail open.
2. **Ring 0 is the catch.** The HARD floor confirms the pack is loaded and the
   validator is reachable *before* relying on it — see below.

The wrapper resolves the validator relative to the committed repo that ships
the hooks (`CE_HOOK_REPO_ROOT`, default = the script's `../..`), while the
governed *posture root* it evaluates is `CLAUDE_PROJECT_DIR` (fallback: the hook
repo). In a normal worktree launch these coincide.

## Stop hook is advisory / observability-only in CC-G-C (D2)

The CC-G-C Stop hook **must not block** and **must not parse the transcript**
for closeout text. It drains the Stop event and records a best-effort,
non-blocking advisory observation under the ignored `.hermes/` evidence root
(`.hermes/cc-g-c-hook-observations/observations.ndjson`). It emits no
`{"decision":"block"}`.

Hard Stop blocking — verifying the canonical closeout terminal sections and a
referenced completion report — depends on **deterministic pointers that only
Ring 0 can inject** (the closeout text location and a `completion_report_ref`).
Inferring them from the transcript in-band would be both unreliable and a
boundary violation. The Ring 2 bridge already implements the Stop block logic;
CC-G-C simply does not arm it. CC-G-D will inject the pointers and arm it.

## CC-G-D (Ring 0) dependencies — satisfied by CC-G-D

The committed hook-pack is defense-in-depth *inside* the lane and remains
**RUNTIME (launch-pinned), DEFEASIBLE** — CC-G-D does **not** make it HARD or
non-overridable. What CC-G-D builds is the **HARD Ring 0 launch/accept refusal**
that runs *before Claude starts*, in the kernel (`ce launch` / `ce lane launch`).
The following Ring 0 responsibilities are now implemented (HARD; refused before
any side effect), not provided by Ring 1:

- **[satisfied]** pin `--setting-sources project` so `settings.local.json` cannot
  weaken the posture, and refuse a `--setting-sources` that omits `project` or
  includes `local` (`CC-D-5`) — `claude_launch_spec.build_governed_claude_command`
  + `evaluate_claude_launch`;
- **[satisfied]** refuse `--bare` (`CC-D-1`);
- **[satisfied]** refuse `-p` / `--print` headless mode for governed authoring
  lanes (`CC-D-2`);
- **[satisfied]** refuse background `agents` sessions / `--agents` (`CC-D-3`) and
  `--remote-control` / `remoteControlAtStartup` (`CC-D-4`);
- **[satisfied]** **confirm the hook-pack is present/parseable/registered and the
  validator is reachable before permitting `--dangerously-skip-permissions`**
  (`CC-D-6`) — `hook_pack_confirm.confirm_hook_pack`; skip-permissions is safe
  only once the pack is confirmed active;
- **[satisfied]** constrain MCP to a CE-owned config with `--strict-mcp-config`
  and refuse uncontrolled/global MCP inheritance (`CC-D-7`); CC-G-D launches no
  MCP server (config-posture only);
- **[reused]** bind the live, visible tmux pane to an Active-Work claim and Pane
  Registry record (§7 governed-posture predicate, `PCO-049`/`PCO-050`) — the
  shipped `lane_runtime.launch` binding, unchanged;
- **[satisfied — Ring 0 facts only]** inject the deterministic closeout /
  completion-report pointers and verify them via the Ring 2 Stop logic
  (`lane_runtime.verify_closeout`). This supplies the facts that *would* arm hard
  Stop blocking but **does not arm it**: the committed advisory Stop hook
  `.claude/hooks/ce-stop.sh` is unchanged. Arming hard Stop blocking is a separate
  follow-on gate (CC-G-E / a ratified CC-G-D Slice 2);
- **[deferred]** mint and verify the future explicit side-effect authority token
  that opens the restricted-mechanics seam (until then, restricted mechanics are
  denied under governed posture with no authority present).

Code: `validators/creator_engine_validator/{claude_launch_spec,hook_pack_confirm}.py`,
wired into `launch_runtime.launch` (`ce launch`, code `G6-LAUNCH-CLAUDE-REFUSED`)
and `lane_runtime.launch` (`ce lane launch`, code `G3-CLAUDE-REFUSED`).

## Decision shapes emitted to Claude

`ce-pretooluse.sh` calls `hook-check --stdin --format claude --posture-root
"$ROOT" --evidence-root .hermes` and passes the Claude-hook-shaped JSON through
verbatim:

- **PreToolUse deny** (governed scope/secret/mechanics violation):
  `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}`
- **PreToolUse allow**: same shape with `permissionDecision: "allow"`.
- **Ungoverned advisory**: maps to `permissionDecision: "allow"` (an ungoverned
  lane is never hard-denied) with the advisory context preserved in the reason.
- `--evidence-root .hermes` keeps ignored instance-evidence writes from being
  denied under governed posture (D3).
- **`--ledger-root` (Gate B, posture-claim reachability):** a governed lane
  launched via `ce lane launch` exports its absolute Active-Work Ledger root as
  `CE_LEDGER_ROOT`; `ce-pretooluse.sh` forwards it as `--ledger-root` so the §7
  posture is resolved from the seat's **real** claim — reachable even from a
  worktree that carries no local ledger. When unset, discovery is scoped to
  `<posture-root>/.hermes/active-work-ledger`, never the whole posture-root tree,
  so tracked `examples/**` claim/pane fixtures can never be matched as governing
  claims. Mirrors the `--reviewer-authority-ref` launch-pinned seam.

The Stop bridge shape (`{"decision":"block","reason":"…"}`) exists in Ring 2 but
is **not** emitted by the CC-G-C Stop hook (advisory-only, D2).
