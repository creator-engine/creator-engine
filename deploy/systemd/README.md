# Creator Engine Gate Daemons (systemd)

These units keep the autonomous gate daemons alive after host reboot:

- `ce-integrator-daemon.service`: runs `queue-daemon` for merge-queue repair.
- `ce-review-pickup-daemon.service`: runs `review-pickup` for review fan-out.

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
GH_TOKEN=ghp_integrator_token
CE_PICKUP_TOKEN=ghp_review_pickup_token
```

`GH_TOKEN` is required by the integrator daemon. Review pickup first uses
`CE_PICKUP_TOKEN`; if it is absent, the CLI falls back to
`~/.ce-keys/ce-dev-2.pat` unless ambient `gh` auth is explicitly enabled.
