"""Check registry for Creator Engine validator checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from ..reporting import CheckResult

CheckCallable = Callable[[Iterable[Path]], CheckResult]


@dataclass(frozen=True)
class CheckDefinition:
    name: str
    frs: tuple[str, ...]
    run: CheckCallable


_REGISTRY: dict[str, CheckDefinition] = {}


def register(name: str, frs: Iterable[str]):
    """Decorator used by per-story checks to register themselves."""
    def decorator(func: CheckCallable) -> CheckCallable:
        _REGISTRY[name] = CheckDefinition(name=name, frs=tuple(frs), run=func)
        return func
    return decorator


def registered_checks() -> dict[str, CheckDefinition]:
    return dict(sorted(_REGISTRY.items()))


def run_registered(paths: Iterable[Path]) -> list[CheckResult]:
    return [definition.run(paths) for definition in registered_checks().values()]


# Import shipped checks after registry helpers are defined so decorators run.
from . import identity as identity  # noqa: E402,F401
from . import sidecar_conformance as sidecar_conformance  # noqa: E402,F401
from . import duplicate_spec_id as duplicate_spec_id  # noqa: E402,F401
from . import definition_of_ready as definition_of_ready  # noqa: E402,F401
from . import mutation_class as mutation_class  # noqa: E402,F401
from . import no_limitless_strings as no_limitless_strings  # noqa: E402,F401
from . import path_manifest_fidelity as path_manifest_fidelity  # noqa: E402,F401
from . import handoff_schema as handoff_schema  # noqa: E402,F401
from . import role_boundary_attribution as role_boundary_attribution  # noqa: E402,F401
