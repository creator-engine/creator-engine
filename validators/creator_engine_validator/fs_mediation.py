"""Ring-1 Section-8c filesystem mediation — Landlock credential-path read-deny.

The CE git/gh runner shims (``runner.ring1_tool_guard``) mediate *shell-level*
``git``/``gh`` invocations, but they never see a NON-git file access: a Section-7
runner seat could still ``cat .env`` / ``open('.env')`` / read ``~/.ssh/id_rsa``
to exfiltrate credentials — entirely outside Ring-1. This module closes that gap
for the **runner subprocess** with kernel-enforced filesystem mediation: a
Linux **Landlock** read-confinement applied to the runner process tree at
launch. The confinement grants ``LANDLOCK_ACCESS_FS_READ_FILE`` only beneath an
explicit allow-list of read roots (the system runtime dirs every dynamically
linked program needs, plus the runner's own workspace); any file-content read
OUTSIDE those roots — the host's ``~/.ssh`` / ``~/.aws`` / ``~/.gnupg`` /
``~/.netrc`` / ``~/.git-credentials`` credential stores, other users' data, an
out-of-workspace ``.env`` — is denied by the kernel before a byte is read.

Design invariants (deliberate, load-bearing):

* **Scope = the RUNNER subprocess only.** This is applied at the local/os-native
  runner launch via a ``preexec_fn`` (apply-then-exec) so the launched process
  cannot opt out — Landlock survives ``execve`` and ``no_new_privs`` lets an
  unprivileged process keep the domain. It does NOT touch the deployed-Claude /
  controller path; OpenShell wires the same hook into its local runner launch
  seam before user code execs.
* **Single source of truth.** The credential-shape predicate is
  ``secret_paths.is_secret_path`` (shared line); this module REUSES it as a
  fail-closed configuration guard (an allow root that is itself credential-shaped
  is rejected) rather than re-deriving the rule set. Importing the *shared*
  ``secret_paths`` module from either version line is allowed, so the v1<->v3
  boundary stays intact.
* **Honest + fail-closed fallback.** When Landlock is unavailable on the host,
  a policy that REQUIRES Section-8c fails closed (refuses to launch the runner
  unconfined); an advisory caller gets a capability object that HONESTLY reports
  ``sandbox_fs_enforced=False`` — this module never silently claims FS mediation
  it did not enforce.
* **Defensive.** This hardens CE's own agent runtime; it is never an offensive
  capability.

Honest non-coverage (declared in the capability object, NOT silently dropped):
a credential file placed INSIDE an allowed workspace root is not carved out by
Landlock alone (Landlock has no sub-path deny) — that residual stays with the
in-band ``is_secret_path`` hook/shim layer; a re-exec or helper launched BEFORE
``restrict_self`` is not constrained; directory enumeration (``READ_DIR``) is
not mediated, only file-content reads (``READ_FILE``); network exfiltration of
credentials is Section-8b (#108); FUSE/fanotify routing of every ``open`` through
``is_secret_path`` is the deferred heavyweight option.
"""

from __future__ import annotations

import ctypes
import os
import struct
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from .secret_paths import CREDENTIAL_PATH_RULE_CLASSES, is_secret_path

# ---------------------------------------------------------------------------
# Landlock UAPI constants (Linux). The syscall numbers are arch-aligned for
# x86_64/aarch64 (Landlock was added with synchronized numbers); on an arch or
# kernel without the syscall the probe returns ``None`` and the honest fallback
# takes over, so a wrong number degrades to "unavailable", never to a false
# "enforced" claim.
# ---------------------------------------------------------------------------
_NR_LANDLOCK_CREATE_RULESET = 444
_NR_LANDLOCK_ADD_RULE = 445
_NR_LANDLOCK_RESTRICT_SELF = 446

_LANDLOCK_CREATE_RULESET_VERSION = 1 << 0
_LANDLOCK_RULE_PATH_BENEATH = 1

# Access-rights bitflags (UAPI ``LANDLOCK_ACCESS_FS_*``). We handle READ_FILE
# only: that mediates opening a file for reading (the credential-content exfil
# vector) while leaving execute/write/enumeration governed by ordinary DAC, so
# the collateral on a normal runner is minimal (dynamic-linker library loads use
# the EXECUTE/mmap path, which we do not handle, but library *reads* are covered
# by allow-listing the system runtime roots below).
_LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2

# ``prctl(PR_SET_NO_NEW_PRIVS, 1, ...)`` — required so an unprivileged process is
# allowed to call ``landlock_restrict_self``.
_PR_SET_NO_NEW_PRIVS = 38

