#!/usr/bin/env python3
"""Host-side contained-seat SELF-PUSH broker daemon CLI."""
from __future__ import annotations

import argparse
import os
import sys

# Make the sibling ``egress_broker`` package importable when run as a script, and put the
# repo's ``validators/`` on the path so reused forge primitives import without env setup.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
_VALIDATORS = os.path.join(_REPO_ROOT, "validators")
if os.path.isdir(_VALIDATORS):
    sys.path.insert(0, _VALIDATORS)

from egress_broker.config import BrokerConfigError, load_broker_config  # noqa: E402
from egress_broker.host_broker import serve_self_push_unix_socket  # noqa: E402
from egress_broker.minter import openssl_signer  # noqa: E402

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 2
EXIT_CONFIG_ERROR = 3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce-egress-self-push-broker",
        description="Host-side Unix-socket daemon for contained-seat SELF-PUSH requests.",
    )
    parser.add_argument("--socket", required=True, help="host Unix socket path for this seat")
    parser.add_argument("--seat", required=True, help="broker seat id bound to this socket, e.g. dev-4")
    parser.add_argument(
        "--host-repo-path",
        required=True,
        help="trusted host repo path; any request repo_path is ignored",
    )
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.ce-egress/broker.json"),
        help="host broker config JSON",
    )
    parser.add_argument("--once", action="store_true", help="serve one request then exit")
    return parser


def main(argv=None, *, serve_fn=None, signer_factory=None) -> int:
    """Parse args, build host-owned seams, and run the Unix-socket broker."""
    args = _build_parser().parse_args(argv)
    run_server = serve_fn or serve_self_push_unix_socket
    build_signer = signer_factory or openssl_signer

    try:
        config = load_broker_config(args.config)
        seat = config.seat(args.seat)
    except BrokerConfigError as exc:
        print(f"[ce-egress-self-push] config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    try:
        signer = build_signer(seat.pem_path)
        run_server(
            args.socket,
            config=config,
            broker_seat_id=args.seat,
            host_repo_path=args.host_repo_path,
            signer=signer,
            once=args.once,
        )
    except Exception as exc:  # noqa: BLE001 - process boundary maps all runtime failures to code 2.
        # Deliberately do not print ``str(exc)``; subprocess/socket errors can contain
        # credential-shaped stderr from lower transports.
        print(
            f"[ce-egress-self-push] broker runtime error: {type(exc).__name__}",
            file=sys.stderr,
        )
        return EXIT_RUNTIME_ERROR
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
