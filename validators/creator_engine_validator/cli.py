"""Command-line interface for the Creator Engine validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .checks import registered_checks, run_registered
from .reporting import CheckResult, ValidationError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creator_engine_validator")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    parser.add_argument("--tenant", help="restrict cross-artifact checks to one tenant")
    parser.add_argument("--list-checks", action="store_true", help="list enabled checks and their FRs")
    sub = parser.add_subparsers(dest="subcommand")

    check = sub.add_parser("check", help="run all enabled checks")
    check.add_argument("paths", nargs="*", default=["."], help="paths to validate")

    sub.add_parser("check-examples", help="validate bundled well-formed/malformed examples")
    sub.add_parser("scan-no-limitless", help="run only the no-LIMITLESS generic-path scan")
    return parser


def _print_checks(json_output: bool) -> int:
    checks = registered_checks()
    if json_output:
        print(json.dumps({"checks": {name: list(defn.frs) for name, defn in checks.items()}}, indent=2, sort_keys=True))
    else:
        if not checks:
            print("No checks registered yet.")
        for name, defn in checks.items():
            print(f"{name}: {', '.join(defn.frs)}")
    return 0


def _emit_results(results: list[CheckResult], json_output: bool) -> int:
    failed = [result for result in results if not result.ok]
    if json_output:
        print(json.dumps({"ok": not failed, "results": [r.to_dict() for r in results]}, indent=2, sort_keys=True))
    else:
        if not results:
            print("No checks registered; 0 validation failures.")
        for result in results:
            status = "PASS" if result.ok else "FAIL"
            print(f"{status} {result.name}")
            for error in result.errors:
                print(error.format())
            for warning in result.warnings:
                print(f"WARN {warning.format()}")
    return 1 if failed else 0


def _check(paths: Sequence[str], json_output: bool) -> int:
    return _emit_results(run_registered([Path(p) for p in paths]), json_output)


def _check_examples(json_output: bool) -> int:
    """Validate bundled well-formed examples and expected-failing malformed examples."""
    expectations = [
        ("well-formed", Path("examples/well-formed"), True, None),
        ("malformed", Path("examples/malformed/identity-record.missing-fields.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/spec.creator-engine.missing-acceptance.yml"), False, "FR-013"),
        ("malformed", Path("examples/malformed/duplicate-spec-id"), False, "FR-027a"),
    ]
    results: list[dict[str, object]] = []
    errors: list[ValidationError] = []
    for kind, path, should_pass, expected_code in expectations:
        check_results = run_registered([path])
        ok = all(result.ok for result in check_results)
        rendered = "\n".join(error.format() for result in check_results for error in result.errors)
        expectation_ok = ok if should_pass else (not ok and expected_code in rendered)
        results.append(
            {
                "kind": kind,
                "path": str(path),
                "expected_pass": should_pass,
                "expected_code": expected_code,
                "ok": ok,
                "expectation_ok": expectation_ok,
                "results": [result.to_dict() for result in check_results],
            }
        )
        if not expectation_ok:
            expected = "pass" if should_pass else f"fail with {expected_code}"
            errors.append(
                ValidationError(
                    code="FR-029" if not should_pass else "FR-028",
                    path=str(path),
                    message=f"example expectation not met: expected {expected}",
                    contract="examples/README.md",
                )
            )
    if json_output:
        print(json.dumps({"ok": not errors, "examples": results, "errors": [e.to_dict() for e in errors]}, indent=2, sort_keys=True))
    else:
        for result in results:
            status = "PASS" if result["expectation_ok"] else "FAIL"
            expectation = "pass" if result["expected_pass"] else f"fail with {result['expected_code']}"
            print(f"{status} example {result['path']} expected {expectation}")
        for error in errors:
            print(error.format())
    return 1 if errors else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        return _print_checks(args.json_output)

    subcommand = args.subcommand or "check"
    if subcommand == "check":
        return _check(getattr(args, "paths", ["."]), args.json_output)
    if subcommand == "check-examples":
        return _check_examples(args.json_output)
    if subcommand == "scan-no-limitless":
        from .checks.no_limitless_strings import run as _run_no_limitless
        result = _run_no_limitless([Path(".")])
        return _emit_results([result], args.json_output)

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
