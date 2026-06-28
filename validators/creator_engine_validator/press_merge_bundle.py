# TODO(controller/dev-1): register `ce press-merge build|render` subparser in
# ce_cli.py wiring to build_bundle()/render_bundle() below. ce_cli.py is owned
# by dev-1 during this fan-out; this module is intentionally CLI-agnostic.
"""Deterministic, no-authority press-merge evidence bundle aggregation.

The press-merge bundle is a PR-keyed sibling of the Gate-7 evidence fan-in
packet. It aggregates already-authored evidence references into one structured
object and one deterministic Markdown surface. It does not ratify, approve,
enqueue, merge, deploy, mutate git/GitHub/CI, or grant authority.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .fanin_runtime import (
    SCHEMA_VERSION,
    AuthorityRefused,
    EvidenceShaMismatch,
    FaninBuildError,
    MissingSourceRatification,
    StaleEvidence,
    _canonical_bytes,
    _content_hash,
    _require_source_ratification,
    _sha256_file,
)
from .loader import LoaderError, load_yaml
from .schema import validate_with_schema

BUNDLE_KIND = "press-merge-bundle"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "press-merge-bundle.schema.yaml"
)
PROSE_CONTRACT = "docs/operations/PRESS_MERGE_BUNDLE.md"


class PressMergeBundleError(FaninBuildError):
    """Base class for press-merge bundle refusals. Carries a gate-style code."""

    code = "PRESS-MERGE-BUNDLE-ERROR"


class PressMergeBundleInputError(PressMergeBundleError):
    code = "PRESS-MERGE-BUNDLE-INPUT"


class PressMergeBundleSchemaError(PressMergeBundleError):
    code = "PRESS-MERGE-BUNDLE-SCHEMA"


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_RE = re.compile(r"[^a-z0-9-]+")


def _require_no_authority(authority_action: str | None) -> None:
    if authority_action:
        raise AuthorityRefused(
            f"press-merge bundles carry no authority; refusing action {authority_action!r}"
        )


def _slug(value: str) -> str:
    slug = _SAFE_ID_RE.sub("-", value.lower()).strip("-")
    return slug or "head"


def _require_sha(value: Any, *, field: str) -> str:
    text = str(value)
    if not _SHA256_RE.match(text):
        raise PressMergeBundleInputError(f"{field} must be a lowercase SHA256 hex string")
    return text


def _resolve_ref(raw_ref: Any, repo_root: Path | str | None) -> tuple[str, Path]:
    if not raw_ref:
        raise PressMergeBundleInputError("evidence ref is missing ref")
    ref = str(raw_ref)
    path = Path(ref)
    if not path.is_absolute() and repo_root is not None:
        path = Path(repo_root) / path
    return ref, path


def _verify_evidence_ref(
    raw_ref: Mapping[str, Any],
    *,
    repo_root: Path | str | None,
    required_kind: str | None = None,
    load_mapping: bool = True,
) -> tuple[dict[str, str], dict[str, Any]]:
    if not isinstance(raw_ref, Mapping):
        raise PressMergeBundleInputError("evidence ref entries must be mappings")
    ref, path = _resolve_ref(raw_ref.get("ref"), repo_root)
    sha256 = _require_sha(raw_ref.get("sha256"), field=f"{ref}.sha256")
    kind = str(raw_ref.get("kind") or required_kind or "evidence")
    if required_kind and kind != required_kind:
        raise PressMergeBundleInputError(f"{ref} kind {kind!r} != {required_kind!r}")
    if not path.is_file():
        raise EvidenceShaMismatch(f"evidence ref not found: {ref}")
    actual = _sha256_file(path)
    if actual != sha256:
        raise StaleEvidence(
            f"stale evidence ref {ref}: pinned={sha256} actual={actual}"
        )
    if not load_mapping:
        return {"kind": kind, "ref": ref, "sha256": sha256}, {}
    try:
        loaded = load_yaml(path)
    except LoaderError as exc:
        raise PressMergeBundleInputError(f"evidence ref {ref} is unreadable: {exc}") from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise PressMergeBundleInputError(f"evidence ref {ref} must load as a mapping")
    return {"kind": kind, "ref": ref, "sha256": sha256}, loaded


def _source_ratification(source_ratification: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(source_ratification, Mapping):
        raise MissingSourceRatification("source_ratification must be a mapping")
    ratification = _require_source_ratification(
        {"source_ratification": dict(source_ratification)}
    )
    return {
        "prompt_ref": ratification["prompt_ref"],
        "sha256": _require_sha(ratification["sha256"], field="source_ratification.sha256"),
    }


def _path_set(values: Any, *, field: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise PressMergeBundleInputError(f"{field} must be a sequence")
    paths = [str(value) for value in values]
    if any(not item for item in paths):
        raise PressMergeBundleInputError(f"{field} cannot contain empty paths")
    return sorted(set(paths))


def _parse_carrier_path_set(path: Path) -> list[str]:
    in_text_block = False
    paths: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "```text":
            in_text_block = True
            paths = []
            continue
        if in_text_block and line == "```":
            return sorted(set(paths))
        if in_text_block and line:
            paths.append(line)
    raise PressMergeBundleInputError(
        f"path manifest {path} does not contain a ```text path-set"
    )


def _diff_summary(
    diff_summary: Mapping[str, Any],
    *,
    repo_root: Path | str | None,
    carrier_manifest_ref: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not isinstance(diff_summary, Mapping):
        raise PressMergeBundleInputError("diff_summary must be a mapping")
    try:
        files_changed = int(diff_summary["files_changed"])
        additions = int(diff_summary["additions"])
        deletions = int(diff_summary["deletions"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PressMergeBundleInputError(
            "diff_summary requires integer files_changed, additions, and deletions"
        ) from exc
    if files_changed < 0 or additions < 0 or deletions < 0:
        raise PressMergeBundleInputError("diff summary counts cannot be negative")

    summary: dict[str, Any] = {
        "files_changed": files_changed,
        "additions": additions,
        "deletions": deletions,
        "path_set": _path_set(diff_summary.get("path_set"), field="diff_summary.path_set"),
        "carrier_path_set": None,
    }
    refs: list[dict[str, str]] = []
    if carrier_manifest_ref is not None:
        ref, _ = _verify_evidence_ref(
            carrier_manifest_ref,
            repo_root=repo_root,
            required_kind="path-manifest",
            load_mapping=False,
        )
        _, carrier_path = _resolve_ref(carrier_manifest_ref.get("ref"), repo_root)
        summary["carrier_path_set"] = {
            "ref": ref["ref"],
            "sha256": ref["sha256"],
            "paths": _parse_carrier_path_set(carrier_path),
        }
        refs.append(ref)
    return summary, refs


def _gate_summary(gates: Any) -> list[dict[str, str]]:
    if gates is None:
        return []
    entries: list[dict[str, Any]]
    if isinstance(gates, Mapping):
        entries = [
            {"name": name, **(value if isinstance(value, Mapping) else {"status": value})}
            for name, value in gates.items()
        ]
    elif isinstance(gates, Sequence) and not isinstance(gates, (str, bytes)):
        entries = list(gates)
    else:
        raise PressMergeBundleInputError("test_results gates must be a mapping or sequence")

    normalized: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise PressMergeBundleInputError("each test/CI gate entry must be a mapping")
        name = entry.get("name") or entry.get("gate")
        status = entry.get("status")
        if not name or not status:
            raise PressMergeBundleInputError("each test/CI gate requires name and status")
        normalized.append(
            {
                "name": str(name),
                "status": str(status),
                "summary": str(entry.get("summary", "")),
            }
        )
    return sorted(normalized, key=lambda item: item["name"])


def _test_results(test_results: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(test_results, Mapping):
        raise PressMergeBundleInputError("test_results must be a mapping")
    status = test_results.get("status")
    if not status:
        raise PressMergeBundleInputError("test_results requires status")
    gates = test_results.get("per_gate_summary", test_results.get("gates"))
    return {"status": str(status), "per_gate_summary": _gate_summary(gates)}


def _review_evidence(
    refs: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path | str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not refs:
        raise PressMergeBundleInputError("at least one review evidence ref is required")
    reviews: list[dict[str, Any]] = []
    evidence_refs: list[dict[str, str]] = []
    for raw in refs:
        ref, record = _verify_evidence_ref(raw, repo_root=repo_root, required_kind="review-evidence")
        verdict = record.get("verdict")
        non_ratification = record.get("non_ratification_statement")
        if not verdict or not non_ratification:
            raise PressMergeBundleInputError(
                f"review evidence {ref['ref']} requires verdict and non_ratification_statement"
            )
        reviews.append(
            {
                "ref": ref["ref"],
                "sha256": ref["sha256"],
                "evidence_id": str(record.get("evidence_id", "")),
                "verdict": str(verdict),
                "notes": {
                    "findings": str(record.get("findings", "")),
                    "recommended_follow_up": str(record.get("recommended_follow_up", "")),
                    "blocking_findings_count": len(record.get("blocking_findings") or []),
                    "non_blocking_findings_count": len(record.get("non_blocking_findings") or []),
                },
                "non_ratification_statement": str(non_ratification),
            }
        )
        evidence_refs.append(ref)
    return sorted(reviews, key=lambda item: (item["ref"], item["sha256"])), evidence_refs


def _computer_use_evidence(
    refs: Sequence[Mapping[str, Any]] | None,
    *,
    repo_root: Path | str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not refs:
        return [], []
    entries: list[dict[str, Any]] = []
    evidence_refs: list[dict[str, str]] = []
    for raw in refs:
        ref, record = _verify_evidence_ref(
            raw,
            repo_root=repo_root,
            required_kind="computer-use-evidence",
            load_mapping=False,
        )
        entries.append(
            {
                "ref": ref["ref"],
                "sha256": ref["sha256"],
                "output_name": str(
                    raw.get("output_name")
                    or record.get("output_name")
                    or record.get("kind")
                    or "computer-use-evidence"
                ),
                "summary": str(raw.get("summary") or record.get("summary") or ""),
            }
        )
        evidence_refs.append(ref)
    return sorted(entries, key=lambda item: (item["output_name"], item["ref"])), evidence_refs


def _evidence_refs(*groups: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    merged = [entry for group in groups for entry in group]
    return sorted(merged, key=lambda item: (item["kind"], item["ref"], item["sha256"]))


def build_bundle(
    *,
    pr_number: int,
    head_ref: str,
    source_ratification: Mapping[str, Any],
    diff_summary: Mapping[str, Any],
    test_results: Mapping[str, Any],
    review_evidence_refs: Sequence[Mapping[str, Any]],
    computer_use_evidence_refs: Sequence[Mapping[str, Any]] | None = None,
    carrier_manifest_ref: Mapping[str, Any] | None = None,
    bundle_id: str | None = None,
    repo_root: Path | str | None = None,
    authority_action: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic structured press-merge bundle.

    The function is CLI-agnostic and pure over local input files. It returns the
    bundle object in memory and raises before returning on missing/stale
    evidence or attempted authority actions.
    """
    _require_no_authority(authority_action)
    if not head_ref:
        raise PressMergeBundleInputError("head_ref is required")
    try:
        pr_num = int(pr_number)
    except (TypeError, ValueError) as exc:
        raise PressMergeBundleInputError("pr_number must be an integer") from exc
    if pr_num <= 0:
        raise PressMergeBundleInputError("pr_number must be positive")

    diff, carrier_refs = _diff_summary(
        diff_summary, repo_root=repo_root, carrier_manifest_ref=carrier_manifest_ref
    )
    reviews, review_refs = _review_evidence(review_evidence_refs, repo_root=repo_root)
    computer_use, computer_refs = _computer_use_evidence(
        computer_use_evidence_refs, repo_root=repo_root
    )

    payload: dict[str, Any] = {
        "kind": BUNDLE_KIND,
        "schema_version": SCHEMA_VERSION,
        "bundle_id": bundle_id or f"pr-{pr_num}-{_slug(head_ref)}",
        "has_authority": False,
        "pr": {"number": pr_num, "head_ref": str(head_ref)},
        "source_ratification": _source_ratification(source_ratification),
        "diff_summary": diff,
        "test_results": _test_results(test_results),
        "review_evidence": reviews,
        "computer_use_evidence": computer_use,
        "evidence_refs": _evidence_refs(carrier_refs, review_refs, computer_refs),
    }
    content_hash = _content_hash(payload)
    bundle = {**payload, "content_hash": content_hash}

    schema_errors = validate_with_schema(
        bundle,
        SCHEMA_PATH,
        "<press-merge-bundle>",
        code="PRESS-MERGE-BUNDLE",
        contract=PROSE_CONTRACT,
    )
    if schema_errors:
        raise PressMergeBundleSchemaError(
            "internal: produced press-merge bundle fails its own schema: "
            + "; ".join(err.format() for err in schema_errors)
        )
    return bundle


