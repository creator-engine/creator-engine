"""Policy-bound, pure-plan-first ``ce worker launch`` Codex one-shot launcher.

The module intentionally contains no ambient-Codex lookup, host configuration
read, container operation, or prompt persistence.  It first creates an
immutable plan from the checked-in policy and only a caller that explicitly
uses :func:`launch` reaches an injectable runner.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any, Protocol, Sequence

import yaml


POLICY_REQUIRED_KEYS = frozenset(
    {
        "kind",
        "schema_version",
        "policy_id",
        "version",
        "codex_binary_template",
        "supported_roles",
        "venues",
        "model_defaults",
        "canonical_add_dirs",
    }
)
POLICY_KIND = "codex-one-shot-launch-policy"
POLICY_SCHEMA_VERSION = "1"
_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


class CodexWorkerLaunchError(ValueError):
    """A policy or caller input was refused before runner invocation."""


@dataclass(frozen=True)
class CodexOneShotPolicy:
    policy_id: str
    version: str
    codex_binary_template: str
    supported_roles: tuple[str, ...]
    venues: tuple[tuple[str, str], ...]
    model: str
    effort: str
    canonical_add_dirs: tuple[str, ...]

    def sandbox_for(self, venue: str) -> str:
        for candidate, sandbox in self.venues:
            if candidate == venue:
                return sandbox
        raise CodexWorkerLaunchError(f"unknown venue: {venue}")

    @property
    def pinned_binary(self) -> str:
        try:
            value = self.codex_binary_template.format(version=self.version)
        except (KeyError, ValueError) as exc:
            raise CodexWorkerLaunchError("invalid codex_binary_template") from exc
        if not PurePath(value).is_absolute():
            raise CodexWorkerLaunchError("policy Codex binary must be absolute")
        return value


@dataclass(frozen=True)
class CodexWorkerLaunchPlan:
    policy_id: str
    policy_version: str
    role: str
    venue: str
    sandbox: str
    model: str
    effort: str
    worktree: str
    run_id: str
    output: str
    argv: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "role": self.role,
            "venue": self.venue,
            "sandbox": self.sandbox,
            "model": self.model,
            "effort": self.effort,
            "worktree": self.worktree,
            "run_id": self.run_id,
            "output": self.output,
            "argv": list(self.argv),
        }


class CodexOneShotRunner(Protocol):
    def run(self, argv: Sequence[str], *, stdin: str) -> int:
        """Run a governed plan. Implementations must not alter ``argv``."""


class SubprocessCodexOneShotRunner:
    """The explicit execution seam; never used by planning or dry-runs."""

    def run(self, argv: Sequence[str], *, stdin: str) -> int:
        completed = subprocess.run(list(argv), input=stdin, text=True, check=False)
        return completed.returncode


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CodexWorkerLaunchError(f"policy {field} must be a nonempty string")
    return value.strip()


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise CodexWorkerLaunchError(f"policy {field} must be a nonempty string list")
    values = tuple(item.strip() for item in value)
    if len(set(values)) != len(values):
        raise CodexWorkerLaunchError(f"policy {field} must not contain duplicates")
    return values


def load_policy(path: str | os.PathLike[str]) -> CodexOneShotPolicy:
    """Load a strict checked-in policy; unknown keys fail closed."""
    try:
        raw = yaml.safe_load(open(path, encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CodexWorkerLaunchError(f"cannot load launcher policy: {path}") from exc
    if not isinstance(raw, dict) or set(raw) != POLICY_REQUIRED_KEYS:
        raise CodexWorkerLaunchError("policy keys must exactly match the v1 schema")
    if raw["kind"] != POLICY_KIND or raw["schema_version"] != POLICY_SCHEMA_VERSION:
        raise CodexWorkerLaunchError("unsupported launcher policy kind or schema_version")
    venues = raw["venues"]
    if not isinstance(venues, dict) or not venues:
        raise CodexWorkerLaunchError("policy venues must be a nonempty mapping")
    venue_items: list[tuple[str, str]] = []
    for venue, sandbox in venues.items():
        venue_items.append((_require_string(venue, "venue"), _require_string(sandbox, "venue sandbox")))
    if len({venue for venue, _ in venue_items}) != len(venue_items):
        raise CodexWorkerLaunchError("policy venues must not contain duplicates")
    defaults = raw["model_defaults"]
    if not isinstance(defaults, dict) or set(defaults) != {"model", "effort"}:
        raise CodexWorkerLaunchError("policy model_defaults must contain only model and effort")
    policy = CodexOneShotPolicy(
        policy_id=_require_string(raw["policy_id"], "policy_id"),
        version=_require_string(raw["version"], "version"),
        codex_binary_template=_require_string(raw["codex_binary_template"], "codex_binary_template"),
        supported_roles=_require_string_list(raw["supported_roles"], "supported_roles"),
        venues=tuple(venue_items),
        model=_require_string(defaults["model"], "model_defaults.model"),
        effort=_require_string(defaults["effort"], "model_defaults.effort"),
        canonical_add_dirs=_require_string_list(raw["canonical_add_dirs"], "canonical_add_dirs"),
    )
    # Validate this now, before a caller has a chance to reach a runner.
    policy.pinned_binary
    return policy


def _normal_absolute(path: str, *, field: str) -> str:
    if not path or not PurePath(path).is_absolute():
        raise CodexWorkerLaunchError(f"{field} must be an absolute path")
    return os.path.normpath(path)


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def _canonical_add_dirs(policy: CodexOneShotPolicy, worktree: str) -> tuple[str, ...]:
    directories: list[str] = []
    for relative in policy.canonical_add_dirs:
        if PurePath(relative).is_absolute() or ".." in PurePath(relative).parts:
            raise CodexWorkerLaunchError("policy canonical_add_dirs must be relative and nonescaping")
        directory = os.path.normpath(os.path.join(worktree, relative))
        if not _inside(directory, worktree) or directory == worktree:
            raise CodexWorkerLaunchError("policy canonical_add_dirs escapes the worktree")
        directories.append(directory)
    return tuple(directories)


def _derive_run_id(*, policy: CodexOneShotPolicy, role: str, venue: str, worktree: str, add_dirs: Sequence[str]) -> str:
    seed = json.dumps(
        {
            "policy_id": policy.policy_id,
            "policy_version": policy.version,
            "role": role,
            "venue": venue,
            "worktree": worktree,
            "add_dirs": list(add_dirs),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "codex-one-shot-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def build_launch_plan(
    *,
    policy: CodexOneShotPolicy,
    role: str,
    venue: str,
    worktree: str,
    codex_binary: str | None = None,
    add_dirs: Sequence[str] = (),
    run_id: str | None = None,
    output: str | None = None,
    caller_flags: Sequence[str] = (),
) -> CodexWorkerLaunchPlan:
    """Build a deterministic plan and refuse every caller-controlled escape."""
    if caller_flags:
        raise CodexWorkerLaunchError("caller Codex flags are not permitted by the governed launcher")
    if role not in policy.supported_roles:
        raise CodexWorkerLaunchError(f"unknown role: {role}")
    sandbox = policy.sandbox_for(venue)
    normalized_worktree = _normal_absolute(worktree, field="worktree")
    pinned_binary = policy.pinned_binary
    supplied_binary = pinned_binary if codex_binary is None else _normal_absolute(codex_binary, field="Codex binary")
    if supplied_binary != pinned_binary:
        raise CodexWorkerLaunchError("Codex binary does not match the policy-pinned template")
    canonical = _canonical_add_dirs(policy, normalized_worktree)
    selected = canonical if not add_dirs else tuple(_normal_absolute(value, field="--add-dir") for value in add_dirs)
    if len(set(selected)) != len(selected):
        raise CodexWorkerLaunchError("duplicate --add-dir")
    for directory in selected:
        if not _inside(directory, normalized_worktree):
            raise CodexWorkerLaunchError("--add-dir escapes the worktree")
        if directory not in canonical:
            raise CodexWorkerLaunchError("--add-dir is not in the policy canonical allowlist")
    # Always order by the policy's canonical order, never caller order.
    ordered_add_dirs = tuple(directory for directory in canonical if directory in selected)
    chosen_run_id = run_id or _derive_run_id(
        policy=policy,
        role=role,
        venue=venue,
        worktree=normalized_worktree,
        add_dirs=ordered_add_dirs,
    )
    if not _RUN_ID_RE.fullmatch(chosen_run_id):
        raise CodexWorkerLaunchError("run_id must be lowercase slug text")
    expected_output = os.path.join(normalized_worktree, ".ce", "state", "codex-one-shot", f"{chosen_run_id}.json")
    if output is not None and _normal_absolute(output, field="output") != expected_output:
        raise CodexWorkerLaunchError("output must equal the deterministic governed output path")
    argv = [
        pinned_binary,
        "exec",
        "--ephemeral",
        "-c",
        "features.multi_agent=false",
        "-c",
        "features.multi_agent_v2=false",
        "-s",
        sandbox,
        "-C",
        normalized_worktree,
    ]
    for directory in ordered_add_dirs:
        argv.extend(("--add-dir", directory))
    argv.extend(("-o", expected_output, "-"))
    return CodexWorkerLaunchPlan(
        policy_id=policy.policy_id,
        policy_version=policy.version,
        role=role,
        venue=venue,
        sandbox=sandbox,
        model=policy.model,
        effort=policy.effort,
        worktree=normalized_worktree,
        run_id=chosen_run_id,
        output=expected_output,
        argv=tuple(argv),
    )


def launch(plan: CodexWorkerLaunchPlan, *, runner: CodexOneShotRunner, stdin: str) -> int:
    """Execute only a previously validated plan through an injectable runner."""
    return runner.run(plan.argv, stdin=stdin)
