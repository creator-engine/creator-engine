# Seat Launch Governance and Containment Runbook

**Status**: Authoritative operator runbook for governed Claude and Codex seat
launches.
**Scope**: `ce launch` Controller seats, claim-bound lane launches, governance
attachment, credential isolation, and containment response.
**Validator sync**:
`validators/creator_engine_validator/checks/operator_runbook_refusal_sync.py`
derives the refusal clause set from `claude_launch_spec.py` and
`codex_launch_spec.py` and checks the structured clause table below.

This runbook is the discoverable operator surface for launching a governed seat.
It does not grant Source ratification, source-host authority, hosted team-mode
authority, or a credential exception. Operators use it to launch or refuse seats
without weakening the code-defined Ring 0 contract.

## 1. Launch Contract

Use `ce launch` for a visible Controller-seat session. `ce hud` is only an
alias for `ce launch`; it is not a separate UI or authority surface.

Run the launcher from the intended repo/worktree, or pass `--repo-root` to the
intended repo/worktree root. `ce launch` does not allocate, create, switch,
clean, or validate git worktrees; worktree allocation and branch setup are
operator/controller responsibilities before launch. The repo root is the seat
`cwd` recorded in lifecycle evidence, the base used for relative
Controller-seat MCP provisioning, and the allowed root for Codex `--add-dir`
checks. A governed seat may author only inside that selected worktree root.
When `--ledger-root` is omitted, lifecycle registration uses
`<repo-root>/.ce/state/active-work-ledger`. For a pre-allocated claim-bound lane
that must bind a prompt pointer, prompt SHA, pane registry record, worktree
path, and Active-Work claim, use `ce lane launch`.

