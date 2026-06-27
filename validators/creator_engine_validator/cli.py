"""Command-line interface for the Creator Engine validator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from .reporting import CheckResult


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creator_engine_validator")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    parser.add_argument("--tenant", help="restrict cross-artifact checks to one tenant")
    parser.add_argument("--list-checks", action="store_true", help="list enabled checks and their FRs")
    sub = parser.add_subparsers(dest="subcommand")

    check = sub.add_parser("check", help="run all enabled checks")
    check.add_argument("paths", nargs="*", default=["."], help="paths to validate")

    check_examples = sub.add_parser("check-examples", help="validate bundled well-formed/malformed examples")
    check_examples.add_argument("examples_root", nargs="?", default="examples", help="examples root to validate (default: examples)")
    sub.add_parser("scan-no-limitless", help="run only the no-LIMITLESS generic-path scan")

    scan_handoffs = sub.add_parser(
        "scan-handoffs",
        help="run only the handoff_schema check against a path (handoff/recommended-prompt docs)",
    )
    scan_handoffs.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_manifest = sub.add_parser(
        "scan-path-manifest",
        help="run only the path_manifest_fidelity check against a path",
    )
    scan_manifest.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_ledger = sub.add_parser(
        "scan-active-work-ledger",
        help="run only the active_work_ledger_schema check against a path",
    )
    scan_ledger.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_ledger_conflicts = sub.add_parser(
        "scan-active-work-ledger-conflicts",
        help="run only the active_work_ledger_conflicts pre-launch check against a path",
    )
    scan_ledger_conflicts.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_leases = sub.add_parser(
        "scan-worktree-leases",
        help="run only the worktree_lease_schema check against a path",
    )
    scan_leases.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_controller_keys = sub.add_parser(
        "scan-controller-keys",
        help="run only the controller_key_schema check against a path",
    )
    scan_controller_keys.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_completion = sub.add_parser(
        "scan-completion-reports",
        help="run the completion_report_schema / required_for_envelope / terminal_sections checks against a path",
    )
    scan_completion.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_pane_registry = sub.add_parser(
        "scan-pane-registry",
        help="run only the pane_registry check against a path",
    )
    scan_pane_registry.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_side_effect_ledger = sub.add_parser(
        "scan-side-effect-ledger",
        help="run only the side_effect_ledger check against a path",
    )
    scan_side_effect_ledger.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_controller_runtime_contract = sub.add_parser(
        "scan-controller-runtime-contract",
        help="run only the controller_runtime_contract check (RV1-020) against a path",
    )
    scan_controller_runtime_contract.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_state_boundary_contract = sub.add_parser(
        "scan-state-boundary-contract",
        help="run only the state_boundary_contract check (RV1-021) against a path",
    )
    scan_state_boundary_contract.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_state_version_record = sub.add_parser(
        "scan-state-version-record",
        help="run only the state_version_record check (RV1-022) against a path",
    )
    scan_state_version_record.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_crosswalk_register = sub.add_parser(
        "scan-crosswalk-register",
        help="run only the crosswalk_register check (G2.001.4 / FR-018) against a path",
    )
    scan_crosswalk_register.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_terminology_v2 = sub.add_parser(
        "scan-terminology-v2",
        help="run only the ce_terminology_v2 check (G2.001.1) against a path",
    )
    scan_terminology_v2.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_runtime_policy = sub.add_parser(
        "scan-runtime-policy",
        help="run only the ce_runtime_policy check (v3 G-1.0 plane-C) against a path",
    )
    scan_runtime_policy.add_argument("path", nargs="?", default=".", help="path to scan")

    scan_public_docs_confidentiality = sub.add_parser(
        "scan-public-docs-confidentiality",
        help=(
            "fast public-docs confidentiality scan: fail if any non-allowlisted "
            "public doc leaks a ce-ops# ticket ref or internal host identifier "
            "(same rule as the CI guard; runs in ce validate-pr before push)"
        ),
    )
    scan_public_docs_confidentiality.add_argument(
        "path", nargs="?", default=".", help="repo root to scan (default: .)"
    )

    openbao_p3 = sub.add_parser(
        "openbao-p3-plan",
        help="render the value-free OpenBao Phase 3 deployment plan; executes no production steps",
    )
    openbao_p3.add_argument(
        "--profile",
        choices=["local-ephemeral", "controller-pilot"],
        required=True,
        help="P3 target profile to render",
    )
    openbao_p3.add_argument(
        "--host-ref",
        default=None,
        help="value-free host reference; required for controller-pilot",
    )
    openbao_p3.add_argument("--address", required=True, help="OpenBao service address")
    openbao_p3.add_argument(
        "--ca-bundle-ref",
        default=None,
        help="value-free CA bundle reference; required for controller-pilot",
    )

    verify_attribution = sub.add_parser(
        "verify-attribution",
        help="role_boundary_attribution check in --base mode (compares <base>..HEAD against active .hermes/handoffs manifests)",
    )
    verify_attribution.add_argument("--base", required=True, help="base commit (e.g., origin/main)")
    verify_attribution.add_argument("paths", nargs="*", default=["."], help="paths to scope")

    verify_path_manifest = sub.add_parser(
        "verify-path-manifest",
        help="path_manifest_fidelity PR-diff gate (compares <base>..HEAD against a PR-carried fenced path manifest; neutral when neither --manifest nor --manifest-dir is given)",
    )
    verify_path_manifest.add_argument("--base", required=True, help="base commit (e.g., the PR base SHA)")
    verify_path_manifest.add_argument(
        "--manifest",
        default=None,
        help="single PR-committed doc carrying the fenced ratified path manifest (ad-hoc / local); omit for a neutral pass. Mutually exclusive with --manifest-dir",
    )
    verify_path_manifest.add_argument(
        "--manifest-dir",
        default=None,
        help="per-PR carrier directory (ce-ops#21, e.g. .ce/pr-manifests): discover this PR's own carrier <dir>/<branch_slug(head)>.md from the diff and enforce diff == its path-set. Requires --head-ref; mutually exclusive with --manifest",
    )
    verify_path_manifest.add_argument(
        "--head-ref",
        default=None,
        help="the PR head branch name (e.g. $GITHUB_HEAD_REF); resolves the expected carrier slug in --manifest-dir mode",
    )
    verify_path_manifest.add_argument(
        "--require-carrier",
        action="store_true",
        help="fail when --manifest-dir mode finds no added per-PR carrier or matching .ce/changelog fragment; intended for CI",
    )
    verify_path_manifest.add_argument("paths", nargs="*", default=["."], help="paths to scope")

    verify_work_sizing_floor = sub.add_parser(
        "verify-work-sizing-floor",
        help="work_sizing_floor PR-diff gate (classifies git diff --numstat --no-renames <base>..HEAD against a declared work class)",
    )
    verify_work_sizing_floor.add_argument("--base", required=True, help="base commit (e.g., the PR base SHA)")
    verify_work_sizing_floor.add_argument(
        "--declared-work-class",
        required=True,
        choices=["tiny", "story", "feature", "epic"],
        help="declared work class to compare against the derived PR-diff floor",
    )
    verify_work_sizing_floor.add_argument("paths", nargs="*", default=["."], help="paths to scope")

    pco_allocate = sub.add_parser(
        "pco-allocate",
        help="PCO-027: allocate a worktree lane (acquire lease, run git worktree add, write claim + event)",
    )
    pco_allocate.add_argument("--lane-id", required=True, help="lane identifier (e.g., pco-slice2r-implementer)")
    pco_allocate.add_argument("--worktree-path", required=True, help="path for the new git worktree")
    pco_allocate.add_argument("--branch", required=True, help="new branch name to create in the worktree")
    pco_allocate.add_argument("--envelope-ref", required=True, help="repo-relative path to the Assignment Envelope (or 'none')")
    pco_allocate.add_argument(
        "--no-write-authority",
        action="store_true",
        help="explicitly allow envelope-ref 'none' and allocate a lane with no tracked-file write authority",
    )
    pco_allocate.add_argument("--controller-id", default=None, help="controller_id override (resolved from local conventions if omitted)")
    pco_allocate.add_argument("--ledger-root", default=None, help="path to .hermes/active-work-ledger (auto-resolved if omitted)")
    pco_allocate.add_argument("--repo-root", default=None, help="repo root path (defaults to cwd)")
    pco_allocate.add_argument("--lease-seconds", type=int, default=3600, help="lease duration in seconds (default: 3600)")
    pco_allocate.add_argument("--pane-label", choices=["architect", "implementer", "controller", "reviewer"], default=None, help="optional pane role label")

    hook_check_p = sub.add_parser(
        "hook-check",
        help="evaluate a Claude hook event (JSON) and emit a machine-readable allow/deny/block decision",
    )
    hook_check_src = hook_check_p.add_mutually_exclusive_group(required=True)
    hook_check_src.add_argument("--input-json", help="path to a Claude hook event JSON file")
    hook_check_src.add_argument("--stdin", action="store_true", help="read the hook event JSON from stdin")
    hook_check_p.add_argument(
        "--posture",
        choices=["auto", "governed", "ungoverned"],
        default="auto",
        help="posture override; 'auto' resolves the §7 predicate from .hermes posture inputs",
    )
    hook_check_p.add_argument(
        "--format",
        dest="output_format",
        choices=["raw", "claude"],
        default="raw",
        help="output shape: 'raw' (default, full CC-G-B decision dict) or 'claude' (minimal Claude Code hook dict)",
    )
    hook_check_p.add_argument("--posture-root", default=None, help="root to resolve .hermes posture inputs (default: event cwd)")
    hook_check_p.add_argument(
        "--ledger-root",
        dest="ledger_root",
        default=None,
        help="launch-pinned absolute Active-Work Ledger root (exported as CE_LEDGER_ROOT "
        "by `ce lane launch`); scopes the §7 posture claim/pane discovery to the seat's "
        "REAL ledger (Gate B) instead of the whole posture-root tree, so tracked "
        "examples/** fixtures can never be matched as governing claims",
    )
    hook_check_p.add_argument("--manifest-doc", default=None, help="handoff/prompt doc carrying the fenced ALLOWED_PATHS manifest")
    hook_check_p.add_argument("--evidence-root", default=None, help="ignored evidence-root prefix the gate may write under")
    hook_check_p.add_argument("--closeout-file", default=None, help="path to the Stop closeout text to verify")
    hook_check_p.add_argument("--completion-report", default=None, help="completion-report artifact to validate on Stop")
    hook_check_p.add_argument(
        "--reviewer-authority-ref",
        dest="reviewer_authority_ref",
        default=None,
        help="launch-pinned reviewer-authority envelope ref injected as ce.reviewer_authority_ref "
        "before context resolution (G2.007.3); resolved under --posture-root",
    )

    pco_release = sub.add_parser(
        "pco-release",
        help="PCO-028: release a worktree lane (mark claim released, remove lease, emit event, git worktree remove)",
    )
    pco_release.add_argument("--lane-id", required=True, help="lane identifier to release")
    pco_release.add_argument("--controller-id", default=None, help="controller_id override (resolved from local conventions if omitted)")
    pco_release.add_argument("--ledger-root", default=None, help="path to .hermes/active-work-ledger (auto-resolved if omitted)")
    pco_release.add_argument("--repo-root", default=None, help="repo root path (defaults to cwd)")
    pco_release.add_argument("--release-reason", default="completed", choices=["completed", "aborted", "lapsed", "handed_off"], help="reason for release (default: completed)")

    release_stage = sub.add_parser(
        "release-stage",
        help="stage deterministic signed-release Pages artifacts; root signing remains Operator-gated",
    )
    release_stage.add_argument("--repo-root", required=True, help="source checkout root to build from")
    release_stage.add_argument("--version", required=True, help="package semver to stage")
    release_stage.add_argument(
        "--build-git-sha",
        default=None,
        help=(
            "checkout HEAD SHA baked into _version.py and the staged manifest; "
            "when supplied, it must match --repo-root HEAD (defaults to HEAD)"
        ),
    )
    release_stage.add_argument("--out", required=True, help="explicit output directory for the staged Pages mirror")
    release_stage.add_argument(
        "--sign-mode",
        default="placeholder",
        choices=["placeholder"],
        help="signing mode; only Operator-gated placeholder staging is supported",
    )
    release_stage.add_argument(
        "--signing-key-id",
        default="ce-dev1-root-v1",
        choices=["ce-root-v1", "ce-dev1-root-v1"],
        help=(
            "valid root trust anchor that will sign this release "
            "(default: ce-dev1-root-v1); becomes the staged spec signature.key_id "
            "and is part of the signed canonical bytes"
        ),
    )
    release_stage.add_argument(
        "--force",
        action="store_true",
        help="replace a non-empty explicit output directory atomically",
    )
    release_stage.add_argument(
        "--dry-run",
        action="store_true",
        help="run build/parity/staging verification without promoting the output directory",
    )

    return parser


def _print_checks(json_output: bool) -> int:
    from .checks import registered_checks

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
    from .checks import run_registered

    return _emit_results(run_registered([Path(p) for p in paths]), json_output)


def _check_examples(json_output: bool) -> int:
    """Validate bundled well-formed examples and expected-failing malformed examples."""
    from .checks import run_registered
    from .reporting import ValidationError

    expectations = [
        ("well-formed", Path("examples/well-formed"), True, None),
        ("malformed", Path("examples/malformed/identity-record.missing-fields.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/spec.creator-engine.missing-acceptance.yml"), False, "FR-013"),
        ("malformed", Path("examples/malformed/duplicate-spec-id"), False, "FR-027a"),
        ("malformed", Path("examples/malformed/handoffs/init-py-corruption.md"), False, "path_manifest_init_py_corruption"),
        ("malformed", Path("examples/malformed/handoffs/hash-mismatch.md"), False, "path_manifest_hash_mismatch"),
        ("malformed", Path("examples/malformed/handoffs/count-mismatch.md"), False, "path_manifest_count_mismatch"),
        ("malformed", Path("examples/malformed/review-evidence/missing-verdict.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/review-evidence/invalid-verdict-value.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/review-evidence/missing-non-ratification-statement.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/architect-evidence/missing-verdict.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/architect-evidence/invalid-verdict-value.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/architect-evidence/missing-non-ratification-statement.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/implementer-evidence/missing-verdict.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/implementer-evidence/invalid-verdict-value.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/implementer-evidence/missing-non-ratification-statement.yml"), False, "FR-001"),
        ("malformed", Path("examples/malformed/completion-reports/missing-envelope-sha256.yaml"), False, "CR-001"),
        ("malformed", Path("examples/malformed/completion-reports/mismatched-sha.yaml"), False, "CR-002"),
        ("malformed", Path("examples/malformed/completion-reports/blocked-without-blocker.yaml"), False, "CR-001"),
        ("malformed", Path("examples/malformed/completion-reports/none-without-rationale.yaml"), False, "CR-001"),
        ("malformed", Path("examples/malformed/worktree-leases/missing-required-fields.yaml"), False, "PCO-020"),
        ("malformed", Path("examples/malformed/worktree-leases/bad-controller-id-pattern.yaml"), False, "PCO-020"),
        ("malformed", Path("examples/malformed/worktree-leases/unknown-top-level-field.yaml"), False, "PCO-020"),
        ("malformed", Path("examples/malformed/worktree-leases/cross-controller-conflict"), False, "PCO-022"),
        ("malformed", Path("examples/malformed/worktree-leases/claim-without-live-lease"), False, "PCO-021"),
        ("malformed", Path("examples/malformed/worktree-leases/signed-lease-bad-sig"), False, "PCO-024"),
        ("malformed", Path("examples/malformed/worktree-leases/signed-lease-revoked-key"), False, "PCO-024"),
        ("malformed", Path("examples/malformed/worktree-leases/signed-lease-unknown-key.yaml"), False, "PCO-024"),
        ("malformed", Path("examples/malformed/controller-keys/missing-required-fields.yaml"), False, "PCO-025"),
        ("malformed", Path("examples/malformed/controller-keys/bad-controller-id-pattern.yaml"), False, "PCO-025"),
        ("malformed", Path("examples/malformed/controller-keys/private-key-material.yaml"), False, "PCO-025"),
        ("well-formed", Path("examples/well-formed/worktree-allocator/successful-state"), True, None),
        ("malformed", Path("examples/malformed/worktree-allocator/pre-existing-conflict"), False, "PCO-010"),
        ("well-formed", Path("examples/well-formed/side-effect-ledger"), True, None),
        ("malformed", Path("examples/malformed/side-effect-ledger/missing-claim"), False, "PCO-056"),
        ("malformed", Path("examples/malformed/side-effect-ledger/duplicate-effect-id"), False, "PCO-057"),
        ("malformed", Path("examples/malformed/side-effect-ledger/secret-payload.yaml"), False, "PCO-059"),
        ("malformed", Path("examples/malformed/side-effect-ledger/unknown-field.yaml"), False, "PCO-063"),
        ("well-formed", Path("examples/well-formed/controller-runtime-contract"), True, None),
        ("malformed", Path("examples/malformed/controller-runtime-contract/misclassified-hosted-authority.yaml"), False, "RV1-020-AUTH"),
        ("malformed", Path("examples/malformed/controller-runtime-contract/secret-value.yaml"), False, "RV1-020-SECRET"),
        ("well-formed", Path("examples/well-formed/state-boundary-contract"), True, None),
        ("malformed", Path("examples/malformed/state-boundary-contract/tracked-write-root.yaml"), False, "RV1-021-WRITE"),
        ("malformed", Path("examples/malformed/state-boundary-contract/secret-config-value.yaml"), False, "RV1-021-SECRET"),
        ("malformed", Path("examples/malformed/state-boundary-contract/hermes-not-ignored.yaml"), False, "RV1-021-IGNORE"),
        ("well-formed", Path("examples/well-formed/state-version-record"), True, None),
        ("malformed", Path("examples/malformed/state-version-record/stale-version.yaml"), False, "RV1-022-STALE"),
        ("malformed", Path("examples/malformed/state-version-record/invalid-status.yaml"), False, "RV1-022"),
        ("well-formed", Path("examples/well-formed/ce-terminology-v2"), True, None),
        ("malformed", Path("examples/malformed/ce-terminology-v2/emits-source-role.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-ROLE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/hermes-active-root.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/source-ratifies-line.md"), False, "VAL-TERMINOLOGY-SOURCE-RATIFIES"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/structured-source-roles.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-ROLE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/nested-hermes-roots.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/plural-hermes-roots.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/nested-source-roles.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-ROLE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/ordered-list-source-ratifies.md"), False, "VAL-TERMINOLOGY-SOURCE-RATIFIES"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/bare-hermes-roots.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/key-and-relative-hermes-roots.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/descriptor-key-source-roles.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-ROLE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/task-list-source-ratifies.md"), False, "VAL-TERMINOLOGY-SOURCE-RATIFIES"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/yaml-source-ratifies.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-RATIFIES"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/active-write-root-hermes.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/canonical-root-hermes.ce.yml"), False, "VAL-WRITE-FREEZE-HERMES-ACTIVE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/plural-ratifiers-source.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-ROLE"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/block-scalar-source-ratifies.ce.yml"), False, "VAL-TERMINOLOGY-SOURCE-RATIFIES"),
        ("malformed", Path("examples/malformed/ce-terminology-v2/forbidden-sidecar.creator-engine.yml"), False, "VAL-TERMINOLOGY-SIDECAR-ALIAS"),
        ("well-formed", Path("examples/well-formed/crosswalk-register"), True, None),
        ("malformed", Path("examples/malformed/crosswalk-register/missing-authoritative.yml"), False, "VAL-CROSSWALK-AUTHORITATIVE"),
        ("malformed", Path("examples/malformed/crosswalk-register/missing-canonical-mappings.yml"), False, "VAL-CROSSWALK-CANONICAL-MAPPING"),
        ("malformed", Path("examples/malformed/crosswalk-register/derived-supersedes-authoritative.yml"), False, "VAL-CROSSWALK-DERIVED-SUPERSEDES"),
        ("malformed", Path("examples/malformed/runtime-policy/unpinned-image.yml"), False, "runtime_policy_image_not_digest_pinned"),
        ("malformed", Path("examples/malformed/runtime-policy/forbidden-mount.yml"), False, "runtime_policy_forbidden_mount"),
        ("malformed", Path("examples/malformed/runtime-policy/controller-key-secret.yml"), False, "runtime_policy_secret_names_only_violation"),
        ("malformed", Path("examples/malformed/runtime-evidence/broken-chain-link.yml"), False, "runtime_evidence_chain_link"),
        ("malformed", Path("examples/malformed/runtime-evidence/mutated-content-hash.yml"), False, "runtime_evidence_content_address"),
        ("malformed", Path("examples/malformed/runtime-evidence/unbound-policy-sha.yml"), False, "runtime_evidence_policy_unbound"),
        ("malformed", Path("examples/malformed/runtime-evidence/agent-action-bad-op.yml"), False, "runtime_evidence_schema_violation"),
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
    if subcommand == "scan-handoffs":
        from .checks.handoff_schema import run as _run_handoff_schema
        result = _run_handoff_schema([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-path-manifest":
        from .checks.path_manifest_fidelity import run as _run_manifest
        result = _run_manifest([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-active-work-ledger":
        from .checks.active_work_ledger_schema import run as _run_ledger
        result = _run_ledger([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-active-work-ledger-conflicts":
        from .checks.active_work_ledger_conflicts import run as _run_ledger_conflicts
        result = _run_ledger_conflicts([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-worktree-leases":
        from .checks.worktree_lease_schema import run as _run_lease
        result = _run_lease([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-controller-keys":
        from .checks.controller_key_schema import run as _run_controller_keys
        result = _run_controller_keys([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-completion-reports":
        from .checks.completion_report_schema import run as _run_cr_schema
        from .checks.completion_report_required_for_envelope import run as _run_cr_pairing
        from .checks.completion_report_terminal_sections import run as _run_cr_terminal
        results = [
            _run_cr_schema([Path(args.path)]),
            _run_cr_pairing([Path(args.path)]),
            _run_cr_terminal([Path(args.path)]),
        ]
        return _emit_results(results, args.json_output)
    if subcommand == "scan-pane-registry":
        from .checks.pane_registry import run as _run_pane_registry
        result = _run_pane_registry([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-side-effect-ledger":
        from .checks.side_effect_ledger import run as _run_side_effect_ledger
        result = _run_side_effect_ledger([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-controller-runtime-contract":
        from .checks.controller_runtime_contract import run as _run_controller_runtime_contract
        result = _run_controller_runtime_contract([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-state-boundary-contract":
        from .checks.state_boundary_contract import run as _run_state_boundary_contract
        result = _run_state_boundary_contract([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-state-version-record":
        from .checks.state_version_record import run as _run_state_version_record
        result = _run_state_version_record([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-crosswalk-register":
        from .checks.crosswalk_register import run as _run_crosswalk_register
        result = _run_crosswalk_register([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-terminology-v2":
        from .checks.ce_terminology_v2 import run as _run_terminology_v2
        result = _run_terminology_v2([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-runtime-policy":
        from .checks.ce_runtime_policy import run as _run_runtime_policy
        result = _run_runtime_policy([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-public-docs-confidentiality":
        from .public_docs_confidentiality import run as _run_public_docs_confidentiality
        result = _run_public_docs_confidentiality([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "openbao-p3-plan":
        return _openbao_p3_plan(args)
    if subcommand == "verify-attribution":
        from .checks.role_boundary_attribution import run_with_base as _run_attribution
        result = _run_attribution([Path(p) for p in args.paths], args.base)
        return _emit_results([result], args.json_output)
    if subcommand == "verify-path-manifest":
        if args.manifest and args.manifest_dir:
            print(
                "ERROR: verify-path-manifest: --manifest and --manifest-dir are mutually exclusive",
                file=sys.stderr,
            )
            return 2
        if args.manifest_dir and not args.head_ref:
            print(
                "ERROR: verify-path-manifest: --manifest-dir requires --head-ref",
                file=sys.stderr,
            )
            return 2
        from .checks.path_manifest_fidelity import run_with_base as _run_path_manifest
        result = _run_path_manifest(
            [Path(p) for p in args.paths],
            args.base,
            args.manifest,
            manifest_dir=args.manifest_dir,
            head_ref=args.head_ref,
            require_carrier=args.require_carrier,
        )
        return _emit_results([result], args.json_output)
    if subcommand == "verify-work-sizing-floor":
        from .checks.work_sizing_floor import run_with_base as _run_work_sizing_floor
        result = _run_work_sizing_floor(
            [Path(p) for p in args.paths],
            args.base,
            declared_work_class=args.declared_work_class,
        )
        return _emit_results([result], args.json_output)
    if subcommand == "hook-check":
        return _hook_check(args)
    if subcommand == "pco-allocate":
        return _pco_allocate(args)
    if subcommand == "pco-release":
        return _pco_release(args)
    if subcommand == "release-stage":
        return _release_stage(args)

    parser.print_usage(sys.stderr)
    return 2


def _release_stage(args) -> int:
    from .release_publish import ReleasePublishError, stage_signed_release

    try:
        result = stage_signed_release(
            repo_root=args.repo_root,
            version=args.version,
            build_git_sha=args.build_git_sha,
            out=args.out,
            sign_mode=args.sign_mode,
            signing_key_id=args.signing_key_id,
            force=args.force,
            dry_run=args.dry_run,
        )
    except ReleasePublishError as exc:
        print(f"ERROR: release-stage refused: {exc}", file=sys.stderr)
        return 1
    payload = {
        "out_dir": str(result.out_dir),
        "version": result.version,
        "build_git_sha": result.build_git_sha,
        "wheel_name": result.wheel_name,
        "wheel_sha256": result.wheel_sha256,
        "sha256s_sha256": result.sha256s_sha256,
        "canonical_spec_sha256": result.canonical_spec_sha256,
        "signature_placeholder": result.signature_placeholder,
        "signing_command": result.signing_command,
        "artifacts": [artifact.__dict__ for artifact in result.artifacts],
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        action = "verified" if args.dry_run else "staged"
        print(f"release-stage: {action} {result.out_dir}")
        print(f"wheel: {result.wheel_name} {result.wheel_sha256}")
        print(f"SHA256SUMS: {result.sha256s_sha256}")
        print(f"canonical spec: {result.canonical_spec_sha256}")
        print(f"signature placeholder: {result.signature_placeholder}")
        print(f"operator signing command: {result.signing_command}")
    return 0


def _openbao_p3_plan(args) -> int:
    from .openbao_p3 import OpenBaoDeploymentConfig, build_p3_deployment_plan

    if args.profile == "local-ephemeral":
        config = OpenBaoDeploymentConfig.local_ephemeral(
            address=args.address,
            allowed_secret_refs=(),
        )
    else:
        if not args.host_ref or not args.ca_bundle_ref:
            print(
                "ERROR: openbao-p3-plan: controller-pilot requires --host-ref and --ca-bundle-ref",
                file=sys.stderr,
            )
            return 2
        config = OpenBaoDeploymentConfig.controller_pilot(
            host_ref=args.host_ref,
            address=args.address,
            ca_bundle_ref=args.ca_bundle_ref,
            allowed_secret_refs=(),
        )
    plan = build_p3_deployment_plan(config)
    payload = {
        "ok": True,
        "profile": plan.profile,
        "ready_for_local_execution": plan.ready_for_local_execution,
        "automated_steps": list(plan.automated_steps),
        "operator_required_steps": list(plan.operator_required_steps),
        "record": dict(plan.record),
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"OpenBao P3 profile: {plan.profile}")
        print(f"ready_for_local_execution: {str(plan.ready_for_local_execution).lower()}")
        print("automated_steps:")
        for step in plan.automated_steps:
            print(f"- {step}")
        print("operator_required_steps:")
        for step in plan.operator_required_steps:
            print(f"- {step}")
    return 0


def _hook_check(args) -> int:
    """Evaluate a Claude hook event and emit a JSON decision.

    Exit ``0`` for any evaluated allow/deny/block decision (a denial is a
    hook decision, not a CLI failure); non-zero only for invalid input or
    arguments.
    """
    from . import hook_check as hc

    if args.stdin:
        raw = sys.stdin.read()
    else:
        try:
            raw = Path(args.input_json).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: hook-check: cannot read --input-json: {exc}", file=sys.stderr)
            return 2

    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: hook-check: invalid event JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(event, dict):
        print("ERROR: hook-check: event JSON must be an object", file=sys.stderr)
        return 2

    seat_class = _launch_pinned_seat_class_from_env()
    if seat_class:
        ce = event.get("ce")
        if not isinstance(ce, dict):
            ce = {}
            event["ce"] = ce
        ce["seat_class"] = seat_class

    # G2.007.3: a live reviewer venue exports its authority ref via the launch-pinned
    # environment; the hook forwards it here. Inject it as ce.reviewer_authority_ref so
    # build_context() resolves it exactly as the synthetic probes proved — but never
    # override an event that already carries its own ce authority (the event wins).
    ref = getattr(args, "reviewer_authority_ref", None)
    if ref:
        ce = event.get("ce")
        if not isinstance(ce, dict):
            ce = {}
            event["ce"] = ce
        if "reviewer_authority_ref" not in ce and "reviewer_authority" not in ce:
            ce["reviewer_authority_ref"] = ref

    worker_id = os.environ.get("CE_WORKER_ID")
    worker_record_ref = os.environ.get("CE_WORKER_RECORD_REF")
    if worker_id or worker_record_ref:
        ce = event.get("ce")
        if not isinstance(ce, dict):
            ce = {}
            event["ce"] = ce
        if worker_id and "worker_id" not in ce:
            ce["worker_id"] = worker_id
        if worker_record_ref and "worker_record_ref" not in ce:
            ce["worker_record_ref"] = worker_record_ref

    context = hc.build_context(
        event,
        posture=args.posture,
        posture_root=args.posture_root,
        ledger_root=getattr(args, "ledger_root", None),
        manifest_doc=args.manifest_doc,
        evidence_root=args.evidence_root,
        closeout_file=args.closeout_file,
        completion_report=args.completion_report,
    )
    decision = hc.evaluate(event, context)
    if getattr(args, "output_format", "raw") == "claude":
        payload = decision.to_claude_hook_dict()
    else:
        payload = decision.to_dict()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _launch_pinned_seat_class_from_env() -> str:
    """Resolve the launch-pinned brain-bootstrap seat class, failing to foreman.

    The hook event itself is not the authority for seat class. A governed launch
    writes a bootstrap payload and exports its path plus digest; only a matching
    payload can opt a seat down to ``worker``. Missing or invalid payloads fail
    closed to ``foreman`` so event-local seat-class claims cannot weaken the live
    hook posture.
    """
    ref = os.environ.get("CE_BRAIN_BOOTSTRAP_REF")
    expected = os.environ.get("CE_BRAIN_BOOTSTRAP_SHA256")
    if not ref and not expected:
        return "foreman"
    if not ref or not expected:
        return "foreman"
    try:
        data = Path(ref).read_bytes()
    except OSError:
        return "foreman"
    if hashlib.sha256(data).hexdigest() != expected:
        return "foreman"
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return "foreman"
    if not isinstance(payload, dict):
        return "foreman"
    context = payload.get("context")
    if not isinstance(context, dict):
        return "foreman"
    raw = context.get("seat_class")
    if raw == "worker":
        return "worker"
    return "foreman"


def _resolve_ledger_root(args_ledger_root: str | None, repo_root_path: Path) -> Path:
    if args_ledger_root:
        return Path(args_ledger_root)
    return repo_root_path / ".hermes" / "active-work-ledger"


def _pco_allocate(args) -> int:
    from .pco_allocator import (
        PcoAllocatorError,
        PcoConflictError,
        RootCheckoutRefused,
        allocate,
        resolve_controller_id,
    )

    if args.envelope_ref == "none" and not args.no_write_authority:
        print(
            "ERROR: pco-allocate refused: --envelope-ref none provisions NO write authority; "
            "pass --no-write-authority to confirm this intentional no-authority lane.",
            file=sys.stderr,
        )
        return 1

    repo_root = Path(args.repo_root) if args.repo_root else Path.cwd()
    ledger_root = _resolve_ledger_root(args.ledger_root, repo_root)
    controller_id = args.controller_id or resolve_controller_id(repo_root)
    if not controller_id:
        print(
            "ERROR: pco-allocate: controller_id could not be resolved. "
            f"Set {__import__('creator_engine_validator.pco_allocator', fromlist=['CONTROLLER_ID_ENV']).CONTROLLER_ID_ENV} "
            "or provide --controller-id.",
            file=sys.stderr,
        )
        return 1

    try:
        allocate(
            repo_root=repo_root,
            ledger_root=ledger_root,
            lane_id=args.lane_id,
            worktree_path=Path(args.worktree_path),
            envelope_ref=args.envelope_ref,
            branch=args.branch,
            controller_id=controller_id,
            lease_seconds=args.lease_seconds,
            pane_label=args.pane_label,
        )
    except RootCheckoutRefused as exc:
        print(f"ERROR: pco-allocate refused — root checkout: {exc}", file=sys.stderr)
        return 1
    except PcoConflictError as exc:
        print(f"ERROR: pco-allocate refused — conflict: {exc}", file=sys.stderr)
        return 1
    except PcoAllocatorError as exc:
        print(f"ERROR: pco-allocate failed: {exc}", file=sys.stderr)
        return 1

    if args.envelope_ref == "none":
        print(
            "⚠ allocated with NO write authority — this seat cannot author tracked files; "
            "every Edit/Write will be advisory-flagged."
        )
    print(f"pco-allocate: lane {args.lane_id!r} allocated at {args.worktree_path}")
    return 0


def _pco_release(args) -> int:
    from .pco_allocator import (
        PcoAllocatorError,
        RootCheckoutRefused,
        release,
        resolve_controller_id,
    )

    repo_root = Path(args.repo_root) if args.repo_root else Path.cwd()
    ledger_root = _resolve_ledger_root(args.ledger_root, repo_root)
    controller_id = args.controller_id or resolve_controller_id(repo_root)
    if not controller_id:
        print(
            "ERROR: pco-release: controller_id could not be resolved. "
            "Provide --controller-id.",
            file=sys.stderr,
        )
        return 1

    try:
        release(
            repo_root=repo_root,
            ledger_root=ledger_root,
            lane_id=args.lane_id,
            controller_id=controller_id,
            release_reason=args.release_reason,
        )
    except RootCheckoutRefused as exc:
        print(f"ERROR: pco-release refused — root checkout: {exc}", file=sys.stderr)
        return 1
    except PcoAllocatorError as exc:
        print(f"ERROR: pco-release failed: {exc}", file=sys.stderr)
        return 1

    print(f"pco-release: lane {args.lane_id!r} released")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
