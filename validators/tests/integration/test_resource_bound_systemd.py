"""v3.5-F Q1 — LIVE systemd integration proof for the bounding wrap.

Guarded ``skipif`` on hosts/runners without user-level cgroup delegation (no
systemd, no live user manager / session D-Bus, or no memory+pids delegation) —
CI-exercised where the runner supports it; elsewhere the pure tests plus the
recorded-evidence fixture (``fixtures/resource_bound_observed.json``) carry
the proof.

Covers the O6/O10 shape (a wrapped throwaway command lands in
``ce-fleet.slice/ce-seat-….scope`` with the limits applied), the launch-confirm
edges (``memory.oom.group`` write + fleet-slice cap on a live scope), and the
O9 shape (a runaway capped at 64M is OOM-killed in isolation, exit 137, the
wrapper's host process unaffected).

Every scope is throwaway (``--collect``, unique unit names); nothing durable
is written to the user manager.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Mapping

import pytest

from creator_engine_validator import resource_bound_spec as rbs

_LIVE_TEST_ENV = "CE_RUN_RESOURCE_BOUND_SYSTEMD_TESTS"
_DESKTOP_ENV_VARS = ("DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP", "DESKTOP_SESSION")


def _truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _live_systemd_test_gate(environ: Mapping[str, str] | None = None) -> tuple[bool, str]:
    """Refuse live resource-bound tests in desktop sessions.

    The OOM-kill proof intentionally starts transient user ``systemd`` scopes
    and kills one of them. On GNOME dogfood desktops that can surface
    application-stopped/OOM notifications to the human desktop. Keep the live
    proof to CI or an explicit non-interactive host opt-in; pure tests and the
    recorded evidence fixture cover ordinary local runs.
    """
    env = os.environ if environ is None else environ
    desktop_vars = [name for name in _DESKTOP_ENV_VARS if env.get(name)]
    if desktop_vars:
        return (
            False,
            "interactive desktop session detected "
            f"({', '.join(desktop_vars)} set); live OOM systemd tests are disabled",
        )
    if _truthy_env(env.get("CI")) or _truthy_env(env.get(_LIVE_TEST_ENV)):
        return True, "live resource-bound systemd tests enabled"
    return (
        False,
        f"set CI=1 or {_LIVE_TEST_ENV}=1 on a non-desktop host to run live "
        "resource-bound systemd tests",
    )


def _bounding_available() -> tuple[bool, str]:
    allowed, reason = _live_systemd_test_gate()
    if not allowed:
        return False, reason
    if shutil.which("systemd-run") is None or shutil.which("systemctl") is None:
        return False, "systemd-run/systemctl not on PATH"
    return rbs.probe_user_bounding()

_AVAILABLE, _REASON = _bounding_available()

live_systemd = pytest.mark.skipif(
    not _AVAILABLE,
    reason=f"live resource-bound systemd tests disabled/unavailable: {_REASON}",
)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.xdist_group("user-systemd"),
]


def _unique_unit(tag: str) -> str:
    return f"ce-seat-itest-{tag}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


def _bound(unit: str, **overrides) -> rbs.ResourceBound:
    values = dict(
        unit=unit,
        slice=rbs.DEFAULT_SLICE,
        memory_high="48M",
        memory_max="64M",
        memory_swap_max="0",
        tasks_max=16,
    )
    values.update(overrides)
    return rbs.ResourceBound(**values)


def test_live_systemd_gate_refuses_desktop_sessions():
    ok, reason = _live_systemd_test_gate(
        {"CI": "1", "DISPLAY": ":0", "XDG_CURRENT_DESKTOP": "GNOME"}
    )
    assert ok is False
    assert "interactive desktop session detected" in reason
    assert "DISPLAY" in reason


def test_live_systemd_gate_requires_ci_or_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("CI", "1")
    ok, reason = _live_systemd_test_gate({})
    assert ok is False
    assert _LIVE_TEST_ENV in reason


def test_live_systemd_gate_uses_ambient_environment_when_not_injected(monkeypatch):
    for name in _DESKTOP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CI", "1")
    ok, reason = _live_systemd_test_gate()
    assert ok is True
    assert "enabled" in reason


@pytest.mark.parametrize("env", [{"CI": "true"}, {_LIVE_TEST_ENV: "1"}])
def test_live_systemd_gate_accepts_headless_ci_or_explicit_opt_in(env):
    ok, reason = _live_systemd_test_gate(env)
    assert ok is True
    assert "enabled" in reason


@live_systemd
def test_wrapped_command_lands_in_fleet_slice_with_limits():
    """O6/O10: the wrap places the command in its scope with the limits live."""
    unit = _unique_unit("limits")
    probe = (
        'cg=$(cut -d: -f3- /proc/self/cgroup); printf "%s\\n" "$cg"; '
        'cat "/sys/fs/cgroup${cg}/memory.max" "/sys/fs/cgroup${cg}/memory.high" '
        '"/sys/fs/cgroup${cg}/pids.max"'
    )
    wrapped = rbs.build_bounded_command(["sh", "-c", probe], _bound(unit))
    proc = subprocess.run(wrapped, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    cgroup_path, memory_max, memory_high, pids_max = proc.stdout.strip().splitlines()
    # systemd dash-expands ce-fleet.slice to nested ce.slice/ce-fleet.slice.
    assert f"ce.slice/ce-fleet.slice/{unit}.scope" in cgroup_path
    assert memory_max == str(64 * 1024 * 1024)
    assert memory_high == str(48 * 1024 * 1024)
    assert pids_max == "16"


@live_systemd
def test_oom_group_write_and_fleet_cap_on_live_scope():
    """The launch-confirm edges against a real, briefly-lived seat scope."""
    unit = _unique_unit("confirm")
    wrapped = rbs.build_bounded_command(["sleep", "10"], _bound(unit))
    holder = subprocess.Popen(
        wrapped, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        target = rbs.write_oom_group(unit)
        assert target.name == "memory.oom.group"
        assert target.read_text(encoding="ascii").strip() == "1"
        # Idempotent runtime-only fleet cap on the (now-existing) slice.
        rbs.apply_fleet_cap("9G")
        rbs.apply_fleet_cap("9G")  # re-apply: idempotent by construction
    finally:
        holder.terminate()
        holder.wait(timeout=10)
        subprocess.run(
            ["systemctl", "--user", "set-property", "--runtime",
             rbs.DEFAULT_SLICE, "MemoryMax=infinity"],
            capture_output=True, text=True,
        )


@live_systemd
def test_isolated_kill_at_memory_max():
    """O9: a 64M-capped runaway dies ALONE — exit 137, this process unharmed.

    ``memory_high`` is pinned EQUAL to ``memory_max`` here: with a gap, the
    reclaim brake throttles the allocator into the O8 stall instead of letting
    it reach the kill ceiling within the test timeout (the very failure mode
    the design's high≈max ladder spacing exists to avoid).
    """
    unit = _unique_unit("oomkill")
    allocator = (
        "x=[]\n"
        "while True:\n"
        "    x.append(bytearray(8 * 1024 * 1024))\n"
    )
    wrapped = rbs.build_bounded_command(
        [sys.executable, "-c", allocator], _bound(unit, memory_high="64M")
    )
    proc = subprocess.run(wrapped, capture_output=True, text=True, timeout=60)
    # systemd-run propagates the kernel group-kill: SIGKILL -> 137 (or the raw
    # negative signal form depending on the propagation path).
    assert proc.returncode in (137, -9), (proc.returncode, proc.stderr[-300:])
    # The wrapper's host process (this test) is alive to assert it: isolation held.
