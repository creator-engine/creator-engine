# Review Pickup Daemon

`cev3 review-pickup` can run as the controller-side review routing daemon. It
polls scoped open PRs, skips draft/failed-CI/already-reviewed PRs, and requests a
non-author governed reviewer seat when `--apply` is set.

Keep credentials out of unit files and logs. Store the controller PAT in the
normal pickup key file, for example:

```sh
install -d -m 0700 /etc/ce-keys
install -m 0600 controller.pat /etc/ce-keys/controller.pat
```

## systemd template

Create `/etc/ce/review-pickup.env`:

```sh
CE_REVIEW_PICKUP_REPO=OWNER/REPO
CE_REVIEW_PICKUP_SEATS=ce-dev-2,ce-dev-3,ce-dev-4
CE_REVIEW_PICKUP_INTERVAL=300
CE_REVIEW_PICKUP_KEYS_DIR=/etc/ce-keys
CE_REVIEW_PICKUP_WORKDIR=/workspace/creator-engine
```

Create `/etc/systemd/system/ce-review-pickup@.service`:

```ini
[Unit]
Description=Creator Engine review-pickup daemon (%i)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/ce/review-pickup.env
ExecStart=/usr/bin/env bash -lc 'cd "$CE_REVIEW_PICKUP_WORKDIR" && exec cev3 review-pickup --identity "$1" --keys-dir "$CE_REVIEW_PICKUP_KEYS_DIR" --repo "$CE_REVIEW_PICKUP_REPO" --seat "$CE_REVIEW_PICKUP_SEATS" --apply --loop --interval "$CE_REVIEW_PICKUP_INTERVAL"' bash %i
Restart=always
RestartSec=15
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Start it:

```sh
systemctl daemon-reload
systemctl enable --now ce-review-pickup@controller.service
```

Use `--dry-run` instead of `--apply` during rollout if you want JSONL routing
logs without reviewer-request mutations.

## nohup fallback

```sh
cd /workspace/creator-engine
nohup cev3 review-pickup \
  --identity controller \
  --keys-dir /etc/ce-keys \
  --repo OWNER/REPO \
  --seat ce-dev-2,ce-dev-3,ce-dev-4 \
  --apply \
  --loop \
  --interval 300 \
  >>/var/log/ce-review-pickup.out \
  2>>/var/log/ce-review-pickup.jsonl &
```
