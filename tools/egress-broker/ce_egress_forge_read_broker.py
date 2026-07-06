#!/usr/bin/env python3
"""Host-side CLI for brokered contained-seat forge reads."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
for _path in (_REPO_ROOT / "validators", _HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from egress_broker.config import load_broker_config  # noqa: E402
from egress_broker.forge_read import cli_payload, handle_forge_read_request  # noqa: E402

EXIT_OK = 0
EXIT_REFUSED = 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce-egress-forge-read-broker",
        description="Host-side broker for contained-seat read-only forge API requests.",
    )
    parser.add_argument("--config", required=True, help="host-local egress broker config JSON")
    parser.add_argument("--seat", required=True, help="broker seat id bound to this request")

    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in ("get-issue", "get-pr", "list-comments"):
        p = sub.add_parser(verb)
        p.add_argument("repo", help="repository in owner/name form")
        p.add_argument("number", type=int, help="issue or PR number")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_broker_config(args.config)
    response = handle_forge_read_request(
        cli_payload(args.verb, args.repo, args.number, seat_id=args.seat),
        config=config,
    )
    print(json.dumps(response, sort_keys=True, separators=(",", ":")))
    return EXIT_OK if response.get("ok") else EXIT_REFUSED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
