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
from . import review_evidence_schema as review_evidence_schema  # noqa: E402,F401
from . import architect_evidence_schema as architect_evidence_schema  # noqa: E402,F401
from . import implementer_evidence_schema as implementer_evidence_schema  # noqa: E402,F401
from . import active_work_ledger_schema as active_work_ledger_schema  # noqa: E402,F401
from . import worktree_lease_schema as worktree_lease_schema  # noqa: E402,F401
from . import controller_key_schema as controller_key_schema  # noqa: E402,F401
from . import active_work_ledger_conflicts as active_work_ledger_conflicts  # noqa: E402,F401
from . import completion_report_schema as completion_report_schema  # noqa: E402,F401
from . import completion_report_required_for_envelope as completion_report_required_for_envelope  # noqa: E402,F401
from . import completion_report_terminal_sections as completion_report_terminal_sections  # noqa: E402,F401
from . import worker_container_policy as worker_container_policy  # noqa: E402,F401
from . import container_instance as container_instance  # noqa: E402,F401
from . import pane_registry as pane_registry  # noqa: E402,F401
from . import side_effect_ledger as side_effect_ledger  # noqa: E402,F401
from . import controller_runtime_contract as controller_runtime_contract  # noqa: E402,F401
from . import state_boundary_contract as state_boundary_contract  # noqa: E402,F401
from . import state_version_record as state_version_record  # noqa: E402,F401
from . import ce_terminology_v2 as ce_terminology_v2  # noqa: E402,F401
from . import role_enum_v2 as role_enum_v2  # noqa: E402,F401
from . import sidecar_schema_v2 as sidecar_schema_v2  # noqa: E402,F401
from . import crosswalk_register as crosswalk_register  # noqa: E402,F401
from . import operating_mode_policy as operating_mode_policy  # noqa: E402,F401
from . import ce_event_block as ce_event_block  # noqa: E402,F401
from . import operating_mode_runtime_carriers as operating_mode_runtime_carriers  # noqa: E402,F401
from . import pcl_record as pcl_record  # noqa: E402,F401
from . import distributed_identity as distributed_identity  # noqa: E402,F401
from . import connector_substrate as connector_substrate  # noqa: E402,F401
from . import extension_hook_contract as extension_hook_contract  # noqa: E402,F401
from . import harness_seat_contract as harness_seat_contract  # noqa: E402,F401
from . import reviewer_authority_envelope as reviewer_authority_envelope  # noqa: E402,F401
from . import ce_runtime_policy as ce_runtime_policy  # noqa: E402,F401
from . import ce_runtime_evidence as ce_runtime_evidence  # noqa: E402,F401
from . import version_boundary as version_boundary  # noqa: E402,F401
from . import v3_naming_hygiene as v3_naming_hygiene  # noqa: E402,F401
from . import ce_spend_envelope as ce_spend_envelope  # noqa: E402,F401
