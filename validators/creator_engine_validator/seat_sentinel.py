"""Standardized per-seat lifecycle sentinels (ce-ops#26) — the shared contract.

Every ``ce launch``-ed governed seat owns an append-only ``events.jsonl`` at
``<state_root>/dispatches/<seat_id>/events.jsonl``. The **writer is a
launcher-generated POSIX-sh supervisor** (``sentinel-wrapper.sh``) that the
pane/substrate executes INSTEAD of the seat command: it appends a ``launched``
event, runs the (already-governed, already-bounded) seat command as its
FOREGROUND child, and appends an ``exited`` event with the exit code on ANY
termination — the seat's model never writes the file, so a silently-dying seat
still produces its exit event (the silence≠success guarantee).

This module is the ONE contract both runtimes hang off:

- v1 launchers (``lane_runtime`` / ``launch_runtime``) call
  :func:`prepare_seat_sentinel` to materialize the wrapper + resolve the pane
  command, OUTERMOST — wrapping the OUTPUT of the resource-bound wrap, so the
  wrapper sits OUTSIDE the seat's ``systemd --scope`` cgroup and survives an
  OOM group-kill of the seat to write ``exited`` (137).
- the v3 reader (``runner.cockpit_readmodel``) calls :func:`load_seat_events`.

Because BOTH a v1 launcher and the v3 reader import it, the module is
**shared** (`_versions`): it imports NOTHING version-specific. A v1↔v3
placement either way would be a HARD-invariant import crossing — shared is the
only legal home for a one-contract-two-runtimes module. The v1→surface crossing
stays files + argv (DATA), never an import.

The script builder (:func:`build_wrapper_script`) is PURE and substrate-neutral
(POSIX sh, no bashisms): a future container seat sets
``ENTRYPOINT ["/bin/sh", "sentinel-wrapper.sh"]`` and emits identical events.

See:
  - ``schemas/seat-event.schema.yaml`` (the line shape)
  - ``docs/architecture/seat-sentinel-contract.md`` (the convention)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import yaml

from .reporting import CheckResult, ValidationError, make_error
from .schema import validate_with_schema

# --- contract constants ----------------------------------------------------

SCHEMA_VERSION = 1
SCHEMA = "schemas/seat-event.schema.yaml"
CONTRACT = "docs/architecture/seat-sentinel-contract.md"

EVENTS_FILENAME = "events.jsonl"
WRAPPER_FILENAME = "sentinel-wrapper.sh"

WRITER_LAUNCHER_WRAPPER = "launcher_wrapper"

EVENT_LAUNCHED = "launched"
EVENT_EXITED = "exited"
EVENT_OUTCOME_RESOLVED = "outcome_resolved"
#: Closed event enum v1 (progress/heartbeat are RESERVED but unemitted).
EVENT_KINDS = (EVENT_LAUNCHED, EVENT_EXITED, EVENT_OUTCOME_RESOLVED)

OUTCOME_SOURCE_RUNTIME_EVIDENCE = "runtime_evidence"
OUTCOME_SOURCE_UNRESOLVED = "unresolved"

#: THE conserved run-OUTCOME enum — kept byte-identical to
#: ``runtime-evidence.schema.yaml``'s ``outcome`` (a unit test pins the two so
#: they cannot drift silently). Referenced here, never forked.
OUTCOME_ENUM = (
    "pr_opened",
    "pr_merged",
    "review_submitted",
    "research_delivered",
    "no_change",
)

#: The evidence-chain layout shared with ``cockpit_readmodel`` / ``evidence_sink``
#: (the RUNS_SUBDIR fix, ce-ops#16): ``<state_root>/runs/<run_id>.runtime-evidence.yaml``.
RUNS_SUBDIR = "runs"
DISPATCHES_SUBDIR = "dispatches"
CHAIN_SUFFIX = ".runtime-evidence.yaml"

# --- check codes -----------------------------------------------------------

CHECK_NAME = "seat_event"
CODE_SCHEMA = "SEAT-001"
CODE_NOT_JSON = "SEAT-002"
CODE_NOT_OBJECT = "SEAT-003"


# --- digests ---------------------------------------------------------------


def command_sha256(argv: Sequence[str]) -> str:
    """Value-free digest of the inner argv (NUL-joined). NEVER the command text."""
    joined = "\x00".join(str(a) for a in argv)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# --- the PURE script builder -----------------------------------------------


def _sh_str(value: str) -> str:
    """Embed ``value`` as the CONTENT of a shell double-quoted JSON string.

    The generated ``emit "{...}"`` argument is itself double-quoted, so inner
    ``"`` become ``\\"``. ``value`` is JSON-escaped first (it is a controlled
    slug, but this is belt-and-braces against any odd character).
    """
    inner = json.dumps(str(value))[1:-1]  # JSON escaping, sans the wrapping quotes
    return inner.replace('"', '\\"')


def _run_id_fragment(run_id: str | None) -> str:
    """The ``run_id`` JSON value spliced into the shell ``"..."`` emit argument."""
    if run_id is None:
        return "null"
    return '\\"' + _sh_str(run_id) + '\\"'


def build_wrapper_script(
    *,
    inner_argv: Sequence[str],
    events_path: str | Path,
    seat_id: str,
    run_id: str | None,
    python_exe: str,
) -> str:
    """PURE: the POSIX-sh supervisor text (deterministic; no timestamps baked in).

    Emits ``launched`` before the FOREGROUND seat child (interactive tty
    preserved), traps HUP/TERM/INT to write a trapped ``exited`` event, writes
    ``exited`` with the child's exit code on a normal return, then shells out to
    the pinned interpreter for the best-effort ``outcome_resolved`` follow-up
    (failure of which never masks the exit event or alters the exit code).
    """
    ev = str(events_path)
    seat = _sh_str(seat_id)
    run = _run_id_fragment(run_id)
    sha = command_sha256(inner_argv)
    seat_dir = str(Path(events_path).parent)
    inner = " ".join(shlex.quote(str(a)) for a in inner_argv)

    common = f'\\"v\\":1,\\"event\\":\\"%s\\",\\"ts\\":\\"$(now)\\",\\"seat_id\\":\\"{seat}\\",\\"run_id\\":{run},\\"writer\\":\\"{WRITER_LAUNCHER_WRAPPER}\\"'
    launched = (
        "{" + (common % EVENT_LAUNCHED) + f',\\"pid\\":$$,\\"command_sha256\\":\\"{sha}\\"}}'
    )
    exited_code = "{" + (common % EVENT_EXITED) + ',\\"exit_code\\":$code}'
    exited_sig = "{" + (common % EVENT_EXITED) + ',\\"exit_code\\":$((128+$1))}'

    return f"""#!/bin/sh
