"""Standalone caller for the gated automerge actuator."""
from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from .automerge_actuator import ActuationResult, actuate_if_ready


def _default_gh_runner(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def actuate_decision(decision_path: str | Path, *, gh_runner=None) -> ActuationResult:
    """Delegate one decision record to the fail-closed actuator."""

    return actuate_if_ready(decision_path, gh_runner=gh_runner or _default_gh_runner)


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _result_payload(result: ActuationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "reason": result.reason,
        "acted": result.acted,
        "auto_merge_result": _jsonable(result.auto_merge_result),
    }


def main(argv: Sequence[str] | None = None, *, out: TextIO = sys.stdout) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m creator_engine_validator.forge.automerge_actuate_cli",
        description="Call the gated automerge actuator for one decision record.",
    )
    parser.add_argument("decision_path", help="path to the automerge decision JSON record")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit JSON outcome")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = actuate_decision(args.decision_path)
    payload = _result_payload(result)
    if args.json_output:
        print(json.dumps(payload, sort_keys=True), file=out)
    else:
        print(
            f"ce automerge-actuate: {result.status} "
            f"reason={result.reason} acted={str(result.acted).lower()}",
            file=out,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["actuate_decision", "main"]
