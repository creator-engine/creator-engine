from __future__ import annotations

from pathlib import Path

from creator_engine_validator import brain_runtime as rt
from creator_engine_validator import brain_probe
from creator_engine_validator.checks import ce_brain_assertions


def _ledger_text() -> str:
    captured: list[str] = []
    rt.assert_claim(
        assertion_id="brain-assertion-check-0001",
        claim={"subject": "validator", "predicate": "accepts", "object": "brain-ledger"},
        scope="unit",
        evidence_ref="validators/tests/unit/test_ce_brain_assertions.py",
        records=[],
        write=lambda _path, text: captured.append(text),
    )
    return captured[-1]


def _probe_ledger_text(*, verdict: str = "present") -> str:
    captured: list[str] = []
    rt.assert_claim(
        assertion_id="brain-assertion-probe-0001",
        claim={
            "subject": "capability",
            "predicate": "probe-verdict",
            "object": "gh_authenticated",
            "verdict": verdict,
        },
        scope="capability-probes",
        evidence_ref="probe:gh_authenticated",
        records=[],
        write=lambda _path, text: captured.append(text),
    )
    return captured[-1]


def test_valid_brain_ledger_passes(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    path.write_text(_ledger_text(), encoding="utf-8")

    errors = ce_brain_assertions.validate_file(path)

    assert errors == []


def test_tampered_brain_ledger_fails(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    records = rt.load_ledger_text(_ledger_text())
    records[0]["scope"] = "tampered"
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")

    errors = ce_brain_assertions.validate_file(path)

    assert any(error.code == rt.CODE_CONTENT_ADDRESS for error in errors), [e.format() for e in errors]


def test_run_reports_explicit_parse_broken_brain_ledger(tmp_path: Path):
    path = tmp_path / "brain" / "assertions.yaml"
    path.parent.mkdir()
    path.write_text("kind: brain-assertion-ledger\nrecords: [\n", encoding="utf-8")

    result = ce_brain_assertions.run([path])

    assert not result.ok
    assert any(error.code == rt.CODE_SCHEMA for error in result.errors), [e.format() for e in result.errors]


def test_run_skips_explicit_parseable_non_brain_yaml(tmp_path: Path):
    path = tmp_path / "identity-record.yml"
    path.write_text("tenant_id: example\nhuman_ratifier_roles:\n  - source\n", encoding="utf-8")

    result = ce_brain_assertions.run([path])

    assert result.ok
    assert result.errors == ()


def test_run_reports_explicit_non_mapping_record_entry(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    data = rt.load_ledger_text(_ledger_text())
    doc = {
        "kind": rt.LEDGER_KIND,
        "record_type": rt.LEDGER_RECORD_TYPE,
        "schema_version": rt.SCHEMA_VERSION,
        "records": ["bad", *data],
    }
    path.write_text(rt.yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")

    result = ce_brain_assertions.run([path])

    assert not result.ok
    assert any(error.code == rt.CODE_SCHEMA for error in result.errors), [e.format() for e in result.errors]


def test_run_reports_explicit_ledger_path_with_non_brain_shape(tmp_path: Path):
    path = tmp_path / ".ce" / "state" / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("tenant_id: example\n", encoding="utf-8")

    result = ce_brain_assertions.run([path])

    assert not result.ok
    assert any(error.code == rt.CODE_SCHEMA for error in result.errors), [e.format() for e in result.errors]


def test_run_reports_parse_broken_state_brain_ledger_from_directory(tmp_path: Path):
    path = tmp_path / ".ce" / "state" / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("kind: brain-assertion-ledger\nrecords: [\n", encoding="utf-8")

    result = ce_brain_assertions.run([tmp_path])

    assert not result.ok
    assert any(error.code == rt.CODE_SCHEMA for error in result.errors), [e.format() for e in result.errors]


def test_run_discovers_brain_ledger(tmp_path: Path):
    path = tmp_path / "nested" / "assertions.yaml"
    path.parent.mkdir()
    path.write_text(_ledger_text(), encoding="utf-8")

    result = ce_brain_assertions.run([tmp_path])

    assert result.ok


def test_probe_backed_assertion_is_reprobed_and_mismatch_fails_closed(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    path.write_text(_probe_ledger_text(verdict="present"), encoding="utf-8")

    errors = ce_brain_assertions.validate_file(
        path,
        probe_context=brain_probe.ProbeContext(
            probes={
                "gh_authenticated": lambda _context: brain_probe.ProbeResult(
                    name="gh_authenticated",
                    verdict="absent",
                    evidence={"source": "unit"},
                )
            }
        ),
    )

    assert any(error.code == brain_probe.CODE_PROBE_DISAGREEMENT for error in errors), [
        e.format() for e in errors
    ]


def test_probe_backed_assertion_live_unknown_fails_closed(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    path.write_text(_probe_ledger_text(verdict="present"), encoding="utf-8")

    errors = ce_brain_assertions.validate_file(
        path,
        probe_context=brain_probe.ProbeContext(
            probes={
                "gh_authenticated": lambda _context: brain_probe.ProbeResult(
                    name="gh_authenticated",
                    verdict="unknown",
                    evidence={"source": "unit"},
                )
            }
        ),
    )

    assert any(error.code == brain_probe.CODE_PROBE_DISAGREEMENT for error in errors), [
        e.format() for e in errors
    ]


def test_probe_backed_assertion_accepts_matching_fresh_probe(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    path.write_text(_probe_ledger_text(verdict="present"), encoding="utf-8")

    errors = ce_brain_assertions.validate_file(
        path,
        probe_context=brain_probe.ProbeContext(
            probes={
                "gh_authenticated": lambda _context: brain_probe.ProbeResult(
                    name="gh_authenticated",
                    verdict="present",
                    evidence={"source": "unit"},
                )
            }
        ),
    )

    assert errors == []


def test_non_probe_assertion_does_not_invoke_probe_layer(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    path.write_text(_ledger_text(), encoding="utf-8")

    def fail_if_called(_context):
        raise AssertionError("probe layer should not run for non-probe evidence")

    errors = ce_brain_assertions.validate_file(
        path,
        probe_context=brain_probe.ProbeContext(probes={"gh_authenticated": fail_if_called}),
    )

    assert errors == []


def test_static_invalid_probe_assertion_does_not_invoke_probe_layer(tmp_path: Path):
    path = tmp_path / "assertions.yaml"
    records = rt.load_ledger_text(_probe_ledger_text(verdict="present"))
    records[0]["claim"]["verdict"] = "absent"
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")

    def fail_if_called(_context):
        raise AssertionError("probe layer should not run for static-invalid ledgers")

    errors = ce_brain_assertions.validate_file(
        path,
        probe_context=brain_probe.ProbeContext(probes={"gh_authenticated": fail_if_called}),
    )

    assert any(error.code == rt.CODE_CONTENT_ADDRESS for error in errors), [
        e.format() for e in errors
    ]
