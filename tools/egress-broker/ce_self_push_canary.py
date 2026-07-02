#!/usr/bin/env python3
"""Contained-seat self-push smoke canary.

This runs inside a contained seat and sends the value-only SELF-PUSH request to
the host broker socket. It intentionally carries no forge credential and fails
loudly on stale socket mounts, broker refusal, or non-applied responses.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


def _current_branch(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "could not resolve current branch").strip())
    branch = proc.stdout.strip()
    if not branch or branch == "HEAD":
        raise RuntimeError("current checkout is detached; pass --branch explicitly")
    return branch


def _read_json_line(sock: socket.socket) -> dict[str, Any]:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    raw = b"".join(chunks).split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
    if not raw:
        raise RuntimeError("broker closed connection without a response")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"broker returned non-JSON response: {raw!r}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"broker returned non-object response: {raw!r}")
    return parsed


def run_canary(args: argparse.Namespace) -> int:
    socket_path = Path(args.socket or os.environ.get("CE_EGRESS_BROKER_SOCKET", ""))
    seat_id = args.seat or os.environ.get("CE_SEAT_ID", "")
    repo = Path(args.repo)
    branch = args.branch or _current_branch(repo)

    if not seat_id:
        print("self-push canary FAIL: missing --seat or CE_SEAT_ID", file=sys.stderr)
        return 2
    if not socket_path.is_absolute():
        print("self-push canary FAIL: missing absolute --socket or CE_EGRESS_BROKER_SOCKET", file=sys.stderr)
        return 2
    if not socket_path.exists():
        print(f"self-push canary FAIL: broker socket does not exist: {socket_path}", file=sys.stderr)
        return 2
    if not socket_path.is_socket():
        print(f"self-push canary FAIL: broker path is not a Unix socket: {socket_path}", file=sys.stderr)
        return 2

    request = {"seat_id": seat_id, "branch": branch}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(args.timeout)
            sock.connect(str(socket_path))
            sock.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
            response = _read_json_line(sock)
    except OSError as exc:
        print(
            f"self-push canary FAIL: could not talk to broker socket {socket_path}: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 3
    except RuntimeError as exc:
        print(f"self-push canary FAIL: {exc}", file=sys.stderr)
        return 3

    if response.get("status") != 200:
        print(
            "self-push canary FAIL: broker refused request: "
            + json.dumps(response, sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
        )
        return 4
    if args.require_applied and response.get("applied") is not True:
        print(
            "self-push canary FAIL: broker response was not applied: "
            + json.dumps(response, sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
        )
        return 4
    if args.require_noop and response.get("pushed") is True:
        print(
            "self-push canary FAIL: broker performed a push; expected no-op ref: "
            + json.dumps(response, sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
        )
        return 5

    print(
        "SELF-PUSH CANARY PASS "
        f"seat={response.get('seat_id', seat_id)} "
        f"branch={response.get('branch', branch)} "
        f"applied={response.get('applied')} "
        f"pushed={response.get('pushed')} "
        f"pr_number={response.get('pr_number')}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Contained-seat smoke canary for the CE egress self-push broker. "
            "Run after local validation from inside the contained seat."
        )
    )
    parser.add_argument("--socket", default=None, help="broker Unix socket; default: CE_EGRESS_BROKER_SOCKET")
    parser.add_argument("--seat", default=None, help="seat id; default: CE_SEAT_ID")
    parser.add_argument("--repo", default=".", help="repo path used to infer --branch when omitted")
    parser.add_argument("--branch", default=None, help="branch to ask the broker to self-push")
    parser.add_argument("--timeout", type=float, default=30.0, help="socket timeout in seconds")
    parser.add_argument(
        "--allow-plan-only",
        dest="require_applied",
        action="store_false",
        help="do not require the broker response to report applied=true",
    )
    parser.add_argument(
        "--require-noop",
        action="store_true",
        help="fail if the broker had to push instead of proving the remote ref was already current",
    )
    parser.set_defaults(require_applied=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_canary(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
