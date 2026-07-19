"""Materialize the governed automerge policy declaration to the live policy state.

Usage:
    python3 deploy/automerge/materialize-automerge-policy.py --repo-root <root> [--dry-run]

This is a deploy script, not a ce CLI surface.  It reads
deploy/automerge/policy-declaration.yaml, validates the declaration
strictly, and writes the result atomically to
<repo-root>/.ce/state/automerge/policy.json via
save_automerge_policy_state.

Fail-closed contract
--------------------
- Unknown top-level keys in the declaration    -> exit 2, nothing written
- Non-bool auto_merge flag in any class/tier   -> exit 2, nothing written
- Empty or missing enabling_decision_ref       -> exit 2, nothing written
- run_mode not in {"ceo", "strangeLoop", "dev"} -> exit 2, nothing written
- Any other ambiguity or import failure        -> exit 2, nothing written

PYTHONPATH must include the validators/ directory so that
creator_engine_validator is importable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent.parent

_DECLARATION_PATH = _SCRIPT_DIR / "policy-declaration.yaml"

_KNOWN_TOP_KEYS = frozenset(
    {"run_mode", "kill_switch", "classes", "tiers", "enabling_decision_ref"}
)

_KNOWN_CLASS_KEYS = frozenset({"auto_merge"})
_KNOWN_TIER_KEYS = frozenset({"auto_merge"})


class DeclarationError(Exception):
    """A fatal validation error in the policy declaration."""


def _load_yaml(path: Path) -> object:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise DeclarationError(f"yaml not importable: {exc}") from exc
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DeclarationError(f"cannot read {path}: {exc}") from exc
    try:
        return yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        raise DeclarationError(f"YAML parse error in {path}: {exc}") from exc


def _validate_declaration(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise DeclarationError("declaration must be a YAML mapping")

    unknown = set(raw.keys()) - _KNOWN_TOP_KEYS
    if unknown:
        raise DeclarationError(
            f"unknown top-level key(s) in declaration: {sorted(unknown)}"
        )

    # run_mode
    run_mode = raw.get("run_mode")
    if not isinstance(run_mode, str) or not run_mode:
        raise DeclarationError("run_mode must be a non-empty string")
    from creator_engine_validator.forge.automerge_policy import AUTOMERGE_ARMING_RUN_MODES
    valid_run_modes = AUTOMERGE_ARMING_RUN_MODES | {"dev"}
    if run_mode not in valid_run_modes:
        raise DeclarationError(
            f"run_mode {run_mode!r} not in valid set {sorted(valid_run_modes)}"
        )

    # kill_switch
    kill_switch = raw.get("kill_switch", False)
    if not isinstance(kill_switch, bool):
        raise DeclarationError("kill_switch must be a boolean")

    # enabling_decision_ref
    enabling_decision_ref = raw.get("enabling_decision_ref")
    if not isinstance(enabling_decision_ref, str) or not enabling_decision_ref.strip():
        raise DeclarationError(
            "enabling_decision_ref must be a non-empty string"
        )

    # classes
    from creator_engine_validator.work_sizing import MUTATION_CLASSES
    raw_classes = raw.get("classes", {})
    if not isinstance(raw_classes, dict):
        raise DeclarationError("classes must be a mapping")
    for class_name, class_val in raw_classes.items():
        if class_name not in MUTATION_CLASSES:
            raise DeclarationError(
                f"unknown mutation class in declaration: {class_name!r}"
            )
        if not isinstance(class_val, dict):
            raise DeclarationError(
                f"class entry {class_name!r} must be a mapping"
            )
        unknown_class_keys = set(class_val.keys()) - _KNOWN_CLASS_KEYS
        if unknown_class_keys:
            raise DeclarationError(
                f"unknown key(s) in class {class_name!r}: {sorted(unknown_class_keys)}"
            )
        auto_merge = class_val.get("auto_merge", False)
        if not isinstance(auto_merge, bool):
            raise DeclarationError(
                f"class {class_name!r} auto_merge must be a boolean, got {auto_merge!r}"
            )

    # tiers
    from creator_engine_validator.forge.automerge_policy import _AUTOMERGE_TIERS
    raw_tiers = raw.get("tiers", {})
    if not isinstance(raw_tiers, dict):
        raise DeclarationError("tiers must be a mapping")
    for tier_name, tier_val in raw_tiers.items():
        if tier_name not in _AUTOMERGE_TIERS:
            raise DeclarationError(
                f"unknown automerge tier in declaration: {tier_name!r}"
            )
        if not isinstance(tier_val, dict):
            raise DeclarationError(
                f"tier entry {tier_name!r} must be a mapping"
            )
        unknown_tier_keys = set(tier_val.keys()) - _KNOWN_TIER_KEYS
        if unknown_tier_keys:
            raise DeclarationError(
                f"unknown key(s) in tier {tier_name!r}: {sorted(unknown_tier_keys)}"
            )
        auto_merge = tier_val.get("auto_merge", False)
        if not isinstance(auto_merge, bool):
            raise DeclarationError(
                f"tier {tier_name!r} auto_merge must be a boolean, got {auto_merge!r}"
            )

    return dict(raw)


def _build_payload(validated: dict) -> dict:
    from creator_engine_validator.work_sizing import MUTATION_CLASSES
    from creator_engine_validator.forge.automerge_policy import _AUTOMERGE_TIERS

    run_mode = validated["run_mode"]
    kill_switch = validated.get("kill_switch", False)
    enabling_decision_ref = validated["enabling_decision_ref"]

    raw_classes = validated.get("classes", {})
    classes_payload = {}
    for class_name in MUTATION_CLASSES:
        if class_name in raw_classes:
            classes_payload[class_name] = {
                "auto_merge": raw_classes[class_name].get("auto_merge", False)
            }
        else:
            classes_payload[class_name] = {"auto_merge": False}

    raw_tiers = validated.get("tiers", {})
    tiers_payload = {}
    for tier_name in _AUTOMERGE_TIERS:
        if tier_name in raw_tiers:
            tiers_payload[tier_name] = {
                "auto_merge": raw_tiers[tier_name].get("auto_merge", False)
            }
        else:
            tiers_payload[tier_name] = {"auto_merge": False}

    return {
        "run_mode": run_mode,
        "kill_switch": kill_switch,
        "classes": classes_payload,
        "tiers": tiers_payload,
        "enabling_decision_ref": enabling_decision_ref,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize governed automerge policy declaration to live policy state.",
        prog="materialize-automerge-policy.py",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT_DEFAULT),
        help="Repository root (default: two directories above this script)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the resulting JSON payload without writing anything",
    )
    parser.add_argument(
        "--declaration",
        default=str(_DECLARATION_PATH),
        help="Path to the policy declaration YAML (default: policy-declaration.yaml next to this script)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    declaration_path = Path(args.declaration).resolve()

    try:
        raw = _load_yaml(declaration_path)
        validated = _validate_declaration(raw)
        payload = _build_payload(validated)
    except DeclarationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    from creator_engine_validator.forge.automerge_policy import (
        AutoMergePolicyState,
        automerge_policy_state_path,
        load_automerge_policy_state,
        save_automerge_policy_state,
    )

    try:
        state = AutoMergePolicyState.from_payload(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: AutoMergePolicyState.from_payload refused the payload: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(state.to_payload(), sort_keys=True, indent=2))
        return 0

    target_path = automerge_policy_state_path(repo_root / ".ce" / "state")
    try:
        save_automerge_policy_state(target_path, state)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: save_automerge_policy_state failed: {exc}", file=sys.stderr)
        return 2

    try:
        effective = load_automerge_policy_state(target_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: reload after write failed: {exc}", file=sys.stderr)
        return 2

    print(f"Materialized policy state to: {target_path}")
    print(json.dumps(effective.to_payload(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
