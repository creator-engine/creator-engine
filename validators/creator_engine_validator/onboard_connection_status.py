"""Read-only projection of the latest onboard-apply connection outcome."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RESOLVED = "RESOLVED"
UNRESOLVED_CONNECTION = "UNRESOLVED_CONNECTION"
UNKNOWN = "UNKNOWN"

# This is the schema-v1 order recorded in ``onboard/ledger.ndjson``.  Keep the
# read-only status projection in the shared layer: importing the v3 apply
# executor only to obtain this wire-format constant would cross the version
# boundary.  A future ledger schema revision must update this decoder together
# with the record format.
LEG_IDS: tuple[str, ...] = (
    "signed_spec_verify",
    "answers_merge",
    "host_dependencies",
    "runtime_posture",
    "cli_exposure",
    "brain_genesis",
    "github_bootstrap_token_probe",
    "github_repo_create",
    "github_app_install",
    "github_workflow_install",
    "github_branch_protection",
    "workspace_checkout",
    "first_project_smoke",
    "brownfield_inventory_drift_check",
    "brownfield_secret_preflight",
    "brownfield_build_scaffold",
    "brownfield_push_branch",
    "brownfield_open_join_pr",
    "brownfield_verify_preserved_checks",
    "brownfield_record_apply_evidence",
)


@dataclass(frozen=True)
class OnboardConnectionStatus:
    state: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"state": self.state, "detail": self.detail}


def _unknown(detail: str) -> OnboardConnectionStatus:
    return OnboardConnectionStatus(UNKNOWN, detail)


def _entry_is_well_formed(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    required_strings = ("schema_version", "invocation_id", "target_repo", "leg_id", "timestamp")
    if any(not isinstance(entry.get(key), str) or not entry[key] for key in required_strings):
        return False
    result = entry.get("result")
    return (
        entry["schema_version"] == "1"
        and isinstance(result, dict)
        and isinstance(result.get("id"), str)
        and isinstance(result.get("status"), str)
        and isinstance(result.get("action"), str)
        and result.get("id") == entry["leg_id"]
    )


def read_status(state_root: Path | str) -> OnboardConnectionStatus:
    """Classify the latest complete invocation without changing the ledger.

    Absence means no failed adoption is recorded. Existing malformed or partial
    ledgers deliberately remain unknown rather than inferring a safe outcome.
    """
    path = Path(state_root) / "onboard" / "ledger.ndjson"
    if not path.exists():
        return OnboardConnectionStatus(RESOLVED, "no onboard ledger recorded")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return _unknown("onboard ledger could not be read")
    if not lines:
        return _unknown("onboard ledger is empty")

    entries: list[dict[str, Any]] = []
    for raw in lines:
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            return _unknown("onboard ledger contains malformed JSON")
        if not _entry_is_well_formed(entry):
            return _unknown("onboard ledger has missing or invalid required fields")
        entries.append(entry)

    latest_id = entries[-1]["invocation_id"]
    latest = [entry for entry in entries if entry["invocation_id"] == latest_id]
    if [entry["leg_id"] for entry in latest] != list(LEG_IDS):
        return _unknown("latest onboard invocation is incomplete or out of order")

    unresolved_leg = "github_bootstrap_token_probe"
    refusal_index = LEG_IDS.index(unresolved_leg)
    refusal = latest[refusal_index]["result"]
    expected_cascade = latest[refusal_index + 1 :]
    if (
        refusal.get("status") == "refused"
        and refusal.get("action") == "forge_identity_unresolved"
        and all(
            entry["result"].get("status") == "skipped"
            and entry["result"].get("action") == "dependency_not_verified"
            for entry in expected_cascade
        )
    ):
        return OnboardConnectionStatus(
            UNRESOLVED_CONNECTION,
            "latest onboard invocation could not resolve the forge identity",
        )
    return OnboardConnectionStatus(RESOLVED, "latest onboard invocation is not the unresolved connection cascade")
