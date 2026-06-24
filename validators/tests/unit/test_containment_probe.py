"""ce-ops#221 Fix-1 — unit tests for the live-runtime containment probe.

Containment must be PROBED from the live kernel runtime, never self-reported.
These tests drive both the pure verdict engine
(:func:`creator_engine_validator.containment_probe.probe_containment`) and the
``ce containment-probe`` CLI surface against fixture ``/proc``-style trees, so
the PASS / FAIL-CLOSED branches are exercised deterministically and offline.

The three load-bearing cases (ce-ops#221):

* a raw host process (namespaces == host, host user-slice cgroup, full caps)
  -> ``contained: false``;
* a gVisor-isolated process (distinct namespaces, runsc cgroup, dropped caps)
  -> ``contained: true, backend: gvisor``;
* an undeterminable process (unreadable /proc) -> fail-closed
  ``contained: false``.
"""
from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli, containment_probe


# Full host capability mask (CAP_LAST_CAP=40 era -> 41-bit) and an example
# dropped sandbox mask.
_FULL_CAP = "000001ffffffffff"
_DROPPED_CAP = "00000000a80425fb"  # typical docker default-cap effective set


def _write(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_bytes(path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_executable(path, content: str) -> None:
    _write(path, content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _make_proc(
    tmp_path,
    pid: str,
    *,
    ns: dict,
    cgroup: str,
    status: str,
    root: str,
    cmdline: str | None = None,
    comm: str | None = None,
):
    base = tmp_path / pid
    for name, ident in ns.items():
        _write(base / "ns" / name, ident)
    _write(base / "cgroup", cgroup)
    _write(base / "status", status)
    _write(base / "root", root)
    if cmdline is not None:
        # /proc/<pid>/cmdline is NUL-separated with a trailing NUL.
        _write(base / "cmdline", "\0".join(cmdline.split(" ")) + "\0")
    if comm is not None:
        _write(base / "comm", comm + "\n")


def _use_target_root(proc_root, pid: str, target_root) -> None:
    root = proc_root / pid / "root"
    root.unlink(missing_ok=True)
    root.symlink_to(target_root, target_is_directory=True)


def _status(cap_eff: str, cap_bnd: str, nnp: str = "0") -> str:
    return (
        "Name:\ttarget\n"
        "Uid:\t1000\t1000\t1000\t1000\n"
        f"NoNewPrivs:\t{nnp}\n"
        f"CapEff:\t{cap_eff}\n"
        f"CapBnd:\t{cap_bnd}\n"
    )


def _host_proc(tmp_path) -> None:
    """pid 1 — the host reference (shared by every fixture below)."""
    _make_proc(
        tmp_path,
        "1",
        ns={
            "mnt": "mnt:[4026531840]",
            "pid": "pid:[4026531836]",
            "net": "net:[4026531992]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/init.scope\n",
        status=_status(_FULL_CAP, _FULL_CAP),
        root="/",
    )


# --------------------------------------------------------------------------- #
# Pure verdict engine.
# --------------------------------------------------------------------------- #
def test_raw_host_process_is_not_contained(tmp_path):
    """A raw host process == host namespaces, host cgroup, full caps -> false."""
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "4242",
        ns={
            "mnt": "mnt:[4026531840]",  # identical to host
            "pid": "pid:[4026531836]",
            "net": "net:[4026531992]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/user.slice/user-1000.slice/session-3.scope\n",
        status=_status(_FULL_CAP, _FULL_CAP),
        root="/",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("4242", reader=reader, host_pid="1")

    assert verdict.contained is False
    assert verdict.backend == "none"
    assert verdict.isolation["mnt"] is False
    assert verdict.isolation["caps"] is False
    assert "host cgroup scope" in verdict.reason or "shared with host" in verdict.reason


def test_gvisor_process_is_contained(tmp_path):
    """Distinct namespaces + runsc cgroup + dropped caps -> contained gvisor."""
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "5151",
        ns={
            "mnt": "mnt:[4026532500]",  # distinct from host
            "pid": "pid:[4026532501]",
            "net": "net:[4026532502]",
            "user": "user:[4026532503]",
        },
        cgroup=(
            "0::/system.slice/runsc-sandbox-"
            "9f2c1a.scope/runsc/cap-container\n"
        ),
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/run/runsc/bundles/9f2c1a/rootfs",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("5151", reader=reader, host_pid="1")

    assert verdict.contained is True
    assert verdict.backend == "gvisor"
    assert verdict.isolation["mnt"] is True
    assert verdict.isolation["caps"] is True
    assert verdict.isolation["net"] is True
    assert verdict.isolation["nnp"] is True
    assert verdict.isolation["root"] is True
    assert verdict.gaps == []


def test_bwrap_container_is_contained(tmp_path):
    """A docker/bwrap-style container is contained and classified bwrap."""
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "6262",
        ns={
            "mnt": "mnt:[4026532600]",
            "pid": "pid:[4026532601]",
            "net": "net:[4026532602]",
            "user": "user:[4026531837]",  # may share host userns; not required
        },
        cgroup="0::/system.slice/docker-abc123.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/var/lib/docker/overlay2/abc/merged",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("6262", reader=reader, host_pid="1")

    assert verdict.contained is True
    assert verdict.backend == "bwrap"


def test_real_gvisor_sandbox_pid_is_contained_by_cmdline(tmp_path):
    """A REAL gVisor sandbox host-PID is detected from its `runsc` argv.

    This is the live WAVE-2 blind spot: `docker inspect .State.Pid` on a runsc
    container returns the host PID of the SENTRY process, which is literally
    `runsc-sandbox --platform=ptrace ...`. gVisor's boundary is the userspace
    sentry, so this host process LEGITIMATELY shares host pid/user namespaces
    and has root=`/`, and its cgroup is a plain `docker-<id>.scope` with NO
    runsc marker. The old cgroup/root-only detector classified it as `bwrap`
    and reported ns:pid:host / ns:user:host / root:host as gaps. The argv read
    fixes both: backend==gvisor AND contained==true, with no host-ns/root gaps.
    """
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "3030",
        ns={
            "mnt": "mnt:[4026532700]",  # sentry has its own mnt ns
            "pid": "pid:[4026531836]",  # SHARES host pid ns (expected)
            "net": "net:[4026532702]",
            "user": "user:[4026531837]",  # SHARES host user ns (expected)
        },
        # Plain docker scope — NO runsc marker in the cgroup for the sandbox PID.
        cgroup="0::/system.slice/docker-7c9d2f0e.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/",  # the runsc-sandbox host process sees the host root
        cmdline="runsc-sandbox --platform=ptrace --root=/var/run/docker/runsc boot",
        comm="runsc-sandbox",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("3030", reader=reader, host_pid="1")

    assert verdict.backend == "gvisor"
    assert verdict.contained is True
    # The sentry host-process sharing host pid/user ns and root=/ must NOT be
    # reported as workload-exposure gaps for gVisor.
    assert "ns:pid:host" not in verdict.gaps
    assert "ns:user:host" not in verdict.gaps
    assert "root:host" not in verdict.gaps
    assert "gvisor" in verdict.reason.lower()


def test_gvisor_gofer_argv_classifies_gvisor(tmp_path):
    """The sibling `runsc-gofer` host-process also classifies as gVisor."""
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "3131",
        ns={
            "mnt": "mnt:[4026532710]",
            "pid": "pid:[4026531836]",
            "net": "net:[4026532712]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/system.slice/docker-7c9d2f0e.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/",
        cmdline="runsc-gofer --root=/var/run/docker/runsc gofer --bundle /run/bundle",
        comm="runsc-gofer",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("3131", reader=reader, host_pid="1")

    assert verdict.backend == "gvisor"
    assert verdict.contained is True


def test_gvisor_systrap_platform_argv_classifies_gvisor(tmp_path):
    """gVisor sentry on the systrap platform is still detected (any platform)."""
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "3232",
        ns={
            "mnt": "mnt:[4026532720]",
            "pid": "pid:[4026531836]",
            "net": "net:[4026532722]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/system.slice/docker-aa11bb.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/",
        cmdline="runsc --platform=systrap --root=/run/docker/runsc boot --bundle /b",
        comm="runsc",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("3232", reader=reader, host_pid="1")

    assert verdict.backend == "gvisor"
    assert verdict.contained is True


def test_runsc_prefixed_imposter_does_not_classify_gvisor(tmp_path):
    """A `runscape`-style imposter must NOT be classified as gVisor.

    Regression guard for the over-broad matcher: the old detector treated any
    argv0/comm basename that merely *started with* `runsc` (e.g. `runscape`,
    `runscan`, `runsc-foo`) as the gVisor sentry. On this fail-closed
    attestation surface that is dangerous: a false gVisor positive sends the
    verdict down the gVisor branch, which strips the ns:pid:host / ns:user:host
    / root:host gaps and can mark `contained=true` on only a non-host cgroup +
    dropped caps. Here we give a `runscape` process the otherwise-gVisor-looking
    shape (host pid/user ns, non-host docker cgroup, dropped caps, root=/) and
    assert it does NOT classify as gVisor and does NOT receive gVisor
    gap-stripping — it falls through to the normal namespace-comparison
    fail-closed path (mnt shared with host -> not contained).
    """
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "4040",
        ns={
            "mnt": "mnt:[4026531840]",  # SHARES host mnt ns (imposter is on host)
            "pid": "pid:[4026531836]",  # shares host pid ns
            "net": "net:[4026532742]",
            "user": "user:[4026531837]",  # shares host user ns
        },
        # Otherwise gVisor-looking: non-host docker scope + dropped caps + root=/.
        cgroup="0::/system.slice/docker-7c9d2f0e.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/",
        cmdline="/usr/bin/runscape --foo --bar",
        comm="runscape",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("4040", reader=reader, host_pid="1")

    # The imposter must NOT be classified as gVisor...
    assert verdict.backend != "gvisor"
    # ...and must NOT get gVisor gap-stripping: the host-shared namespaces stay
    # visible as gaps and drive the normal fail-closed decision.
    assert "ns:pid:host" in verdict.gaps
    assert "ns:user:host" in verdict.gaps
    assert "root:host" in verdict.gaps
    assert verdict.contained is False
    assert "fail-closed" in verdict.reason


def test_undeterminable_process_fails_closed(tmp_path):
    """No readable /proc for the target -> fail-closed contained=false."""
    _host_proc(tmp_path)
    # Deliberately do NOT create /proc/<pid> for 7373.
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("7373", reader=reader, host_pid="1")

    assert verdict.contained is False
    assert "fail-closed" in verdict.reason
    assert verdict.isolation["mnt"] is None
    assert verdict.isolation["caps"] is None
    assert any("unreadable" in g for g in verdict.gaps)


def test_isolated_namespaces_but_host_caps_is_not_contained(tmp_path):
    """Positive-evidence rule: distinct ns is not enough without dropped caps.

    This is the exact shape of a false "CONTAINED" claim — partial isolation
    must NOT be reported as contained.
    """
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "8484",
        ns={
            "mnt": "mnt:[4026532800]",  # distinct
            "pid": "pid:[4026532801]",
            "net": "net:[4026531992]",  # shares host net
            "user": "user:[4026531837]",
        },
        cgroup="0::/user.slice/user-1000.slice/session-9.scope\n",  # host scope
        status=_status(_FULL_CAP, _FULL_CAP),  # full host caps
        root="/",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    verdict = containment_probe.probe_containment("8484", reader=reader, host_pid="1")

    assert verdict.contained is False
    assert verdict.isolation["caps"] is False


def test_verdict_is_pure_and_deterministic(tmp_path):
    """Same fixture tree -> identical payload across calls."""
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "9090",
        ns={
            "mnt": "mnt:[4026532900]",
            "pid": "pid:[4026532901]",
            "net": "net:[4026532902]",
            "user": "user:[4026532903]",
        },
        cgroup="0::/system.slice/runsc-x.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/run/runsc/rootfs",
    )
    reader = containment_probe.ProcReader(root=str(tmp_path))
    a = containment_probe.probe_containment("9090", reader=reader, host_pid="1").payload
    b = containment_probe.probe_containment("9090", reader=reader, host_pid="1").payload
    assert a == b


def test_ring1_probe_resolves_shim_under_target_proc_root(tmp_path):
    proc_root = tmp_path / "proc"
    target_root = tmp_path / "target-root"
    marker = tmp_path / "target-ring1-args"
    target_path_dir = "/__ce_target_only_ring1__/shim"
    (proc_root / "6001").mkdir(parents=True)
    target_shim_dir = target_root / target_path_dir.lstrip("/")
    target_shim_dir.mkdir(parents=True)
    target_shim_dir.chmod(0o700)
    assert not (Path(target_path_dir) / "git").exists()
    _write_executable(
        target_shim_dir / "git",
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$*\" > \"$CE_RING1_PROBE_MARKER\"\n"
        "exit 121\n",
    )
    _use_target_root(proc_root, "6001", target_root)
    _write_bytes(
        proc_root / "6001" / "environ",
        (
            f"PATH={target_path_dir}:/usr/bin\0"
            "CE_RING1_POSTURE=governed\0"
            f"CE_RING1_PROBE_MARKER={marker}\0"
        ).encode("utf-8"),
    )

    verdict = containment_probe.probe_ring1_enforcement(
        "6001",
        reader=containment_probe.ProcReader(root=str(proc_root)),
    )

    assert verdict["enforced"] is True
    assert verdict["shim_path"] == f"{target_path_dir}/git"
    assert marker.read_text(encoding="utf-8").strip().startswith("push --dry-run")


def test_ring1_probe_ignores_controller_host_shim_when_target_root_lacks_it(tmp_path):
    proc_root = tmp_path / "proc"
    target_root = tmp_path / "target-root"
    marker = tmp_path / "host-ring1-args"
    (proc_root / "6001").mkdir(parents=True)
    target_root.mkdir()
    _use_target_root(proc_root, "6001", target_root)

    host_shim_dir = tmp_path / "host-ring1"
    host_shim_dir.mkdir()
    host_shim_dir.chmod(0o700)
    _write_executable(
        host_shim_dir / "git",
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$*\" > \"$CE_RING1_PROBE_MARKER\"\n"
        "exit 121\n",
    )
    _write_bytes(
        proc_root / "6001" / "environ",
        (
            f"PATH={host_shim_dir}:/usr/bin\0"
            "CE_RING1_POSTURE=governed\0"
            f"CE_RING1_PROBE_MARKER={marker}\0"
        ).encode("utf-8"),
    )

    verdict = containment_probe.probe_ring1_enforcement(
        "6001",
        reader=containment_probe.ProcReader(root=str(proc_root)),
    )

    assert verdict["enforced"] is False
    assert verdict["reason"] == "guarded tool not found on target PATH"
    assert not marker.exists()


# --------------------------------------------------------------------------- #
# CLI surface.
# --------------------------------------------------------------------------- #
def test_cli_host_process_exits_nonzero(tmp_path, capsys):
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "4242",
        ns={
            "mnt": "mnt:[4026531840]",
            "pid": "pid:[4026531836]",
            "net": "net:[4026531992]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/user.slice/user-1000.slice/session-3.scope\n",
        status=_status(_FULL_CAP, _FULL_CAP),
        root="/",
    )
    rc = ce_cli.main(
        [
            "containment-probe",
            "4242",
            "--proc-root",
            str(tmp_path),
            "--host-pid",
            "1",
            "--json",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["contained"] is False
    assert out["backend"] == "none"


def test_cli_gvisor_process_exits_zero(tmp_path, capsys):
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "5151",
        ns={
            "mnt": "mnt:[4026532500]",
            "pid": "pid:[4026532501]",
            "net": "net:[4026532502]",
            "user": "user:[4026532503]",
        },
        cgroup="0::/system.slice/runsc-sandbox.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/run/runsc/rootfs",
    )
    rc = ce_cli.main(
        [
            "containment-probe",
            "5151",
            "--proc-root",
            str(tmp_path),
            "--host-pid",
            "1",
            "--json",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["contained"] is True
    assert out["backend"] == "gvisor"


def test_cli_full_attestation_reports_herdr_and_ring1_probe_evidence(tmp_path, capsys):
    target_root = tmp_path / "target-root"
    _host_proc(tmp_path)
    _make_proc(
        tmp_path,
        "5151",
        ns={
            "mnt": "mnt:[4026532500]",
            "pid": "pid:[4026532501]",
            "net": "net:[4026532502]",
            "user": "user:[4026532503]",
        },
        cgroup="0::/system.slice/runsc-sandbox.scope\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/run/runsc/rootfs",
    )
    _use_target_root(tmp_path, "5151", target_root)
    shim_dir = target_root / "ring1-shim"
    shim_dir.mkdir(parents=True)
    shim_dir.chmod(0o700)
    _write_executable(
        shim_dir / "git",
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$*\" > \"$CE_RING1_PROBE_MARKER\"\n"
        "exit 121\n",
    )
    _write_bytes(
        tmp_path / "5151" / "environ",
        (
            "PATH=/ring1-shim:/usr/bin\0"
            "CE_RING1_POSTURE=governed\0"
            f"CE_RING1_PROBE_MARKER={tmp_path / 'ring1-args'}\0"
        ).encode("utf-8"),
    )
    herdr = tmp_path / "herdr"
    _write_executable(
        herdr,
        "#!/usr/bin/env sh\n"
        "printf '{\"status\":\"ready\",\"pane_id\":\"%s\"}\\n' \"$4\"\n",
    )

    rc = ce_cli.main(
        [
            "containment-probe",
            "5151",
            "--proc-root",
            str(tmp_path),
            "--host-pid",
            "1",
            "--herdr-socket",
            str(tmp_path / "control.sock"),
            "--herdr-pane-id",
            "pane-1",
            "--herdr-binary",
            str(herdr),
            "--json",
        ]
    )
    out = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert out["contained"] is True
    assert out["attested"] is True
    assert out["herdr_session"]["live"] is True
    assert out["ring1_enforcement"]["enforced"] is True
    assert (tmp_path / "ring1-args").read_text(encoding="utf-8").strip().startswith(
        "push --dry-run"
    )


def test_cli_undeterminable_fails_closed(tmp_path, capsys):
    _host_proc(tmp_path)
    rc = ce_cli.main(
        [
            "containment-probe",
            "7373",
            "--proc-root",
            str(tmp_path),
            "--host-pid",
            "1",
            "--json",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["contained"] is False
    assert "fail-closed" in out["reason"]
