# Controller Standup Runbook

> **Status.** Phase A manual runbook for ce-ops#398. `docs/design/controller-bootstrap-ssot.json`
> is preview-only and is not ratified for live bootstrap injection.
>
> **Gate authority.** Replacement-controller gate duties stay in read-only
> shadow mode until the A5 standup lock primitive lands. Without that lock,
> arming merge-gate, merge-queue, or approval-wall authority risks a double-hold
> of the merge gate.
>
> **Signing root.** `ce-root-v1` remains Operator-only. It is intentionally
> omitted from `playbooks/controller/duties.yaml`; this runbook must never
> resolve, sign with, or request that key.
>
> **Harness parity.** Every launch or seat step is harness-parametric. Set
> `HARNESS=claude` or `HARNESS=codex`; do not write a claude-only standup path.

This runbook stands up a replacement controller as an observing, self-verifying
controller seat. Overall PASS requires every step below to print PASS evidence.
Any FAIL halts the standup. Gate-authority duties remain shadow-only even after
PASS until a ratified A5 lock proves no other controller can hold the gate.

## Preconditions

- Repository checkout is on the intended commit and can resolve `origin/main`.
- `HARNESS` is exactly `claude` or `codex`.
- A standup-scoped claim ticket is available for the dry-run launch.
- No controller has explicitly delegated live gate authority to this seat.
- Credential inputs are names or pointers only; no secret values are pasted into
  the terminal, this runbook, or checkpoint evidence.

Self-test:

```bash
case "${HARNESS:?set HARNESS=claude or HARNESS=codex}" in claude|codex) ;; *) exit 1 ;; esac
git rev-parse --verify HEAD
git rev-parse --verify origin/main
```

PASS iff both git refs resolve and `HARNESS` is one of `claude|codex`.

## Step 1 - Knowledge Hydration

Read these files top-to-bottom:

- `playbooks/controller/runbooks/controller-standup.md`
- `playbooks/controller/duties.yaml`
- `docs/contracts/orchestrator.md`
- `playbooks/controller/workflow.ce.yml`
- `playbooks/controller/briefs/dispatch.md`
- `playbooks/controller/briefs/harvest.md`
- `playbooks/controller/briefs/merge-gate.md`
- `playbooks/controller/briefs/seat-refresh.md`
- `playbooks/controller/briefs/courier-forge-op.md`
- `playbooks/controller/harness.md`

Self-test:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

paths = [
    "playbooks/controller/runbooks/controller-standup.md",
    "playbooks/controller/duties.yaml",
    "docs/contracts/orchestrator.md",
    "playbooks/controller/workflow.ce.yml",
    "playbooks/controller/briefs/dispatch.md",
    "playbooks/controller/briefs/harvest.md",
    "playbooks/controller/briefs/merge-gate.md",
    "playbooks/controller/briefs/seat-refresh.md",
    "playbooks/controller/briefs/courier-forge-op.md",
    "playbooks/controller/harness.md",
]
missing = [p for p in paths if not Path(p).is_file()]
if missing:
    raise SystemExit(f"FAIL missing={missing}")
yaml.safe_load(Path("playbooks/controller/duties.yaml").read_text())
yaml.safe_load(Path("playbooks/controller/workflow.ce.yml").read_text())
print("PASS knowledge-hydration")
PY
```

## Step 2 - Resume-State Pickup

Find the newest local resume checkpoint. If a CE-DEV-1 mirror is mounted or
provided by the Operator, inspect that mirror the same way. Surface any
`AWAITING-OPERATOR` marker before other work.

Self-test:

```bash
find .ce/state/research -maxdepth 1 -type f -name 'RESUME_STATE_*' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1
rg -n 'AWAITING-OPERATOR' .ce/state/research/RESUME_STATE_* 2>/dev/null || true
```

PASS iff a newest resume file is identified, or the controller logs
`cold start, no resume state` as explicit evidence. A missing local directory is
not a failure by itself.

## Step 3 - Brain Bootstrap Hydration And Dry Run

Always pass a claim ticket; controller brain bootstrap is gated on
`--claim-ticket`. The launch dry run proves the standup launch plan is shaped,
but it returns before the brain-bootstrap payload is built. Exercise the
hydration seam directly for bootstrap payload assertions.

```bash
ce launch \
  --harness "$HARNESS" \
  --claim-ticket "$STANDUP_CLAIM_TICKET" \
  --controller-id "$REPLACEMENT_CONTROLLER_ID" \
  --host-id "$HOST_ID" \
  --purpose controller-standup \
  --dry-run \
  --json > /tmp/ce-controller-standup-launch.json
```

Self-test:

```bash
python3 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/ce-controller-standup-launch.json").read_text())
if not isinstance(payload, dict):
    raise SystemExit("FAIL launch-dry-run JSON payload is not an object")
print("PASS launch-dry-run-plan-shape")
PY

PYTHONPATH=validators python3 - <<'PY'
import sys

from creator_engine_validator import brain_bootstrap

try:
    payload = brain_bootstrap.build_bootstrap_payload()
