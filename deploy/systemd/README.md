# Creator Engine Gate Daemons (systemd)

These units keep the autonomous gate daemons alive after host reboot:

- `ce-belt-daemon.service`: runs `ce pickup poll` in observe-only mode for the
  work-pickup conveyor belt; it does not claim work or launch seats.
- `ce-integrator-daemon.service`: runs `queue-daemon` for merge-queue repair.
- `ce-review-pickup-daemon.service`: runs `review-pickup` for review fan-out.
- `ce-ratifier-queue.service`: folds controller-supplied candidate/evidence
  snapshots into a durable, proposal-only ratifier queue; it cannot approve,
  enqueue, merge, sign, or remove the legacy session crons.
- `ce-model-drift-watcher.service`: observes the tracked model canon in fixed
  DGX/VPS containers and writes durable controller-inbox drift alarms.
- `ce-codex-seat@.service`: clears any stale named Codex seat container, starts
  a fresh detached runsc container through the checked-in launcher, and keeps
  `docker wait <container>` in the foreground so systemd owns restart.

Install from the repository root:

```sh
deploy/systemd/install-gate-daemons-systemd.sh
```

The default install target is the user systemd manager at
`~/.config/systemd/user`. Use `--system` to install into `/etc/systemd/system`.
The installer renders the checked-in unit templates with the current source
checkout path, runs `daemon-reload`, enables the gate daemon services, and
starts them.
Use `--no-start` to render/enable without starting.

Create the env file before starting services. Defaults:

- user: `~/.config/creator-engine/gate-daemons.env`
- system: `/etc/creator-engine/gate-daemons.env`

Example:

```sh
CE_GATE_REPO=creator-engine/creator-engine
CE_GATE_AUTHORIZED_REVIEWERS=<the configured reviewer seats>
CE_BELT_IDENTITY=ce-dev-4
CE_BELT_INTERVAL_SECONDS=120
CE_BELT_LABELS=enhancement
GH_TOKEN=<integrator-token>
CE_PICKUP_TOKEN=<review-pickup-token>
CE_RATIFIER_QUEUE_CANDIDATES_PATH=/owner-only/path/ratifier-candidates.json
# Optional; the unit default is %h/.local/state/creator-engine/ratifier-queue/state.json
CE_RATIFIER_QUEUE_STATE_PATH=/owner-only/path/ratifier-state.json
CE_RATIFIER_QUEUE_INTERVAL_SECONDS=120
```

`GH_TOKEN` and `CE_GATE_AUTHORIZED_REVIEWERS` are required by the integrator
daemon. `CE_GATE_AUTHORIZED_REVIEWERS` is a comma-separated list for the
configured reviewer seats whose approvals may authorize merge-queue enqueue;
missing or empty config fails closed. Review pickup first uses
`CE_PICKUP_TOKEN`; if it is absent, the CLI falls back to the configured
reviewer seats' local credential files unless ambient `gh` auth is explicitly
enabled.

## Model drift observer

`ce-model-drift-watcher.service` has a separate zero-token environment file:
`~/.config/creator-engine/ce-model-drift.env` for user installs and
`/etc/creator-engine/ce-model-drift.env` for system installs. The installer
creates it owner-only with only canon, state, lease, inbox, and 60-second
cadence settings. It does not carry GitHub, OpenBao, Vault, PAT, or credential
file values. The watcher can only read each canon-pinned container TOML and
`codex --version`; it never restarts a container or changes configuration.

To source the review-pickup token through OpenBao, add the OpenBao client
environment and the review-pickup SecretRef to the same env file:

```sh
BAO_ADDR=<openbao-url>
BAO_TOKEN=<openbao-token>
BAO_CACERT=<optional-ca-cert-path>
CE_OPENBAO_ALLOWED_REFS=path=forge/reviewer/gh-token;field=token;purpose=review-pickup-token;owner_ref=controller:reviewer;policy_sha=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982
CE_PICKUP_TOKEN_SECRET_BACKEND=openbao
CE_PICKUP_TOKEN_SECRET_MOUNT=ce-kv
CE_PICKUP_TOKEN_SECRET_PATH=forge/reviewer/gh-token
CE_PICKUP_TOKEN_SECRET_FIELD=token
CE_PICKUP_TOKEN_SECRET_PURPOSE=review-pickup-token
CE_PICKUP_TOKEN_SECRET_OWNER_REF=controller:reviewer
CE_PICKUP_TOKEN_SECRET_REF_POLICY_SHA=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982
CE_PICKUP_TOKEN_SECRET_TARGET_REF=file:/run/user/<uid>/creator-engine/review-pickup-token
```

The unit keeps the static `CE_PICKUP_TOKEN` path active by default. Its template
includes a commented OpenBao-ready `ExecStart` replacement with the
`--pickup-token-secret-*` flags wired to env-file values; switch to that command
only after the OpenBao delivery path has been verified live.

The belt daemon requires `CE_BELT_IDENTITY` because `ce pickup poll` resolves
credentials from `CE_PICKUP_TOKEN` or `~/.ce-keys/<identity>.pat` by default.
It runs a simple systemd-supervised loop around the one-shot poll command and
keeps the poll observe-only: no `--claim`, no `--enable-launch`, and no ambient
`gh` credential use unless the operator changes the command to pass the CLI's
explicit ambient-auth flag. Set optional `CE_BELT_LABELS` to pass one scoped
`--label` filter such as `enhancement`; leave it unset to observe the default
pickup queries.

## Ratifier-Queue Reversible Handoff