#: The system runtime roots a dynamically linked program needs in order to load
#: its interpreter, shared libraries, CA/config files, ``/proc`` and device nodes.
#: Allow-listing these for READ keeps the runner functional; none of them is a
#: per-user credential store (``~/.ssh`` etc. live under ``$HOME``, which is
#: deliberately NOT here). ``$HOME`` credential dirs are denied by omission.
DEFAULT_SYSTEM_READ_ROOTS: tuple[str, ...] = (
    "/usr",
    "/lib",
    "/lib64",
    "/bin",
    "/sbin",
    "/etc",
    "/opt",
    "/proc",
    "/dev",
)

#: Stable mechanism identifiers surfaced in the capability declaration.
MECHANISM_LANDLOCK = "landlock-read-confinement"
MECHANISM_NONE = "none"

#: The honest non-coverage caveats, declared in every capability object so a
#: reader never mistakes Section-8c for total FS mediation.
NON_COVERAGE: tuple[str, ...] = (
    "a credential file INSIDE an allowed read root is not carved out by Landlock "
    "alone (no sub-path deny); that residual is covered by the in-band "
    "is_secret_path hook/shim layer",
    "a re-exec or helper launched BEFORE restrict_self is not constrained",
    "directory enumeration (READ_DIR) is not mediated; only file-content reads "
    "(READ_FILE)",
    "network exfiltration of credentials is Section-8b (#108), not this layer",
    "FUSE/fanotify routing of every open() through is_secret_path is the deferred "
    "heavyweight option",
)


class FsMediationError(RuntimeError):
    """Base class for Section-8c filesystem-mediation errors."""


class FsMediationUnavailable(FsMediationError):
    """Landlock FS mediation was REQUIRED by policy but cannot be enforced here.

    Raised by the fail-closed path so a Section-8c-required runner launch refuses
    rather than silently running unconfined.
    """


class LandlockApplyError(FsMediationError):
    """A Landlock syscall failed while applying the read-confinement.

    Raised inside the child (``preexec_fn``) so :class:`subprocess.Popen`
    surfaces it and the launch fails closed — never exec'ing unconfined after a
    partial ruleset.
    """


def _libc() -> ctypes.CDLL:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc


def landlock_abi_version() -> int | None:
    """Return the host's Landlock ABI version (>=1), or ``None`` when Landlock
    is unavailable (no LSM, syscall ``ENOSYS``, or a non-Linux host).

    Pure probe: it allocates no ruleset and changes no process state — it calls
    ``landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)``, the
    UAPI version query.
    """
    if sys.platform != "linux":
        return None
    try:
        libc = _libc()
    except OSError:
        return None
    res = libc.syscall(
        _NR_LANDLOCK_CREATE_RULESET,
        None,
        ctypes.c_size_t(0),
        ctypes.c_uint32(_LANDLOCK_CREATE_RULESET_VERSION),
    )
    if res < 1:
        return None
    return int(res)


def fs_mediation_available() -> bool:
    """True when Landlock can enforce a read-confinement on this host."""
    return landlock_abi_version() is not None


def _python_runtime_roots() -> tuple[str, ...]:
    """Read roots for the running Python interpreter + stdlib (so a confined
    runner that shells back into Python can still import its standard library)."""
    roots = {sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix}
    return tuple(sorted(r for r in roots if r))


@dataclass(frozen=True)
class RunnerFsConfinement:
    """The read-confinement applied to a runner subprocess.

    ``workspace_read_roots`` are the runner's own work directories (its checkout,
    scratch, ``$HOME`` set to a sandbox dir, …). ``DEFAULT_SYSTEM_READ_ROOTS``
    plus the Python runtime roots are added so a dynamically linked program runs;
    everything ELSE — notably the host's ``$HOME`` credential stores — is denied
    for file reads.

    **Fail-closed config guard (reuses the single source of truth):** if any
    configured workspace root is itself credential-shaped per
    ``secret_paths.is_secret_path``, construction raises — you cannot accidentally
    allow-list a credential store back into the runner's read surface.
    """

    workspace_read_roots: tuple[str, ...]
    include_system_roots: bool = True
    include_python_roots: bool = True

    def __post_init__(self) -> None:
        if not self.workspace_read_roots:
            raise ValueError("at least one workspace read root is required")
        for root in self.workspace_read_roots:
            if not isinstance(root, str) or not root.strip():
                raise ValueError(f"workspace read root must be a non-empty path: {root!r}")
            label = is_secret_path(root)
            if label is not None:
                raise ValueError(
                    f"refusing to allow-list a credential-shaped read root {root!r} "
                    f"(matched rule: {label}); it would re-expose a credential store "
                    "to the runner"
                )

    def resolved_read_roots(self) -> tuple[str, ...]:
        """The full, de-duplicated allow-list of read roots, in a stable order.

        Non-existent roots are kept here (the declaration is intent); the applier
        skips ones that cannot be opened so a missing optional root never makes
        the launch fail.
        """
        roots: list[str] = []
        if self.include_system_roots:
            roots.extend(DEFAULT_SYSTEM_READ_ROOTS)
        if self.include_python_roots:
            roots.extend(_python_runtime_roots())
        roots.extend(self.workspace_read_roots)
        seen: set[str] = set()
        ordered: list[str] = []
        for r in roots:
            if r not in seen:
                seen.add(r)
                ordered.append(r)
        return tuple(ordered)