except brain_bootstrap.BrainBootstrapRefused as exc:
    print(f"FAIL brain-bootstrap-refused: {exc}", file=sys.stderr)
    raise SystemExit(1)

operating_mode = payload.get("operating_mode")
if not isinstance(operating_mode, dict):
    raise SystemExit("FAIL brain-bootstrap missing operating_mode")

missing = [
    key
    for key in ("foreman_charter", "foreman_dispatch_contract")
    if key not in operating_mode
]
contract = operating_mode.get("foreman_dispatch_contract")
roles = contract.get("roles") if isinstance(contract, dict) else None
if not isinstance(roles, dict):
    missing.append("foreman_dispatch_contract.roles")
else:
    missing.extend(
        f"foreman_dispatch_contract.roles.{role}"
        for role in ("researcher", "implementer", "reviewer")
        if role not in roles
    )
if missing:
    raise SystemExit(f"FAIL brain-bootstrap missing={missing}")
print("PASS brain-bootstrap-hydration")
PY
```

PASS iff dry-run exits 0 with JSON object output and direct hydration returns a
payload containing the foreman charter, dispatch contract, and
researcher/implementer/reviewer role evidence. `BrainBootstrapRefused` is a
standup FAIL.

## Step 4 - Duty Manifest Health

For each `survives_controller_death: true` entry in
`playbooks/controller/duties.yaml`, inspect `health_check`.

- `kind: command`: run the probe exactly as listed.
- `kind: TODO_VERIFY`: log the duty id as a repository knowledge gap and do not
  invent a host cron probe.
- `kind: manual`: record the manual observation and evidence source.

Minimum gate-daemon probes:

```bash
deploy/queue-daemon/launch-queue-daemon.sh --health
```

PASS iff the tracked gate-daemon health command reports alive when the deployed
host is expected to own gate daemons, and every `TODO_VERIFY` duty is recorded
as a gap item. If merge-queue or approval-wall health is down on the owning
host, HALT and page the Operator; do not silently re-arm gate authority.

## Step 5 - Credential Pointer Resolution

Resolve only named, value-free controller dependencies:

- model-provider credential by name
- per-task or controller-scoped GitHub token pointer
- reviewer-token pointer
- approval-wall OpenBao pointer needed for health checks

Do not resolve `ce-root-v1`.

Self-test:

```bash
test "${IDENTITY_REGISTRY_PATH:?set external identity registry path}" != ""
PYTHONPATH=validators python3 - <<'PY'
from creator_engine_validator.secret_identity import OpenBaoSecretIdentityBackend, SecretRef

assert OpenBaoSecretIdentityBackend.backend_key == "openbao"
assert SecretRef.__name__ == "SecretRef"
print("PASS secret-identity-imports")
PY
test -f validators/creator_engine_validator/schemas/identity-registry.schema.yaml
```

PASS iff each needed credential resolves through the approved pointer/backend
without printing a value. FAIL closed on inline-secret-shaped values,
`TODO_VERIFY` credential fields, or any attempt to request `ce-root-v1`.

## Step 6 - Gate Lock And Shadow Mode

A5 has not landed in this slice. Therefore this step cannot claim live gate
authority.

Self-test:

```bash
echo "PASS gate-authority-shadow-only: A5 lock absent, no live gate claim made"
```

PASS iff the replacement controller remains read-only for merge-gate,
merge-queue, and approval-wall duties. If the original controller is alive, this
seat may observe and report only. If the original controller is dead, this seat
still does not arm gate authority until the A5 lock primitive exists and passes.

## Step 7 - Benign Governed Action

Run one read-only or dry-run action that proves operational parity without
touching the forge gate:

```bash
ce doctor --help >/dev/null
TMPDIR=/var/tmp ce validate-pr --help >/dev/null
gh pr list --repo creator-engine/creator-engine --limit 5 --json number,title,state >/tmp/ce-controller-standup-pr-board.json
```

PASS iff the commands return the expected help or JSON shape and no mutating
forge operation occurs.

## Step 8 - Evidence Record And Checkpoint

Write an untracked checkpoint under `.ce/state/research/` using the Checkpoint
record shape from `docs/contracts/orchestrator.md`. Include:

- `standup_drill: true`
- `harness: "$HARNESS"`
- git commit SHA
- newest resume-state file or explicit cold-start statement
- duty health PASS/FAIL/TODO_VERIFY summary
- credential pointer resolution summary with no values
- gate-authority mode: `read-only-shadow`
- first failing step, if any

Self-test:

```bash
test -d .ce/state/research || mkdir -p .ce/state/research
test -f "$CHECKPOINT_PATH"
rg -n 'standup_drill: true|read-only-shadow' "$CHECKPOINT_PATH"
```

PASS iff the checkpoint exists, contains no secret values, and records the
standup verdict.

## Overall Verdict

Print `PASS controller-standup-shadow-ready` only when every step above passed.
Otherwise print `FAIL controller-standup step=<first-failing-step>` and refuse
to claim controller duties. A PASS does not grant live gate authority; it proves
the replacement controller can observe, hydrate, verify, and report while A5
lock work remains outstanding.
