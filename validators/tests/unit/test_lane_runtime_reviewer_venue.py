"""G2.007.3 — ce lane launch can stand up a distinct, authority-carrying reviewer venue.

Two substrate properties are exercised here, both fail-closed:

1. Reviewer venue identity: a lane launched as ``role=reviewer`` + ``lane_kind=review``
   is recorded as a distinct reviewer venue in the ignored governance sidecar (the
   schema-locked pane record is untouched), and ``is_distinct_reviewer_venue`` proves it.
2. Reviewer authority injection: a ``reviewer_authority_ref`` is validated as a
   schema-valid reviewer-authority envelope BEFORE any side effect, exported into the
   pane environment as ``CE_REVIEWER_AUTHORITY_REF``, and recorded on the result/sidecar.
   An invalid envelope, or a ref on a non-reviewer venue, is refused before any spawn.

All state lives under pytest ``tmp_path``; the tmux adapter is a recording double.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, lane_runtime
from creator_engine_validator.tmux_adapter import TmuxPane

_SECRET = "ghp_supersecret_reviewer_token_value"


def _owner_only_env(path: Path, *, mode: int = 0o600) -> Path:
    path.write_text(f"GITHUB_REVIEWR_TOKEN={_SECRET}\n", encoding="utf-8")
    os.chmod(path, mode)
    return path


class RecordingAdapter:
    """tmux double that records the env passed to ensure_pane."""

    kind = "tmux"

    def __init__(self, *, available: bool = True):
        self._available = available
        self.spawned: list[tuple[str, str, list[str]]] = []
        self.last_env = None

    def is_available(self) -> bool:
        return self._available

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command)))
        self.last_env = dict(env) if env else None
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3",
                        pane_tty="/dev/pts/9", pane_pid=4242,
                        pane_cwd=(str(cwd) if cwd else None))


def _prompt(tmp_path: Path) -> tuple[Path, str]:
    p = tmp_path / "prompt.md"
    p.write_text("governed reviewer venue prompt\n", encoding="utf-8")
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def _ledger(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _claim(ledger_root: Path, controller_id: str, lane_id: str) -> None:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_timestamp": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "worktree_path": "/worktrees/rev-lane",
        "envelope_ref": "none",
        "branch": "reviewer/rev-lane",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
    }
    path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")


def _write_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-reviewer-venue-0001",
        claim={"subject": "lane", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref="validators/tests/unit/test_lane_runtime_reviewer_venue.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def _envelope(**override) -> dict:
    rec = {
        "envelope_id": "rva-pr108-reviewer",
        "mechanic": "pr_review",
        "pr_number": 108,
        "head_sha": "aa02b0ceb192b38f52da0d99f798e1e2710a8a22",
        "actor": "ubuntuaws745-cmyk",
        "ratified_prompt_sha": "ae1b9db11155f4ad841ef3fa399cd508c64d1ff184d1e0d1437e859c0dacfe27",
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T10:43:13Z",
    }
    rec.update(override)
    return rec


def _write_envelope(repo_root: Path, rel: str = "reviewer-authority.ce.yml", **override) -> str:
    path = repo_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"reviewer_authority_envelope": _envelope(**override)}), encoding="utf-8")
    return rel


CID = "ce-claude-g20073-engineer"
LID = "rev-lane"


def _inner_argv(result):
    """Recover the EXACT step-6c output argv embedded in the seat-sentinel wrapper.

    ce-ops#26: the pane command is now ``["/bin/sh", <wrapper>]``; the governed +
    bounded argv runs FOREGROUND inside the wrapper (the line before ``code=$?``).
    """
    import shlex

    wrapper = Path(result.events_ref).parent / "sentinel-wrapper.sh"
    lines = wrapper.read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    return shlex.split(lines[idx - 1])


def _launch_reviewer(tmp_path, *, adapter=None, **overrides):
    prompt, sha = _prompt(tmp_path)
    ledger = _ledger(tmp_path)
    _claim(ledger, CID, LID)
    _write_brain_ledger(tmp_path / ".ce" / "state")
    kwargs = dict(
        controller_id=CID,
        lane_id=LID,
        role="reviewer",
        prompt=prompt,
        prompt_sha=sha,
        repo_root=tmp_path,
        ledger_root=ledger,
        lane_kind="review",
        tmux_adapter=adapter or RecordingAdapter(),
    )
    kwargs.update(overrides)
    return lane_runtime.launch(**kwargs)


# --- venue identity predicate ---
def test_is_distinct_reviewer_venue_true_for_reviewer_review():
    assert lane_runtime.is_distinct_reviewer_venue(role="reviewer", lane_kind="review") is True


@pytest.mark.parametrize("role,kind", [
    ("implementer", "review"),
    ("reviewer", "implementation"),
    ("controller", None),
    ("reviewer", None),
])
def test_is_distinct_reviewer_venue_false_otherwise(role, kind):
    assert lane_runtime.is_distinct_reviewer_venue(role=role, lane_kind=kind) is False


# --- authority injection: env + sidecar + result ---
def test_reviewer_authority_ref_exported_to_pane_env(tmp_path):
    ref = _write_envelope(tmp_path)
    adapter = RecordingAdapter()
    result = _launch_reviewer(tmp_path, adapter=adapter, reviewer_authority_ref=ref)
    assert adapter.last_env is not None
    assert adapter.last_env.get("CE_REVIEWER_AUTHORITY_REF") == ref
    assert result.reviewer_authority_ref == ref


def test_reviewer_venue_identity_recorded_in_sidecar(tmp_path):
    ref = _write_envelope(tmp_path)
    result = _launch_reviewer(tmp_path, reviewer_authority_ref=ref)
    sidecar = lane_runtime._governance_sidecar_path(_ledger(tmp_path), CID, LID)
    assert sidecar.is_file()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data.get("reviewer_venue") is True
    assert data.get("role") == "reviewer"
    assert data.get("lane_kind") == "review"
    assert data.get("reviewer_authority_ref") == ref


# --- fail-closed refusals (before any side effect) ---
def test_invalid_envelope_refused_before_spawn(tmp_path):
    ref = _write_envelope(tmp_path, mechanic="merge")  # not a valid pr_review envelope
    adapter = RecordingAdapter()
    with pytest.raises(lane_runtime.ReviewerAuthorityInvalid):
        _launch_reviewer(tmp_path, adapter=adapter, reviewer_authority_ref=ref)
    assert adapter.spawned == []


def test_missing_envelope_file_refused_before_spawn(tmp_path):
    adapter = RecordingAdapter()
    with pytest.raises(lane_runtime.ReviewerAuthorityInvalid):
        _launch_reviewer(tmp_path, adapter=adapter, reviewer_authority_ref="nope.ce.yml")
    assert adapter.spawned == []


def test_authority_ref_on_non_reviewer_role_refused(tmp_path):
    ref = _write_envelope(tmp_path)
    adapter = RecordingAdapter()
    with pytest.raises(lane_runtime.ReviewerVenueIdentityInvalid):
        _launch_reviewer(tmp_path, adapter=adapter, reviewer_authority_ref=ref,
                         role="implementer")
    assert adapter.spawned == []


def test_authority_ref_with_wrong_lane_kind_refused(tmp_path):
    ref = _write_envelope(tmp_path)
    adapter = RecordingAdapter()
    with pytest.raises(lane_runtime.ReviewerVenueIdentityInvalid):
        _launch_reviewer(tmp_path, adapter=adapter, reviewer_authority_ref=ref,
                         lane_kind="implementation")
    assert adapter.spawned == []


def test_no_reviewer_authority_ref_leaves_env_clean(tmp_path):
    # A plain reviewer lane without an injected ref carries no authority env var.
    adapter = RecordingAdapter()
    _launch_reviewer(tmp_path, adapter=adapter)
    assert not (adapter.last_env or {}).get("CE_REVIEWER_AUTHORITY_REF")


# --- v3.1-G2f (F4/D2) seat-env-file exec-wrap ---


class _FakeSystemctl:
    """Minimal systemctl seam for the resource-bound composition test."""

    def __init__(self, *, cgroupfs_root: Path):
        self.calls: list[list[str]] = []
        self._root = cgroupfs_root

    def __call__(self, argv, check=False):
        self.calls.append(list(argv))
        if argv[2] == "show" and "ActiveState" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="inactive\n", stderr="")
        if argv[2] == "show" and "ControlGroup" in argv:
            unit = argv[-1].removesuffix(".scope")
            cg = f"/ce.slice/ce-fleet.slice/{unit}.scope"
            (self._root / cg.lstrip("/")).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(argv, 0, stdout=f"{cg}\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _ok_probe(runner=None, **_):
    return True, "fake host supports bounding"


def test_seat_env_file_wraps_command_without_secret_in_argv(tmp_path):
    env_file = _owner_only_env(tmp_path / "reviewer.env")
    adapter = RecordingAdapter()
    result = _launch_reviewer(
        tmp_path, adapter=adapter, command=["claude"],
        mcp_config_path=".hermes/rev-lane/mcp/ce-mcp.json",
        seat_env_file=env_file,
    )
    (_, _, command), = adapter.spawned
    # ce-ops#26: the pane runs the sentinel wrapper; the seat-env wrap is INSIDE it.
    assert command == ["/bin/sh", str(Path(result.events_ref).parent / "sentinel-wrapper.sh")]
    inner = _inner_argv(result)
    # the wrap prefix sources the file by PATH, then execs the governed command
    assert inner[:5] == [
        "sh", "-c", lane_runtime._SEAT_ENV_WRAP_SCRIPT, "ce-seat-env", str(env_file.resolve()),
    ]
    # the governed claude tokens survive byte-identically AFTER the wrap prefix
    assert "claude" in inner[5:]
    # the SECRET VALUE never appears in any argv token, the wrapper text, nor the env
    assert not any(_SECRET in tok for tok in inner), "secret leaked into argv"
    assert _SECRET not in (Path(result.events_ref).parent / "sentinel-wrapper.sh").read_text()
    assert not any(_SECRET in v for v in (adapter.last_env or {}).values())


def test_seat_env_file_refuses_missing_or_world_readable(tmp_path):
    # missing file → refused before any side effect (no pane spawn)
    adapter = RecordingAdapter()
    with pytest.raises(lane_runtime.SeatEnvFileInvalid):
        _launch_reviewer(tmp_path, adapter=adapter, command=["claude"],
                         seat_env_file=tmp_path / "absent.env")
    assert adapter.spawned == []
    # group/world-readable file → refused before any side effect
    world = _owner_only_env(tmp_path / "loose.env", mode=0o644)
    adapter2 = RecordingAdapter()
    with pytest.raises(lane_runtime.SeatEnvFileInvalid):
        _launch_reviewer(tmp_path, adapter=adapter2, command=["claude"],
                         seat_env_file=world)
    assert adapter2.spawned == []


def test_seat_env_wrap_sits_inside_resource_bound_wrap(tmp_path):
    """The resource-bound wrap is OUTERMOST (systemd-run …); the seat-env wrap sits
    inside it so the sourced env lives within the bounded unit."""
    env_file = _owner_only_env(tmp_path / "reviewer.env")
    adapter = RecordingAdapter()
    policy = tmp_path / "runtime-policy.yaml"
    policy.write_text(yaml.safe_dump({
        "resource_envelopes": [
            {"scope": "seat", "memory_high": "3500M", "memory_max": "4G",
             "memory_swap_max": "256M", "tasks_max": 512},
            {"scope": "fleet", "memory_max": "9G"},
        ],
        "resource_enforcement": "enforce",
    }, sort_keys=True), encoding="utf-8")
    result = _launch_reviewer(
        tmp_path, adapter=adapter, command=["claude"],
        mcp_config_path=".hermes/rev-lane/mcp/ce-mcp.json",
        seat_env_file=env_file,
        runtime_policy=policy,
        systemctl_runner=_FakeSystemctl(cgroupfs_root=tmp_path),
        support_probe=_ok_probe,
        cgroupfs_root=tmp_path,
    )
    (_, _, command), = adapter.spawned
    # ce-ops#26: the sentinel wrapper is OUTERMOST (the pane command); the bounded
    # command — systemd-run wrap with the seat-env wrap inside it — runs within it.
    assert command == ["/bin/sh", str(Path(result.events_ref).parent / "sentinel-wrapper.sh")]
    inner = _inner_argv(result)
    assert inner[0] == "systemd-run"  # the resource wrap is outermost INSIDE the wrapper
    sh_idx = inner.index("sh")
    # the seat-env wrap sits INSIDE the systemd-run wrap
    assert inner[sh_idx:sh_idx + 5] == [
        "sh", "-c", lane_runtime._SEAT_ENV_WRAP_SCRIPT, "ce-seat-env", str(env_file.resolve()),
    ]
    assert not any(_SECRET in tok for tok in inner)


def test_bridge_seat_env_wrap_matches_lane_runtime():
    """ce-ops#58 drift-guard. The bridge keeps a LOCAL copy of the seat-env wrap script
    (it imports no v1 module, and ``lane_runtime`` is v1-classified), and the bridge's
    step-2.5 gh-identity probe sources the seat-env with it. The probe is only honest if
    it sources IDENTICALLY to how ``ce lane launch --seat-env-file`` will — so the two
    copies MUST stay byte-identical."""
    from creator_engine_validator import v3_seat_bridge

    assert v3_seat_bridge._SEAT_ENV_WRAP_SCRIPT == lane_runtime._SEAT_ENV_WRAP_SCRIPT
