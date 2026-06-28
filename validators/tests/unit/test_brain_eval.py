from __future__ import annotations

import json

from creator_engine_validator import brain_eval, ce_cli


def test_brain_eval_runs_end_to_end_with_both_legs_and_k_values():
    report = brain_eval.run_eval()
    payload = report.to_dict()

    assert payload["ok"] is True
    assert payload["case_count"] == len(brain_eval.GOLDEN_CASES)
    assert payload["fixture_count"] == len(brain_eval.FIXTURES)
    assert payload["passed_count"] == payload["case_count"]
    assert payload["failed_count"] == 0
    assert payload["k_values"] == [3, 5]
    assert set(payload["metrics"]) == {"keyword", "semantic"}
    for leg in ("keyword", "semantic"):
        assert set(payload["metrics"][leg]) == {"recall@3", "recall@5"}
        assert 0.0 <= payload["metrics"][leg]["recall@3"] <= 1.0
        assert 0.0 <= payload["metrics"][leg]["recall@5"] <= 1.0

    assert len(payload["cases"]) == payload["case_count"]
    first = payload["cases"][0]
    assert set(first) == {"case_id", "query", "expected_refs", "passed", "legs"}
    assert set(first["legs"]) == {"keyword", "semantic"}
    for leg in ("keyword", "semantic"):
        assert set(first["legs"][leg]) == {"hits_by_k", "recall_by_k"}
        assert set(first["legs"][leg]["hits_by_k"]) == {"3", "5"}
        assert set(first["legs"][leg]["recall_by_k"]) == {"recall@3", "recall@5"}


def test_brain_eval_report_is_stable_for_same_inputs():
    first = brain_eval.run_eval().to_dict()
    second = brain_eval.run_eval().to_dict()

    assert first == second


def test_brain_eval_accepts_custom_k_values():
    payload = brain_eval.run_eval(k_values=(1, 5, 3, 3)).to_dict()

    assert payload["k_values"] == [1, 3, 5]
    for leg in ("keyword", "semantic"):
        assert set(payload["metrics"][leg]) == {"recall@1", "recall@3", "recall@5"}


def test_ce_brain_eval_json_cli(capsys):
    ret = ce_cli.main(["brain", "eval", "--json"])

    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["case_count"] == len(brain_eval.GOLDEN_CASES)
    assert set(payload["metrics"]) == {"keyword", "semantic"}


def test_ce_brain_eval_human_cli(capsys):
    ret = ce_cli.main(["brain", "eval"])

    assert ret == 0
    out = capsys.readouterr().out
    assert "ce brain eval: OK" in out
    assert "keyword:" in out
    assert "semantic:" in out
