#!/usr/bin/env python3
"""ADR-0007 egress broker — the thin, deterministic CLI.

A non-agent host-side command that couriers a contained seat's signed commit to the forge under
fail-closed policy, attributed to the seat's OWN App. It is a shell over
``egress_broker.orchestrator.courier``: parse the seat/repo/branch + config, load the broker
config, build the seat's openssl RS256 signer (the App PEM stays on disk — only ``openssl``
reads it), run the courier, and map the outcome to an exit code.

Usage::

    python tools/egress-broker/ce_egress_broker.py \\
        --seat dev-4 \\
        --repo-path /home/cedev4/ce-workspaces/creator-engine \\
        --branch ce-some-feature \\
        --config ~/.ce-egress/broker.json \\
        [--apply] [--json]

Without ``--apply`` it is a **dry-run**: it verifies + audits the plan but mints/pushes nothing
(the safe default). With ``--apply`` it mints → pushes → opens/updates the attributed PR →
revokes. Exit codes: ``0`` allow, ``2`` fail-closed refusal, ``3`` config error. Fail-closed —
deny on any verification doubt.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace

# Make the sibling ``egress_broker`` package importable when run as a script, and put the
# repo's ``validators/`` on the path so the reused ``creator_engine_validator.forge`` primitives
# import without any env setup (additive — a pip-installed validator still resolves first).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
_VALIDATORS = os.path.join(_REPO_ROOT, "validators")
if os.path.isdir(_VALIDATORS):
    sys.path.insert(0, _VALIDATORS)

from egress_broker.config import BrokerConfigError, load_broker_config  # noqa: E402
from egress_broker.minter import openssl_signer  # noqa: E402
from egress_broker.orchestrator import EgressRefused, courier as _real_courier  # noqa: E402

#: Exit codes — small, stable contract for the controller's wrapper.
EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_CONFIG_ERROR = 3


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ce-egress-broker",
        description="Deterministic ADR-0007 egress broker — courier a contained seat's signed "
        "commit to the forge under fail-closed policy (v0).",
    )
    p.add_argument("--seat", required=True, help="seat id whose App couriers the commit (e.g. dev-4)")
    p.add_argument("--repo-path", required=True, help="host-side path to the seat's repo (its bind-mount)")
    p.add_argument("--branch", required=True, help="the seat-authored head branch to courier")
    p.add_argument("--config", required=True, help="path to the broker config JSON")
    p.add_argument("--audit-log", default=None, help="override the audit log path from the config")
    p.add_argument(
        "--declared-work-class",
        choices=("tiny", "story", "feature", "epic"),
        default=None,
        help="PR body work-class declaration; defaults to the per-branch PR carrier when omitted",
    )
    p.add_argument("--apply", action="store_true", help="actually mint+push+PR (default: dry-run plan)")
    p.add_argument("--json", action="store_true", help="emit the result as JSON on stdout")
    return p


def _emit(result, *, as_json: bool) -> None:
    payload = {
        "seat_id": result.seat_id,
        "branch": result.branch,
        "head_sha": result.head_sha,
        "allowed": result.allowed,
        "applied": result.applied,
        "pushed": result.pushed,
        "pr_number": result.pr_number,
        "installation_id": result.installation_id,
    }
    if as_json:
        print(json.dumps(payload, sort_keys=True))
        return
    verb = "PUSHED + PR" if result.applied else "ALLOWED (dry-run plan — not applied)"
    print(f"[ce-egress] {verb}: seat={result.seat_id} branch={result.branch} head={result.head_sha[:12]}")
    if result.applied:
        print(f"[ce-egress]   installation={result.installation_id} pr=#{result.pr_number} pushed={result.pushed}")


def main(argv=None, *, courier_fn=None) -> int:
    """Parse args, load config, run the courier, and return an exit code (fail-closed)."""
    args = _build_parser().parse_args(argv)
    run_courier = courier_fn or _real_courier

    try:
        config = load_broker_config(args.config)
    except BrokerConfigError as exc:
        print(f"[ce-egress] config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    if args.audit_log:
        config = replace(config, audit_log=args.audit_log)

    # Build the seat's openssl RS256 signer ONLY for an apply run on a known seat (the PEM is
    # read by openssl at sign time, never here). An unknown seat is left to the courier, which
    # refuses + audits it; we do not pre-empt that path.
    signer = None
    if args.apply:
        try:
            seat = config.seat(args.seat)
            signer = openssl_signer(seat.pem_path)
        except BrokerConfigError:
            signer = None

    try:
        result = run_courier(
            args.seat,
            args.repo_path,
            args.branch,
            config=config,
            signer=signer,
            apply=args.apply,
            declared_work_class=args.declared_work_class,
        )
    except EgressRefused as exc:
        print(f"[ce-egress] REFUSED (fail-closed): {exc}", file=sys.stderr)
        return EXIT_REFUSED

    _emit(result, as_json=args.json)
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
