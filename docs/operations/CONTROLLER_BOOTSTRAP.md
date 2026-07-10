# CONTROLLER_BOOTSTRAP - Replacement Main Controller: Spawn and Resume

## 0. Purpose and scope

Use this runbook when the primary controller host is unavailable, the active
controller is in an outage, or an operator is running a replacement-controller
drill exercise.

Scope is limited to spawning a replacement main controller. It does not cover
seat provisioning or tenant onboarding.

The intended outcome is a running controller that can resume the factory
conveyor from centralized state within one shift.

## 1. Prerequisites

Target host: a replacement-controller host with source-host access and access to
the controller state source.

- `git` 2.40 or newer is installed.
- `python3` 3.11 or newer is installed. A uv-managed venv is preferred.
- The `ce` binary is accessible in `PATH`, installed via
  `pip install creator-engine` or from the repo's `main` branch worktree.
- A scoped source-host token is available to the shell, for example as
  `GH_TOKEN`. Do not hardcode token values or source credentials from a
  documented host-local path.
- SSH or equivalent operator access to `<replacement-host>` is confirmed for the
  replacement-controller user.
- `jq` is installed for manifest inspection.
- `yq` or an equivalent structured YAML reader is installed for identity
  registry inspection while `ce identity lookup` remains pending.
- `rsync` or an equivalent file-sync tool is installed for manual state
  snapshot restore.
- The `creator-engine` repo clone exists at `<repo-root>` and is checked out to
  `origin/main`.

## 2. Identity hydration

The source of truth is the identity registry at `infra/identity-registry.yaml`
in the identity registry repository. That file is the authoritative CE identity
SSOT under the registry-wins precedence rule.

When an identity is present in `infra/identity-registry.yaml`, that value is
authoritative. Controllers must not derive or override it from environment
files, memory, or live API calls.

Recall path:

```bash
ce identity lookup <app-name-or-app-id>
```

The lookup returns non-secret fields: `app_id`, `installation_id`, and the
`pem_custody` pointer. Status note: recall CLI implementation is a pending
identity SSOT recall slice. Until it lands, consult the registry YAML directly.

PEM files and PAT tokens are not in the registry. The registry contains only
custody pointers. Secrets are brought to the replacement host out of band. The
OpenBao lane is the ratified long-term target; see the gap list in Section 7.

Registry inspection step:

```bash
APP_NAME=<app-name> \
  yq '.apps[] | select(.name == strenv(APP_NAME))' \
  <identity-registry-clone>/infra/identity-registry.yaml
```

Availability note: `infra/identity-registry.yaml` is not present in the
`creator-engine` checkout; use the identity registry repository clone.

## 3. State hydration

The state source is the controller state snapshot produced by
`tools/controller/state_sync.py` on `<state-branch>` in the state target
repository. The branch name should identify `<state-source>` without embedding
host-local topology in this public runbook.

`tools/controller/state_sync.py` is not present in this checkout, and the
inverse restore operation is not implemented in slice 1. Do not run or document
the restore inverse as an executable command until the state sync restore slice
lands.

For slice 1, restore manually from a checked out state snapshot:

```bash
git -C <state-repo-root> fetch <state-remote> <state-branch>
git -C <state-repo-root> worktree add --detach <state-snapshot-root> FETCH_HEAD
rsync -a <state-snapshot-root>/arc_state/ <repo-root>/.ce/state/research/
rsync -a <state-snapshot-root>/dispatch_briefs/ <repo-root>/.ce/briefs/
rsync -a <state-snapshot-root>/dispatch_claims/ <repo-root>/.ce/claims/
```

If `memory.tar.gz` is present and the drill requires memory recall, extract it
to the replacement controller's configured memory location. Memory sync is
opt-in for slice 1.

Integrity check: verify `manifest.json` `sha256` for each restored file before
launching the controller.

Status note: the snapshot producer and restore inverse must both be available
before this step can become a one-command operation.

## 4. Standby surface provisioning

Script:

```text
provision-standby-surface.sh
```

Resolve the current tracked script path from the repo instead of copying a
host-specific deployment path into this runbook:

```bash
STANDBY_SCRIPT=$(git -C <repo-root> ls-files '*provision-standby-surface.sh' | head -n 1)
test -n "$STANDBY_SCRIPT"
```

The script:

- Creates a dedicated git worktree at `<standby-root>` pinned to `origin/main`,
  decoupled from the shared mutable checkout.
- Verifies `tools/mint-forge-token.py --help` executes without traceback.

