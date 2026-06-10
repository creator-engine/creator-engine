"""Unit tests for the v3.5-C A-C1 ``decision_record`` check (Decision Records)."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import decision_record as chk
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.mutation_class import PRIVILEGED_NAMES

FIXTURES = Path(__file__).resolve().parents[2] / "examples" / "decision-record"


def _fixture(name: str) -> Path:
    return FIXTURES / name


def _record(**overrides):
    base = {
        "kind": "decision-record", "record_type": "adr", "schema_version": "1",
        "id": "ADR-0001", "title": "a decision", "status": "proposed",
        "date": "2026-06-01", "decision_makers": ["alice"],
        "review_by": "2026-12-01", "mutation_class": "docs",
        "evidence_refs": [{"kind": "doc", "ref": "docs/x.md", "tag": "x"}],
    }
    base.update(overrides)
    return base


def _codes(record, known_ids=frozenset()):
    return sorted({e.code for e in chk.validate_decision_record(record, Path("r.md"), known_ids)})


def _write_md(path: Path, front_matter: dict, body: str = "# body\n") -> Path:
    path.write_text("---\n" + yaml.safe_dump(front_matter) + "---\n\n" + body, encoding="utf-8")
    return path


# --- registration -------------------------------------------------------------
def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg
    assert chk.CODE_SELF_RATIFIED in reg[chk.CHECK_NAME].frs


# --- fixtures (the gate's green-def) -------------------------------------------
def test_valid_adr_fixture_passes():
    result = chk.run([_fixture("valid-adr.md")])
    assert result.ok, [e.format() for e in result.errors]


def test_valid_rfc_fixture_passes():
    result = chk.run([_fixture("valid-rfc.md")])
    assert result.ok, [e.format() for e in result.errors]


def test_self_ratified_privileged_fixture_rejected():
    result = chk.run([_fixture("invalid-self-ratified-privileged.md")])
    assert any(e.code == chk.CODE_SELF_RATIFIED for e in result.errors)


def test_superseded_no_target_fixture_rejected():
    result = chk.run([_fixture("invalid-superseded-no-target.md")])
    assert any(e.code == chk.CODE_SUPERSEDED_UNRESOLVED for e in result.errors)


def test_fixture_dir_scan_flags_only_the_invalid_records():
    result = chk.run([FIXTURES])
    flagged = {Path(e.path.split(":")[0]).name for e in result.errors}
    assert any(name.startswith("invalid-self-ratified-privileged") for name in flagged)
    assert any(name.startswith("invalid-superseded-no-target") for name in flagged)
    assert not any(name.startswith("valid-") for name in flagged)


# --- schema teeth --------------------------------------------------------------
def test_missing_evidence_refs_rejected():
    rec = _record()
    del rec["evidence_refs"]
    assert chk.CODE_SCHEMA in _codes(rec)


def test_empty_evidence_refs_rejected():
    assert chk.CODE_SCHEMA in _codes(_record(evidence_refs=[]))


def test_untagged_evidence_ref_rejected():
    assert chk.CODE_SCHEMA in _codes(
        _record(evidence_refs=[{"kind": "doc", "ref": "docs/x.md"}])
    )


def test_missing_review_by_rejected():
    rec = _record()
    del rec["review_by"]
    assert chk.CODE_SCHEMA in _codes(rec)


def test_rfc_only_fields_on_adr_rejected():
    assert chk.CODE_SCHEMA in _codes(_record(disposition="merge"))
    assert chk.CODE_SCHEMA in _codes(_record(fcp={"opened_at": "2026-06-01"}))


def test_unknown_status_rejected():
    assert chk.CODE_SCHEMA in _codes(_record(status="ratified"))


# --- invariant teeth -----------------------------------------------------------
def test_accepted_without_ratification_rejected():
    assert chk.CODE_RATIFICATION_MISSING in _codes(_record(status="accepted"))


def test_accepted_with_ratification_passes():
    rec = _record(
        status="accepted",
        ratification={
            "ratified_by": "bob", "ratified_at": "2026-06-02",
            "ratification_prompt_sha": "a" * 64,
        },
    )
    assert _codes(rec) == []


def test_privileged_self_ratification_rejected_for_every_privileged_class():
    for cls in sorted(PRIVILEGED_NAMES):
        rec = _record(
            status="accepted", mutation_class=cls,
            ratification={
                "ratified_by": "alice", "ratified_at": "2026-06-02",
                "ratification_prompt_sha": "a" * 64,
            },
        )
        assert chk.CODE_SELF_RATIFIED in _codes(rec), cls


def test_non_privileged_self_ratification_is_allowed():
    # docs-class: the area owner may ratify their own area's decision (§A.5 tier 1).
    rec = _record(
        status="accepted", mutation_class="docs",
        ratification={
            "ratified_by": "alice", "ratified_at": "2026-06-02",
            "ratification_prompt_sha": "a" * 64,
        },
    )
    assert chk.CODE_SELF_RATIFIED not in _codes(rec)


def test_superseded_with_resolvable_target_passes():
    rec = _record(status="superseded", crosswalk={"superseded_by": "ADR-0002"})
    assert chk.CODE_SUPERSEDED_UNRESOLVED not in _codes(rec, frozenset({"ADR-0002"}))


def test_superseded_with_unresolvable_target_rejected():
    rec = _record(status="superseded", crosswalk={"superseded_by": "ADR-9999"})
    assert chk.CODE_SUPERSEDED_UNRESOLVED in _codes(rec, frozenset({"ADR-0001"}))


def test_accepted_rfc_with_open_fcp_concern_rejected():
    rec = _record(
        record_type="rfc", status="accepted", id="RFC-0001",
        disposition="merge",
        fcp={"opened_at": "2026-06-01",
             "concerns": [{"name": "naming", "status": "open"}]},
        ratification={
            "ratified_by": "bob", "ratified_at": "2026-06-02",
            "ratification_prompt_sha": "a" * 64,
        },
    )
    assert chk.CODE_FCP_OPEN_CONCERN in _codes(rec)


def test_proposed_rfc_may_carry_open_concerns():
    rec = _record(
        record_type="rfc", status="proposed", id="RFC-0001",
        disposition="merge",
        fcp={"opened_at": "2026-06-01",
             "concerns": [{"name": "naming", "status": "open"}]},
    )
    assert chk.CODE_FCP_OPEN_CONCERN not in _codes(rec)


# --- discovery + run() ---------------------------------------------------------
def test_run_resolves_supersession_within_scanned_set(tmp_path):
    _write_md(tmp_path / "ADR-0001-old.md",
              _record(status="superseded", crosswalk={"superseded_by": "ADR-0002"}))
    _write_md(tmp_path / "ADR-0002-new.md", _record(id="ADR-0002"))
    result = chk.run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_run_ignores_markdown_without_the_discriminator(tmp_path):
    (tmp_path / "notes.md").write_text("# just notes\n", encoding="utf-8")
    _write_md(tmp_path / "other.md", {"kind": "scope-record"})
    assert chk.run([tmp_path]).ok


def test_run_skips_template_files(tmp_path):
    # a template carries placeholder values that would never validate
    _write_md(tmp_path / "ADR-0000-template.md", {"kind": "decision-record", "id": "<id>"})
    assert chk.run([tmp_path]).ok


def test_run_flags_unparseable_self_named_record(tmp_path):
    (tmp_path / "ADR-0042-broken.md").write_text(
        "---\nkind: [unclosed\n---\n# broken\n", encoding="utf-8"
    )
    result = chk.run([tmp_path])
    assert any(e.code == chk.CODE_INVALID for e in result.errors)


def test_repo_templates_and_convention_docs_are_green():
    # the shipped convention surface itself validates (templates skipped).
    repo_root = Path(__file__).resolve().parents[3]
    result = chk.run([repo_root / "docs" / "decisions", repo_root / "docs" / "rfcs"])
    assert result.ok, [e.format() for e in result.errors]