# generated by creator_engine_validator.seat_sentinel — do not edit
# ce-ops#26 seat lifecycle sentinel. The launcher's supervisor, NOT the seat's
# model, writes this file; a silently-dying seat still produces its exit event.
EV={shlex.quote(ev)}
emit() {{ printf '%s\\n' "$1" >> "$EV"; }}
now() {{ date -u +%Y-%m-%dT%H:%M:%SZ; }}
emit "{launched}"
on_sig() {{ emit "{exited_sig}"; exit $((128+$1)); }}
trap 'on_sig 1' HUP
trap 'on_sig 15' TERM
trap 'on_sig 2' INT
{inner}
code=$?
emit "{exited_code}"
{shlex.quote(python_exe)} -m creator_engine_validator.seat_sentinel resolve-outcome \\
    --events "$EV" --seat-dir {shlex.quote(seat_dir)} >/dev/null 2>&1 || true
exit $code
"""


# --- materialization (the launcher's I/O edge) -----------------------------


class SeatSentinel:
    """The materialized sentinel surface the launcher splices into the pane."""

    __slots__ = ("seat_dir", "events_path", "wrapper_path", "pane_command")

    def __init__(self, seat_dir: Path, events_path: Path, wrapper_path: Path) -> None:
        self.seat_dir = seat_dir
        self.events_path = events_path
        self.wrapper_path = wrapper_path
        #: The pane command the launcher spawns INSTEAD of the seat command.
        self.pane_command: list[str] = ["/bin/sh", str(wrapper_path)]


def seat_dir_for(state_root: str | Path, seat_id: str) -> Path:
    """``<state_root>/dispatches/<seat_id>`` — the seat's surface directory."""
    return Path(state_root) / DISPATCHES_SUBDIR / seat_id


def prepare_seat_sentinel(
    *,
    seat_dir: str | Path,
    inner_argv: Sequence[str],
    seat_id: str,
    run_id: str | None,
    python_exe: str | None = None,
) -> SeatSentinel:
    """Write ``sentinel-wrapper.sh`` (0700) into ``seat_dir`` and resolve the pane cmd.

    The resolved ABSOLUTE events path is baked into the wrapper — consumers never
    guess. Idempotent: re-materializing overwrites the wrapper. Returns a
    :class:`SeatSentinel` whose ``pane_command`` the launcher spawns.
    """
    seat_dir = Path(seat_dir)
    seat_dir.mkdir(parents=True, exist_ok=True)
    events_path = (seat_dir / EVENTS_FILENAME).resolve()
    wrapper_path = (seat_dir / WRAPPER_FILENAME).resolve()
    exe = python_exe or sys.executable
    script = build_wrapper_script(
        inner_argv=inner_argv,
        events_path=events_path,
        seat_id=seat_id,
        run_id=run_id,
        python_exe=exe,
    )
    wrapper_path.write_text(script, encoding="utf-8")
    wrapper_path.chmod(0o700)
    return SeatSentinel(seat_dir, events_path, wrapper_path)


# --- the parser (tolerant; readers) ----------------------------------------


def parse_event_line(line: str) -> dict[str, Any] | None:
    """Tolerant: a parsed JSON object, else ``None`` (blank/garbage skipped)."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def iter_events_file(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield each well-formed event object in an ``events.jsonl`` (tolerant skip)."""
    p = Path(path)
    if not p.is_file():
        return
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        obj = parse_event_line(line)
        if obj is not None:
            yield obj


