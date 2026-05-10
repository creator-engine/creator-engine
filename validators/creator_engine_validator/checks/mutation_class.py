"""Mutation-class taxonomy and class/action mismatch validation for US3 A2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .sidecar_utils import iter_sidecar_paths

CONTRACT = "docs/contracts/mutation-class-taxonomy.md"
TAXONOMY_PATH = Path("docs/contracts/mutation-class-taxonomy.yml")
TENANT_OVERLAY_FILENAME = "mutation-classes.yml"

BASELINE_NAMES: tuple[str, ...] = (
    "docs",
    "code",
    "schema",
    "deploy",
    "governance",
    "identity",
    "security",
    "attestation",
    "redaction",
)
BASELINE_NAMES_SET: frozenset[str] = frozenset(BASELINE_NAMES)
PRIVILEGED_NAMES: frozenset[str] = frozenset(
    {"deploy", "governance", "identity", "security", "attestation", "redaction"}
)

RESERVED_VOCABULARY: frozenset[str] = frozenset(
    {
        "propose", "edit", "commit", "open_pr", "attest", "advise_only",
        "merge", "deploy", "publish",
        "issue_credential", "revoke_credential",
        "alter_org_settings", "alter_tenant_settings", "alter_repo_settings",
        "approve_redaction",
        "weaken_attestation_gate", "weaken_redaction_gate",
    }
)
RESERVED_RESTRICTED: frozenset[str] = frozenset(
    {
        "merge", "deploy", "publish",
        "issue_credential", "revoke_credential",
        "alter_org_settings", "alter_tenant_settings", "alter_repo_settings",
        "approve_redaction",
        "weaken_attestation_gate", "weaken_redaction_gate",
    }
)


def _validate_class_entry(path: Path, entry: dict[str, Any], idx: int) -> list[ValidationError]:
    errors: list[ValidationError] = []
    base = f"/{idx}"
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        errors.append(make_error("FR-006", path, f"{base}/name", "class entry missing name", CONTRACT))
        return errors

    vocab = entry.get("action_vocabulary")
    permitted = entry.get("agent_permitted_actions")
    vocab_set: set[str] = set(vocab) if isinstance(vocab, list) else set()
    permitted_set: set[str] = set(permitted) if isinstance(permitted, list) else set()

    if isinstance(vocab, list):
        for action in vocab:
            if action not in RESERVED_VOCABULARY:
                errors.append(
                    make_error(
                        "FR-006",
                        path,
                        f"{base}/action_vocabulary",
                        f"action {action!r} is not in the reserved-action vocabulary for class {name!r}",
                        CONTRACT,
                    )
                )

    if isinstance(permitted, list):
        for action in permitted:
            if action not in RESERVED_VOCABULARY:
                errors.append(
                    make_error(
                        "FR-006",
                        path,
                        f"{base}/agent_permitted_actions",
                        f"action {action!r} is not in the reserved-action vocabulary for class {name!r}",
                        CONTRACT,
                    )
                )
        not_in_vocab = permitted_set - vocab_set
        for action in sorted(not_in_vocab):
            errors.append(
                make_error(
                    "FR-006",
                    path,
                    f"{base}/agent_permitted_actions",
                    f"action {action!r} not declared in action_vocabulary of class {name!r}",
                    CONTRACT,
                )
            )
        restricted = permitted_set & RESERVED_RESTRICTED
        for action in sorted(restricted):
            errors.append(
                make_error(
                    "FR-008",
                    path,
                    f"{base}/agent_permitted_actions",
                    f"class {name!r} agent_permitted_actions includes reserved-restricted action {action!r} (Reading A)",
                    CONTRACT,
                )
            )

    if name in PRIVILEGED_NAMES and entry.get("human_ratification_required") is not True:
        errors.append(
            make_error(
                "FR-008",
                path,
                f"{base}/human_ratification_required",
                f"privileged class {name!r} requires human_ratification_required: true",
                CONTRACT,
            )
        )

    return errors


def validate_taxonomy_file(path: Path, data: Any) -> list[ValidationError]:
    """Validate the substrate baseline taxonomy file."""
    errors: list[ValidationError] = []
    if not isinstance(data, list):
        errors.append(
            make_error("FR-006", path, "/", "mutation-class taxonomy file must be a YAML sequence", CONTRACT)
        )
        return errors

    name_counts: dict[str, int] = {}
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(make_error("FR-006", path, f"/{idx}", "class entry must be a mapping", CONTRACT))
            continue
        errors.extend(_validate_class_entry(path, entry, idx))
        name = entry.get("name")
        if isinstance(name, str):
            name_counts[name] = name_counts.get(name, 0) + 1
        if name in BASELINE_NAMES_SET and entry.get("is_baseline") is not True:
            errors.append(
                make_error(
                    "FR-006",
                    path,
                    f"/{idx}/is_baseline",
                    f"baseline class {name!r} must declare is_baseline: true",
                    CONTRACT,
                )
            )

    for baseline in BASELINE_NAMES:
        count = name_counts.get(baseline, 0)
        if count == 0:
            errors.append(
                make_error("FR-006", path, "/", f"baseline class {baseline!r} missing from taxonomy", CONTRACT)
            )
        elif count > 1:
            errors.append(
                make_error(
                    "FR-006",
                    path,
                    "/",
                    f"baseline class {baseline!r} declared more than once ({count}x)",
                    CONTRACT,
                )
            )

    return errors


def validate_overlay_file(path: Path, data: Any) -> list[ValidationError]:
    """Validate a tenant mutation-classes.yml overlay (extension classes only)."""
    errors: list[ValidationError] = []
    if not isinstance(data, list):
        errors.append(
            make_error("FR-006", path, "/", "tenant mutation-classes overlay must be a YAML sequence", CONTRACT)
        )
        return errors
    seen_names: dict[str, int] = {}
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(make_error("FR-006", path, f"/{idx}", "class entry must be a mapping", CONTRACT))
            continue
        errors.extend(_validate_class_entry(path, entry, idx))
        name = entry.get("name")
        if isinstance(name, str) and name in BASELINE_NAMES_SET:
            errors.append(
                make_error(
                    "FR-006",
                    path,
                    f"/{idx}/name",
                    f"tenant extension reuses baseline class name {name!r}",
                    CONTRACT,
                )
            )
        if entry.get("is_baseline") is not False:
            errors.append(
                make_error(
                    "FR-006",
                    path,
                    f"/{idx}/is_baseline",
                    f"tenant overlay entry {name!r} must declare is_baseline: false (tenant extensions cannot claim baseline status)",
                    CONTRACT,
                )
            )
        if isinstance(name, str):
            if name in seen_names:
                errors.append(
                    make_error(
                        "FR-006",
                        path,
                        f"/{idx}/name",
                        f"duplicate tenant extension class name {name!r} within overlay (first at /{seen_names[name]})",
                        CONTRACT,
                    )
                )
            else:
                seen_names[name] = idx
    return errors


def _build_index(
    taxonomy: list[dict[str, Any]],
    overlays: list[list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in taxonomy:
        name = entry.get("name")
        if isinstance(name, str):
            index[name] = entry
    for overlay in overlays:
        for entry in overlay:
            name = entry.get("name")
            if isinstance(name, str) and name not in index:
                index[name] = entry
    return index


def _find_overlay_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    overlays: list[Path] = []
    for raw in paths:
        p = Path(raw)
        candidates: list[Path]
        if p.is_file() and p.name == TENANT_OVERLAY_FILENAME:
            candidates = [p]
        elif p.is_dir():
            candidates = sorted(p.rglob(TENANT_OVERLAY_FILENAME))
        else:
            candidates = []
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                overlays.append(candidate)
    return overlays


def validate_tasks_sidecar_against_taxonomy(
    path: Path, data: Any, index: dict[str, dict[str, Any]]
) -> list[ValidationError]:
    """For each task entry, assert mutation_class is known and permitted_actions is allowed."""
    errors: list[ValidationError] = []
    if not isinstance(data, dict):
        return errors
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return errors
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        cls_name = task.get("mutation_class")
        if not isinstance(cls_name, str) or not cls_name:
            continue
        cls = index.get(cls_name)
        if cls is None:
            errors.append(
                make_error(
                    "FR-006",
                    path,
                    f"/tasks/{idx}/mutation_class",
                    f"declared mutation_class {cls_name!r} is not in the baseline taxonomy or any tenant overlay",
                    CONTRACT,
                )
            )
            continue
        permitted_class = cls.get("agent_permitted_actions")
        permitted_class_set: set[str] = (
            set(permitted_class) if isinstance(permitted_class, list) else set()
        )
        permitted_task = task.get("permitted_actions")
        if not isinstance(permitted_task, list):
            continue
        for action in permitted_task:
            if action not in permitted_class_set:
                errors.append(
                    make_error(
                        "FR-027a",
                        path,
                        f"/tasks/{idx}/permitted_actions",
                        f"permitted_actions item {action!r} not allowed by class {cls_name!r} (agent_permitted_actions: {sorted(permitted_class_set)})",
                        CONTRACT,
                    )
                )
    return errors


@register("mutation_class", ["FR-006", "FR-008", "FR-027a"])
def run(paths: Iterable[Path]) -> CheckResult:
    paths_list = [Path(p) for p in paths]
    errors: list[ValidationError] = []

    try:
        taxonomy_data = load_yaml(TAXONOMY_PATH)
    except LoaderError as exc:
        errors.append(make_error("FR-006", TAXONOMY_PATH, "", str(exc), CONTRACT))
        return CheckResult(name="mutation_class", errors=tuple(errors))

    errors.extend(validate_taxonomy_file(TAXONOMY_PATH, taxonomy_data))
    taxonomy_list: list[dict[str, Any]] = (
        [e for e in taxonomy_data if isinstance(e, dict)] if isinstance(taxonomy_data, list) else []
    )

    overlays_data: list[list[dict[str, Any]]] = []
    for overlay_path in _find_overlay_files(paths_list):
        try:
            overlay = load_yaml(overlay_path)
        except LoaderError as exc:
            errors.append(make_error("FR-006", overlay_path, "", str(exc), CONTRACT))
            continue
        errors.extend(validate_overlay_file(overlay_path, overlay))
        if isinstance(overlay, list):
            overlays_data.append(
                [e for e in overlay if isinstance(e, dict) and e.get("is_baseline") is False]
            )

    index = _build_index(taxonomy_list, overlays_data)

    for sidecar in iter_sidecar_paths(paths_list, kind="tasks"):
        try:
            data = load_yaml(sidecar)
        except LoaderError as exc:
            errors.append(make_error("FR-006", sidecar, "", str(exc), CONTRACT))
            continue
        errors.extend(validate_tasks_sidecar_against_taxonomy(sidecar, data, index))

    return CheckResult(name="mutation_class", errors=tuple(errors))
