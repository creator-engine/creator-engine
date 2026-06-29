"""RV1-061 — governed-environment guard predicate (DP-3 = B).

This is the v1.0 substitute for mandatory project-dev containerization: an
explicit, fail-closed predicate — surfaced through ``ce doctor`` / ``ce check``
— that asserts governed-environment posture and refuses ungoverned host drift.

The evaluator is **pure**: it takes a fully-resolved :class:`EnvironmentFacts`
snapshot and returns a :class:`GuardResult`. Host detection (subprocess /
filesystem probing) lives in :mod:`doctor_runtime`, so the predicate logic is
deterministic and offline-testable. Clause identifiers map to the RED cases in
``docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md`` §4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .packaging_runtime import PackagingContractResult, interpreter_in_contract

# Clause identifiers (RED-G-1 .. RED-G-6).
CLAUSE_INTERPRETER = "RED-G-1"
CLAUSE_TMUX = "RED-G-2"
CLAUSE_PODMAN = "RED-G-3"
CLAUSE_STATE_PATH = "RED-G-4"
CLAUSE_HIDDEN_CONTINUATION = "RED-G-5"
CLAUSE_PACKAGING = "RED-G-6"
CLAUSE_INSTALLED_CE = "CE-DOGFOOD-1"


@dataclass(frozen=True)
class EnvironmentFacts:
    """A resolved snapshot of the host posture the guard reasons over."""

    version_info: Sequence[int]
    repo_root_is_git: bool
    hermes_ignored: bool
    tmux_available: bool
    podman_available: bool = False
    podman_rootless: bool = False
    uv_available: bool = False
    packaging: PackagingContractResult | None = None
    hidden_continuation: bool = False
    active_work_ledger_present: bool = True
    ce_invocation: str = "unknown"
    ce_package_origin: str = "unknown"
    ce_dogfood_installed: bool = False
    ce_source_tree_context: bool = True


@dataclass(frozen=True)
class GuardCheck:
    clause: str
    name: str
    applicable: bool
    ok: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "clause": self.clause,
            "name": self.name,
            "applicable": self.applicable,
            "ok": self.ok,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class GuardResult:
    checks: tuple[GuardCheck, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks if c.applicable)

    @property
    def refusals(self) -> list[GuardCheck]:
        return [c for c in self.checks if c.applicable and not c.ok]

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "refused_clauses": [c.clause for c in self.refusals],
            "checks": [c.to_dict() for c in self.checks],
        }


def evaluate(
    facts: EnvironmentFacts,
    *,
    require_visible_launch: bool = False,
    require_worker: bool = False,
    check_packaging: bool = True,
    require_installed_ce: bool = False,
) -> GuardResult:
    """Evaluate the six ungoverned-host clauses against ``facts``.

    ``applicable`` distinguishes "this clause does not gate this run" (e.g. the
    tmux clause when no visible launch is requested) from a refusal. A clause
    that is applicable and not ``ok`` is a fail-closed refusal.
    """
    checks: list[GuardCheck] = []

    # RED-G-1 — interpreter contract is always enforced.
    in_contract = interpreter_in_contract(facts.version_info)
    got = ".".join(str(x) for x in facts.version_info)
    checks.append(
        GuardCheck(
            clause=CLAUSE_INTERPRETER,
            name="python-interpreter-contract",
            applicable=True,
            ok=in_contract,
            detail=(
                f"interpreter {got} satisfies floor >=3.14 / target 3.14.x"
                if in_contract
                else f"interpreter {got} is out-of-contract; require floor >=3.14 / target band 3.14.x"
            ),
        )
    )

    # RED-G-2 — tmux required only for a visibility-required launch (PCO-049).
    checks.append(
        GuardCheck(
            clause=CLAUSE_TMUX,
            name="visible-terminal-tmux",
            applicable=require_visible_launch,
            ok=facts.tmux_available,
            detail=(
                "tmux available for the contract-conformant visible terminal (PCO-049)"
                if facts.tmux_available
                else "tmux missing; no contract-conformant visible terminal for the launcher (PCO-049)"
            ),
        )
    )

    # RED-G-3 — rootless Podman required only for worker execution (PCO-045).
    podman_ok = facts.podman_available and facts.podman_rootless
    if not facts.podman_available:
        podman_detail = "rootless Podman unavailable for worker execution (PCO-045)"
    elif not facts.podman_rootless:
        podman_detail = "rootful Podman presented; rootless required for worker execution (PCO-045)"
    else:
        podman_detail = "rootless Podman available for worker execution (PCO-045)"
    checks.append(
        GuardCheck(
            clause=CLAUSE_PODMAN,
            name="rootless-podman-worker",
            applicable=require_worker,
            ok=podman_ok,
            detail=podman_detail,
        )
    )

    # RED-G-4 — .hermes governed state-path posture (enforced inside a git repo).
    state_ok = (not facts.repo_root_is_git) or facts.hermes_ignored
    checks.append(
        GuardCheck(
            clause=CLAUSE_STATE_PATH,
            name="governed-state-path",
            applicable=facts.repo_root_is_git,
            ok=state_ok,
            detail=(
                ".hermes/ is git-ignored; governed state-path posture intact"
                if state_ok
                else ".hermes/ is not git-ignored; ungoverned state-path posture (state-boundary)"
            ),
        )
    )

    # RED-G-5 — no unsafe hidden continuation; there is no hidden fallback.
    checks.append(
        GuardCheck(
            clause=CLAUSE_HIDDEN_CONTINUATION,
            name="no-hidden-continuation",
            applicable=True,
            ok=not facts.hidden_continuation,
            detail=(
                "no hidden/dead-pane continuation posture detected"
                if not facts.hidden_continuation
                else "unsafe hidden continuation posture; in-flight work must not be treated as ratified"
            ),
        )
    )

    # RED-G-6 — packaging drift from the Option B contract.
    packaging = facts.packaging
    packaging_applicable = check_packaging and facts.ce_source_tree_context
    packaging_ok = bool(packaging.ok) if packaging is not None else False
    if not facts.ce_source_tree_context:
        packaging_detail = "packaging contract applies only in CE source-tree developer context"
    elif packaging is None:
        packaging_detail = "packaging contract not evaluated"
    elif packaging_ok:
        packaging_detail = "packaging posture matches the Option B contract"
    else:
        packaging_detail = "packaging contract drift: " + "; ".join(packaging.violations)
    checks.append(
        GuardCheck(
            clause=CLAUSE_PACKAGING,
            name="packaging-contract",
            applicable=packaging_applicable,
            ok=packaging_ok,
            detail=packaging_detail,
        )
    )

    dogfood_detail = (
        "running through installed CE console script"
        if facts.ce_dogfood_installed
        else (
            "not running through installed CE console script "
            f"(invocation={facts.ce_invocation}, package_origin={facts.ce_package_origin})"
        )
    )
    checks.append(
        GuardCheck(
            clause=CLAUSE_INSTALLED_CE,
            name="installed-ce-dogfood-posture",
            applicable=require_installed_ce,
            ok=facts.ce_dogfood_installed,
            detail=dogfood_detail,
        )
    )

    return GuardResult(checks=tuple(checks))
