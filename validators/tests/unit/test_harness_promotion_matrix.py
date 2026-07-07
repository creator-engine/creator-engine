from __future__ import annotations

from pathlib import Path

from creator_engine_validator import harness_matrix as hm
from creator_engine_validator.checks import harness_promotion_matrix as chk
from creator_engine_validator.cli import main


def _bad_row() -> hm.HarnessRow:
    return hm.HarnessRow(
        "codex",
        "Ring 1",
        {
            "code-support": hm.Cell(hm.GREEN, "candidate hook support exists"),
            "launch-wired": hm.Cell(hm.YELLOW, "deferred", verified=False),
            "live-proven": hm.Cell(hm.RED, "not live-proven"),
            "promotion-approved": hm.Cell(hm.RED, "not approved"),
        },
        hm.Cell(hm.GATE_YES, "incorrect promotion"),
    )


def test_gate_capable_requires_all_green_or_exception():
    matrix = hm.HarnessMatrix((_bad_row(),))

    errors = chk.evaluate(matrix)

    assert len(errors) == 1
    assert errors[0].code == chk.CODE_GATE_WITHOUT_GREEN
    assert "codex/Ring 1" in errors[0].path


def test_dated_operator_exception_allows_non_green_gate_row():
    row = hm.HarnessRow(
        _bad_row().provider,
        _bad_row().ring,
        _bad_row().cells,
        _bad_row().gate_capable,
        hm.PromotionException(
            date="2026-07-06",
            ratification_ref="operator-ratification-471",
            provenance="Operator ratified the exception",
        ),
    )

    assert chk.evaluate(hm.HarnessMatrix((row,))) == ()


def test_rendered_doc_must_match_source_matrix(tmp_path: Path):
    package = tmp_path / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (package / "harness_matrix.py").write_text("# marker\n", encoding="utf-8")
    doc = tmp_path / hm.DOC_PATH
    doc.parent.mkdir(parents=True)
    doc.write_text("stale\n", encoding="utf-8")

    errors = chk.evaluate_repo(tmp_path)

    assert any(error.code == chk.CODE_DOC_MISMATCH for error in errors)


def test_verify_harness_promotion_matrix_cli_returns_nonzero_for_stale_doc(tmp_path: Path, capsys):
    package = tmp_path / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (package / "harness_matrix.py").write_text("# marker\n", encoding="utf-8")
    doc = tmp_path / hm.DOC_PATH
    doc.parent.mkdir(parents=True)
    doc.write_text("stale\n", encoding="utf-8")

    assert main(["verify-harness-promotion-matrix", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL harness_promotion_matrix" in out
    assert str(hm.DOC_PATH) in out


def test_check_invocation_does_not_run_repo_wide_harness_promotion_gate(monkeypatch, capsys):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("harness promotion matrix evaluator must not run from generic ce check")

    monkeypatch.setattr(chk, "evaluate_repo", fail_if_called)

    assert main(["check", "examples/well-formed/identity-record.yml"]) == 0

    out = capsys.readouterr().out
    assert "harness_promotion_matrix" not in out
    assert "harness_promotion_gate_without_all_green" not in out
