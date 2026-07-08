# Singleton Daemon Redeploy Runbook

## Purpose And Scope

Operator decision 1 in `.ce/state/decisions/DECISIONS_20260708.md` requires a
bounded, repeatable redeploy path before new singleton authority is armed. This
runbook covers the first redeploy surface for singleton daemons. The live target
is `queue-daemon`; `option-a-materializer` is accepted by the CLI as a forward
placeholder and is not deployed yet.

This procedure is intended for the VPS controller host that owns the singleton
systemd service. It does not replace the queue-daemon relocation runbook; it
wraps the existing unit, launcher, and health probe into one operator command.

## Prerequisites

- The operator has a current checkout of this repository on the controller host.
- Passwordless `sudo` is available for systemd operations and installing the
  system unit.
- Docker or the configured container engine is available for the queue-daemon
  launcher.
- The queue-daemon env file exists, defaults to
  `/etc/creator-engine/ce-queue-daemon.env`, and has mode exactly `0600`.
- The env file contains the keys documented in
  `deploy/queue-daemon/RELOCATION.md`.

If the env file is missing or has the wrong mode, remediate before redeploying:

```bash
sudo install -d -m 0755 /etc/creator-engine
sudo install -m 0600 -o root -g root /dev/null /etc/creator-engine/ce-queue-daemon.env
sudoedit /etc/creator-engine/ce-queue-daemon.env
sudo chmod 0600 /etc/creator-engine/ce-queue-daemon.env
```

## Dry-Run Workflow

From the checkout root:

```bash
deploy/singleton-redeploy/redeploy-singleton.sh \
  --daemon queue-daemon \
  --dry-run \
  --repo-root "$PWD" \
  --env-file /etc/creator-engine/ce-queue-daemon.env
```

The dry run verifies the env-file precondition and prints the planned install,
daemon reload, enable/restart, active-state wait, and health-probe actions. It
does not write the systemd unit, reload systemd, or restart the service.

The smoke test exercises only dry-run behavior and can be run before live use:

```bash
deploy/singleton-redeploy/smoke-singleton-redeploy.sh
```

## Live Queue-Daemon Redeploy

After the dry run is clean, run the live redeploy from the checkout root:

```bash
deploy/singleton-redeploy/redeploy-singleton.sh \
  --daemon queue-daemon \
  --repo-root "$PWD" \
  --env-file /etc/creator-engine/ce-queue-daemon.env
```

The script renders the checked-in `ce-queue-daemon.service` for the selected
checkout and env file, compares it to `/etc/systemd/system/ce-queue-daemon.service`
with `cmp -s`, installs it only when content changed, reloads systemd only after
a unit change, enables and restarts the service, waits up to 30 seconds for an
active state, then runs `deploy/queue-daemon/launch-queue-daemon.sh --health`.

## Failure Handling

If the env-file check fails, follow `deploy/queue-daemon/RELOCATION.md` and fix
the env file before trying again. The redeploy script fails closed and will not
restart the service when the env file is absent or not mode `0600`.

If the service does not become active, inspect:

```bash
sudo systemctl status ce-queue-daemon.service --no-pager
journalctl -u ce-queue-daemon.service -n 100 --no-pager
```

If the health probe fails, refresh the affected credential or service dependency
through the approved secret channel, then rerun the redeploy. For rollback,
follow `deploy/queue-daemon/RELOCATION.md` section "Rollback To DGX" and confirm
that exactly one queue daemon is active before leaving rollback state.

## Option A Materializer Placeholder

`deploy/singleton-redeploy/redeploy-singleton.sh --daemon option-a-materializer`
is intentionally stubbed. Dry-run mode reports that the daemon is a future
singleton target. Live mode exits nonzero because no committed systemd unit or
launcher exists yet. The stub should be replaced when the materializer daemon is
committed.
