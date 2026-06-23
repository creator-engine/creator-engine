"""ce-ops#220 — unit tests for the PROBED harness-support capability matrix.

The matrix is the antidote to the containment-probe incident (ce-ops#221): every
cell must be DERIVED from the live adapter specs / committed config at runtime —
never hand-asserted in prose. These tests pin the load-bearing invariants:

* claude Ring-1 == ``present`` and is backed by the committed ``.claude/settings.json``
  PreToolUse hook-pack (no backing file -> not ``present``).
* codex Ring-1 == ``managed-non-bypassable`` IFF a committed managed-hook config
  pins ``allow_managed_hooks_only`` — else ``none``/``present`` (NEVER managed on a
  prose claim).
* NO capability is ever reported as present without a backing file.
* the containment cell is ``deferred``/asserted-but-unverifiable while the live
  herdr launch is a fail-closed U2 stub (the exact cell the false 'contained
  gVisor' claim would have failed).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import harness_matrix as hm

# The real repo root (validators/creator_engine_validator -> repo root is 4 up
# from this test file: tests/unit/<file> -> validators -> repo).
REPO_ROOT = Path(__file__).resolve().parents[3]


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _row(matrix: hm.HarnessMatrix, harness: str) -> hm.HarnessRow:
    return next(r for r in matrix.rows if r.harness == harness)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_matrix_covers_all_harnesses_and_capabilities():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    assert tuple(r.harness for r in matrix.rows) == hm.HARNESSES
    for row in matrix.rows:
        assert set(row.cells) == set(hm.CAPABILITIES)


def test_to_dict_is_json_safe():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    payload = json.loads(json.dumps(matrix.to_dict()))
    assert payload["issue"] == "ce-ops#220"
    assert payload["capabilities"] == list(hm.CAPABILITIES)
    assert {r["harness"] for r in payload["rows"]} == set(hm.HARNESSES)


# ---------------------------------------------------------------------------
# Invariant: claude Ring-1 = full (committed PreToolUse hook-pack)
# ---------------------------------------------------------------------------


def test_claude_ring1_is_present_and_backed_by_settings():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    cell = _row(matrix, "claude").cells["ring1"]
    assert cell.value == hm.RING1_PRESENT
    assert cell.verified is True
    # Backing file is the committed .claude/settings.json PreToolUse pack.
    assert ".claude/settings.json" in cell.provenance
    assert "PreToolUse" in cell.provenance


def test_claude_ring1_is_none_without_a_pretooluse_hook(tmp_path: Path):
    # A repo with NO committed PreToolUse pack -> claude Ring-1 must NOT be present.
    repo = tmp_path / "no-hooks"
    (repo / ".claude").mkdir(parents=True)
    (repo / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {}}), encoding="utf-8"
    )
    matrix = hm.build_matrix(repo_root=repo)
    cell = _row(matrix, "claude").cells["ring1"]
    assert cell.value == hm.RING1_NONE
    assert cell.verified is False


# ---------------------------------------------------------------------------
# Invariant: codex Ring-1 = managed-non-bypassable IFF allow_managed_hooks_only
# ---------------------------------------------------------------------------


def test_codex_ring1_is_not_managed_without_a_committed_pin(tmp_path: Path):
    # With NO committed codex managed-hook config pinning the non-bypassable flag,
    # the cell MUST NOT be `managed` (never `managed-non-bypassable` on a prose
    # claim). The managed claim REQUIRES the backing pin. The confirm predicate
    # exists on main, so the derived state is `present` but verified=False (the
    # "asserted-but-unverifiable" middle state) — never silently managed.
    repo = tmp_path / "codex-no-pin"
    repo.mkdir()
    matrix = hm.build_matrix(repo_root=repo)
    cell = _row(matrix, "codex").cells["ring1"]
    assert cell.value != hm.RING1_MANAGED
    if cell.value == hm.RING1_PRESENT:
        # A `present` codex Ring-1 without a committed pin must be flagged unverified.
        assert cell.verified is False


def test_codex_ring1_is_managed_on_main_where_the_pin_is_committed():
    # PR #387 landed the codex managed Ring-1 hook pack on main with
    # `allow_managed_hooks_only = true`. The matrix DERIVES this from the committed
    # .codex/requirements.toml — so codex Ring-1 is managed-non-bypassable today,
    # and the cell cites the real backing file (not a prose claim).
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    cell = _row(matrix, "codex").cells["ring1"]
    assert cell.value == hm.RING1_MANAGED
    assert cell.verified is True
    assert hm.CODEX_MANAGED_PIN in cell.provenance
    assert ".codex/requirements.toml" in cell.provenance


def test_codex_ring1_is_managed_when_allow_managed_hooks_only_is_pinned(tmp_path: Path):
    repo = tmp_path / "codex-managed"
    (repo / ".codex").mkdir(parents=True)
    (repo / ".codex" / "requirements.toml").write_text(
        "allow_managed_hooks_only = true\n", encoding="utf-8"
    )
    matrix = hm.build_matrix(repo_root=repo)
    cell = _row(matrix, "codex").cells["ring1"]
    assert cell.value == hm.RING1_MANAGED
    assert cell.verified is True
    assert hm.CODEX_MANAGED_PIN in cell.provenance
    assert "requirements.toml" in cell.provenance


def test_codex_ring1_not_managed_without_the_pin_even_if_config_present(tmp_path: Path):
    # A committed config that does NOT pin the flag must NOT yield managed.
    repo = tmp_path / "codex-unpinned"
    (repo / ".codex").mkdir(parents=True)
    (repo / ".codex" / "config.toml").write_text(
        "approval_policy = 'never'\n", encoding="utf-8"
    )
    matrix = hm.build_matrix(repo_root=repo)
    cell = _row(matrix, "codex").cells["ring1"]
    assert cell.value != hm.RING1_MANAGED


# ---------------------------------------------------------------------------
# Invariant: never report a capability present without a backing file
# ---------------------------------------------------------------------------


def test_no_cell_is_present_without_a_backing_file_reference():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    present_values = {hm.RING1_PRESENT, hm.RING1_MANAGED, "present"}
    for row in matrix.rows:
        for cap in hm.CAPABILITIES:
            cell = row.cells[cap]
            if cell.value in present_values and cell.verified:
                # A verified-present cell must cite a real file path / module file.
                assert (
                    ".py" in cell.provenance
                    or ".json" in cell.provenance
                    or ".toml" in cell.provenance
                ), f"{row.harness}/{cap} present without a backing file: {cell.provenance}"


def test_unverified_present_cells_are_flagged_not_silently_present(tmp_path: Path):
    # When claude Ring-1 cannot be confirmed (no PreToolUse), the cell must be
    # `none` + verified=False, never a silent `present`.
    repo = tmp_path / "empty"
    (repo / ".claude").mkdir(parents=True)
    (repo / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    matrix = hm.build_matrix(repo_root=repo)
    cell = _row(matrix, "claude").cells["ring1"]
    assert not (cell.value == hm.RING1_PRESENT and cell.verified)


# ---------------------------------------------------------------------------
# Invariant: containment is the ce-ops#221 antidote (probed, not asserted)
# ---------------------------------------------------------------------------


def test_containment_is_deferred_and_unverified_while_launch_is_stubbed():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    for row in matrix.rows:
        cell = row.cells["containment"]
        # Live gVisor/OpenShell launch is the U2 fail-closed stub -> deferred +
        # asserted-but-unverifiable. A prose 'contained gVisor' claim cannot pass.
        assert cell.verified is False
        assert "deferred" in cell.value
        assert "herdr_containment" in cell.provenance


def test_herdr_launch_probe_observes_the_failclosed_stub():
    # The probe DERIVES containment by invoking the stub and observing the
    # fail-closed raise — it is not a hardcoded boolean.
    assert hm._herdr_launch_is_wired() is False


# ---------------------------------------------------------------------------
# Ring-0 present for every harness (cred-scrub / launch envelope)
# ---------------------------------------------------------------------------


def test_ring0_present_for_every_harness_with_backing_spec():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    for harness in hm.HARNESSES:
        cell = _row(matrix, harness).cells["ring0"]
        assert cell.value == "present"
        assert cell.verified is True
        assert ".py" in cell.provenance


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def test_markdown_renders_table_and_provenance_and_unverifiable_marker():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    md = hm.render_markdown(matrix)
    assert "ce-ops#220" in md
    assert "| harness |" in md
    assert "## Provenance" in md
    # The containment cell is asserted-but-unverifiable -> the `*` marker + flag.
    assert "*" in md
    assert "asserted-but-unverifiable" in md


def test_json_render_round_trips():
    matrix = hm.build_matrix(repo_root=REPO_ROOT)
    payload = json.loads(hm.render_json(matrix))
    assert payload["kind"] == "harness-support-matrix"


# ---------------------------------------------------------------------------
# CLI surface: ce harness-matrix
# ---------------------------------------------------------------------------


def test_cli_help_is_reachable():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["harness-matrix", "--help"])
    assert exc.value.code == 0


def test_cli_emits_markdown_by_default(capsys):
    ret = ce_cli.main(["harness-matrix", "--repo-root", str(REPO_ROOT)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "CE harness-support capability matrix" in out
    assert "ce-ops#220" in out


def test_cli_emits_json(capsys):
    ret = ce_cli.main(["harness-matrix", "--repo-root", str(REPO_ROOT), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["issue"] == "ce-ops#220"
    rows = {r["harness"]: r for r in payload["rows"]}
    # The headline invariants are stable through the CLI surface too: claude Ring-1
    # is the committed PreToolUse pack; codex Ring-1 is managed-non-bypassable on
    # main (PR #387 pinned allow_managed_hooks_only).
    assert rows["claude"]["cells"]["ring1"]["value"] == hm.RING1_PRESENT
    assert rows["codex"]["cells"]["ring1"]["value"] == hm.RING1_MANAGED
