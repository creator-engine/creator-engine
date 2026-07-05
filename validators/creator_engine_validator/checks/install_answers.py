"""Install-answers-file validation (v3.5-E.3 — the IaC onboarding artifact).

Validates **CE install answers files** (`ce-install.answers.yaml`, the
declarative two-mode-installer input — committable, so it lands via governed
PR and MUST hold the same floor in CI that the installer holds at apply time)
against `schemas/install-answers.schema.yaml` plus the cross-field governance
invariants:

- **fail-closed on unknown keys:** `additionalProperties: false` everywhere in
  the schema — a typo'd key ERRORS at the schema layer, never silently falls
  through to an interactive ask (the classic IaC footgun).
- **secrets never by value:** every secret-typed field (the schema's
  `x-ce-sensitivity: secret` annotations) must be a SecretRef
  (`env://` · `file://` · `prompt://` · `keychain://`); a raw value is
  refused belt-and-braces even where the schema pattern would already catch
  it (defense against schema drift).
- **cost opt-out is ratified-HUMAN-only:** `cost.profile: custom` REQUIRES a
  `cost.optout {ratified_prompt_sha, approver_ref, educate_acknowledged:
  true}` binding (the G-5 invariant, recorded in-file as an attestation).
- **no weaker grader without ratification:** a `github.protections` object
  that WEAKENS the CE reference posture (the floor lives IN the schema as
  `x-ce-reference-posture` data — single source of truth) requires the same
  ratification-binding shape. An agent preparing an answers file can
  configure anything except a weaker grader.

This is a **shared** check: it imports only the shared engine and MUST NOT
import a v3 module (the `version_boundary` ratchet) — the pure two-mode
installer ENGINE consuming these files is `v3_installer` (v3-classified);
the few-line invariant predicates are deliberately mirrored here, exactly as
`ce_spend_envelope._check_optout` mirrors `v3_installer._valid_optout`.

Shape + invariants ONLY: this check verifies an answers file's governance
well-formedness; it never resolves a SecretRef, probes a host, or plans an
install.

See:
  - `docs/contracts/installer.md`
  - `schemas/install-answers.schema.yaml`
  - `creator_engine_validator/v3_installer.py` (the consuming engine)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..reporting import CheckResult, ValidationError, make_error
from ..schema import load_schema, validate_with_schema
from . import register

CHECK_NAME = "install_answers"
CONTRACT = "docs/contracts/installer.md"
SCHEMA = "schemas/install-answers.schema.yaml"

#: The canonical answers-file basename; `<qualifier>.ce-install.answers.yaml`
#: variants are discovered too (e.g. `vps-pilot.ce-install.answers.yaml`).
ANSWERS_BASENAME = "ce-install.answers.yaml"

# Failure codes (explicit error classes).
CODE_SCHEMA = "VAL-IA-SCHEMA"
CODE_INVALID = "VAL-IA-INVALID"
CODE_RAW_SECRET = "VAL-IA-RAW-SECRET"
CODE_OPTOUT_UNRATIFIED = "VAL-IA-OPTOUT-UNRATIFIED"
CODE_WEAKENED_UNRATIFIED = "VAL-IA-WEAKENED-UNRATIFIED"

_SECRET_REF_RE = re.compile(r"^(env|file|prompt|keychain)://\S+$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_answers_file(path: Path) -> bool:
    return path.name == ANSWERS_BASENAME or path.name.endswith(f".{ANSWERS_BASENAME}")


def iter_answers_files(
    paths: Iterable[Path],
) -> tuple[list[tuple[Path, dict[str, Any]]], list[ValidationError]]:
    """Discover answers files under ``paths`` by their canonical basename.

    Returns ``(documents, errors)`` — parse failures and non-mapping documents
    for a file that *names itself* an answers file are surfaced as
    ``VAL-IA-INVALID``, never silently skipped.
    """
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("PyYAML is required; install validators/requirements.txt") from exc
    seen: set[Path] = set()
    documents: list[tuple[Path, dict[str, Any]]] = []
    errors: list[ValidationError] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path] if _is_answers_file(path) else []
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("*.yaml") if _is_answers_file(p))
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                errors.append(make_error(CODE_INVALID, candidate, "", str(exc), CONTRACT))
                continue
            if not isinstance(data, dict):
                errors.append(make_error(
                    CODE_INVALID, candidate, "",
                    f"answers file must be a YAML mapping, got {type(data).__name__}",
                    CONTRACT,
                ))
                continue
            documents.append((candidate, data))
    return documents, errors


def _iter_secret_keys(node: Any, prefix: str = "") -> Iterator[str]:
    """Dotted paths of every `x-ce-sensitivity: secret` input in the schema."""
    if not isinstance(node, dict):
        return
    properties = node.get("properties")
    if not isinstance(properties, dict):
        return
    for name, sub in properties.items():
        if not isinstance(sub, dict):
            continue
        key = f"{prefix}{name}"
        if sub.get("x-ce-sensitivity") == "secret":
            yield key
        elif isinstance(sub.get("properties"), dict):
            yield from _iter_secret_keys(sub, prefix=f"{key}.")


def _lookup(mapping: Any, dotted: str) -> tuple[bool, Any]:
    node = mapping
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _valid_binding(binding: Any) -> bool:
    """The answers-file ratification-binding shape (educate acknowledged
    in-band — the file cannot skip the educate-first step)."""
    if not (
        isinstance(binding, dict)
        and isinstance(binding.get("ratified_prompt_sha"), str)
        and bool(_HEX64_RE.match(binding["ratified_prompt_sha"]))
        and isinstance(binding.get("approver_ref"), str)
        and bool(_HEX64_RE.match(binding["approver_ref"]))
        and binding.get("educate_acknowledged") is True
    ):
        return False
    provenance = binding.get("approver_ref_provenance")
    if provenance is None:
        return True
    return (
        isinstance(provenance, dict)
        and set(provenance) == {"identity_ref", "method"}
        and isinstance(provenance.get("identity_ref"), str)
        and bool(provenance["identity_ref"])
        and isinstance(provenance.get("method"), str)
        and bool(provenance["method"])
    )


def _check_raw_secrets(
    document: dict[str, Any], path: Path, schema: dict[str, Any]
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for key in _iter_secret_keys(schema):
        present, value = _lookup(document, key)
        if not present:
            continue
        if not (isinstance(value, str) and _SECRET_REF_RE.match(value)):
            errors.append(make_error(
                CODE_RAW_SECRET, path, key,
                f"{key} is secret-typed and MUST be a SecretRef "
                "(env:// · file:// · prompt:// · keychain://); a raw secret "
                "value never enters a committable answers file",
                CONTRACT,
            ))
    return errors


def _check_cost_optout(document: dict[str, Any], path: Path) -> list[ValidationError]:
    cost = document.get("cost")
    if not isinstance(cost, dict) or cost.get("profile") != "custom":
        return []
    if _valid_binding(cost.get("optout")):
        return []
    return [make_error(
        CODE_OPTOUT_UNRATIFIED, path, "cost/optout",
        "cost.profile 'custom' (the cap opt-out) REQUIRES cost.optout "
        "{ratified_prompt_sha, approver_ref, educate_acknowledged: true} — "
        "a ratified-HUMAN-only choice; an agent can never opt out of cost "
        "enforcement",
        CONTRACT,
    )]


def _protection_weakenings(desired: dict[str, Any], floor: dict[str, Any]) -> list[str]:
    """Mirror of ``v3_installer.protection_weakenings`` (shared check may not
    import v3): absent keys inherit the floor; only an explicit answer weakens."""
    weakenings: list[str] = []
    floor_checks = floor.get("required_checks", [])
    if "required_checks" in desired:
        desired_checks = desired["required_checks"] if isinstance(desired["required_checks"], list) else []
        dropped = [c for c in floor_checks if c not in desired_checks]
        if dropped:
            weakenings.append(f"required_checks drops the CE gate {dropped!r}")
    for flag in ("strict", "dismiss_stale", "enforce_admins", "squash_only"):
        if floor.get(flag) is True and desired.get(flag) is False:
            weakenings.append(f"{flag} disabled below the reference floor")
    floor_reviews = floor.get("required_reviews", 1)
    if isinstance(desired.get("required_reviews"), int) and desired["required_reviews"] < floor_reviews:
        weakenings.append(
            f"required_reviews {desired['required_reviews']} below the floor {floor_reviews}"
        )
    return weakenings


def _check_protection_weakening(
    document: dict[str, Any], path: Path, schema: dict[str, Any]
) -> list[ValidationError]:
    github = document.get("github")
    protections = github.get("protections") if isinstance(github, dict) else None
    if not isinstance(protections, dict):
        return []
    floor_node = (
        schema.get("properties", {})
        .get("github", {})
        .get("properties", {})
        .get("protections", {})
    )
    floor = floor_node.get("x-ce-reference-posture")
    if not isinstance(floor, dict):  # the schema IS the floor; absent = check bug
        return [make_error(
            CODE_WEAKENED_UNRATIFIED, path, "github/protections",
            "the answers schema carries no x-ce-reference-posture — the "
            "governance floor must be data in the schema",
            CONTRACT,
        )]
    weakenings = _protection_weakenings(protections, floor)
    if not weakenings or _valid_binding(protections.get("ratification")):
        return []
    return [make_error(
        CODE_WEAKENED_UNRATIFIED, path, "github/protections",
        "github.protections weakens the CE reference floor ("
        + "; ".join(weakenings)
        + ") and REQUIRES a ratification binding {ratified_prompt_sha, "
        "approver_ref, educate_acknowledged: true} — an agent can configure "
        "anything except a weaker grader",
        CONTRACT,
    )]


def validate_answers_document(
    document: dict[str, Any], path: Path, schema: dict[str, Any] | None = None
) -> list[ValidationError]:
    """Validate one answers document against schema + governance invariants."""
    schema = schema if schema is not None else load_schema(SCHEMA)
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(document, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_raw_secrets(document, path, schema))
    errors.extend(_check_cost_optout(document, path))
    errors.extend(_check_protection_weakening(document, path, schema))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_RAW_SECRET, CODE_OPTOUT_UNRATIFIED,
     CODE_WEAKENED_UNRATIFIED],
)
def run(paths: Iterable[Path]) -> CheckResult:
    documents, errors = iter_answers_files([Path(p) for p in paths])
    if documents:
        schema = load_schema(SCHEMA)
        for document_path, document in documents:
            errors.extend(validate_answers_document(document, document_path, schema))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
