# Integrator Belt Daemon

The autonomous merge daemon is exposed through the v3 CLI:

```bash
python -m creator_engine_validator.v3_cli queue-daemon \
  --repo OWNER/REPO \
  --authorized-reviewer REVIEWER_LOGIN \
  --once \
  --dry-run
python -m creator_engine_validator.v3_cli queue-daemon \
  --repo OWNER/REPO \
  --authorized-reviewer REVIEWER_LOGIN \
  --loop \
  --interval 60
```

Use `--org ORG` instead of `--repo OWNER/REPO` only when the token is intended to operate
across that org scope. The daemon refuses an unscoped run.

`--authorized-reviewer` is required fail-closed config. Pass one or more GitHub
reviewer logins whose approvals may authorize merge-queue enqueue. Repeat the
flag or provide a comma-separated value, for example
`--authorized-reviewer ce-dev-3,ce-dev-4`. After the settle window, missing,
empty, or non-matching reviewer config prevents enqueue.

For hosts without a service manager, run it under `nohup` from a controlled environment:

```bash
GH_TOKEN=... CE_GATE_AUTHORIZED_REVIEWERS=ce-dev-3,ce-dev-4 \
  nohup python -m creator_engine_validator.v3_cli queue-daemon \
  --repo OWNER/REPO \
  --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS" \
  --loop \
  --interval 60 \
  >> .ce/integrator-belt/daemon.log 2>&1 &
```

For systemd or another supervisor, use the same command line and let the
supervisor own restart policy, environment injection, and log routing. The
checked-in systemd unit reads `CE_GATE_AUTHORIZED_REVIEWERS` from its
EnvironmentFile and passes it as `--authorized-reviewer
"$CE_GATE_AUTHORIZED_REVIEWERS"`. The daemon logs one JSON line per decision to
stderr and never prints token values.
