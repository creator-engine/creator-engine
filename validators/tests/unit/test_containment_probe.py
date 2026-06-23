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

import pytest

from creator_engine_validator import ce_cli, containment_probe


# Full host capability mask (CAP_LAST_CAP=40 era -> 41-bit) and an example
# dropped sandbox mask.
_FULL_CAP = "000001ffffffffff"
_DROPPED_CAP = "00000000a80425fb"  # typical docker default-cap effective set


def _write(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_proc(tmp_path, pid: str, *, ns: dict, cgroup: str, status: str, root: str):
    base = tmp_path / pid
    for name, ident in ns.items():
        _write(base / "ns" / name, ident)
    _write(base / "cgroup", cgroup)
    _write(base / "status", status)
    _write(base / "root", root)


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
