# Integrator Belt Daemon

The autonomous merge daemon is exposed through the v3 CLI:

```bash
python -m creator_engine_validator.v3_cli queue-daemon --repo OWNER/REPO --once --dry-run
python -m creator_engine_validator.v3_cli queue-daemon --repo OWNER/REPO --loop --interval 60
```

Use `--org ORG` instead of `--repo OWNER/REPO` only when the token is intended to operate
across that org scope. The daemon refuses an unscoped run.

For hosts without a service manager, run it under `nohup` from a controlled environment:

```bash
GH_TOKEN=... nohup python -m creator_engine_validator.v3_cli queue-daemon \
  --repo OWNER/REPO \
  --loop \
  --interval 60 \
  >> .ce/integrator-belt/daemon.log 2>&1 &
```

For systemd or another supervisor, use the same command line and let the supervisor own restart
policy, environment injection, and log routing. The daemon logs one JSON line per decision to
stderr and never prints token values.