@dataclass(frozen=True)
class FsMediationCapability:
    """An HONEST declaration of what Section-8c enforced for one runner launch.

    Serializable to a plain dict for the evidence spine. ``sandbox_fs_enforced``
    is the load-bearing field: ``False`` means NO kernel FS mediation was applied
    (advisory/unavailable), and it is never ``True`` unless a Landlock ruleset was
    actually built and restricted onto the process.
    """

    sandbox_fs_enforced: bool
    mechanism: str
    landlock_abi: int | None
    handled_access: tuple[str, ...]
    allow_read_roots: tuple[str, ...]
    recognized_credential_classes: tuple[str, ...]
    non_coverage: tuple[str, ...] = NON_COVERAGE

    def to_dict(self) -> dict[str, object]:
        return {
            "sandbox_fs_enforced": self.sandbox_fs_enforced,
            "mechanism": self.mechanism,
            "landlock_abi": self.landlock_abi,
            "handled_access": list(self.handled_access),
            "allow_read_roots": list(self.allow_read_roots),
            "recognized_credential_classes": list(self.recognized_credential_classes),
            "non_coverage": list(self.non_coverage),
        }


def build_runner_fs_capability(
    confinement: RunnerFsConfinement, *, require_enforcement: bool
) -> FsMediationCapability:
    """Resolve the Section-8c capability for ``confinement`` on this host.

    When Landlock is available, returns an ``sandbox_fs_enforced=True`` capability
    describing the read-confinement that :func:`landlock_preexec` /
    :func:`run_confined` will apply.

    When Landlock is unavailable:

    * ``require_enforcement=True`` → raises :class:`FsMediationUnavailable`
      (fail closed: a Section-8c-required runner must not launch unconfined).
    * ``require_enforcement=False`` → returns an honest
      ``sandbox_fs_enforced=False`` capability (advisory; no FS mediation claimed).
    """
    abi = landlock_abi_version()
    if abi is None:
        if require_enforcement:
            raise FsMediationUnavailable(
                "Landlock filesystem mediation is required by policy (Ring-1 "
                "Section-8c) but is unavailable on this host; refusing to launch the "
                "runner without credential-path read-deny (fail-closed)"
            )
        return FsMediationCapability(
            sandbox_fs_enforced=False,
            mechanism=MECHANISM_NONE,
            landlock_abi=None,
            handled_access=(),
            allow_read_roots=confinement.resolved_read_roots(),
            recognized_credential_classes=CREDENTIAL_PATH_RULE_CLASSES,
        )
    return FsMediationCapability(
        sandbox_fs_enforced=True,
        mechanism=MECHANISM_LANDLOCK,
        landlock_abi=abi,
        handled_access=("read_file",),
        allow_read_roots=confinement.resolved_read_roots(),
        recognized_credential_classes=CREDENTIAL_PATH_RULE_CLASSES,
    )