def load_seat_events(state_root: str | Path) -> dict[str, list[dict[str, Any]]] | None:
    """Read every seat's events under ``<state_root>/dispatches/*/events.jsonl``.

    Returns ``seat_id -> [event, ...]``. ``None`` when the dispatches directory
    is unreachable (source absent — distinct from reachable-but-empty). Tolerant:
    malformed lines are skipped, never raised (read-only observability must not
    crash the view).
    """
    dispatches = Path(state_root) / DISPATCHES_SUBDIR
    if not dispatches.is_dir():
        return None
    out: dict[str, list[dict[str, Any]]] = {}
    for events_path in sorted(dispatches.glob(f"*/{EVENTS_FILENAME}")):
        seat_id = events_path.parent.name
        out[seat_id] = list(iter_events_file(events_path))
    return out


# --- the validator (schema + conditional shape; used by the check) ---------


def validate_seat_event(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate ONE event object against the schema (conditional requireds included)."""
    return validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)


def _looks_like_events_file(path: Path) -> bool:
    return path.is_file() and path.name == EVENTS_FILENAME


def iter_events_files(paths: Iterable[Path]) -> list[Path]:
    """Discover ``events.jsonl`` files under ``paths`` (file or dir roots)."""
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_events_file(path):
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(path.rglob(EVENTS_FILENAME))
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen or not candidate.is_file():
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def check_seat_events(paths: Iterable[Path]) -> CheckResult:
    """The registered ``seat_event`` check body (kept here so the check module is thin).

    Each line of every discovered ``events.jsonl`` must be a JSON object valid
    against ``seat-event.schema.yaml`` (with the per-event-kind conditional
    requireds). A blank line is skipped; a non-JSON or non-object line errors.
    """
    errors: list[ValidationError] = []
    for events_path in iter_events_files(paths):
        try:
            text = events_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(make_error(CODE_NOT_JSON, events_path, "/", str(exc), CONTRACT))
            continue
        for lineno, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except ValueError as exc:
                errors.append(
                    make_error(
                        CODE_NOT_JSON,
                        events_path,
                        f"line {lineno}",
                        f"event line is not valid JSON: {exc}",
                        CONTRACT,
                    )
                )
                continue
            if not isinstance(obj, dict):
                errors.append(
                    make_error(
                        CODE_NOT_OBJECT,
                        events_path,
                        f"line {lineno}",
                        "event line must be a JSON object",
                        CONTRACT,
                    )
                )
                continue
            errors.extend(validate_seat_event(obj, events_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))


# --- resolve-outcome (the best-effort semantic follow-up; §3.4) ------------


def _utc_now_str() -> str:
    # Imported lazily so the module's import graph stays trivially shared.
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_outcome(events_path: str | Path, seat_dir: str | Path) -> dict[str, Any]:
    """Append an ``outcome_resolved`` event by joining the run's evidence chain.

    Mechanical knowledge (exit codes) is never semantics: ``pr_opened`` is a
    forge fact in the run's evidence chain. Reads
    ``<state_root>/runs/<run_id>.runtime-evidence.yaml`` (the layout
    ``cockpit_readmodel.load_chains`` reads) by the ``run_id`` carried on the
    ``launched`` line; absent/unreadable ⇒ ``outcome: null, outcome_source:
    unresolved``. Returns the appended event dict.
    """
    events_path = Path(events_path)
    seat_dir = Path(seat_dir)

    run_id: str | None = None
    for event in iter_events_file(events_path):
        if event.get("event") == EVENT_LAUNCHED:
            rid = event.get("run_id")
            run_id = rid if isinstance(rid, str) and rid else None
            break

    outcome: str | None = None
    source = OUTCOME_SOURCE_UNRESOLVED
    evidence_ref: str | None = None

    if run_id:
        # <state_root>/dispatches/<seat_id> -> <state_root>
        state_root = seat_dir.parent.parent
        chain_path = state_root / RUNS_SUBDIR / f"{run_id}{CHAIN_SUFFIX}"
        if chain_path.is_file():
            try:
                doc = yaml.safe_load(chain_path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                doc = None
            if isinstance(doc, dict):
                source = OUTCOME_SOURCE_RUNTIME_EVIDENCE
                evidence_ref = str(chain_path)
                records = doc.get("records")
                if isinstance(records, list):
                    for rec in reversed(records):
                        if isinstance(rec, dict) and rec.get("outcome") in OUTCOME_ENUM:
                            outcome = rec["outcome"]
                            break

    event = {
        "v": SCHEMA_VERSION,
        "event": EVENT_OUTCOME_RESOLVED,
        "ts": _utc_now_str(),
        "seat_id": seat_dir.name,
        "run_id": run_id,
        "writer": WRITER_LAUNCHER_WRAPPER,
        "outcome": outcome,
        "outcome_source": source,
        "evidence_ref": evidence_ref,
    }
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    return event


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="creator_engine_validator.seat_sentinel")
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser(
        "resolve-outcome",
        help="append a best-effort outcome_resolved event from the run's evidence chain",
    )
    resolve.add_argument("--events", required=True)
    resolve.add_argument("--seat-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "resolve-outcome":
        resolve_outcome(args.events, args.seat_dir)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
