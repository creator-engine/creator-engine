"""Fast tests for contained-launch pre-spawn policy validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, launch_runtime
from creator_engine_validator.launch_runtime import (
    ContainedLaunchPreflightRefused,
    ContainedLaunchPlanUnverifiable,
    _validate_contained_launch_plan,
)
from creator_engine_validator.tmux_adapter import TmuxPane


pytestmark = pytest.mark.fast

_VALID_DIGEST = "sha256:" + "a" * 64
_ZERO_DIGEST = "sha256:" + "0" * 64


def _make_policy(
    *,
    sha: str = _VALID_DIGEST,
    mounts: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "kind": "runtime-policy-record",
        "policy_id": "test-policy",
        "image_ref": {"name": "ghcr.io/test/ce-seat", "sha": sha},
        "mount_manifest": mounts if mounts is not None else [],
    }


def test_zero_digest_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    policy = _make_policy(sha=_ZERO_DIGEST, mounts=[{"path": str(tmp_path), "mode": "rw"}])

    with pytest.raises(ContainedLaunchPreflightRefused, match="placeholder"):
        _validate_contained_launch_plan(policy, sentinel)


def test_valid_digest_passes(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    policy = _make_policy(mounts=[{"path": str(tmp_path), "mode": "rw"}])

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert updated["image_ref"]["sha"] == _VALID_DIGEST
    assert warnings == []


def test_absent_optional_dotfile_skipped(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_dir = str(tmp_path / "home" / "user" / ".claude")
    policy = _make_policy(
        mounts=[
            {"path": str(tmp_path), "mode": "rw"},
            {"path": absent_dir, "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert absent_dir not in [entry["path"] for entry in updated["mount_manifest"]]
    assert any("skipping mount" in warning for warning in warnings)


def test_absent_config_claude_skipped(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_dir = str(tmp_path / "home" / "user" / ".config" / "claude")
    policy = _make_policy(
        mounts=[
            {"path": str(tmp_path), "mode": "rw"},
            {"path": absent_dir, "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert absent_dir not in [entry["path"] for entry in updated["mount_manifest"]]
    assert warnings


def test_absent_required_path_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_required = str(tmp_path / "required" / "workspace")
    policy = _make_policy(
        mounts=[
            {"path": str(tmp_path), "mode": "rw"},
            {"path": absent_required, "mode": "ro"},
        ]
    )

    with pytest.raises(
        ContainedLaunchPlanUnverifiable,
        match="bind source path does not exist",
    ):
        _validate_contained_launch_plan(policy, sentinel)


def test_sentinel_not_covered_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "other-dir" / "sentinel-wrapper.sh"
    sentinel.parent.mkdir()
    sentinel.touch()
    mounted_dir = tmp_path / "mounted"
    mounted_dir.mkdir()
    policy = _make_policy(mounts=[{"path": str(mounted_dir), "mode": "rw"}])

    with pytest.raises(
        ContainedLaunchPlanUnverifiable,
        match="not under any mounted source",
    ):
        _validate_contained_launch_plan(policy, sentinel)


def test_sentinel_covered_passes(tmp_path: Path) -> None:
    mounted_dir = tmp_path / "repo"
    mounted_dir.mkdir()
    sentinel = mounted_dir / ".ce" / "state" / "sentinel-wrapper.sh"
    sentinel.parent.mkdir(parents=True)
    sentinel.touch()
    policy = _make_policy(mounts=[{"path": str(mounted_dir), "mode": "rw"}])

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert len(updated["mount_manifest"]) == 1
    assert warnings == []


def test_returned_policy_excludes_absent_optional_mounts(tmp_path: Path) -> None:
    present = tmp_path / "present"
    present.mkdir()
    sentinel = present / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_optional = str(tmp_path / "some" / "path" / ".codex")
    policy = _make_policy(
        mounts=[
            {"path": str(present), "mode": "ro"},
            {"path": absent_optional, "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert updated["mount_manifest"] == [{"path": str(present), "mode": "ro"}]
    assert warnings


def test_empty_mount_manifest_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    policy = _make_policy(mounts=[])

    with pytest.raises(
        ContainedLaunchPreflightRefused,
        match="not under any mounted source",
    ):
        _validate_contained_launch_plan(policy, sentinel)


def test_no_warnings_when_all_mounts_present(tmp_path: Path) -> None:
    mounted = tmp_path / "workspace"
    mounted.mkdir()
    sentinel = mounted / "sentinel-wrapper.sh"
    sentinel.touch()
    codex_config = tmp_path / "home" / "user" / ".config" / "codex"
    codex_config.mkdir(parents=True)
    policy = _make_policy(
        mounts=[
            {"path": str(mounted), "mode": "rw"},
            {"path": str(codex_config), "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert len(updated["mount_manifest"]) == 2
    assert warnings == []


# ---------------------------------------------------------------------------
# launch() integration — demotion branch and parent-refusal abort
#
# These tests drive ``launch_runtime.launch()`` directly, monkeypatching only
# ``_validate_contained_launch_plan`` so the preflight behaviour is isolated
# without re-testing the validator's own rules (covered above). The surrounding
# scaffolding mirrors the idioms in test_ce_launch_cli.py.
# ---------------------------------------------------------------------------

_LAUNCH_FAKE_PID = 4242
_LAUNCH_FAKE_PID_STR = str(_LAUNCH_FAKE_PID)
_FULL_CAP = "000001ffffffffff"
_DROPPED_CAP = "00000000a80425fb"


class _FakeAdapter:
    """Minimal tmux adapter stub: records spawns, returns a deterministic pane."""

    kind = "tmux"

    def __init__(self, *, pane_pid: int | None = None) -> None:
        self._pane_pid = pane_pid
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return True

    def session_exists(self, session: str) -> bool:  # noqa: ARG002
        return False

    def ensure_pane(
        self, *, session: str, window: str, command, cwd=None, env=None
    ) -> TmuxPane:
        self.spawned.append((session, window, list(command)))
        return TmuxPane(
            session_id="$1",
            window_id="@2",
            pane_id="%3",
            pane_pid=self._pane_pid,
        )


class _FakeContainerRunner:
    """Minimal container-runner stub for the docker backend visible-launch path."""

    def __init__(self, *, runtime_probe_pid: int | None = None) -> None:
        self._pid = runtime_probe_pid

    def available(self) -> bool:
        return True

    def egress_enforceable(self) -> bool:
        return True

    def run(self, argv, input_text=None):  # pragma: no cover
        raise AssertionError("visible bridge must not call delegate.run() directly")

    def runtime_probe(self, *, run_id: str, argv, surface):
        if self._pid is None:
            return None
        return {
            "pid": self._pid,
            "run_id": run_id,
            "launch_owned": True,
            "probe_contract": "ce-launch-owned-probe-v1",
            "source": "fake-container-runner",
        }


def _write_launch_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-contained-preflight-launch-0001",
        claim={"subject": "controller", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref=(
            "validators/tests/unit/test_contained_launch_preflight.py#launch-brain-ledger"
        ),
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    ledger = brain_runtime.ledger_path(state_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def _write_launch_docker_policy(repo_root: Path) -> Path:
    """Write a minimal docker runtime-policy-record at the default discovery path."""
    policy = {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "default-controller-docker",
        "policy_sha": "a" * 64,
        "role": "controller",
        "image_ref": {
            "name": "registry.example/creator-engine/seat",
            "sha": "sha256:" + "b" * 64,
        },
        "mount_manifest": [
            {
                "path": str(repo_root),
                "mode": "rw",
                "write_justification": "allocated worktree for this seat",
            },
        ],
        "egress_allowlist": [],
        "secret_allowlist": [],
        "grant_extensible": False,
        "grant_authority": "controller",
        "isolation_backend": "docker",
    }
    target = repo_root / ".ce" / "state" / "onboard" / "runtime" / "runtime-policy.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(policy, sort_keys=True), encoding="utf-8")
    return target


def _write_proc_file(base: Path, relpath: str, content: str) -> None:
    target = base / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _make_contained_proc_root(root: Path, pid: str) -> None:
    """Create a minimal /proc layout with host PID 1 and a contained target PID."""
    # Host PID 1 — unconfined, root namespaces
    for ns_name, ns_id in [
        ("mnt", "mnt:[4026531840]"),
        ("pid", "pid:[4026531836]"),
        ("net", "net:[4026531992]"),
        ("user", "user:[4026531837]"),
    ]:
        _write_proc_file(root, f"1/ns/{ns_name}", ns_id)
    _write_proc_file(root, "1/cgroup", "0::/init.scope\n")
    _write_proc_file(
        root, "1/status",
        f"Name:\tproof\nNoNewPrivs:\t0\nCapEff:\t{_FULL_CAP}\nCapBnd:\t{_FULL_CAP}\n",
    )
    _write_proc_file(root, "1/root", "/")
    # Target PID — different mount namespace, dropped caps, sandbox cgroup
    for ns_name, ns_id in [
        ("mnt", "mnt:[4026532500]"),
        ("pid", "pid:[4026532501]"),
        ("net", "net:[4026532502]"),
        ("user", "user:[4026532503]"),
    ]:
        _write_proc_file(root, f"{pid}/ns/{ns_name}", ns_id)
    _write_proc_file(
        root, f"{pid}/cgroup",
        "0::/system.slice/runsc-sandbox-proof.scope/runsc/container\n",
    )
    _write_proc_file(
        root, f"{pid}/status",
        f"Name:\tproof\nNoNewPrivs:\t1\nCapEff:\t{_DROPPED_CAP}\nCapBnd:\t{_DROPPED_CAP}\n",
    )
    _write_proc_file(root, f"{pid}/root", "/run/runsc/proof/rootfs")
    _write_proc_file(root, f"{pid}/comm", "runsc-sandbox\n")


def test_launch_unverifiable_demotes_to_warning(tmp_path: Path, monkeypatch, caplog) -> None:
    """ContainedLaunchPlanUnverifiable raised by the validator is caught by launch(),
    emits a WARNING, and the spawn proceeds normally (demotion branch, lines 2064-2065
    of launch_runtime.py).
    """
    import logging

    state_root = tmp_path / ".ce" / "state"
    _write_launch_brain_ledger(state_root)
    _write_launch_docker_policy(tmp_path)

    proc_root = tmp_path / "proc"
    _make_contained_proc_root(proc_root, _LAUNCH_FAKE_PID_STR)

    adapter = _FakeAdapter(pane_pid=_LAUNCH_FAKE_PID)
    container_runner = _FakeContainerRunner(runtime_probe_pid=_LAUNCH_FAKE_PID)

    sentinel_msg = "host-fact-not-verifiable-during-test"

    monkeypatch.setattr(
        launch_runtime,
        "_validate_contained_launch_plan",
        lambda _policy, _sentinel: (_ for _ in ()).throw(
            ContainedLaunchPlanUnverifiable(sentinel_msg)
        ),
    )

    with caplog.at_level(logging.WARNING, logger="creator_engine_validator.launch_runtime"):
        result = launch_runtime.launch(
            harness="hermes",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=container_runner,
            containment_proc_root=proc_root,
        )

    assert result.spawned is True, "launch() must proceed past Unverifiable (demotion branch)"
    assert adapter.spawned, "tmux pane must be spawned"
    warning_text = " ".join(r.message for r in caplog.records if r.levelno >= logging.WARNING)
    assert sentinel_msg in warning_text, (
        "launch() must emit the Unverifiable message as a WARNING"
    )


def test_launch_preflight_refused_parent_aborts(tmp_path: Path, monkeypatch) -> None:
    """ContainedLaunchPreflightRefused (the parent class, not the Unverifiable subclass)
    raised by the validator is NOT caught by the demotion handler and propagates out of
    launch(), aborting before any spawn.
    """
    state_root = tmp_path / ".ce" / "state"
    _write_launch_brain_ledger(state_root)
    _write_launch_docker_policy(tmp_path)

    adapter = _FakeAdapter(pane_pid=_LAUNCH_FAKE_PID)

    monkeypatch.setattr(
        launch_runtime,
        "_validate_contained_launch_plan",
        lambda _policy, _sentinel: (_ for _ in ()).throw(
            ContainedLaunchPreflightRefused("placeholder-digest-hard-refuse")
        ),
    )

    with pytest.raises(ContainedLaunchPreflightRefused, match="placeholder-digest-hard-refuse"):
        launch_runtime.launch(
            harness="hermes",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=_FakeContainerRunner(runtime_probe_pid=_LAUNCH_FAKE_PID),
        )

    assert adapter.spawned == [], "launch() must not spawn when preflight is refused"