def apply_read_confinement(read_roots: Iterable[str]) -> None:
    """Apply the Landlock read-confinement to the CURRENT process (in place).

    Builds a ruleset handling ``READ_FILE``, grants it beneath each existing root
    in ``read_roots``, sets ``no_new_privs``, then ``restrict_self``. After this
    returns, the process (and everything it ``execve``s) can read files only
    beneath the granted roots; any other file open for reading fails ``EACCES``.

    Intended to run in a child just before ``exec`` (see :func:`landlock_preexec`).
    Raises :class:`FsMediationUnavailable` if Landlock is not present and
    :class:`LandlockApplyError` on any syscall failure, so a caller never believes
    a partial or absent ruleset is enforcing.
    """
    if landlock_abi_version() is None:
        raise FsMediationUnavailable(
            "apply_read_confinement called but Landlock is unavailable on this host"
        )
    libc = _libc()

    # Create the ruleset. We pass the 8-byte v1 ``landlock_ruleset_attr`` (just
    # ``handled_access_fs``); a smaller-than-current attr is the UAPI-blessed way
    # to stay compatible across ABI versions.
    ruleset_attr = struct.pack("=Q", _LANDLOCK_ACCESS_FS_READ_FILE)
    ruleset_fd = libc.syscall(
        _NR_LANDLOCK_CREATE_RULESET, ruleset_attr, ctypes.c_size_t(len(ruleset_attr)), 0
    )
    if ruleset_fd < 0:
        err = ctypes.get_errno()
        raise LandlockApplyError(f"landlock_create_ruleset failed: {os.strerror(err)}")

    try:
        for root in read_roots:
            try:
                parent_fd = os.open(root, os.O_PATH | os.O_CLOEXEC)
            except OSError:
                # A missing/optional root is skipped, not fatal — the declared
                # allow-list is intent; only openable roots can be granted.
                continue
            try:
                # ``struct landlock_path_beneath_attr`` is packed: u64 access +
                # s32 parent_fd == 12 bytes ("=Qi" yields exactly that, no pad).
                rule_attr = struct.pack(
                    "=Qi", _LANDLOCK_ACCESS_FS_READ_FILE, parent_fd
                )
                rc = libc.syscall(
                    _NR_LANDLOCK_ADD_RULE,
                    ruleset_fd,
                    _LANDLOCK_RULE_PATH_BENEATH,
                    rule_attr,
                    0,
                )
                if rc != 0:
                    err = ctypes.get_errno()
                    raise LandlockApplyError(
                        f"landlock_add_rule failed for {root!r}: {os.strerror(err)}"
                    )
            finally:
                os.close(parent_fd)

        if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            err = ctypes.get_errno()
            raise LandlockApplyError(f"prctl(NO_NEW_PRIVS) failed: {os.strerror(err)}")

        if libc.syscall(_NR_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0) != 0:
            err = ctypes.get_errno()
            raise LandlockApplyError(f"landlock_restrict_self failed: {os.strerror(err)}")
    finally:
        os.close(ruleset_fd)


def landlock_preexec(confinement: RunnerFsConfinement) -> Callable[[], None]:
    """Return a ``preexec_fn`` that applies ``confinement`` in the child.

    Pass the result as :class:`subprocess.Popen`'s ``preexec_fn``: the
    confinement is applied AFTER fork and BEFORE exec, so the launched runner is
    confined from its first instruction and cannot opt out.
    """
    read_roots = confinement.resolved_read_roots()

    def _preexec() -> None:  # pragma: no cover - runs only in the forked child
        apply_read_confinement(read_roots)

    return _preexec


def compose_preexec_fns(
    first: Callable[[], None], second: Callable[[], None]
) -> Callable[[], None]:
    """Return a ``preexec_fn`` that runs ``first`` then ``second`` in the child."""

    def _preexec() -> None:  # pragma: no cover - runs only in the forked child
        first()
        second()

    return _preexec


def run_confined(
    argv: Sequence[str],
    confinement: RunnerFsConfinement,
    *,
    require_enforcement: bool = True,
    **popen_kwargs: object,
) -> subprocess.CompletedProcess:
    """Run ``argv`` as a runner subprocess under the Landlock read-confinement.

    Resolves the capability first (so ``require_enforcement`` fails closed when
    Landlock is unavailable), then launches ``argv`` with the confinement applied
    via ``preexec_fn``. Extra ``popen_kwargs`` (``cwd``, ``env``, ``capture_output``,
    ``text``, ``timeout`` …) are forwarded to :func:`subprocess.run`.
    """
    capability = build_runner_fs_capability(
        confinement, require_enforcement=require_enforcement
    )
    if capability.sandbox_fs_enforced:
        fs_preexec = landlock_preexec(confinement)
        caller_preexec = popen_kwargs.get("preexec_fn")
        if caller_preexec is None:
            popen_kwargs["preexec_fn"] = fs_preexec
        elif callable(caller_preexec):
            # Landlock must be installed before any caller-supplied child hook can
            # run, otherwise that hook could read credentials before exec.
            popen_kwargs["preexec_fn"] = compose_preexec_fns(fs_preexec, caller_preexec)
        else:
            raise TypeError("preexec_fn must be callable when supplied")
    return subprocess.run(list(argv), **popen_kwargs)  # type: ignore[arg-type]