`ce-ratifier-queue.service` is default-off in authority: it reads only the
operator-created, owner-only candidate document named by
`CE_RATIFIER_QUEUE_CANDIDATES_PATH`, persists an owner-only local proposal
state, and emits `PENDING`, `STALE`, `BLOCKED`, or `ATTESTED` evidence. An
`ATTESTED` row is never an approval, enqueue, merge, signature, or ratification
act. The service has no forge or credential configuration.

The candidate document is strict JSON with `version: 1` and a `candidates`
array. Each candidate supplies immutable PR/head identity plus the complete
injected ready-attestation fact shape. Do not put credentials, tokens, or raw
controller identity values in either document.

Controller deployment evidence template (the controller, not this installer,
owns the live transition):

1. Run the installer with `--no-start`; inspect the rendered unit, candidate
   path, state parent, and state-file permissions (owner-only).
2. Start `ce-ratifier-queue.service`, observe two successful intervals, then
   restart it and prove preserved candidate order, checked count, timestamp,
   and PR/head dedup identity.
3. Compare both queue summaries with the legacy `:23` and `:53` session passes.
   Any mismatch stops the handoff, stops the service, retains the old crons,
   and removes only the new local state after evidence is captured.
4. Only after that evidence is accepted may the controller remove the legacy
   session crons. This repository change neither starts the service nor removes
   a cron.

## Egress Self-Push Broker Peer Credentials

`ce-egress-broker.service` uses its own environment file, not
`gate-daemons.env`:

- user: `~/.config/creator-engine/ce-egress-broker.env`
- system: `/etc/creator-engine/ce-egress-broker.env`

Required values:

```sh
CE_EGRESS_BROKER_SOCKET=/run/ce-egress/dev-3.sock
CE_EGRESS_BROKER_SEAT=dev-3
CE_EGRESS_BROKER_EXPECTED_PEER_UID=<contained-seat-uid>
CE_EGRESS_BROKER_EXPECTED_PEER_GID=<contained-seat-gid>
CE_EGRESS_BROKER_REPO=/workspace/creator-engine
CE_EGRESS_BROKER_CONFIG=/etc/ce-egress/broker-dev3.json
```

The daemon returns JIT credential values on this Unix stream, so it refuses to
start without explicit expected peer UID/GID values and rejects mismatched
`SO_PEERCRED` peers before request parsing.

## Egress Self-Review Broker Run Mode

`ce-egress-self-review.service` uses its own environment file, not
`gate-daemons.env`:

- user: `~/.config/creator-engine/ce-egress-self-review.env`
- system: `/etc/creator-engine/ce-egress-self-review.env`

Keep the committed and deployed default inert:

```sh
CE_EGRESS_SELF_REVIEW_SOCKET=/run/ce-egress/dev-3-review.sock
CE_EGRESS_SELF_REVIEW_CONFIG=/etc/ce-egress/broker-dev3.json
CE_EGRESS_RUN_MODE=dev
```

With `CE_EGRESS_RUN_MODE=dev`, the broker starts with `--run-mode dev` and
autonomous `APPROVE` remains refused. To arm Surface-B later, the Operator must
set `CE_EGRESS_RUN_MODE=strangeLoop` in that environment file and restart the
self-review broker unit. To roll back/disarm, set `CE_EGRESS_RUN_MODE=dev` and
restart the same unit. This repository change only wires regenerated units for
that future env-flip plus restart; it does not perform the env flip, restart,
redeploy, or any live arming act.

## Detached Codex Seat Template

`ce-codex-seat@.service` is a system-level template for contained Codex seats.
Before each start, it removes any stale container with the configured seat name.
It then runs the selected launcher with `--detach tui`; the launcher renders
`docker run -d --name ...`, polls herdr readiness through `docker exec`, and
returns. The unit keeps `docker wait <container>` in the foreground after the
detached launch, so systemd owns the seat lifecycle and restarts the unit when
the container exits. No host tmux is required.

Create one env file per instance:

```sh
sudo install -d -m 0755 /etc/creator-engine
sudo tee /etc/creator-engine/ce-codex-seat-dgx.env >/dev/null <<'EOF'
CE_CODEX_SEAT_LAUNCHER=deploy/dgx-runsc/run-codex-runsc.sh
CE_CODEX_SEAT_CONTAINER_NAME=ce-dgx-codex
CE_DGX_CONTAINER_NAME=ce-dgx-codex
CE_DGX_REPO=/workspace/creator-engine
CE_DGX_CODEX_HOME=/home/cedev4/.codex
CE_DGX_CODEX_BIN=/home/cedev4/.codex/packages/standalone/current/bin/codex
EOF
```

For the VPS image, switch the launcher and names:

```sh
sudo tee /etc/creator-engine/ce-codex-seat-vps.env >/dev/null <<'EOF'
CE_CODEX_SEAT_LAUNCHER=deploy/vps-runsc/run-vps-runsc.sh
CE_CODEX_SEAT_CONTAINER_NAME=ce-vps-codex
CE_VPS_CONTAINER_NAME=ce-vps-codex
CE_VPS_REPO=/workspace/creator-engine
CE_VPS_CODEX_HOME=/home/ce/.codex
EOF
```

Enable an instance:

```sh
sudo cp deploy/systemd/ce-codex-seat@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ce-codex-seat@dgx.service
```

Verify herdr without host tmux:

```sh
docker exec --env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane list
docker exec --env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1
docker exec --env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane send w1:p1 $'printf detached-herdr-ok\\n\\n'
```