The operator selects the harness explicitly:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli launch --harness claude
PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli launch --harness codex
```

`--dry-run --json` may be used to inspect the deterministic plan. The runtime
dry run does not spawn tmux, perform provider login, acquire a live terminal,
write lifecycle state, or perform resource-bound launch-confirm. The CLI still
performs preflight checks and any requested `--claim-ticket` acquisition before
it enters the launch runtime, so omit `--claim-ticket` for a no-claim preview.

Operator-relevant `ce launch` flags:

| Flag | Contract |
|---|---|
| `--harness <claude|codex|hermes|openclaw>` | Selects the Controller-seat harness. This runbook covers governed Claude and Codex seats. |
| `--session <name>` | Names the tmux session. The default is `ce-controller`. It also contributes to Controller-seat state paths such as the default MCP config path. |
| `--window <name>` | Names the tmux window. The default is `controller`. |
| `--resume` | Attaches an existing launcher session. If the named session does not exist, launch is refused instead of spawning or continuing hidden. |
| `--dry-run` | Builds the deterministic launch plan at the launch-runtime layer. No tmux spawn, provider login, lifecycle write, or resource-bound launch-confirm occurs; requested `--claim-ticket` acquisition still happens before the runtime call. |
| `--no-tmux` | Refuse-only request for a non-visible/headless Controller seat. Governed authoring seats require a visible tmux surface, so this refuses before side effects. |
| `--mcp-config <path>` | Claude-only governed MCP config path. The launcher requires a CE-owned repo-relative path, pins `--strict-mcp-config`, provisions the file under `--repo-root` when absent, and refuses absolute, `~`, or escaping paths. |
| `--completion-report-ref <ref>` | Deterministic completion-report pointer accepted for closeout verification surfaces. The governed Claude command builder does not emit it as a Claude argv flag. |
| `--closeout-file <path>` | Deterministic closeout text pointer accepted for closeout verification surfaces. The governed Claude command builder does not emit it as a Claude argv flag. |
| `--runtime-policy <path>` | Reads a ratified runtime policy before launch. When the policy declares governed resource envelopes, the launcher wraps the governed command in the resource-bound runtime and records the applied `resource_bound` evidence; dry-run renders that block offline. |
| `--claim-ticket <ticket>` | Acquires and verifies a work-claim lock before any launch side effect. A foreign active claim refuses the launch. On success the claim binding is recorded in seat lifecycle evidence; if `--purpose` is omitted, the ticket becomes the default purpose. |
| `--repo-root <path>` | Sets the repo/worktree root used for lifecycle registration, seat `cwd`, Controller-seat state, relative MCP provisioning, and Codex allowed-root checks. Default: `.`. |
| `--ledger-root <path>` | Sets the Active-Work Ledger root for lifecycle registration. Default: `<repo-root>/.ce/state/active-work-ledger`. |
| `--controller-id <id>` | Records the owner/controller id in the governed seat lifecycle record. |
| `--host-id <id>` | Records the host id in the governed seat lifecycle record. |
| `--purpose <text>` | Records an operator-readable purpose in the governed seat lifecycle record. |
| `--json` | Emits the launch result or dry-run plan as machine-readable JSON. |
| `--claude-arg=<value>` | Repeatable Claude harness arg. Dashed values must use `=`. Ring 0 parses these args, refuses the `CC-D-*` surfaces below, then rebuilds the governed Claude command. |
| `--codex-arg=<value>` | Repeatable allowlisted Codex harness arg. Dashed values must use `=`. Ring 0 parses these args, refuses the `CDX-D-*` surfaces below, and wraps Codex with the credential-scrubbing environment command. |

For Claude, pass harness args only through `--claude-arg=<value>`. Ring 0 parses
those args before any tmux spawn, refuses every `CC-D-*` surface below, and then
builds the governed command by pinning:

- `--setting-sources project`
- `--strict-mcp-config`
- `--mcp-config <CE-owned path>`

For Codex, pass harness args only through `--codex-arg=<value>`. Ring 0 parses
those args before any tmux spawn, refuses every `CDX-D-*` surface below, and
then wraps the command with an environment scrub that removes common ambient
source-host write credentials.

For claim-bound work lanes, use `ce lane launch` with a live Active-Work claim,
prompt pointer, expected prompt SHA256, repo root, ledger root, and the
pre-allocated worktree path. The lane primitive writes the Pane Registry binding
only after prompt, visibility, claim, conflict, and tmux checks pass. A prompt
pasted into chat is not a launch contract; the contract is the checked path plus
expected hash plus live claim.

## 2. Operator Provisioning From Zero

On an unprovisioned host or clone, perform provisioning as the operator before
any seat launch:

1. Install the validator dependencies from the checked-in wheelhouse. Do not
   fetch network packages during launch authority.
2. Run `ce doctor --json` from checkout source with `PYTHONPATH=validators`.
3. Install host prerequisites that the doctor names, such as tmux for visible
   seats and rootless Podman for worker execution.
4. Initialize only repo-local ignored runtime state under `.ce/state` and
   `.hermes` using the repo's `ce init` / bootstrap contract. Do not put
   credentials into tracked files.
5. Create or acquire the work claim before launch. A foreign active claim or an
   absent required claim is a stop condition, not a reason to run a raw harness.
6. Re-run `ce launch --dry-run --json --harness <claude|codex>` and inspect the
   planned command before the live launch.

Minimal source-backed bootstrap shape:

```bash
python3 -m venv .venv
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
"$CE_VALIDATOR_PYTHON" -m pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.ce_cli doctor --json
```

If any preflight refuses, halt and fix the named prerequisite. Do not fall back
to raw `claude`, raw `codex`, headless mode, unmanaged settings, or copied
tokens.

## 3. Governance Attachment

The real attachment mechanism is launch-pinned environment plus repository
evidence, not a chat statement or prompt convention:

- `ce launch` records a governed seat lifecycle entry under ignored CE state,
  including the launch surface, harness, controller identity, host identity,
  purpose, and work-claim binding when supplied.
- `ce lane launch` binds the live Active-Work claim to a Pane Registry record
  under `.hermes/active-work-ledger/panes/...` after all refusal predicates pass.
- `--claim-ticket` is the operator-facing way to tie a Controller-seat launch to
  the intended issue or task before side effects. A foreign active claim refuses
  launch.
- For governed Claude lanes, the hook attachment path is the same
  launch-pinned environment bridge described in
  [`GOVERNED_LANE_LAUNCH_PROTOCOL.md`](./GOVERNED_LANE_LAUNCH_PROTOCOL.md), not
  prompt text. `lane_runtime.launch` exports the absolute Active-Work Ledger
  root as `CE_LEDGER_ROOT` into the tmux pane environment.
  `.claude/hooks/ce-pretooluse.sh` reads that variable and forwards
  `--ledger-root <value>` to `creator_engine_validator hook-check`. The CLI
  passes that flag into `hook_check.build_context(..., ledger_root=...)`; from
  there `_posture_discovery_root()` scopes governed-posture claim and pane
  discovery to that real ledger root rather than to arbitrary tracked fixtures
  or the whole worktree.
- Reviewer mechanics require a reviewer-authority envelope reference carried by
  a distinct reviewer venue. `ce lane launch --role reviewer --lane-kind review
  --reviewer-authority-ref <ref>` validates the envelope before side effects,
  exports the ref as `CE_REVIEWER_AUTHORITY_REF`, and records the venue sidecar.
  `.claude/hooks/ce-pretooluse.sh` forwards it as
  `--reviewer-authority-ref <ref>`; the CLI injects
  `ce.reviewer_authority_ref` into the hook event before
  `hook_check.build_context()`, and `_resolve_side_effect_authority()` loads and
  validates the bounded reviewer-authority envelope. Without the env var, flag,
  or valid envelope, restricted reviewer actions remain denied.
- Source ratification and mechanics authority are separate from seat launch.
  Launch evidence can support ratification; it cannot ratify itself.

A seat is considered governed only when the live seat identity points at the
expected claim and the claim remains unreleased. If that binding is missing,
ambiguous, or stale, stop and repair the governance state before continuing.

## 4. Isolated Seat Identity And Container Model

Each governed seat has a bounded identity and must run under an isolated
OS/container identity. This is a load-bearing credential boundary, not an
operator preference. Use a separate Linux user, a container identity, or an
equivalent containerized execution boundary for the seat. Do not run a governed
seat as the controller user or any same-UID identity that can read the
controller's source-host or broker credentials. The controller account may hold
high-blast credentials; sharing that identity collapses the credential boundary
and expands the blast radius of any compromised seat.

Each governed seat identity includes:

- one harness (`claude` or `codex` for this runbook),
- one visible tmux surface unless explicitly in dry-run planning,
- one controller id and host id,
- one purpose and work claim for the task,
- one repo/worktree root, and
- one transcript/evidence chain for closeout.

Worker execution is a separate containment layer. Worker containers are
rootless, policy-bound, and claim-bound. The tracked policy names the image
digest, mount manifest, egress allowlist, and secret allowlist by name only. The
runtime container-instance record records the applied policy SHA and claim id.
A running container that outlives its claim is a refusal/remediation condition:
terminate or reap it, revoke broker grants, and record evidence.

Operators must not reuse a seat identity, OS/container user, pane, container,
worktree, or credential grant across unrelated claims. Release the claim and
stop or archive the seat before reusing the surface.

## 5. Credential Boundary

The controller holds keys. Seats consume bounded references and evidence:

- Governed seats are isolated OS/container identities, never the controller user
  identity. A seat started as the controller user is not a governed seat for
  authoring purposes; stop it, treat the credential boundary as contaminated,
  and relaunch under a separate Linux user or container identity. The controller
  user may hold source-host and broker credentials; the seat identity must not
  inherit those ambient credentials or filesystem access.
- Source-host write credentials stay out of tracked files, prompts, command
  lines, transcript bodies, and model context.
- Codex launches scrub `GH_TOKEN`, `GITHUB_TOKEN`, enterprise token variables,
  GitHub host/config variables, and debug variables before invoking `codex`.
- Claude launches use strict project settings and CE-owned MCP config paths;
  user/global MCP inheritance is not an authority source.
- Worker containers receive secret grant names and broker lease ids, never
  secret values in tracked records.
- Privileged actions flow through the controller/broker boundary. For
  high-blast or irreversible operations, the broker proxies the action and
  returns value-free evidence instead of handing keys to the seat.

If a credential appears in a prompt, argv, tracked file, transcript excerpt, or
validator error, treat the seat as contaminated: stop, rotate/revoke the grant,
archive the incident evidence without the secret value, and relaunch from a new
seat identity.

## 6. Refusal Clause Remedies

The table between the markers is machine-checked. The first column must list
exactly the current `CLAUSE_*` string values from the Claude and Codex launch
spec modules.

<!-- ce-launch-refusal-clauses:start -->
| Clause ID | Harness | Refused surface | Operator remedy |
|---|---|---|---|
| CC-D-1 | Claude | `--bare` skips hooks, settings, and governance discovery. | Remove `--bare`; launch through `ce launch --harness claude` or `ce lane launch` so Ring 0 pins project settings and strict MCP. |
| CC-D-2 | Claude | `-p` / `--print` headless authoring mode. | Use a visible tmux seat for governed authoring. Reserve print mode for read-only scripted checks outside governed authoring lanes. |
| CC-D-3 | Claude | `agents` subcommand or `--agents` background sessions. | Use one operator-visible pane per governed lane. Allocate another governed lane instead of hidden background agents. |
| CC-D-4 | Claude | `--remote-control`, `--remote-control-at-startup`, or `remoteControlAtStartup`. | Remove remote-control surfaces. All control must occur through the visible archived seat and repository evidence. |
| CC-D-5 | Claude | `settings.local.json` or `--setting-sources` excluding `project` or including `local`. | Pin `--setting-sources project` through the launcher. Move required policy into committed project settings or a ratified CE-owned config. |
| CC-D-6 | Claude | `--dangerously-skip-permissions` without confirmed hook-pack load. | Confirm the hook-pack through Ring 0 first, or remove skip-permissions. Without confirmation, relaunch in normal permission posture. |
| CC-D-7 | Claude | Uncontrolled MCP inheritance or non-CE-owned MCP config. | Use `--strict-mcp-config` with a repo-relative CE-owned MCP config path. Auto-provision the default empty config when appropriate. |
| CDX-D-1 | Codex | Headless subcommands such as `exec`, `review`, `mcp-server`, `exec-server`, `app-server`, or `apply`. | Use `ce launch --harness codex` for a visible governed authoring seat. Run scripted checks outside the authoring-seat launcher. |
| CDX-D-2 | Codex | Remote-control or remote-token surfaces. | Remove remote flags and tokens. Route any remote/source-host action through the controller or broker with evidence. |
| CDX-D-3 | Codex | `--ephemeral` disables durable transcript identity. | Relaunch without ephemeral mode so the seat has durable transcript and lifecycle evidence. |
| CDX-D-4 | Codex | Posture bypass flags such as `--dangerously-bypass-hook-trust`, `--ignore-rules`, or `--ignore-user-config`. | Remove bypass flags. If posture needs to change, ratify and encode the new posture in CE governance rather than launch argv. |
| CDX-D-5 | Codex | `--add-dir` expands writable scope outside the declared worktree root. | Restrict writable scope to the allowed repo/worktree root. Allocate another governed worktree for additional scope. |
| CDX-D-6 | Codex | Missing explicit or verified bypass mode. | Set exactly the accepted top-level Codex config keys in `~/.codex/config.toml`: `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`, or use the approved explicit argv path by passing `--codex-arg=--dangerously-bypass-approvals-and-sandbox` through the launcher. Other key names, values, or raw `codex` invocations are not accepted. |
| CDX-D-7 | Codex | Non-allowlisted Codex launch flags. | Remove the flag. Add support in the pure launch spec only after governance review and tests. |
<!-- ce-launch-refusal-clauses:end -->

## 7. Containment Response

When a refusal fires before side effects, the correct outcome is a stopped
launch and a repaired invocation. Do not retry by invoking the harness directly.

When a violation is discovered after launch:

1. Stop the seat or container.
2. Preserve value-free evidence: clause id, seat id, claim id, command surface,
   and affected paths. Do not copy secrets into the incident note.
3. Release or quarantine the claim if the governance binding is suspect.
4. Revoke broker grants and source-host tokens associated with the seat.
5. Relaunch only after the refusal clause has a concrete remedy applied.

The operator may continue only from a clean governed launch whose refusal table
still matches the code-derived clause set.
