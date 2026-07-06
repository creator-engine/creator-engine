"""Command-line interface for the Creator Engine validator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from .check_profiles import CHECK_PROFILES, emit_profile_notices, omitted_checks_for_profile
from .reporting import CheckResult
from .work_sizing import WORK_CLASS_INPUTS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creator_engine_validator")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    parser.add_argument("--tenant", help="restrict cross-artifact checks to one tenant")
    parser.add_argument("--list-checks", action="store_true", help="list enabled checks and their FRs")
    parser.add_argument(
        "--profile",
        choices=CHECK_PROFILES,
        default=None,
        help=argparse.SUPPRESS,
    )
    sub = parser.add_subparsers(dest="subcommand")

    check = sub.add_parser("check", help="run all enabled checks")
    check.add_argument("paths", nargs="*", default=["."], help="paths to validate")
    check.add_argument(
        "--profile",
        choices=CHECK_PROFILES,
        default=None,
        help=argparse.SUPPRESS,
    )

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
    guard_public_docs_confidentiality_push = sub.add_parser(
        "guard-public-docs-confidentiality-push",
        help=(
            "pre-push/pre-receive confidentiality guard: read git ref updates "
            "from stdin and fail if any pushed tree leaks a ce-ops# ticket ref "
            "or internal host identifier"
        ),
    )
    guard_public_docs_confidentiality_push.add_argument(
        "path", nargs="?", default=".", help="repo root to scan (default: .)"
    )
    guard_public_docs_confidentiality_push.add_argument(
        "--object",
        dest="objects",
        action="append",
        default=[],
        help="explicit commit/tree object to scan instead of reading hook stdin; may be repeated",
    )

    scan_portability_plane = sub.add_parser(
        "scan-portability-plane",
        help=(
            "fail if portable control-plane validator modules contain Linux runtime-plane "
            "assumptions not declared in the portability manifest"
        ),
    )
    scan_portability_plane.add_argument(
        "path", nargs="?", default=".", help="repo root to scan (default: .)"
    )

    scan_install_spec_signature = sub.add_parser(
        "scan-install-spec-signature",
        help=(
            "fail-closed install-spec SSHSIG scan: rejects placeholder values, "
            "invalid base64, content_sha mismatch, and non-verifying signatures"
        ),
    )
    scan_install_spec_signature.add_argument(
        "path", nargs="?", default=".", help="repo root to scan (default: .)"
    )

    scan_support_corpus = sub.add_parser(
        "scan-support-corpus",
        help=(
            "fail if the `ce ask` product-lens corpus allowlist lists a doc that "
            "is NOT confidentiality-clean (the corpus must be a subset of the "
            "confidentiality-clean surface; reuses the #571/#306 guard)"
        ),
    )
    scan_support_corpus.add_argument(
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
        help="work_sizing_floor PR-diff gate (classifies git diff --numstat --find-renames <base>..HEAD against a declared work class)",
    )
    verify_work_sizing_floor.add_argument("--base", required=True, help="base commit (e.g., the PR base SHA)")
    verify_work_sizing_floor.add_argument(
        "--declared-work-class",
        required=True,
        choices=WORK_CLASS_INPUTS,
        help="declared work class to compare against the derived PR-diff floor",
    )
    verify_work_sizing_floor.add_argument("paths", nargs="*", default=["."], help="paths to scope")

    verify_test_coupling = sub.add_parser(
        "verify-test-coupling",
        help=(
            "test_coupling PR-diff gate (fails when <base>..HEAD adds or modifies "
            "non-test source code without adding or modifying tests)"
        ),
    )
    verify_test_coupling.add_argument("--base", required=True, help="base commit (e.g., the PR base SHA)")
    verify_test_coupling.add_argument(
        "--pr-body-file",
        default=None,
        help="optional file containing PR body text for CE-TEST-COUPLING-EXEMPT override detection",
    )
    verify_test_coupling.add_argument("paths", nargs="*", default=["."], help="paths to scope")

    verify_version_drift = sub.add_parser(
        "verify-version-drift",
        help="version_drift current-version surface gate (compares unsigned docs/deploy defaults against version.py)",
    )
    verify_version_drift.add_argument("paths", nargs="*", default=["."], help="paths to scope")

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
        default="ce-root-v1",
        choices=["ce-root-v1", "ce-dev1-root-v1"],
        help=(
            "valid root trust anchor that will sign this release "
            "(default: ce-root-v1, the public trust root the install recipe is "
            "authored for; ce-dev1-root-v1 is the dev/test anchor and rewrites "
            "the embedded recipe); becomes the staged spec signature.key_id "
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

    release_finalize = sub.add_parser(
        "release-finalize",
        help="verify an Operator SSHSIG and prepare publishable signed release artifacts; no sign/publish",
    )
    release_finalize.add_argument("--stage", required=True, help="staged release directory from `release`")
    sig_src = release_finalize.add_mutually_exclusive_group(required=True)
    sig_src.add_argument("--signature-base64", help="base64-encoded SSHSIG over llms-install.canonical")
    sig_src.add_argument("--signature-file", help="file containing the base64-encoded SSHSIG")
    release_finalize.add_argument("--out", required=True, help="explicit output directory for signed publishable artifacts")
    release_finalize.add_argument(
        "--force",
        action="store_true",
        help="replace a non-empty explicit output directory atomically",
    )

    release_bump = sub.add_parser(
        "release-bump",
        help="drive the canonical version sources to a release target (staged only; no commit/sign/publish)",
    )
    release_bump.add_argument("--repo-root", default=".", help="repo root holding validators/ (default: .)")
    bump_src = release_bump.add_mutually_exclusive_group(required=True)
    bump_src.add_argument("--tag", help="release/vX.Y.Z tag; version derived from it (tag-as-source-of-truth)")
    bump_src.add_argument(
        "--part",
        choices=["major", "minor", "patch"],
        help="compute next version by bumping this part of the current version (rehearsal path)",
    )
    release_bump.add_argument(
        "--commit",
        action="store_true",
        help="create a fresh local branch, commit only the version bump, and generate PR carriers; no push/PR",
    )
    release_bump.add_argument(
        "--out-branch",
        default=None,
        help="fresh local branch to create when --commit is set",
    )

    release_changelog = sub.add_parser(
        "release-changelog",
        help="aggregate .ce/changelog/*.md fragments since the last release/* tag into release notes",
    )
    release_changelog.add_argument("--repo-root", default=".", help="repo root holding .ce/changelog/ (default: .)")
    release_changelog.add_argument("--version", required=True, help="release version the notes are for")
    release_changelog.add_argument(
        "--since-tag",
        default=None,
        help="select fragments introduced after this ref (default: most recent release/* tag, else all)",
    )
    release_changelog.add_argument(
        "--date",
        dest="release_date",
        default=None,
        help="release-note date YYYY-MM-DD (default: latest selected fragment date, else undated)",
    )
    release_changelog.add_argument("--out", default=None, help="write the release notes to this file (default: stdout)")
    release_changelog.add_argument(
        "--github-out",
        default=None,
        help="write the GitHub release body markdown to this file",
    )

    release = sub.add_parser(
        "release",
        help="orchestrate bump → changelog → release-stage into a staged, signature-shaped artifact (no sign/publish)",
    )
    release.add_argument("--repo-root", default=".", help="source checkout root to build from (default: .)")
    rel_src = release.add_mutually_exclusive_group(required=True)
    rel_src.add_argument("--tag", help="release/vX.Y.Z tag; version derived (tag-as-source-of-truth)")
    rel_src.add_argument("--version", help="explicit X.Y.Z to stage at (drives the sources to it)")
    rel_src.add_argument("--part", choices=["major", "minor", "patch"], help="next version by bumping this part")
    release.add_argument("--out", required=True, help="explicit output directory for the staged Pages mirror")
    release.add_argument(
        "--signing-key-id",
        default="ce-root-v1",
        choices=["ce-root-v1", "ce-dev1-root-v1"],
        help="root trust anchor that will sign this release (placeholder staged; default: ce-root-v1, the public trust root)",
    )
    release.add_argument("--changelog-out", default=None, help="also write aggregated release notes to this file")
    release.add_argument("--github-out", default=None, help="also write the GitHub release body markdown to this file")
    release.add_argument("--force", action="store_true", help="replace a non-empty output directory atomically")
    release.add_argument(
        "--preflight-mode",
        choices=["validate-pr", "release-tag"],
        default="validate-pr",
        help=(
            "preflight gate to run before staging; release-tag avoids PR-diff carrier "
            "assumptions for detached release tag checkouts"
        ),
    )
    release.add_argument(
        "--preflight-head-ref",
        default=None,
        help="explicit head ref for validate-pr preflight when the checkout is detached",
    )
    release.add_argument(
        "--preflight-declared-work-class",
        default=None,
        choices=WORK_CLASS_INPUTS,
        help="explicit work class for validate-pr preflight when carrier discovery is not desired",
    )
    release.add_argument(
        "--dry-run",
        action="store_true",
        help="run the full bump/changelog/stage verification without promoting the output directory",
    )

    return parser


def _print_checks(json_output: bool, profile: str | None = None) -> int:
    from .checks import registered_checks

    checks = registered_checks()
    omissions = omitted_checks_for_profile(profile)
    if omissions and profile is not None:
        emit_profile_notices(profile, omissions)
        checks = {name: defn for name, defn in checks.items() if name not in omissions}
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


def _check(paths: Sequence[str], json_output: bool, profile: str | None = None) -> int:
    from .checks import run_registered

    omissions = omitted_checks_for_profile(profile)
    if omissions and profile is not None:
        emit_profile_notices(profile, omissions)
    results = [
        result
        for result in run_registered([Path(p) for p in paths])
        if result.name not in omissions
    ]
    return _emit_results(results, json_output)


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
        return _print_checks(args.json_output, getattr(args, "profile", None))

    subcommand = args.subcommand or "check"
    if subcommand == "check":
        return _check(getattr(args, "paths", ["."]), args.json_output, getattr(args, "profile", None))
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
    if subcommand == "guard-public-docs-confidentiality-push":
        from .public_docs_confidentiality import run_push_guard

        lines = [] if args.objects else sys.stdin.read().splitlines()
        result = run_push_guard(lines, repo_root=Path(args.path), object_refs=args.objects)
        return _emit_results([result], args.json_output)
    if subcommand == "scan-portability-plane":
        from .checks.portability_plane import run as _run_portability_plane
        result = _run_portability_plane([Path(args.path)])
        return _emit_results([result], args.json_output)
    if subcommand == "scan-install-spec-signature":
        from .checks.install_spec_signature_guard import CHECK_NAME, validate_repo

        result = CheckResult(name=CHECK_NAME, errors=tuple(validate_repo(Path(args.path))))
        return _emit_results([result], args.json_output)
    if subcommand == "scan-support-corpus":
        from .support_corpus import run as _run_support_corpus
        result = _run_support_corpus([Path(args.path)])
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
    if subcommand == "verify-test-coupling":
        from .checks.test_coupling import run_with_base as _run_test_coupling

        pr_body = None
        if args.pr_body_file:
            try:
                pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                print(f"ERROR: verify-test-coupling: could not read --pr-body-file: {exc}", file=sys.stderr)
                return 2
        result = _run_test_coupling(
            [Path(p) for p in args.paths],
            args.base,
            pr_body=pr_body,
        )
        return _emit_results([result], args.json_output)
    if subcommand == "verify-version-drift":
        from .checks.version_drift import run as _run_version_drift

        result = _run_version_drift([Path(p) for p in args.paths])
        return _emit_results([result], args.json_output)
    if subcommand == "hook-check":
        return _hook_check(args)
    if subcommand == "pco-allocate":
        return _pco_allocate(args)
    if subcommand == "pco-release":
        return _pco_release(args)
    if subcommand == "release-stage":
        return _release_stage(args)
    if subcommand == "release-finalize":
        return _release_finalize(args)
    if subcommand == "release-bump":
        return _release_bump(args)
    if subcommand == "release-changelog":
        return _release_changelog(args)
    if subcommand == "release":
        return _release(args)

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


def _release_finalize(args) -> int:
    from .release_publish import ReleasePublishError, finalize_signed_release

    if args.signature_file:
        try:
            signature_base64 = Path(args.signature_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            print(f"ERROR: release-finalize refused: could not read signature file: {exc}", file=sys.stderr)
            return 1
    else:
        signature_base64 = args.signature_base64

    try:
        result = finalize_signed_release(
            stage=args.stage,
            signature_base64=signature_base64,
            out=args.out,
            force=args.force,
        )
    except ReleasePublishError as exc:
        print(f"ERROR: release-finalize refused: {exc}", file=sys.stderr)
        return 1
    payload = {
        "out_dir": str(result.out_dir),
        "version": result.version,
        "canonical_spec_sha256": result.canonical_spec_sha256,
        "signed_spec_sha256": result.signed_spec_sha256,
        "signature_sha256": result.signature_sha256,
        "signing_key_id": result.signing_key_id,
        "artifacts": [artifact.__dict__ for artifact in result.artifacts],
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"release-finalize: verified signed artifacts at {result.out_dir}")
        print(f"version: {result.version}")
        print(f"canonical spec sha256: {result.canonical_spec_sha256}")
        print(f"signed spec sha256: {result.signed_spec_sha256}")
        print(f"signature sha256: {result.signature_sha256}")
        print("publish seam: upload this directory only after normal release ratification")
    return 0


def _release_bump(args) -> int:
    from .release_bump import ReleaseBumpError, bump_release_version, commit_release_bump

    try:
        if args.commit:
            result = commit_release_bump(
                repo_root=args.repo_root,
                tag=args.tag,
                part=args.part,
                out_branch=args.out_branch or "",
            )
            payload = {
                "version": result.bump.version,
                "previous_version": result.bump.previous_version,
                "source": result.bump.source,
                "version_py": str(result.bump.version_py),
                "pyproject": str(result.bump.pyproject),
                "branch": result.branch,
                "commit_sha": result.commit_sha,
                "commit_message": result.commit_message,
                "changelog": str(result.carriers.changelog_path),
                "manifest": str(result.carriers.manifest_path),
                "carrier_paths": list(result.carriers.paths),
            }
            if getattr(args, "json_output", False):
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    "release-bump commit: "
                    f"{result.bump.previous_version} -> {result.bump.version} "
                    f"on {result.branch}"
                )
                print(f"commit: {result.commit_sha}")
                print(f"message: {result.commit_message}")
                print(f"changelog: {result.carriers.changelog_path}")
                print(f"manifest:  {result.carriers.manifest_path}")
            return 0

        result = bump_release_version(repo_root=args.repo_root, tag=args.tag, part=args.part)
    except ReleaseBumpError as exc:
        print(f"ERROR: release-bump refused: {exc}", file=sys.stderr)
        return 1
    payload = {
        "version": result.version,
        "previous_version": result.previous_version,
        "source": result.source,
        "version_py": str(result.version_py),
        "pyproject": str(result.pyproject),
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"release-bump: {result.previous_version} -> {result.version} (source: {result.source})")
        print(f"version.py: {result.version_py}")
        print(f"pyproject:  {result.pyproject}")
    return 0


def _release_changelog(args) -> int:
    from .release_changelog import ReleaseChangelogError, aggregate_changelog

    try:
        result = aggregate_changelog(
            repo_root=args.repo_root,
            version=args.version,
            since_tag=args.since_tag,
            release_date=args.release_date,
        )
    except ReleaseChangelogError as exc:
        print(f"ERROR: release-changelog refused: {exc}", file=sys.stderr)
        return 1
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.notes, encoding="utf-8")
    if args.github_out:
        github_out_path = Path(args.github_out)
        github_out_path.parent.mkdir(parents=True, exist_ok=True)
        github_out_path.write_text(result.github_body, encoding="utf-8")
    if getattr(args, "json_output", False):
        print(
            json.dumps(
                {
                    "version": result.version,
                    "release_date": result.release_date,
                    "fragment_count": result.fragment_count,
                    "since_tag": result.since_tag,
                    "out": args.out,
                    "github_out": args.github_out,
                    "notes": result.notes,
                    "github_body": result.github_body,
                    "towncrier": (
                        {
                            "runtime_available": result.towncrier.runtime_available,
                            "config": result.towncrier.config,
                        }
                        if result.towncrier
                        else None
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif args.out or args.github_out:
        targets = []
        if args.out:
            targets.append(f"notes -> {args.out}")
        if args.github_out:
            targets.append(f"github body -> {args.github_out}")
        print(
            f"release-changelog: wrote {result.fragment_count} fragment(s) "
            f"(since {result.since_tag or 'all'}, date {result.release_date}) "
            f"{', '.join(targets)}"
        )
    else:
        print(result.notes)
    return 0


def _release(args) -> int:
    from .release_orchestrator import ReleaseOrchestrationError, orchestrate_release

    try:
        result = orchestrate_release(
            repo_root=args.repo_root,
            out=args.out,
            tag=args.tag,
            version=args.version,
            part=args.part,
            signing_key_id=args.signing_key_id,
            changelog_out=args.changelog_out,
            github_out=args.github_out,
            force=args.force,
            dry_run=args.dry_run,
            preflight_mode=args.preflight_mode,
            preflight_head_ref=args.preflight_head_ref,
            preflight_declared_work_class=args.preflight_declared_work_class,
        )
    except ReleaseOrchestrationError as exc:
        print(f"ERROR: release refused: {exc}", file=sys.stderr)
        return 1
    packet = result.packet
    packet_payload = {
        "version": packet.version,
        "artifacts": {
            "llms-install.canonical": packet.canonical_path,
            "release-stage-manifest.yml": packet.manifest_path,
            "SIGNING-INSTRUCTIONS.md": packet.signing_instructions_path,
        },
        "canonical_spec_sha256": packet.canonical_spec_sha256,
        "shas": {
            "build_git_sha": packet.build_git_sha,
            "wheel_sha256": packet.wheel_sha256,
            "sha256s_sha256": packet.sha256s_sha256,
            "canonical_spec_sha256": packet.canonical_spec_sha256,
        },
        "signing_key_id": packet.signing_key_id,
        "intended_public_anchor": packet.intended_public_anchor,
        "signature_placeholder": packet.signature_placeholder,
        "signing_command": packet.signing_command,
        "github_release_body": packet.github_release_body,
    }
    payload = {
        "version": result.version,
        "previous_version": result.bump.previous_version,
        "bump_source": result.bump.source,
        "preflight_head_sha": result.preflight.head_sha,
        "preflight_validate_pr_returncode": result.preflight.validate_pr.returncode,
        "changelog_fragment_count": result.changelog.fragment_count,
        "changelog_since_tag": result.changelog.since_tag,
        "changelog_out": str(result.changelog_out) if result.changelog_out else None,
        "github_out": str(result.github_out) if result.github_out else None,
        "out_dir": str(result.stage.out_dir),
        "build_git_sha": packet.build_git_sha,
        "wheel_sha256": packet.wheel_sha256,
        "sha256s_sha256": packet.sha256s_sha256,
        "canonical_spec_sha256": packet.canonical_spec_sha256,
        "signing_key_id": packet.signing_key_id,
        "intended_public_anchor": packet.intended_public_anchor,
        "signature_placeholder": packet.signature_placeholder,
        "signing_command": packet.signing_command,
        "canonical_path": packet.canonical_path,
        "manifest_path": packet.manifest_path,
        "signing_instructions_path": packet.signing_instructions_path,
        "github_release_body": packet.github_release_body,
        "ratification_packet": packet_payload,
        "dry_run": bool(args.dry_run),
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        action = "verified" if args.dry_run else "staged"
        print(f"release: {action} {result.stage.out_dir}")
        print(f"version: {result.bump.previous_version} -> {result.version} (source: {result.bump.source})")
        print(f"changelog: {result.changelog.fragment_count} fragment(s) since {result.changelog.since_tag or 'all'}")
        print(f"canonical spec sha256: {packet.canonical_spec_sha256}")
        print(f"signing key id: {packet.signing_key_id}")
        print(f"intended public anchor: {packet.intended_public_anchor}")
        print(f"signature placeholder: {packet.signature_placeholder}")
        print("RATIFICATION PACKET (Operator signs offline; nothing here signs/publishes):")
        print(f"  canonical bytes:      {packet.canonical_path}")
        print(f"  stage manifest:       {packet.manifest_path}")
        print(f"  signing instructions: {packet.signing_instructions_path}")
        print(f"  signing command:      {packet.signing_command}")
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