Current status: the tracked script contains a legacy embedded takeover check
that invokes `ce takeover --dry-run --json` without the parser-required `--from`,
`--harness`, and `--repo-root` arguments. Direct execution is expected to exit
nonzero under the current CLI before it can provide successful provisioning or
drill evidence. Treat the script as pending repair; do not use it as a live
runbook step until its embedded takeover invocation is updated.

Required environment variables:

- `SHARED_ROOT=<repo-root>`
- `STANDBY_ROOT=<standby-root>`

Do not rely on host-local script defaults; pass both roots explicitly.

Manual standby surface preparation until the script is repaired:

```bash
git -C <repo-root> fetch origin main
git -C <repo-root> worktree add --detach <standby-root> origin/main
git -C <standby-root> rev-parse --verify HEAD
```

If `<standby-root>` already exists, refresh it explicitly instead of re-running
the pending script:

```bash
git -C <standby-root> fetch origin main
git -C <standby-root> checkout --detach origin/main
```

Manual post-provisioning verification:

```bash
ce takeover --from <predecessor-controller> --harness <harness> --repo-root <repo-root> --dry-run --json \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["ring0_verify"]["ok"] is True'
```

## 5. Launch - harness-agnostic

Entry command:

```bash
ce launch --repo-root <repo-root>
```

Optional harness flag:

```bash
ce launch --repo-root <repo-root> --harness claude
ce launch --repo-root <repo-root> --harness codex
```

Per doctrine, `ce launch` is harness-agnostic. Omit the flag to use the
installed default.

The controller's SSOT-fed operating files, including `AGENTS.md`, `CLAUDE.md`,
and `.claude/agents/`, are present in the main-tracked checkout and do not need
hand tuning.

After launch, confirm AWAITING-OPERATOR posture:

```bash
ce posture
```

The posture output should show:

```text
state=AWAITING-OPERATOR
predecessor=<predecessor-controller>
```

## 6. Takeover drill

Mandatory at first launch:

```bash
ce takeover --from <predecessor-controller> --harness <harness> --repo-root <repo-root> --dry-run --json \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["ring0_verify"]["ok"] is True'
```

Weekly drill cadence, moving to monthly after two consecutive clean runs pass:

```bash
ce continuity-drill --from <predecessor-controller> --harness <harness> --repo-root <repo-root> --json
```

Run the continuity drill with `CE_STANDBY_LIVENESS_JSON` populated from the
standby's `ce takeover --from <predecessor-controller> --harness <harness>
--repo-root <repo-root> --dry-run --json` output.

A drill is GREEN only when `standby_liveness.ok=true` appears in the
continuity-drill output. Raw boolean `CE_STANDBY_LIVENESS=1` is rejected with
WARNING status.

Before each drill, manually confirm `<standby-root>` is on `origin/main` until
the pending standby script repair lands.

## 7. Gap list

| Gap | Status | Tracking |
|---|---|---|
| Secrets custody | OpenBao lane is the ratified long-term target. Until it lands, PEM and PAT files are brought to the replacement host out of band. Do not put secrets in git. | OpenBao program |
| State sync push wiring | Slice 1 snapshot tooling is not present in this checkout. The current supported path is manual restore from the checked out state snapshot. Automated push-on-snapshot and inverse restore are later slices. | State sync follow-up |
| Identity recall CLI | `ce identity lookup` is not yet implemented. Registry must be read directly with `yq` or another structured YAML reader. | Identity SSOT recall follow-up |
| Memory sync | Controller memory requires opt-in snapshot inclusion and is not yet part of the default sync cadence. | State sync follow-up |
| Parallel worker venue | A freshly deployed controller does not automatically prove parity with an established controller's session-level worker fleet. The full harvest-to-review-to-gate-to-closeout acceptance cycle is not yet runnable from this runbook alone. | Controller parity program |
| Standby provisioning script | The tracked standby script still invokes the legacy bare takeover command and is expected to exit nonzero under the current CLI. Use the manual standby preparation and takeover verification commands above until the script is repaired. | Standby script follow-up |

## 8. Validation checklist

```text
[ ] identity registry repository readable and contains fleet entries
[ ] ce takeover --from <predecessor-controller> --harness <harness> --repo-root <repo-root> --dry-run --json -> ring0_verify.ok=true, initial_state=AWAITING-OPERATOR
[ ] manual standby preparation confirms <standby-root> is detached at origin/main
[ ] ce posture -> state=AWAITING-OPERATOR (after live launch)
[ ] ce continuity-drill --from <predecessor-controller> --harness <harness> --repo-root <repo-root> --json -> status=GREEN (with standby liveness env set)
[ ] validators/tests/unit/test_controller_bootstrap_paths.py -> all pass
```
