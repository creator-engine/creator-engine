"""Config-driven path-to-mutation-class classifier for automerge dry runs.

The classifier is pure and fail-closed. It reads path predicates from policy
data and returns the highest-risk mutation class touched by a changed path set.
Unknown or ambiguous input resolves to the configured fail-closed class.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Mapping, Sequence

import yaml

from ..work_sizing import MUTATION_CLASSES

DEFAULT_MUTATION_POLICY_PATH: Final[Path] = Path(__file__).with_name(
    "automerge_mutation_policy.yaml"
)

CLASS_ORDER: Final[tuple[str, ...]] = MUTATION_CLASSES
AUTO_CLASSES: Final[frozenset[str]] = frozenset({"none", "docs"})
GESTURE_CLASSES: Final[frozenset[str]] = frozenset(
    cls for cls in CLASS_ORDER if cls not in AUTO_CLASSES
)
PRIVILEGED_CLASSES: Final[frozenset[str]] = frozenset(
    {"governance", "identity", "security", "attestation", "redaction"}
)


class MutationPolicyError(Exception):
    """Mutation-class policy could not be loaded safely."""


@dataclass(frozen=True)
class MutationPolicy:
    """Secret-free path classification policy."""

    path_predicates: Mapping[str, tuple[str, ...]]
    class_order: tuple[str, ...] = CLASS_ORDER
    fail_closed_class: str = "redaction"
    state_path: str = ".ce/state/automerge/policy.json"
    decisions_dir: str = ".ce/state/automerge/decisions"
    required_checks: tuple[str, ...] = ()
    raw: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MutationPolicy":
        raw_order = payload.get("class_order", CLASS_ORDER)
        if not isinstance(raw_order, Sequence) or isinstance(raw_order, (str, bytes)):
            raise MutationPolicyError("class_order must be a sequence")
        class_order = tuple(str(item) for item in raw_order)
        if set(class_order) != set(MUTATION_CLASSES):
            raise MutationPolicyError("class_order must contain the mutation taxonomy")

        fail_closed_class = str(payload.get("fail_closed_class", "redaction"))
        if fail_closed_class not in class_order:
            raise MutationPolicyError("fail_closed_class must be a mutation class")

        raw_predicates = payload.get("path_predicates")
        if not isinstance(raw_predicates, Mapping):
            raise MutationPolicyError("path_predicates must be an object")

        predicates: dict[str, tuple[str, ...]] = {}
        for cls_name, raw_patterns in raw_predicates.items():
            class_name = str(cls_name)
            if class_name not in class_order:
                raise MutationPolicyError("path predicate class is unknown")
            if not isinstance(raw_patterns, Sequence) or isinstance(raw_patterns, (str, bytes)):
                raise MutationPolicyError("path predicate patterns must be a sequence")
            patterns = tuple(str(pattern) for pattern in raw_patterns if str(pattern))
            predicates[class_name] = patterns

        raw_required = payload.get("required_checks", ())
        if not isinstance(raw_required, Sequence) or isinstance(raw_required, (str, bytes)):
            raise MutationPolicyError("required_checks must be a sequence")

        return cls(
            path_predicates=predicates,
            class_order=class_order,
            fail_closed_class=fail_closed_class,
            state_path=str(payload.get("state_path", ".ce/state/automerge/policy.json")),
            decisions_dir=str(payload.get("decisions_dir", ".ce/state/automerge/decisions")),
            required_checks=tuple(str(check) for check in raw_required if str(check)),
            raw=dict(payload),
        )

    @property
    def policy_sha(self) -> str:
        material = self.raw if self.raw is not None else self.to_payload()
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return {
            "class_order": list(self.class_order),
            "fail_closed_class": self.fail_closed_class,
            "state_path": self.state_path,
            "decisions_dir": self.decisions_dir,
            "required_checks": list(self.required_checks),
            "path_predicates": {
                class_name: list(patterns)
                for class_name, patterns in self.path_predicates.items()
            },
        }

    def class_rank(self, class_name: str) -> int:
        try:
            return self.class_order.index(class_name)
        except ValueError:
            return self.class_order.index(self.fail_closed_class)


def load_mutation_policy(path: str | Path = DEFAULT_MUTATION_POLICY_PATH) -> MutationPolicy:
    """Load the checked-in automerge mutation policy."""

    policy_path = Path(path)
    try:
        payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MutationPolicyError(str(exc)) from exc
    if not isinstance(payload, Mapping):
        raise MutationPolicyError("mutation policy must be a mapping")
    return MutationPolicy.from_payload(payload)


@lru_cache(maxsize=1)
def default_mutation_policy() -> MutationPolicy:
    return load_mutation_policy(DEFAULT_MUTATION_POLICY_PATH)


def mutation_class_for_paths(
    paths: Sequence[str],
    policy: MutationPolicy | Mapping[str, Any] | None = None,
) -> str:
    """Return the highest-risk mutation class for ``paths``.

    ``policy`` may be a loaded :class:`MutationPolicy` or a raw policy mapping.
    Unknown paths and invalid policy inputs resolve to the most-privileged
    configured class instead of raising into callers that need a decision.
    """

    resolved = _coerce_policy(policy)
    if not paths:
        return resolved.fail_closed_class

    highest = resolved.fail_closed_class
    highest_rank = -1
    fail_rank = resolved.class_rank(resolved.fail_closed_class)

    for raw_path in paths:
        path = _normalize_path(raw_path)
        if not path:
            return resolved.fail_closed_class
        matches = _matching_classes(path, resolved)
        if not matches:
            return resolved.fail_closed_class
        for class_name in matches:
            rank = resolved.class_rank(class_name)
            if rank > highest_rank:
                highest = class_name
                highest_rank = rank
        if highest_rank >= fail_rank:
            return resolved.fail_closed_class

    return highest if highest_rank >= 0 else resolved.fail_closed_class


def _coerce_policy(policy: MutationPolicy | Mapping[str, Any] | None) -> MutationPolicy:
    if policy is None:
        try:
            return default_mutation_policy()
        except MutationPolicyError:
            return MutationPolicy(path_predicates={}, fail_closed_class="redaction")
    if isinstance(policy, MutationPolicy):
        return policy
    try:
        return MutationPolicy.from_payload(policy)
    except MutationPolicyError:
        return MutationPolicy(path_predicates={}, fail_closed_class="redaction")


def _normalize_path(path: object) -> str:
    return str(path).replace("\\", "/").strip().strip("/")


def _matching_classes(path: str, policy: MutationPolicy) -> list[str]:
    matched: list[str] = []
    for class_name, patterns in policy.path_predicates.items():
        if any(_matches(path, pattern) for pattern in patterns):
            matched.append(class_name)
    return matched


def _matches(path: str, pattern: str) -> bool:
    normalized_pattern = pattern.replace("\\", "/").strip().strip("/")
    if not normalized_pattern:
        return False
    if "/" not in normalized_pattern:
        return fnmatch.fnmatchcase(Path(path).name, normalized_pattern)
    return fnmatch.fnmatchcase(path, normalized_pattern)
