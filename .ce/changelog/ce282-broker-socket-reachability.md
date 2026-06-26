---
slug: ce282-broker-socket-reachability
date: 2026-06-26
kind: fix
scope: deploy / egress broker socket reachability
issue: ce-ops#282
closes: ce-ops#270
---

**contained-seat broker socket reachability + canonical self-review mount.**

The GATE beta canary could not drive the egress broker from inside the container because
the mounted sockets were owned by group docker (gid 108) mode 0660, but the contained seat
runs uid/gid 1003. The seat fell back to host-side invocation. Additionally,
`run-vps-runsc.sh` had no canonical variable or mount for the self-review broker socket.

- `deploy/systemd/ce-egress-broker.service`: added `ExecStartPost` that sets the socket
  group to `CE_EGRESS_SEAT_GID` (a unit env var supplied via the EnvironmentFile) and mode
  0660, so the contained seat uid (whose gid matches the seat gid, e.g. 1003) can connect.
  Added comment that `CE_EGRESS_SEAT_GID` must match the container seat's gid.
- `deploy/systemd/ce-egress-self-review.service`: same `ExecStartPost` + comment treatment
  applied to the self-review broker socket.
- `deploy/vps-runsc/run-vps-runsc.sh`: added `CE_VPS_EGRESS_SELF_REVIEW_SOCKET` (host) /
  `CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET` (container, default `/run/ce-egress-review.sock`)
  variables mirroring the self-push pair exactly — same validation (require
  `CE_VPS_SEAT_ID` explicit + `dev-N` format when set, absolute-path checks for both host
  and container paths, socket existence check at runtime), same `--mount` + `--env`
  injection into the docker command. Closes ce-ops#270.
