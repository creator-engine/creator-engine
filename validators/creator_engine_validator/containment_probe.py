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

import os
from dataclasses import dataclass, field

# A full set of effective capabilities (CapEff) on a 64-cap kernel. A host shell
# typically carries the full bounding/effective mask; a sandboxed process drops
# most of it. We treat "still holds the full host mask" as *not* dropped.
_FULL_CAP_MASKS = {
    0x0000003FFFFFFFFF,  # 38-bit historical full mask
    0x0000007FFFFFFFFF,  # 39-bit
    0x000000FFFFFFFFFF,  # 40-bit
    0x000001FFFFFFFFFF,  # 41-bit (caps up to CAP_CHECKPOINT_RESTORE)
}


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


def _detect_backend(cgroup: str | None, pid_root: str | None) -> str:
    """Classify the sandbox backend from cgroup scope + mount-root markers.

    * ``gvisor`` — a ``runsc`` scope appears in the cgroup path (gVisor renders
      its sandbox/container under a ``runsc-*`` scope), or the mount root points
      into a runsc bundle.
    * ``bwrap`` — a bubblewrap / ``runc`` / ``containerd`` / ``docker`` /
      ``libpod`` (Podman) container scope, or a ``newroot``/``bwrap`` mount root.
    * ``none`` — no sandbox markers (host).
    """
    hay = (cgroup or "").lower()
    root = (pid_root or "").lower()
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
    backend = _detect_backend(cgroup, pid_root)

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
    # contained=True ONLY with positive kernel-isolation evidence:
    #   distinct mnt namespace  AND  non-host cgroup scope  AND  dropped caps.
    mnt_isolated = ns_isolation.get("mnt")
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
