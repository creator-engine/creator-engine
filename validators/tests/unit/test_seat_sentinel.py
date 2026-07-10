"""ce-ops#26 seat lifecycle sentinels — contract + generated-wrapper tests.

E-1 (contract): schema-valid examples pass / malformed fail; builder determinism
+ shlex round-trip; enum-identity vs runtime-evidence; parser tolerance.
E-2 (silence≠success): the REAL generated script under /bin/sh — exit code,
SIGKILL child, trapped wrapper signals, resolve-outcome, broken interpreter.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import seat_sentinel
from creator_engine_validator.checks import registered_checks

REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATORS_DIR = REPO_ROOT / "validators"
WELL_FORMED = REPO_ROOT / "examples" / "well-formed" / "seat-events"
MALFORMED = REPO_ROOT / "examples" / "malformed" / "seat-events"


# --- contract: enum identity (drift = red) ---------------------------------


def _runtime_evidence_outcome_enum() -> list[str]:
    doc = yaml.safe_load((REPO_ROOT / "schemas" / "runtime-evidence.schema.yaml").read_text())
    # walk to the `outcome` property's enum (it lives under the record schema)
    found: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            outcome = node.get("outcome")
            if isinstance(outcome, dict) and isinstance(outcome.get("enum"), list):
                found.append(outcome["enum"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    assert found, "could not locate the runtime-evidence `outcome` enum"
    return found[0]


def test_outcome_enum_identical_to_runtime_evidence():
    assert list(seat_sentinel.OUTCOME_ENUM) == _runtime_evidence_outcome_enum()


def test_seat_event_schema_enum_matches_runtime_evidence():
    schema = yaml.safe_load(
        (REPO_ROOT / "schemas" / "seat-event.schema.yaml").read_text()
    )
    enum = schema["properties"]["outcome"]["oneOf"][1]["enum"]
    assert enum == _runtime_evidence_outcome_enum()


# --- contract: examples pass / malformed fail ------------------------------


def test_well_formed_events_pass():
    result = seat_sentinel.check_seat_events([WELL_FORMED])
    assert result.errors == (), [e.format() for e in result.errors]


def test_malformed_events_each_line_errors():
    result = seat_sentinel.check_seat_events([MALFORMED])
    # every non-blank line in the malformed corpus is independently bad
    text = (MALFORMED / "events.jsonl").read_text()
    nonblank = [ln for ln in text.splitlines() if ln.strip()]
    assert len(result.errors) >= len(nonblank), [e.format() for e in result.errors]


def test_registered_check_present():
    assert seat_sentinel.CHECK_NAME in registered_checks()


# --- contract: builder purity + value-freeness -----------------------------


def test_build_wrapper_script_deterministic():
    argv = ["systemd-run", "--user", "--scope", "--", "claude", "--print"]
    kwargs = dict(
        inner_argv=argv,
        events_path="/abs/.ce/state/dispatches/seat-x/events.jsonl",
        seat_id="seat-x",
        run_id="run-x-1",
        python_exe="/venv/bin/python",
    )
    a = seat_sentinel.build_wrapper_script(**kwargs)
    b = seat_sentinel.build_wrapper_script(**kwargs)
    assert a == b
    assert a.startswith("#!/bin/sh")


def test_build_wrapper_script_is_value_free():
    # The command TEXT must never appear — only its sha256 digest.
    secret_argv = ["claude", "--token", "sk-secret-value-123"]
    script = seat_sentinel.build_wrapper_script(
        inner_argv=secret_argv,
        events_path="/x/events.jsonl",
        seat_id="seat",
        run_id=None,
        python_exe="/p",
    )
    # the inner argv IS in the script (it must run the seat) — but the EVENT it
    # emits carries only the digest. Assert the launched-event emit line digests.
    assert seat_sentinel.command_sha256(secret_argv) in script
    # run_id null renders as a bare JSON null, not the string "None"
    assert '\\"run_id\\":null' in script


def test_build_wrapper_script_exports_launch_injection_refs():
    argv = ["claude", "--print"]
    digest = seat_sentinel.command_sha256(argv)
    script = seat_sentinel.build_wrapper_script(
        inner_argv=argv,
        events_path="/x/events.jsonl",
        seat_id="seat",
        run_id=None,
        python_exe="/p",
        exports={
            "CE_BRAIN_BOOTSTRAP_SHA256": "a" * 64,
            "CE_BRAIN_BOOTSTRAP_REF": "/x/brain-bootstrap.json",
        },
    )

    assert "export CE_BRAIN_BOOTSTRAP_REF=/x/brain-bootstrap.json" in script
    assert f"export CE_BRAIN_BOOTSTRAP_SHA256={'a' * 64}" in script
    assert digest in script
    assert "claude --print\ncode=$?" in script


def test_run_id_fragment():
    assert seat_sentinel._run_id_fragment(None) == "null"
    assert seat_sentinel._run_id_fragment("run-1") == '\\"run-1\\"'


# --- contract: parser tolerance --------------------------------------------


def test_parse_event_line_tolerant():
    assert seat_sentinel.parse_event_line("") is None
    assert seat_sentinel.parse_event_line("   ") is None
    assert seat_sentinel.parse_event_line("not json") is None
    assert seat_sentinel.parse_event_line("[1,2]") is None  # not an object
    assert seat_sentinel.parse_event_line('{"event":"launched"}') == {"event": "launched"}


def test_load_seat_events_none_when_absent(tmp_path):
    assert seat_sentinel.load_seat_events(tmp_path) is None  # no dispatches dir


def test_load_seat_events_groups_by_seat(tmp_path):
    d = tmp_path / "dispatches" / "seat-a"
    d.mkdir(parents=True)
    (d / "events.jsonl").write_text(
        '{"event":"launched"}\n\ngarbage\n{"event":"exited"}\n'
    )
    loaded = seat_sentinel.load_seat_events(tmp_path)
    assert loaded == {"seat-a": [{"event": "launched"}, {"event": "exited"}]}


# --- E-2: the REAL generated wrapper under /bin/sh -------------------------

# A generous ceiling that won't be reached in practice but tolerates a slow,
# CPU-contended runner (e.g. the merge-queue runner under pytest-xdist load).
# We poll for the expected condition at a short interval rather than relying on
# a tight fixed wall-clock bound (ce-ops#209): the assertion is unchanged, only
# the timing is hardened. A genuinely hung process still fails at this ceiling.
_WRAPPER_CEILING_S = 60.0
_WRAPPER_POLL_S = 0.05


def _poll_until(predicate, *, ceiling=_WRAPPER_CEILING_S, interval=_WRAPPER_POLL_S):
    """Poll ``predicate`` until truthy or the generous ceiling elapses.

    Returns the predicate's truthy value, or ``False`` on timeout. Deterministic
    in behavior — only the wall-clock budget is generous so a loaded runner has
    room to make progress.
    """
    deadline = time.monotonic() + ceiling
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    return False


def _wrapper_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(VALIDATORS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _materialize(tmp_path, inner_argv, *, seat_id="seat-x", run_id=None, python_exe=None):
    sentinel = seat_sentinel.prepare_seat_sentinel(
        seat_dir=tmp_path / "dispatches" / seat_id,
        inner_argv=inner_argv,
        seat_id=seat_id,
        run_id=run_id,
        python_exe=python_exe or sys.executable,
    )
    assert sentinel.pane_command == ["/bin/sh", str(sentinel.wrapper_path)]
    assert oct(sentinel.wrapper_path.stat().st_mode)[-3:] == "700"
    return sentinel


def _events(sentinel):
    return [
        json.loads(ln)
        for ln in sentinel.events_path.read_text().splitlines()
        if ln.strip()
    ]


def _wait_for_event(sentinel, event_name):
    def read_events_when_present():
        if not sentinel.events_path.is_file():
            return False
        events = []
        try:
            lines = sentinel.events_path.read_text().splitlines()
        except FileNotFoundError:
            return False
        for line in lines:
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                return False
        return events if any(e.get("event") == event_name for e in events) else False

    return _poll_until(read_events_when_present)


def test_wrapper_exit_code_two_lines(tmp_path):
    sentinel = _materialize(
        tmp_path, ["/bin/sh", "-c", "exit 7"], python_exe="/nonexistent/python"
    )
    proc = subprocess.run(sentinel.pane_command, env=_wrapper_env())
    assert proc.returncode == 7
    events = _events(sentinel)
    assert [e["event"] for e in events] == ["launched", "exited"]
    assert events[0]["event"] == "launched" and events[0]["pid"] > 0
    assert events[1]["exit_code"] == 7
    # both lines are schema-valid
    for ev in events:
        assert seat_sentinel.validate_seat_event(ev, sentinel.events_path) == []


def test_wrapper_child_sigkill_yields_137(tmp_path):
    sentinel = _materialize(
        tmp_path, ["/bin/sh", "-c", "kill -KILL $$"], python_exe="/nonexistent/python"
    )
    proc = subprocess.run(sentinel.pane_command, env=_wrapper_env())
    assert proc.returncode == 137
    events = _events(sentinel)
    assert events[-1]["event"] == "exited"
    assert events[-1]["exit_code"] == 137


@pytest.mark.parametrize("sig,code", [(signal.SIGTERM, 143), (signal.SIGHUP, 129)])
def test_wrapper_trapped_signal_writes_exit(tmp_path, sig, code):
    sentinel = _materialize(
        tmp_path, ["/bin/sh", "-c", "sleep 30"], python_exe="/nonexistent/python"
    )
    proc = subprocess.Popen(
        sentinel.pane_command, env=_wrapper_env(), start_new_session=True
    )
    # wait for the launched line before signalling — poll for the artifact up to
    # a generous ceiling instead of a tight fixed bound (ce-ops#209).
    assert _poll_until(
        lambda: sentinel.events_path.is_file()
        and bool(sentinel.events_path.read_text().strip())
    ), "wrapper never wrote its launched line within the ceiling"
    # the pane-kill reality: the signal hits the whole process group
    os.killpg(os.getpgid(proc.pid), sig)
    # bound the wait by the same generous ceiling: a genuinely hung process still
    # fails, but a slow loaded runner is tolerated.
    proc.wait(timeout=_WRAPPER_CEILING_S)
    events = _wait_for_event(sentinel, seat_sentinel.EVENT_EXITED)
    assert events, "wrapper never wrote its trapped-signal exit line within the ceiling"
    assert events[-1]["event"] == "exited"
    assert events[-1]["exit_code"] == code


def test_wrapper_broken_interpreter_preserves_exit_no_outcome(tmp_path):
    sentinel = _materialize(
        tmp_path, ["/bin/sh", "-c", "exit 3"], python_exe="/nonexistent/python"
    )
    proc = subprocess.run(sentinel.pane_command, env=_wrapper_env())
    assert proc.returncode == 3  # broken resolver never alters the exit code
    events = _events(sentinel)
    assert [e["event"] for e in events] == ["launched", "exited"]  # no outcome_resolved


def test_wrapper_resolves_outcome_from_chain(tmp_path):
    run_id = "run-x-1"
    # the run's evidence chain at <state_root>/runs/<run_id>.runtime-evidence.yaml
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / f"{run_id}.runtime-evidence.yaml").write_text(
        yaml.safe_dump(
            {"records": [{"record_type": "runtime_run_outcome", "outcome": "pr_opened"}]}
        )
    )
    sentinel = _materialize(
        tmp_path, ["/bin/sh", "-c", "exit 0"], seat_id=run_id, run_id=run_id
    )
    proc = subprocess.run(sentinel.pane_command, env=_wrapper_env())
    assert proc.returncode == 0
    events = _events(sentinel)
    assert [e["event"] for e in events] == ["launched", "exited", "outcome_resolved"]
    resolved = events[-1]
    assert resolved["outcome"] == "pr_opened"
    assert resolved["outcome_source"] == "runtime_evidence"
    assert seat_sentinel.validate_seat_event(resolved, sentinel.events_path) == []


def test_resolve_outcome_unresolved_when_chain_absent(tmp_path):
    run_id = "run-missing"
    seat_dir = tmp_path / "dispatches" / run_id
    seat_dir.mkdir(parents=True)
    events_path = seat_dir / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "v": 1,
                "event": "launched",
                "ts": "2026-06-12T08:00:00Z",
                "seat_id": run_id,
                "run_id": run_id,
                "writer": "launcher_wrapper",
                "pid": 1,
                "command_sha256": "0" * 64,
            }
        )
        + "\n"
    )
    event = seat_sentinel.resolve_outcome(events_path, seat_dir)
    assert event["outcome"] is None
    assert event["outcome_source"] == "unresolved"
    assert event["evidence_ref"] is None
