# PR path manifest - ce221-probe-gvisor-detect

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce221-probe-gvisor-detect

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#221 — fix a real gVisor blind spot in the CE containment-attestation
probe (`containment_probe.py`, added in ce-ops#221 Fix-1 / #388). A live WAVE-2
dry-run showed that probing a REAL gVisor container's host PID — the
`runsc-sandbox` process `docker inspect --format {{.State.Pid}}` returns —
yielded `backend: "bwrap"` (wrong) and listed `ns:pid:host`, `ns:user:host`,
`root:host` as gaps. Root cause: backend detection inspected only the cgroup
string + mount-root link; for a gVisor sandbox PID the cgroup is a plain
`docker-<id>.scope` and root is `/`, so it fell through to the bwrap branch. The
DEFINITIVE gVisor signal is the process argv (`runsc-sandbox --platform=ptrace
...`), which the probe never read. This is on the WAVE-2 critical path — it is
what lets us declare a converted seat contained `backend=gvisor` by our OWN
probe, honestly.

The changes:
- `ProcReader` gains `cmdline(pid)` (`/proc/<pid>/cmdline`, NUL-split) and
  `comm(pid)` reads — pure, fixture-injectable like the existing ns/cgroup/
  status/root reads.
- Backend detection classifies `backend = "gvisor"` when the target argv0/comm
  is a `runsc` sentry/gofer host-process (any platform: ptrace/systrap/kvm),
  checked ABOVE the bwrap fallthrough; existing cgroup/mount-root `runsc`
  markers are still honoured (defense in depth).
- The gVisor verdict reflects the gVisor model: isolation is the userspace
  SENTRY, so the `runsc-sandbox` host-process legitimately shares host pid/user
  namespaces and has `root=/`. Those are NOT workload-exposure gaps for gVisor.
  `contained=true` is justified by the sandbox sentry present + dropped caps +
  non-host cgroup scope; the host-ns/root gaps are stripped and the reason
  explains the gVisor case. The bwrap/runc/host namespace-comparison model and
  the fail-closed contract are unchanged.
- Unit tests add a real gVisor-sandbox-PID fixture (cmdline
  `runsc-sandbox --platform=ptrace ...`, host pid/user ns, docker-scope cgroup,
  dropped caps) asserting `backend=="gvisor"` AND `contained==true` with no
  host-ns/root gaps, plus a `runsc-gofer` and a `runsc --platform=systrap`
  case; the existing raw-host / bwrap / partial / fail-closed cases are kept.

Per-file purpose (the closed path-set - 4 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce221-probe-gvisor-detect.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce221-probe-gvisor-detect.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/containment_probe.py`** *(M)* - argv/comm read + gVisor backend detection + gVisor verdict model.
- **`validators/tests/unit/test_containment_probe.py`** *(M)* - real gVisor-sandbox-PID detection coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5be9a2cde47d24a82a7d9aef3cfe13f6d6570130e9795910190cd2af81db6592

```text
.ce/changelog/ce221-probe-gvisor-detect.md
.ce/pr-manifests/ce221-probe-gvisor-detect.md
validators/creator_engine_validator/containment_probe.py
validators/tests/unit/test_containment_probe.py
```
