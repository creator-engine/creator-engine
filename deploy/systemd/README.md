# Creator Engine Gate Daemons (systemd)

These units keep the autonomous gate daemons alive after host reboot:

- `ce-integrator-daemon.service`: runs `queue-daemon` for merge-queue repair.
- `ce-review-pickup-daemon.service`: runs `review-pickup` for review fan-out.
- `ce-codex-seat@.service`: starts a detached runsc Codex seat container through
  the checked-in launcher and leaves Docker's restart policy on the container.

Install from the repository root:

```sh
deploy/systemd/install-gate-daemons-systemd.sh
```

The default install target is the user systemd manager at
`~/.config/systemd/user`. Use `--system` to install into `/etc/systemd/system`.
The installer renders the checked-in unit templates with the current source
checkout path, runs `daemon-reload`, enables both services, and starts them.
Use `--no-start` to render/enable without starting.

Create the env file before starting services. Defaults:

- user: `~/.config/creator-engine/gate-daemons.env`
- system: `/etc/creator-engine/gate-daemons.env`

Example:

```sh
CE_GATE_REPO=creator-engine/creator-engine
CE_GATE_AUTHORIZED_REVIEWERS=ce-dev-3,ce-dev-4
GH_TOKEN=ghp_integrator_token
CE_PICKUP_TOKEN=ghp_review_pickup_token
```

`GH_TOKEN` and `CE_GATE_AUTHORIZED_REVIEWERS` are required by the integrator
daemon. `CE_GATE_AUTHORIZED_REVIEWERS` is a comma-separated list of reviewer
GitHub logins whose approvals may authorize merge-queue enqueue; missing or
empty config fails closed. Review pickup first uses `CE_PICKUP_TOKEN`; if it is
absent, the CLI falls back to `~/.ce-keys/ce-dev-2.pat` unless ambient `gh`
auth is explicitly enabled.

## Detached Codex Seat Template

`ce-codex-seat@.service` is a system-level template for contained Codex seats.
It runs the selected launcher with `--detach tui`; the launcher renders
`docker run -d --name ...`, polls herdr readiness through `docker exec`, and
returns. The unit sets `CE_DGX_DOCKER_RESTART_POLICY=unless-stopped` and
`CE_VPS_DOCKER_RESTART_POLICY=unless-stopped`, so Docker supervises the
container after the one-shot launch completes. No host tmux is required.

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
