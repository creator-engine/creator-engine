from __future__ import annotations

import json
import stat
from pathlib import Path

import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator import containment_status
from creator_engine_validator import harness_matrix as hm


_FULL_CAP = "000001ffffffffff"
_DROPPED_CAP = "00000000a80425fb"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_executable(path: Path, content: str) -> None:
    _write(path, content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_yaml(path: Path, data: object) -> None:
    _write(path, yaml.safe_dump(data, sort_keys=True))


def _status(cap_eff: str, cap_bnd: str, nnp: str = "0") -> str:
    return (
        "Name:\tseat\n"
        f"NoNewPrivs:\t{nnp}\n"
        f"CapEff:\t{cap_eff}\n"
        f"CapBnd:\t{cap_bnd}\n"
    )


def _make_proc(tmp_path: Path, pid: str, *, ns: dict[str, str], cgroup: str, status: str, root: str) -> None:
    base = tmp_path / pid
    for name, ident in ns.items():
        _write(base / "ns" / name, ident)
    _write(base / "cgroup", cgroup)
    _write(base / "status", status)
    _write(base / "root", root)


def _use_target_root(proc_root: Path, pid: str, target_root: Path) -> None:
    root = proc_root / pid / "root"
    root.unlink(missing_ok=True)
    root.symlink_to(target_root, target_is_directory=True)


def _host_proc(proc_root: Path) -> None:
    _make_proc(
        proc_root,
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


def _contained_proc(proc_root: Path, pid: str) -> None:
    _make_proc(
        proc_root,
        pid,
        ns={
            "mnt": "mnt:[4026532500]",
            "pid": "pid:[4026532501]",
            "net": "net:[4026532502]",
            "user": "user:[4026532503]",
        },
        cgroup="0::/system.slice/runsc-seat.scope/runsc/container\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/run/runsc/rootfs",
    )


def _host_scope_proc(proc_root: Path, pid: str) -> None:
    _make_proc(
        proc_root,
        pid,
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


def _seat_contract(seat_id: str, harness: str = "codex") -> dict:
    return {
        "seat_contract": {
            "seat_id": seat_id,
            "harness": harness,
            "launch_posture": {
                "model_pin": True,
                "strict_mcp_config": True,
                "terminal_visibility": "operator_visible",
                "setting_sources": ["project"],
                "full_permission_mode": True,
                "ring0_hook_pack_confirmed": True,
                "permission_mode_flag": "--yolo",
            },
            "refused_modes": [
                "bare",
                "print_headless",
                "background_agents",
                "remote_control",
                "settings_local_weakening",
            ],
            "enforcement_ring": "ring_0",
            "required_hook_pack": {
                "extension_id": "codex-hook-pack",
                "extension_kind": "hook_pack",
                "ring": "ring_1",
                "enforcement_strength": "defeasible",
                "hooks": [
                    {
                        "hook_id": "pretooluse",
                        "event": "PreToolUse",
                        "defeasible": True,
                        "failure_posture": "fail_open",
                    }
                ],
            },
            "emitting_role": "implementer",
            "operating_mode": "strict",
            "recorded_at": "2026-06-23T00:00:00Z",
        }
    }


def test_explicit_seat_bindings_probe_each_pid_and_fail_closed(tmp_path: Path):
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _contained_proc(proc_root, "5151")
    _host_scope_proc(proc_root, "4242")

    result = containment_status.probe_fleet(
        seat_specs=["seat-a=5151", "seat-b=4242", "seat-c=7373"],
        registry_paths=[],
        proc_root=proc_root,
        host_pid="1",
    )

    assert [row.payload for row in result.rows] == [
        {
            "seat": "seat-a",
            "contained": True,
            "backend": "gvisor",
            "herdr_session": "none",
            "ring1": "none",
        },
        {
            "seat": "seat-b",
            "contained": False,
            "backend": "none",
            "herdr_session": "none",
            "ring1": "none",
        },
        {
            "seat": "seat-c",
            "contained": False,
            "backend": "none",
            "herdr_session": "none",
            "ring1": "none",
        },
    ]


def test_registry_binding_uses_matrix_harness_and_live_pane_pid_not_contract_for_ring1(tmp_path: Path):
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _contained_proc(proc_root, "6001")

    registry = tmp_path / "registry"
    _write_yaml(registry / "matrix" / "codex.ce.yml", _seat_contract("seat-codex"))
    _write_yaml(
        registry / "panes" / "seat-codex.yaml",
        {
            "kind": "pane-registry-record",
            "record_type": "pane_identity",
            "schema_version": "1",
            "controller_id": "ctrl-one",
            "lane_id": "lane-one",
            "claim_ref": "claims/ctrl-one/lane-one.yaml",
            "host_id": "ce-dev-1",
            "pane_id": "seat-codex",
            "role": "implementer",
            "status": "active",
            "record_timestamp": "2026-06-23T00:00:00Z",
            "registered_at": "2026-06-23T00:00:00Z",
            "last_seen_at": "2026-06-23T00:00:00Z",
            "visibility": "operator_visible",
            "terminal": {
                "kind": "tmux",
                "session_id": "$1",
                "window_id": "@1",
                "pane_id": "%1",
                "pane_pid": 6001,
            },
        },
    )

    result = containment_status.probe_fleet(
        seat_specs=["seat-codex"],
        registry_paths=[registry],
        proc_root=proc_root,
        host_pid="1",
    )

    assert [row.payload for row in result.rows] == [
        {
            "seat": "codex",
            "contained": True,
            "backend": "gvisor",
            "herdr_session": "none",
            "ring1": "none",
        }
    ]


def test_ring1_enforced_only_after_target_shim_denies_probe(tmp_path: Path):
    proc_root = tmp_path / "proc"
    target_root = tmp_path / "target-root"
    _host_proc(proc_root)
    _contained_proc(proc_root, "6001")
    _use_target_root(proc_root, "6001", target_root)

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
        proc_root / "6001" / "environ",
        (
            "PATH=/ring1-shim:/usr/bin\0"
            "CE_RING1_POSTURE=governed\0"
            f"CE_RING1_PROBE_MARKER={tmp_path / 'ring1-args'}\0"
        ).encode("utf-8"),
    )

    result = containment_status.probe_fleet(
        seat_specs=["seat-codex=6001"],
        registry_paths=[],
        proc_root=proc_root,
        host_pid="1",
    )

    assert [row.payload for row in result.rows] == [
        {
            "seat": "seat-codex",
            "contained": True,
            "backend": "gvisor",
            "herdr_session": "none",
            "ring1": "enforced",
        }
    ]
    assert (tmp_path / "ring1-args").read_text(encoding="utf-8").strip().startswith(
        "push --dry-run"
    )


def test_herdr_registry_binding_is_live_only_when_socket_probe_succeeds(tmp_path: Path):
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _contained_proc(proc_root, "7001")
    herdr = tmp_path / "herdr"
    _write_executable(
        herdr,
        "#!/usr/bin/env sh\n"
        "printf '{\"status\":\"ready\",\"pane_id\":\"%s\"}\\n' \"$4\"\n",
    )

    registry = tmp_path / "registry"
    _write_yaml(
        registry / "seats" / "host" / "seat-herdr.yaml",
        {
            "kind": "seat-lifecycle-record",
            "record_type": "seat_lifecycle",
            "schema_version": "1",
            "seat": {"seat_id": "seat-herdr", "host_id": "ce-dev-1"},
            "terminal": {
                "kind": "herdr",
                "surface_ref": "herdr-surface-918aa1506d296ee1a72da70227854392",
                "pane_id": "pane-herdr",
                "pid": 7001,
                "socket_path": str(tmp_path / "control.sock"),
            },
            "harness": {"kind": "codex", "harness_session_id": "session-live"},
        },
    )

    result = containment_status.probe_fleet(
        seat_specs=["codex"],
        registry_paths=[registry],
        proc_root=proc_root,
        host_pid="1",
        herdr_binary=str(herdr),
    )

    assert [row.payload for row in result.rows] == [
        {
            "seat": "codex",
            "contained": True,
            "backend": "gvisor",
            "herdr_session": "live",
            "ring1": "none",
        }
    ]


def test_unprobeable_and_prose_only_seats_fail_closed_false(tmp_path: Path):
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    registry = tmp_path / "registry"
    _write_yaml(
        registry / "seats.yaml",
        {
            "seats": [
                {
                    "seat": "prose-seat",
                    "pid": 7373,
                    "contained": True,
                    "backend": "gvisor",
                    "note": "CONTAINED gVisor; do not trust this prose",
                }
            ]
        },
    )

    result = containment_status.probe_fleet(
        seat_specs=[],
        registry_paths=[registry],
        proc_root=proc_root,
        host_pid="1",
    )

    assert [row.seat for row in result.rows] == list(hm.HARNESSES)
    assert all(row.contained is False and row.backend == "none" for row in result.rows)
    assert "prose-seat" not in {row.seat for row in result.rows}
    assert result.ok is False


def test_cli_outputs_json_and_table(tmp_path: Path, capsys):
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _contained_proc(proc_root, "5151")

    rc = ce_cli.main(
        [
            "containment-status",
            "--seat",
            "seat-a=5151",
            "--proc-root",
            str(proc_root),
            "--host-pid",
            "1",
            "--json",
        ]
    )
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {
        "seats": [
            {
                "seat": "seat-a",
                "contained": True,
                "backend": "gvisor",
                "herdr_session": "none",
                "ring1": "none",
            }
        ]
    }

    rc = ce_cli.main(
        [
            "containment-status",
            "--seat",
            "seat-a=5151",
            "--proc-root",
            str(proc_root),
            "--host-pid",
            "1",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "seat-a" in out
    assert "gvisor" in out
    assert "enforced" not in out
