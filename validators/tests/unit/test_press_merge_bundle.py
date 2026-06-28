from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import fanin_runtime, press_merge_bundle


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _review_record(tmp_path: Path, *, verdict: str = "no_blocking_findings") -> Path:
    record = {
        "evidence_id": "review-w3",
        "verdict": verdict,
        "findings": "Reviewed diff, tests, and evidence refs.",
        "recommended_follow_up": "No follow-up.",
        "blocking_findings": [],
        "non_blocking_findings": [{"artifact_ref": "docs/x.md"}],
        "non_ratification_statement": (
            "This review evidence is NOT Source ratification and does not "
            "authorize merge, deploy, branch deletion, branch protection "
            "mutation, or live repository-settings change."
        ),
    }
    return _write(tmp_path / "evidence" / "review.yml", yaml.safe_dump(record, sort_keys=True))


def _computer_use_record(tmp_path: Path) -> Path:
    return _write(tmp_path / "evidence" / "closed-set-report.txt", "closed set passed\n")


def _carrier(tmp_path: Path) -> Path:
    return _write(
        tmp_path / ".ce" / "pr-manifests" / "w3.md",
        """# PR path manifest

AUTHORIZED_PATHS_COUNT=3

```text
.ce/pr-manifests/w3.md
validators/creator_engine_validator/press_merge_bundle.py
validators/tests/unit/test_press_merge_bundle.py
```
""",
    )


def _bundle_inputs(tmp_path: Path, *, computer_use: bool = False) -> dict:
    review = _review_record(tmp_path)
    carrier = _carrier(tmp_path)
    inputs = {
        "pr_number": 321,
        "head_ref": "w3-evidence-bundle-press-merge",
        "repo_root": tmp_path,
        "source_ratification": {
            "prompt_ref": "/tmp/ce-brief-w3.md",
            "sha256": "a" * 64,
        },
        "diff_summary": {
            "files_changed": 3,
            "additions": 120,
            "deletions": 4,
            "path_set": [
                "validators/tests/unit/test_press_merge_bundle.py",
                ".ce/pr-manifests/w3.md",
                "validators/creator_engine_validator/press_merge_bundle.py",
            ],
        },
        "carrier_manifest_ref": {
            "kind": "path-manifest",
            "ref": ".ce/pr-manifests/w3.md",
            "sha256": _sha256_file(carrier),
        },
        "test_results": {
            "status": "pass",
            "gates": {
                "unit": {"status": "pass", "summary": "focused unit tests passed"},
                "lint": {"status": "not_run", "summary": "not required for unit fixture"},
            },
        },
        "review_evidence_refs": [
            {
                "kind": "review-evidence",
                "ref": "evidence/review.yml",
                "sha256": _sha256_file(review),
            }
        ],
    }
    if computer_use:
        computer = _computer_use_record(tmp_path)
        inputs["computer_use_evidence_refs"] = [
            {
                "kind": "computer-use-evidence",
                "ref": "evidence/closed-set-report.txt",
                "sha256": _sha256_file(computer),
                "output_name": "closed-set-report",
                "summary": "closed-set report present",
            }
        ]
    return inputs


def test_build_bundle_is_deterministic_byte_identical(tmp_path):
    inputs = _bundle_inputs(tmp_path)

    first = press_merge_bundle.build_bundle(**inputs)
    second = press_merge_bundle.build_bundle(**inputs)

    assert first == second
    assert press_merge_bundle.bundle_bytes(first) == press_merge_bundle.bundle_bytes(second)
    assert first["content_hash"] == second["content_hash"]


def test_bundle_preserves_no_authority_invariant(tmp_path):
    bundle = press_merge_bundle.build_bundle(**_bundle_inputs(tmp_path))

    assert bundle["has_authority"] is False
    with pytest.raises(fanin_runtime.AuthorityRefused):
        press_merge_bundle.build_bundle(**_bundle_inputs(tmp_path), authority_action="merge")

    tampered = dict(bundle)
    tampered["has_authority"] = True
    with pytest.raises(fanin_runtime.AuthorityRefused):
        press_merge_bundle.render_bundle(tampered)


def test_missing_evidence_ref_fails_closed(tmp_path):
    inputs = _bundle_inputs(tmp_path)
    inputs["review_evidence_refs"] = [
        {"kind": "review-evidence", "ref": "evidence/missing.yml", "sha256": "b" * 64}
    ]

    with pytest.raises(fanin_runtime.EvidenceShaMismatch):
        press_merge_bundle.build_bundle(**inputs)


def test_stale_evidence_ref_fails_closed(tmp_path):
    inputs = _bundle_inputs(tmp_path)
    review = tmp_path / "evidence" / "review.yml"
    review.write_text(review.read_text(encoding="utf-8") + "changed: true\n", encoding="utf-8")

    with pytest.raises(fanin_runtime.StaleEvidence):
        press_merge_bundle.build_bundle(**inputs)


def test_renderer_is_stable_and_contains_required_sections(tmp_path):
    bundle = press_merge_bundle.build_bundle(**_bundle_inputs(tmp_path, computer_use=True))

    first = press_merge_bundle.render_bundle(bundle)
    second = press_merge_bundle.render_bundle(bundle)

    assert first == second
    assert "# Press-Merge Bundle: PR #321" in first
    assert "## Diff Summary" in first
    assert "## Test/CI Roll-Up" in first
    assert "## Review Evidence" in first
    assert "## Computer-Use Evidence" in first
    assert "This bundle carries no merge authority." in first


def test_computer_use_is_included_when_present_and_omitted_when_absent(tmp_path):
    without_computer = press_merge_bundle.build_bundle(**_bundle_inputs(tmp_path / "without"))
    with_computer = press_merge_bundle.build_bundle(**_bundle_inputs(tmp_path / "with", computer_use=True))

    assert without_computer["computer_use_evidence"] == []
    assert "## Computer-Use Evidence" not in press_merge_bundle.render_bundle(without_computer)
    assert with_computer["computer_use_evidence"][0]["output_name"] == "closed-set-report"
    assert "## Computer-Use Evidence" in press_merge_bundle.render_bundle(with_computer)
