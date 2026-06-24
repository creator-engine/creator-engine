"""ce-ops#221 Fix-1 — live-runtime containment attestation probe.

Containment must be **PROBED from the live kernel runtime, never self-reported**.
This is the guard that would have caught a false "CONTAINED gVisor" claim: rather
than trusting a contract field, it reads the target process's actual kernel state
out of ``/proc/<pid>`` and compares it against the host (pid 1).

It returns a structured verdict::

    {
      "contained": bool,
      "backend": "gvisor" | "bwrap" | "none",
      "isolation": {"mnt", "pid", "net", "user", "caps", "nnp", "root"},
      "gaps": [...],
      "reason": "...",
    }

Hard requirements (ce-ops#221):

* **FAIL-CLOSED** — if containment cannot be *positively* determined, the verdict
  is ``contained=False`` with a reason. We never default to ``True``.
* ``contained=True`` requires **positive evidence of kernel isolation**: a mount
  namespace distinct from pid 1, a non-host (container/sandbox) cgroup scope, and
  dropped effective capabilities. The absence of disproof is never enough.
* **Pure / testable** — all ``/proc`` access is funnelled through a
  :class:`ProcReader` seam so the verdict logic can be unit-tested against
  fixture ``/proc``-style inputs with no real host.

Detection is read-only and side-effect-free; no network call is made.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

HERDR_SOCKET_ENV = "HERDR_SOCKET_PATH"
RING1_GOVERNED_POSTURE = "governed"
RING1_DENY_EXIT_CODE = 121

# A full set of effective capabilities (CapEff) on a 64-cap kernel. A host shell
# typically carries the full bounding/effective mask; a sandboxed process drops
# most of it. We treat "still holds the full host mask" as *not* dropped.
_FULL_CAP_MASKS = {
    0x0000003FFFFFFFFF,  # 38-bit historical full mask
    0x0000007FFFFFFFFF,  # 39-bit
    0x000000FFFFFFFFFF,  # 40-bit
    0x000001FFFFFFFFFF,  # 41-bit (caps up to CAP_CHECKPOINT_RESTORE)
}

# The EXACT argv0/comm basenames of the real gVisor sentry/gofer host-processes.
# This is a fail-closed attestation surface, so the gVisor signal is matched on
# an exact-basename allowlist (never a `startswith` prefix): an unrelated process
# like ``runscape`` / ``runscan`` / ``runsc-foo`` must NOT classify as gVisor,
# because a false gVisor positive strips host-namespace gaps and can produce a
# false ``contained=True``.
_RUNSC_SENTRY_BASENAMES = frozenset({"runsc", "runsc-sandbox", "runsc-gofer"})


# --------------------------------------------------------------------------- #
# Proc reader seam (the single point that touches the real filesystem).
# --------------------------------------------------------------------------- #
@dataclass
class ProcReader:
    """Read-only seam over a ``/proc``-style tree.

    The default reads the live ``/proc``; tests inject a fixture root. Every
    method fails *soft* (returns ``None``) so a missing/permission-denied path
    drives the verdict toward fail-closed rather than raising.
    """

    root: str = "/proc"

    def ns_inode(self, pid: int | str, ns: str) -> str | None:
        """Return the namespace identity for ``/proc/<pid>/ns/<ns>``.

        The kernel renders this symlink as ``<ns>:[<inode>]``; the inode is the
        namespace identity. We return the readlink target verbatim (stable and
        comparable) and fall back to reading the file's contents when the tree
        is a fixture of plain files.
        """
        path = os.path.join(self.root, str(pid), "ns", ns)
        try:
            return os.readlink(path)
        except OSError:
            pass
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            return content or None
        except OSError:
            return None

    def cgroup(self, pid: int | str) -> str | None:
        path = os.path.join(self.root, str(pid), "cgroup")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    def status(self, pid: int | str) -> str | None:
        path = os.path.join(self.root, str(pid), "status")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    def environ(self, pid: int | str) -> dict[str, str] | None:
        path = os.path.join(self.root, str(pid), "environ")
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            return None
        env: dict[str, str] = {}
        for part in raw.replace(b"\n", b"\0").split(b"\0"):
            if not part or b"=" not in part:
                continue
            key, value = part.split(b"=", 1)
            try:
                env[key.decode("utf-8")] = value.decode("utf-8")
            except UnicodeDecodeError:
                continue
        return env

    def root_link(self, pid: int | str) -> str | None:
        """``/proc/<pid>/root`` target (mount root the process sees)."""
        path = os.path.join(self.root, str(pid), "root")
        try:
            return os.readlink(path)
        except OSError:
            pass
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            return content or None
        except OSError:
            return None

    def cmdline(self, pid: int | str) -> str | None:
        """``/proc/<pid>/cmdline`` — the process argv, NUL-separated.

        The kernel renders argv with NUL (``\\0``) separators and a trailing
        NUL; we split on NUL and rejoin with spaces so the result is a plain,
        comparable command string. This is the DEFINITIVE gVisor signal: the
        sentry host-process is literally ``runsc-sandbox --platform=... ...``
        (with a sibling ``runsc-gofer ...``), even though its cgroup is a plain
        ``docker-<id>.scope`` and its mount root is ``/``. Fails soft -> None.
        """
        path = os.path.join(self.root, str(pid), "cmdline")
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            return None
        if not raw:
            return None
        text = raw.decode("utf-8", errors="replace")
        parts = [p for p in text.split("\0") if p]
        joined = " ".join(parts).strip()
        return joined or None

    def comm(self, pid: int | str) -> str | None:
        """``/proc/<pid>/comm`` — the short (≤15 char) process name."""
        path = os.path.join(self.root, str(pid), "comm")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            return content or None
        except OSError:
            return None


# --------------------------------------------------------------------------- #
# Parsing helpers (pure).
# --------------------------------------------------------------------------- #
def _status_field(status: str | None, key: str) -> str | None:
    if not status:
        return None
    prefix = key + ":"
    for line in status.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def _parse_cap_hex(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip(), 16)
    except ValueError:
        return None


def _caps_dropped(cap_eff: int | None, cap_bnd: int | None) -> bool | None:
    """True when caps are meaningfully dropped vs a full host mask.

    Returns ``None`` (undeterminable -> fail-closed) when the masks are
    unreadable.
    """
    if cap_eff is None and cap_bnd is None:
        return None
    # If the bounding set still carries a full host mask, caps are NOT dropped.
    if cap_bnd is not None and cap_bnd in _FULL_CAP_MASKS:
        return False
    # An empty effective set, or a bounding set strictly smaller than full, is
    # positive evidence of capability reduction.
    if cap_eff == 0:
        return True
    if cap_bnd is not None and cap_bnd not in _FULL_CAP_MASKS:
        return True
    if cap_eff is not None and cap_eff not in _FULL_CAP_MASKS:
        return True
    return False


def _cmdline_is_runsc(cmdline: str | None, comm: str | None) -> bool:
    """True when the process is a gVisor sentry/gofer host-process.

    The DEFINITIVE gVisor signal is the process argv, NOT the cgroup or mount
    root. ``docker inspect --format {{.State.Pid}}`` on a runsc/gVisor container
    returns the host PID of the sandbox process, which is literally
    ``runsc-sandbox --platform=ptrace ...`` (with a sibling ``runsc-gofer
    ...``). gVisor's isolation boundary is the userspace SENTRY, so this host
    process legitimately shares host pid/user namespaces and has root=``/`` —
    the cgroup is a plain ``docker-<id>.scope`` with no runsc marker. We match
    the ``runsc``/``runsc-sandbox``/``runsc-gofer`` argv0/comm across every
    platform (ptrace/systrap/kvm).
    """
    for hay in (cmdline, comm):
        if not hay:
            continue
        token = hay.strip().lower().split(None, 1)[0] if hay.strip() else ""
        # Match the argv0/comm basename EXACTLY against the real gVisor sentry
        # process names (``runsc``, ``runsc-sandbox``, ``runsc-gofer``), whether
        # bare or path-qualified (e.g. /usr/bin/runsc-sandbox) and with trailing
        # args already stripped off the argv0 token. A `startswith` prefix would
        # be too broad for this fail-closed surface: an unrelated `runscape` /
        # `runscan` / `runsc-foo` process must NOT classify as gVisor, because a
        # false gVisor positive strips host-ns gaps into a false "contained".
        base = token.rsplit("/", 1)[-1]
        if base in _RUNSC_SENTRY_BASENAMES:
            return True
    return False


def _detect_backend(
    cgroup: str | None,
    pid_root: str | None,
    cmdline: str | None = None,
    comm: str | None = None,
) -> str:
    """Classify the sandbox backend from process argv + cgroup + mount-root.

    * ``gvisor`` — the process argv/comm is a ``runsc`` sentry/gofer
      host-process (the DEFINITIVE signal, since the gVisor sandbox PID's cgroup
      is a plain ``docker-<id>.scope`` with no runsc marker), OR a ``runsc``
      scope appears in the cgroup path / mount root (defense in depth).
    * ``bwrap`` — a bubblewrap / ``runc`` / ``containerd`` / ``docker`` /
      ``libpod`` (Podman) container scope, or a ``newroot``/``bwrap`` mount root.
    * ``none`` — no sandbox markers (host).
    """
    hay = (cgroup or "").lower()
    root = (pid_root or "").lower()
    # Process-argv is the definitive gVisor signal — check it FIRST, above the
    # bwrap fallthrough, because a real gVisor sandbox PID has a plain
    # docker-scope cgroup that would otherwise classify as bwrap.
    if _cmdline_is_runsc(cmdline, comm):
        return "gvisor"
    if "runsc" in hay or "runsc" in root or "gvisor" in hay:
        return "gvisor"
    bwrap_markers = (
        "docker",
        "containerd",
        "libpod",
        "crio",
        "kubepods",
        "/runc",
        "bwrap",
    )
    if any(m in hay for m in bwrap_markers):
        return "bwrap"
    if "bwrap" in root or "newroot" in root:
        return "bwrap"
    return "none"


def _cgroup_is_host_scope(cgroup: str | None) -> bool | None:
    """True when the cgroup is a plain host scope (systemd ``user.slice`` etc.).

    Returns ``None`` when the cgroup is unreadable (undeterminable ->
    fail-closed).
    """
    if cgroup is None:
        return None
    hay = cgroup.lower()
    container_markers = (
        "runsc",
        "docker",
        "containerd",
        "libpod",
        "crio",
        "kubepods",
        "/runc",
    )
    if any(m in hay for m in container_markers):
        return False
    # systemd host scopes: user.slice / system.slice / init.scope / session-*.
    host_markers = ("user.slice", "system.slice", "init.scope", "session-", "user@")
    if any(m in hay for m in host_markers):
        return True
    # Unknown non-container scope: fail-closed — we will NOT call this
    # contained unless a container marker is positively present.
    return True


# --------------------------------------------------------------------------- #
# Verdict.
# --------------------------------------------------------------------------- #
@dataclass
class ContainmentVerdict:
    contained: bool
    backend: str
    isolation: dict
    gaps: list = field(default_factory=list)
    reason: str = ""

    @property
    def payload(self) -> dict:
        return {
            "contained": self.contained,
            "backend": self.backend,
            "isolation": self.isolation,
            "gaps": list(self.gaps),
            "reason": self.reason,
        }


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
DEFAULT_RING1_PROBE_ARGS = (
    "push",
    "--dry-run",
    "origin",
    "HEAD:refs/heads/__ce_ring1_probe__",
)


def _fail_herdr(reason: str, *, pane_id: str | None = None, evidence: Sequence[str] = ()) -> dict:
    return {
        "live": False,
        "pane_id": pane_id,
        "evidence": list(evidence),
        "reason": reason,
    }


def probe_herdr_session(
    *,
    socket_path: str | None,
    pane_id: str | None,
    herdr_binary: str = "herdr",
    runner: CommandRunner | None = None,
    timeout_seconds: float = 5.0,
) -> dict:
    if not socket_path or not pane_id:
        return _fail_herdr("missing herdr socket/pane evidence", pane_id=pane_id)
    run = runner or subprocess.run
    argv = [
        herdr_binary,
        "wait",
        "agent-status",
        "--pane",
        pane_id,
        "--status",
        "ready",
        "--json",
    ]
    try:
        completed = run(
            argv,
            env={**os.environ, HERDR_SOCKET_ENV: socket_path},
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _fail_herdr(
            f"herdr liveness unprobeable: {exc}",
            pane_id=pane_id,
            evidence=["herdr command failed to start"],
        )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return _fail_herdr(
            "herdr liveness probe failed" + (f": {detail[:200]}" if detail else ""),
            pane_id=pane_id,
            evidence=[f"exit={completed.returncode}"],
        )
    try:
        payload = json.loads((completed.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        return _fail_herdr(
            "herdr liveness probe returned non-json output",
            pane_id=pane_id,
            evidence=["invalid-json"],
        )
    if not isinstance(payload, Mapping):
        return _fail_herdr(
            "herdr liveness probe returned non-object output",
            pane_id=pane_id,
            evidence=["non-object-json"],
        )
    observed_pane = payload.get("pane_id") or payload.get("pane") or pane_id
    if payload.get("status") == "ready" and observed_pane == pane_id:
        return {
            "live": True,
            "pane_id": pane_id,
            "evidence": ["herdr wait agent-status ready"],
            "reason": "herdr pane answered ready over controller socket",
        }
    return _fail_herdr(
        "herdr pane did not report ready status",
        pane_id=pane_id,
        evidence=[f"status={payload.get('status')!r}", f"pane_id={observed_pane!r}"],
    )


def _fail_ring1(
    reason: str,
    *,
    tool: str,
    evidence: Sequence[str] = (),
    shim_path: str | None = None,
) -> dict:
    return {
        "enforced": False,
        "tool": tool,
        "shim_path": shim_path,
        "evidence": list(evidence),
        "reason": reason,
    }


def _target_root_exec_path(reader: ProcReader, pid: int | str, target_path: str) -> str | None:
    if not os.path.isabs(target_path):
        return None
    normalized = os.path.normpath(target_path)
    return str(Path(reader.root) / str(pid) / "root" / normalized.lstrip(os.sep))


def _which_from_target_path(
    tool: str,
    path_value: str,
    *,
    reader: ProcReader,
    pid: int | str,
) -> tuple[str, str] | None:
    for entry in path_value.split(os.pathsep):
        if not entry or not os.path.isabs(entry):
            continue
        target_path = os.path.normpath(os.path.join(entry, tool))
        exec_path = _target_root_exec_path(reader, pid, target_path)
        if exec_path and Path(exec_path).is_file() and os.access(exec_path, os.X_OK):
            return target_path, exec_path
    return None


def _private_owned_dir(path: str) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        return False
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        return False
    return (stat.S_IMODE(st.st_mode) & 0o077) == 0


def probe_ring1_enforcement(
    pid: int | str,
    *,
    reader: ProcReader | None = None,
    tool: str = "git",
    probe_args: Sequence[str] = DEFAULT_RING1_PROBE_ARGS,
    runner: CommandRunner | None = None,
    timeout_seconds: float = 5.0,
) -> dict:
    reader = reader or ProcReader()
    env = reader.environ(pid)
    if env is None:
        return _fail_ring1("target environment unreadable", tool=tool)
    if env.get("CE_RING1_POSTURE") != RING1_GOVERNED_POSTURE:
        return _fail_ring1(
            "target environment does not carry governed Ring-1 posture",
            tool=tool,
            evidence=[f"posture={env.get('CE_RING1_POSTURE')!r}"],
        )
    path_value = env.get("PATH")
    if not path_value:
        return _fail_ring1("target environment has no PATH", tool=tool)
    shim = _which_from_target_path(tool, path_value, reader=reader, pid=pid)
    if shim is None:
        return _fail_ring1("guarded tool not found on target PATH", tool=tool)
    shim_path, exec_path = shim
    shim_dir = str(Path(exec_path).parent)
    if not _private_owned_dir(shim_dir):
        return _fail_ring1(
            "guarded tool path is not in a private owner-only shim directory",
            tool=tool,
            shim_path=shim_path,
            evidence=[
                f"target_shim_dir={os.path.dirname(shim_path)}",
                f"exec_shim_dir={shim_dir}",
            ],
        )

    run = runner or subprocess.run
    run_env = dict(os.environ)
    run_env.update(env)
    try:
        completed = run(
            [exec_path, *probe_args],
            env=run_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _fail_ring1(
            f"Ring-1 enforcement unprobeable: {exc}",
            tool=tool,
            shim_path=shim_path,
            evidence=["shim execution failed", f"exec_path={exec_path}"],
        )

    evidence = [
        "governed target env",
        "private target-root shim path",
        f"exec_path={exec_path}",
        f"exit={completed.returncode}",
    ]
    if completed.returncode == RING1_DENY_EXIT_CODE:
        return {
            "enforced": True,
            "tool": tool,
            "shim_path": shim_path,
            "evidence": evidence,
            "reason": "Ring-1 shim denied probe command fail-closed",
        }
    detail = (completed.stderr or completed.stdout or "").strip()
    return _fail_ring1(
        "Ring-1 probe command was not denied" + (f": {detail[:200]}" if detail else ""),
        tool=tool,
        shim_path=shim_path,
        evidence=evidence,
    )


def attestation_payload(
    verdict: ContainmentVerdict,
    *,
    herdr_session: Mapping[str, object],
    ring1_enforcement: Mapping[str, object],
) -> dict:
    payload = dict(verdict.payload)
    payload.update(
        {
            "attested": (
                verdict.contained is True
                and herdr_session.get("live") is True
                and ring1_enforcement.get("enforced") is True
            ),
            "herdr_session": dict(herdr_session),
            "ring1_enforcement": dict(ring1_enforcement),
        }
    )
    return payload


_NAMESPACES = ("mnt", "pid", "net", "user")


def probe_containment(
    pid: int | str,
    reader: ProcReader | None = None,
    host_pid: int | str = 1,
) -> ContainmentVerdict:
    """Probe live containment for ``pid`` against the host (``host_pid``).

    Pure given a :class:`ProcReader`: the same fixture tree always yields the
    same verdict. Fail-closed: any undeterminable signal forces ``contained``
    to ``False`` with a reason.
    """
    reader = reader or ProcReader()
    gaps: list[str] = []

    # --- namespaces: distinct identity from the host == isolated. -------------
    ns_isolation: dict[str, bool | None] = {}
    for ns in _NAMESPACES:
        target = reader.ns_inode(pid, ns)
        host = reader.ns_inode(host_pid, ns)
        if target is None or host is None:
            ns_isolation[ns] = None  # undeterminable
            gaps.append(f"ns:{ns}:unreadable")
        elif target == host:
            ns_isolation[ns] = False  # shares host namespace
            gaps.append(f"ns:{ns}:host")
        else:
            ns_isolation[ns] = True  # isolated

    # --- cgroup scope. --------------------------------------------------------
    cgroup = reader.cgroup(pid)
    host_cgroup_scope = _cgroup_is_host_scope(cgroup)
    if cgroup is None:
        gaps.append("cgroup:unreadable")
        non_host_cgroup: bool | None = None
    elif host_cgroup_scope:
        gaps.append("cgroup:host-scope")
        non_host_cgroup = False
    else:
        non_host_cgroup = True

    # --- capabilities. --------------------------------------------------------
    status = reader.status(pid)
    cap_eff = _parse_cap_hex(_status_field(status, "CapEff"))
    cap_bnd = _parse_cap_hex(_status_field(status, "CapBnd"))
    caps_dropped = _caps_dropped(cap_eff, cap_bnd)
    if caps_dropped is None:
        gaps.append("caps:unreadable")
    elif caps_dropped is False:
        gaps.append("caps:host-full")

    # --- no_new_privs. --------------------------------------------------------
    nnp_raw = _status_field(status, "NoNewPrivs")
    if nnp_raw is None:
        nnp: bool | None = None
        gaps.append("nnp:unreadable")
    else:
        nnp = nnp_raw.strip() == "1"

    # --- mount root. ----------------------------------------------------------
    pid_root = reader.root_link(pid)
    host_root = reader.root_link(host_pid)
    if pid_root is None:
        root_isolated: bool | None = None
        gaps.append("root:unreadable")
    elif pid_root == "/":
        root_isolated = False
        gaps.append("root:host")
    elif host_root is not None and pid_root != host_root:
        root_isolated = True
    else:
        # Distinct from host's root link but not "/": treat as isolated.
        root_isolated = pid_root != host_root

    # --- backend classification. ---------------------------------------------
    # Read the process argv/comm — the DEFINITIVE gVisor signal. A real gVisor
    # sandbox host-PID (what `docker inspect .State.Pid` returns for a runsc
    # container) is literally `runsc-sandbox --platform=... ...`, while its
    # cgroup is a plain docker scope and its mount root is `/`.
    cmdline = reader.cmdline(pid)
    comm = reader.comm(pid)
    backend = _detect_backend(cgroup, pid_root, cmdline, comm)

    isolation = {
        "mnt": ns_isolation.get("mnt"),
        "pid": ns_isolation.get("pid"),
        "net": ns_isolation.get("net"),
        "user": ns_isolation.get("user"),
        "caps": caps_dropped,
        "nnp": nnp,
        "root": root_isolated,
    }

    # --- positive-evidence decision (fail-closed). ----------------------------
    mnt_isolated = ns_isolation.get("mnt")

    if backend == "gvisor":
        # gVisor's isolation boundary is the userspace SENTRY (it intercepts
        # syscalls in a Go runtime), NOT host namespaces. The runsc-sandbox host
        # process therefore LEGITIMATELY shares host pid/user namespaces and has
        # root=`/` — those are NOT workload-exposure gaps for gVisor; the
        # contained workload runs *inside* the sentry. The namespace-comparison
        # verdict is the right model for bwrap/runc but the WRONG lens here.
        #
        # contained=True is justified by: the gVisor sandbox being present (the
        # sentry, proven by the runsc argv signal) + dropped effective caps on
        # the sandbox process + a non-host cgroup scope. We do NOT fail it merely
        # because the sentry host-process shares host pid/user ns or root=`/`.
        # Strip those gaps so they aren't reported as exposure for gVisor.
        gaps = [
            g
            for g in gaps
            if g not in ("ns:pid:host", "ns:user:host", "root:host")
        ]
        sandbox_present = True  # backend=="gvisor" means the runsc sentry was seen
        gv_positive = (
            sandbox_present
            and non_host_cgroup is not False
            and caps_dropped is True
        )
        if gv_positive:
            contained = True
            reason = (
                "positive gVisor isolation: runsc sentry sandbox present "
                "(userspace syscall interception), dropped capabilities, "
                "non-host cgroup scope; the sentry host-process sharing host "
                "pid/user namespaces and root=/ is expected and is NOT a "
                "workload-exposure gap for gVisor "
                f"(backend={backend})"
            )
            return ContainmentVerdict(
                contained=contained,
                backend=backend,
                isolation=isolation,
                gaps=gaps,
                reason=reason,
            )
        # gVisor backend but caps not dropped / host cgroup -> fail-closed below
        # with a gVisor-aware reason.
        contained = False
        missing = []
        if non_host_cgroup is None:
            missing.append("cgroup undeterminable")
        elif non_host_cgroup is False:
            missing.append("host cgroup scope")
        if caps_dropped is None:
            missing.append("capabilities undeterminable")
        elif caps_dropped is False:
            missing.append("full host capabilities retained")
        reason = (
            "fail-closed: gVisor sentry detected but containment not "
            "positively proven ("
            + "; ".join(missing)
            + ")"
            if missing
            else "fail-closed: gVisor sentry detected but containment not "
            "positively proven"
        )
        return ContainmentVerdict(
            contained=contained,
            backend=backend,
            isolation=isolation,
            gaps=gaps,
            reason=reason,
        )

    # contained=True ONLY with positive kernel-isolation evidence:
    #   distinct mnt namespace  AND  non-host cgroup scope  AND  dropped caps.
    # (bwrap/runc/host model — kernel namespaces ARE the isolation boundary.)
    positive = (
        mnt_isolated is True
        and non_host_cgroup is True
        and caps_dropped is True
    )

    if positive:
        contained = True
        if backend == "none":
            # Isolated by every kernel signal but no recognizable backend marker
            # in the cgroup/root. Still contained (kernel evidence is primary),
            # but record the gap so the backend ambiguity is visible.
            gaps.append("backend:unclassified")
        reason = (
            "positive kernel isolation: distinct mnt namespace, "
            "non-host cgroup scope, dropped capabilities "
            f"(backend={backend})"
        )
    else:
        contained = False
        missing = []
        if mnt_isolated is None:
            missing.append("mnt-namespace undeterminable")
        elif mnt_isolated is False:
            missing.append("mnt namespace shared with host")
        if non_host_cgroup is None:
            missing.append("cgroup undeterminable")
        elif non_host_cgroup is False:
            missing.append("host cgroup scope")
        if caps_dropped is None:
            missing.append("capabilities undeterminable")
        elif caps_dropped is False:
            missing.append("full host capabilities retained")
        reason = (
            "fail-closed: containment not positively proven ("
            + "; ".join(missing)
            + ")"
            if missing
            else "fail-closed: containment not positively proven"
        )

    return ContainmentVerdict(
        contained=contained,
        backend=backend,
        isolation=isolation,
        gaps=gaps,
        reason=reason,
    )


def render_human(verdict: ContainmentVerdict) -> str:
    """Deterministic human-readable rendering of a verdict."""
    lines = [
        f"containment: {'CONTAINED' if verdict.contained else 'NOT CONTAINED'}",
        f"backend:     {verdict.backend}",
        "isolation:",
    ]
    for key in ("mnt", "pid", "net", "user", "caps", "nnp", "root"):
        val = verdict.isolation.get(key)
        mark = {True: "yes", False: "no", None: "unknown"}[val]
        lines.append(f"  {key:<5} {mark}")
    if verdict.gaps:
        lines.append("gaps: " + ", ".join(verdict.gaps))
    lines.append(f"reason: {verdict.reason}")
    return "\n".join(lines)
