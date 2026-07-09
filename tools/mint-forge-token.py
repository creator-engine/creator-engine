#!/usr/bin/env python3
"""Forge token minter for standby controller use.

Requires: GH_TOKEN or the CE egress broker configured for token minting.
"""
from __future__ import annotations

import argparse
import os
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without minting",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.dry_run:
        print("DRY-RUN: would mint a forge token via CE egress broker or GH_TOKEN env")
        print("DRY-RUN: GH_TOKEN present:", "yes" if os.environ.get("GH_TOKEN") else "no")
        return

    token = os.environ.get("GH_TOKEN")
    if not token:
        print(
            "ERROR: GH_TOKEN not set. Set GH_TOKEN or configure the CE egress broker "
            "for token minting.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Current standby bootstrap path: pass through the scoped ambient token.
    # Broker-backed minting can replace this once the egress broker is available.
    print(token)


if __name__ == "__main__":
    try:
        main()
    except ImportError as exc:
        print(
            "ERROR: optional dependency unavailable while minting forge token: "
            f"{exc}. Configure the CE egress broker or provide GH_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)