def bundle_bytes(bundle: Mapping[str, Any]) -> bytes:
    """Return deterministic canonical JSON bytes for a bundle object."""
    _require_bundle_no_authority(bundle)
    return _canonical_bytes(dict(bundle)).encode("utf-8")


def _require_bundle_no_authority(bundle: Mapping[str, Any]) -> None:
    if bundle.get("has_authority") is not False:
        raise AuthorityRefused("press-merge bundle must have has_authority: false")


def render_bundle(bundle: Mapping[str, Any]) -> str:
    """Render a deterministic Markdown ratification surface from a bundle."""
    _require_bundle_no_authority(bundle)
    pr = bundle["pr"]
    diff = bundle["diff_summary"]
    tests = bundle["test_results"]
    lines: list[str] = [
        f"# Press-Merge Bundle: PR #{pr['number']} (`{pr['head_ref']}`)",
        "",
        f"Content hash: `{bundle['content_hash']}`",
        "",
        "## Diff Summary",
        "",
        f"- Files changed: {diff['files_changed']}",
        f"- Additions: {diff['additions']}",
        f"- Deletions: {diff['deletions']}",
        "- Paths:",
    ]
    paths = diff.get("path_set") or []
    lines.extend([f"  - `{path}`" for path in paths] or ["  - None"])
    carrier = diff.get("carrier_path_set")
    if carrier:
        lines.extend(
            [
                f"- Carrier path-set ref: `{carrier['ref']}`",
                f"- Carrier path-set sha256: `{carrier['sha256']}`",
                "- Carrier paths:",
            ]
        )
        lines.extend([f"  - `{path}`" for path in carrier["paths"]] or ["  - None"])
    else:
        lines.append("- Carrier path-set: None")

    lines.extend(
        [
            "",
            "## Test/CI Roll-Up",
            "",
            f"- Overall status: `{tests['status']}`",
            "",
            "| Gate | Status | Summary |",
            "| --- | --- | --- |",
        ]
    )
    for gate in tests.get("per_gate_summary", []):
        lines.append(f"| {gate['name']} | `{gate['status']}` | {gate['summary']} |")
    if not tests.get("per_gate_summary"):
        lines.append("| None | `not_reported` |  |")

    lines.extend(["", "## Review Evidence", ""])
    for review in bundle.get("review_evidence", []):
        lines.extend(
            [
                f"### {review['evidence_id'] or review['ref']}",
                "",
                f"- Ref: `{review['ref']}`",
                f"- SHA256: `{review['sha256']}`",
                f"- Verdict: `{review['verdict']}`",
                f"- Blocking findings: {review['notes']['blocking_findings_count']}",
                f"- Non-blocking findings: {review['notes']['non_blocking_findings_count']}",
                f"- Notes: {review['notes']['findings']}",
                f"- Recommended follow-up: {review['notes']['recommended_follow_up']}",
                f"- Non-ratification: {review['non_ratification_statement']}",
                "",
            ]
        )

    computer_use = bundle.get("computer_use_evidence", [])
    if computer_use:
        lines.extend(["## Computer-Use Evidence", ""])
        for entry in computer_use:
            lines.extend(
                [
                    f"- `{entry['output_name']}`: `{entry['ref']}`",
                    f"  - SHA256: `{entry['sha256']}`",
                    f"  - Summary: {entry['summary']}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "This bundle carries no merge authority. It does not ratify, approve, enqueue, "
            "merge, deploy, mutate branch protection, or modify live repository settings.",
            "",
        ]
    )
    return "\n".join(lines)
