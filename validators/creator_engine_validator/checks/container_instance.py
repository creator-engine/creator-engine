"""Container-Instance record schema validation and substrate predicates.

Validates Container-Instance records against
``schemas/container-instance.schema.yaml`` and enforces the Slice 2I-S
per-instance substrate predicates:

* ``PCO-041``: schema validation — every container-instance record MUST
  validate against the container-instance schema. Structural failures
  (not a YAML mapping) are distinguished from schema failures.
* ``PCO-043``: container outlives claim — refuses a container-instance
  record whose ``claim_released_at`` is present (the bound claim was
  released) AND whose ``stopped_at`` is ``null`` (the container is still
  running). This is the static substrate surface that backs the
  ``garbage_collect_worker`` sweeper (spec §e.9).
* ``PCO-044``: image SHA matches policy — refuses a container-instance
  record whose ``image_sha`` does not equal ``policy_ref.image_sha``.
  The policy-declared image SHA is embedded in ``policy_ref`` so this
  check requires no cross-file lookup.

A file is treated as a candidate Container-Instance record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write
  temp files are skipped, per protocol);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``container-instance-record``.

Failures cite ``PCO-041``, ``PCO-043``, or ``PCO-044`` and the prose
contract at ``docs/operations/WORKER_CONTAINER_PROTOCOL.md``.

See:
  - ``docs/operations/WORKER_CONTAINER_PROTOCOL.md``
  - ``docs/architecture/parallel-controller-orchestration.md``
  - ``schemas/container-instance.schema.yaml``
  - ``specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "container_instance"
CONTRACT = "docs/operations/WORKER_CONTAINER_PROTOCOL.md"
SCHEMA = "schemas/container-instance.schema.yaml"
KIND_VALUE = "container-instance-record"
CODE_SCHEMA = "PCO-041"
CODE_OUTLIVES_CLAIM = "PCO-043"
CODE_IMAGE_SHA_MISMATCH = "PCO-044"
CODE_INVALID = "container_instance_invalid_record"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_instance(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def _check_outlives_claim(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """PCO-043: refuse if claim was released but container is still running."""
    claim_released_at = record.get("claim_released_at")
    stopped_at = record.get("stopped_at")

    if claim_released_at is not None and stopped_at is None:
        instance_id = record.get("instance_id", "<unknown>")
        claim_id = record.get("claim_id", "<unknown>")
        return [make_error(
            CODE_OUTLIVES_CLAIM,
            path,
            "stopped_at",
            (
                f"container instance '{instance_id}' outlives its released claim "
                f"'{claim_id}': claim_released_at is set but stopped_at is null; "
                "the container MUST be garbage-collected via garbage_collect_worker "
                "(PCO-043, §g.4 of worker-isolation-runtime.md)"
            ),
            CONTRACT,
        )]
    return []


def _check_image_sha_mismatch(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """PCO-044: refuse if instance image_sha differs from policy_ref.image_sha."""
    policy_ref = record.get("policy_ref")
    if not isinstance(policy_ref, dict):
        return []

    policy_image_sha = policy_ref.get("image_sha")
    instance_image_sha = record.get("image_sha")

    if policy_image_sha is None or instance_image_sha is None:
        return []

    if instance_image_sha != policy_image_sha:
        instance_id = record.get("instance_id", "<unknown>")
        policy_id = policy_ref.get("policy_id", "<unknown>")
        return [make_error(
            CODE_IMAGE_SHA_MISMATCH,
            path,
            "image_sha",
            (
                f"container instance '{instance_id}' image SHA mismatch: "
                f"instance image_sha={instance_image_sha!r} does not match "
                f"policy_ref.image_sha={policy_image_sha!r} from policy "
                f"'{policy_id}'; the allocator MUST NOT substitute a different "
                "image after the policy was ratified "
                "(PCO-044, §g.5 of worker-isolation-runtime.md)"
            ),
            CONTRACT,
        )]
    return []


def iter_container_instance_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Container-Instance files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_instance(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_container_instance(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the Container-Instance schema and predicates.

    Applies PCO-041 (schema validation), PCO-043 (outlives-claim),
    and PCO-044 (image SHA mismatch).
    """
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_outlives_claim(record, path))
    errors.extend(_check_image_sha_mismatch(record, path))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_OUTLIVES_CLAIM, CODE_IMAGE_SHA_MISMATCH])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_container_instance_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error(
                CODE_INVALID,
                record_path,
                "/",
                "container-instance record must be a YAML mapping",
                CONTRACT,
            ))
            continue
        errors.extend(validate_container_instance(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
