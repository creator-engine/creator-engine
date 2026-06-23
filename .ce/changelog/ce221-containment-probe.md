---
slug: ce221-containment-probe
date: 2026-06-23
kind: added
scope: live-runtime containment attestation probe
issue: ce-ops#221
---

Added the CE containment-attestation probe (ce-ops#221 Fix-1): containment is now
PROBED from the live kernel runtime, never self-reported. This is the guard that
would have caught a false "CONTAINED gVisor" claim.

New `ce containment-probe [pid]` subcommand reads the target process's actual
kernel state from `/proc/<pid>` and emits a structured verdict
(`{contained, backend, isolation, gaps, reason}`):

- namespaces — `/proc/<pid>/ns/{mnt,pid,net,user}` identity vs pid 1 (distinct ==
  isolated);
- cgroup — docker/containerd/runsc scope vs a host `user.slice` tmux scope;
- backend — gVisor (runsc) vs bwrap/container vs none, from cgroup/mount-root
  markers;
- caps — `CapEff`/`CapBnd` dropped vs the full host mask;
- no_new_privs and the `/proc/<pid>/root` mount-root target;
- network namespace isolation.

The verdict is FAIL-CLOSED: `contained=true` requires positive kernel-isolation
evidence (distinct mnt namespace AND non-host cgroup scope AND dropped caps);
any undeterminable signal forces `contained=false` with a reason, and the CLI
exits non-zero. The proc-reading is factored behind a `ProcReader` seam so the
verdict engine is unit-tested against fixture `/proc` trees (raw host process,
gVisor-isolated process, undeterminable case).
