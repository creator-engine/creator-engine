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

## CC-G-D (Ring 0) dependencies

The committed hook-pack is defense-in-depth *inside* the lane. The following
remain the responsibility of the Ring 0 kernel (`ce launch` / `ce lane launch`,
CC-G-D) and are **not** provided by Ring 1:

- pin `--setting-sources project` so `settings.local.json` cannot weaken the
  posture, and verify it;
- refuse `--bare` (defeats the entire enforcement layer);
- refuse `-p` / `--print` headless mode for governed authoring lanes;
- refuse background `agents` sessions and `--remote-control` /
  `remoteControlAtStartup` (invisible/unarchivable, outside the visible-pane
  model);
- **confirm the hook-pack is loaded and the validator is reachable before
  permitting `--dangerously-skip-permissions`** (skip-permissions is safe only
  once the pack is confirmed active);
- bind the live, visible tmux pane to an Active-Work claim and Pane Registry
  record (§7 governed-posture predicate, `PCO-049`/`PCO-050`);
- inject the deterministic closeout / completion-report pointers that arm hard
  Stop blocking (D2);
- mint and verify the future explicit side-effect authority token that opens
  the restricted-mechanics seam (until then, restricted mechanics are denied
  under governed posture with no authority present).

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

The Stop bridge shape (`{"decision":"block","reason":"…"}`) exists in Ring 2 but
is **not** emitted by the CC-G-C Stop hook (advisory-only, D2).
