# Installed CE Dogfood Migration

Use the installed console scripts for fleet automation instead of invoking CE
from a source checkout with `PYTHONPATH=validators python -m ...`.

## Belt Poll

Before:

```bash
PYTHONPATH=validators python -m creator_engine_validator.v3_cli queue-poll --repo creator-engine/creator-engine
```

After:

```bash
ce queue-poll --repo creator-engine/creator-engine
```

Keep the existing token environment (`GH_TOKEN` by default) and poll flags. The
installed `ce` command enters the same `creator_engine_validator.v3_cli:main`
handler as `python -m creator_engine_validator.v3_cli`.

## Queue Daemon

Before:

```bash
PYTHONPATH=validators python -m creator_engine_validator.v3_cli queue-daemon --repo creator-engine/creator-engine --loop --interval 120 --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS" --json
```

After:

```bash
ce queue-daemon --repo creator-engine/creator-engine --loop --interval 120 --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS" --json
```

For the checked-in systemd belt unit, remove any `Environment=PYTHONPATH=validators`
line and invoke the installed console script:

```ini
ExecStart=/usr/bin/env ce queue-daemon --repo "$CE_GATE_REPO" --loop --interval 120 --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS" --json
```

The daemon still needs the same `CE_GATE_REPO`, `GH_TOKEN`, and
`CE_GATE_AUTHORIZED_REVIEWERS` environment. Ensure the systemd manager's PATH
can resolve the installed `ce` script, or provide PATH in the env file.

## Review Pickup Daemon

Before:

```bash
PYTHONPATH=validators python -m creator_engine_validator.v3_cli review-pickup --identity <controller-identity> --repo <owner/repo> --seat <peer-seats> --loop --interval 120 --apply --inbox-path .ce/state/controller-inbox/awaiting-review.json --json
```

After:

```bash
ce review-pickup --identity <controller-identity> --repo <owner/repo> --seat <peer-seats> --loop --interval 120 --apply --inbox-path .ce/state/controller-inbox/awaiting-review.json --json
```

For the checked-in systemd review unit:

```ini
ExecStart=/usr/bin/env ce review-pickup --identity <controller-identity> --repo "$CE_GATE_REPO" --seat <peer-seats> --loop --interval 120 --apply --inbox-path .ce/state/controller-inbox/awaiting-review.json --json
```

Keep the review pickup token posture unchanged: `CE_PICKUP_TOKEN` is preferred,
with the existing key-file or ambient-auth fallback rules owned by the CLI.

## Lane Launch

Before:

```bash
PYTHONPATH=validators python -m creator_engine_validator.ce_cli lane launch ...
```

After:

```bash
ce lane launch ...
```

The pickup belt now builds `ce lane launch` by default. For a temporary
source-checkout fallback, set:

```bash
CE_LANE_LAUNCH_BIN="python -m creator_engine_validator.ce_cli"
```

## Verify Posture

Run:

```bash
ce doctor --require-installed-ce
```

The command fails when CE is still being run from a source checkout or through
`python -m`. JSON output exposes `ce_dogfood_invocation`,
`ce_package_origin`, and `ce_dogfood_installed` under `prerequisites`.
