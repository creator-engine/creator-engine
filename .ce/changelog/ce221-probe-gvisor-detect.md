---
slug: ce221-probe-gvisor-detect
date: 2026-06-23
kind: fixed
scope: gVisor backend detection in the live-runtime containment probe
issue: ce-ops#221
---

Fixed a real gVisor blind spot in the CE containment-attestation probe
(`ce containment-probe`, added in ce-ops#221 Fix-1). A live WAVE-2 dry-run
showed that probing a REAL gVisor container's host PID — the `runsc-sandbox`
process that `docker inspect --format {{.State.Pid}}` returns for a runsc/gVisor
container — was misclassified as `backend: "bwrap"` and reported
`ns:pid:host`, `ns:user:host`, `root:host` as containment gaps.

Root cause: backend detection inspected only the cgroup string and mount-root
link. For a gVisor sandbox PID the cgroup is a plain `docker-<id>.scope` and the
root is `/`, so neither carried a `runsc`/`gvisor` marker and detection fell
through to the bwrap branch. The DEFINITIVE gVisor signal is the process argv:
the sentry host-process is literally `runsc-sandbox --platform=ptrace ...` (with
a sibling `runsc-gofer ...`), which the probe never read.

The fix:

- `ProcReader` gains a `cmdline(pid)` read (`/proc/<pid>/cmdline`, NUL-split)
  and a `comm(pid)` read, both pure and fixture-injectable like the existing
  ns/cgroup/status/root reads.
- Backend detection now classifies `backend = "gvisor"` when the target argv0
  or comm is a `runsc` sentry/gofer host-process (any platform:
  ptrace/systrap/kvm), checked ABOVE the bwrap fallthrough. The existing
  cgroup/mount-root `runsc` markers are still honoured (defense in depth).
- For a recognized gVisor backend the verdict reflects the gVisor model: the
  isolation boundary is the userspace SENTRY (it intercepts syscalls), so the
  `runsc-sandbox` host-process legitimately SHARES host pid/user namespaces and
  has `root=/`. Those are NOT workload-exposure gaps for gVisor.
  `contained=true` is justified by the sandbox sentry being present + dropped
  effective capabilities + a non-host cgroup scope; the host-ns/root gaps are
  stripped from the verdict and the reason explains the gVisor case.

The bwrap/runc/host model is unchanged — kernel namespaces remain its isolation
boundary, and the fail-closed contract still holds (a genuinely-uncontained host
process with no sandbox, host cgroup, and full caps stays `contained=false`).
A gVisor-shaped fixture (cmdline `runsc-sandbox --platform=ptrace ...`, host
pid/user ns, docker-scope cgroup, dropped caps) now asserts `backend=="gvisor"`
AND `contained==true`.
