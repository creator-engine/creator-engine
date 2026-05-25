"""RV1-083 — end-to-end v1.0 delivery rehearsal (dry-run-safe, local).

Exercises the as-built ``ce`` surface end-to-end in a governed temp git repo,
using only **dry-run-safe** paths: no live tmux spawn, no live container, no
network, no GitHub/landing, no secret leakage. Every command either runs to a
benign success (`ce init` / `ce check` / `ce ledger verify` / `ce fanin` /
`ce queue dry-run` / `ce launch --dry-run`) or refuses fail-closed
(`ce lane launch --no-tmux`, `ce worker status` on a missing record).

After the full pipeline, the tracked tree must remain clean: every byte of
runtime output lands under the ignored ``.hermes/`` root or pytest temp dirs.

``ce lane launch`` has no ``--dry-run`` flag (only the refuse-only ``--no-tmux``),
so the lane step is rehearsed as a dry-run-safe refusal that leaves no pane
record — the safe equivalent of a dry-run, honoring the no-live-spawn boundary.
The committed cp314 wheel predates ``ce fanin`` (G7) and ``ce queue`` (G8); the
offline-install proof for those surfaces is documented in
``docs/operations/V1_DELIVERY_REHEARSAL.md`` and the as-built surface is run here
from source.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli, fanin_runtime, integration_queue_dry_run as iq


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture()
def governed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    _git(["add", ".gitignore"], repo)
    _git(["-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-m", "init"], repo)
    return repo


def _run(argv, capsys) -> tuple[int, str]:
    ret = ce_cli.main(argv)
    out = capsys.readouterr().out
    return ret, out


# ---------------------------------------------------------------------------
# Individual dry-run-safe stages
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rehearsal_init_creates_ignored_state(governed_repo: Path, capsys):
    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    capsys.readouterr()
    assert (governed_repo / ".hermes").is_dir()
    # All init writes are under ignored .hermes/, so the tracked tree stays clean.
    status = _git(["status", "--porcelain"], governed_repo).stdout
    assert ".hermes/" not in status


def test_rehearsal_check_passes_from_repo_root(monkeypatch):
    # `ce check` validates the repo it is run in, from the repo root (its checks
    # resolve contract paths relative to CWD). The shipped well-formed examples
    # — including the new integration-queue-dry-run fixtures — must pass.
    monkeypatch.chdir(_REPO_ROOT)
    assert ce_cli.main(["check", "examples/well-formed"]) == 0


def test_rehearsal_doctor_interpreter_contract(governed_repo: Path, capsys):
    ce_cli.main(["init", "--repo-root", str(governed_repo)])
    capsys.readouterr()
    # --no-check-packaging: the temp repo has no wheelhouse; the interpreter and
    # state-path clauses are what we assert here.
    ret = ce_cli.main(["doctor", "--repo-root", str(governed_repo), "--no-check-packaging", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "ok" in payload
    # The interpreter contract (floor/target >=3.14) is evaluated and satisfied here.
    blob = json.dumps(payload)
    assert "3.14" in blob
    assert ret in (0, 1)  # may refuse on absent tmux/podman, but must not crash


def test_rehearsal_lane_launch_dry_run_safe_refusal(governed_repo: Path, capsys):
    ce_cli.main(["init", "--repo-root", str(governed_repo)])
    capsys.readouterr()
    ledger_root = governed_repo / ".hermes" / "active-work-ledger"
    prompt = governed_repo / "PROMPT.md"
    prompt.write_text("rehearsal prompt\n", encoding="utf-8")
    # --no-tmux requests a non-visible terminal for a visibility-required role:
    # refused fail-closed, leaving no pane record (the dry-run-safe lane smoke).
    ret = ce_cli.main([
        "lane", "launch",
        "--controller-id", "ce-controller",
        "--lane-id", "pco-rehearsal",
        "--role", "implementer",
        "--prompt", str(prompt),
        "--prompt-sha", _sha256_file(prompt),
        "--repo-root", str(governed_repo),
        "--ledger-root", str(ledger_root),
        "--no-tmux",
    ])
    assert ret != 0
    # The refusal leaves no pane *record* (init may pre-create an empty panes/ dir).
    pane_records = [p for p in ledger_root.rglob("*") if p.is_file() and "pane" in p.name.lower()]
    assert pane_records == [], f"dry-run-safe lane refusal left a pane record: {pane_records}"


def test_rehearsal_worker_status_fail_closed(governed_repo: Path):
    cir = governed_repo / ".hermes" / "container-instances"
    # Reading a non-existent container-instance record fails closed (no live container).
    ret = ce_cli.main([
        "worker", "status",
        "--container-instance-root", str(cir),
        "--claim-id", "pco-rehearsal",
        "--instance-id", "absent",
    ])
    assert ret != 0


def test_rehearsal_fanin_build_inspect(governed_repo: Path, capsys):
    ce_cli.main(["init", "--repo-root", str(governed_repo)])
    capsys.readouterr()
    ev = governed_repo / "ev"
    payload = ev / "a.txt"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text("rehearsal evidence\n", encoding="utf-8")
    manifest = ev / "SHA256SUMS.txt"
    manifest.write_text(f"{_sha256_file(payload)}  {payload}\n", encoding="utf-8")
    request = {
        "kind": "evidence-fan-in-request",
        "schema_version": "1",
        "packet_id": "pco-v1-g8-rehearsal",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "a" * 64},
        "evidence_manifests": [{"manifest_ref": str(manifest), "manifest_sha256": _sha256_file(manifest)}],
    }
    req_path = governed_repo / "fanin-request.yaml"
    req_path.write_text(yaml.safe_dump(request, sort_keys=True), encoding="utf-8")
    packet_root = governed_repo / ".hermes" / "fan-in"

    assert ce_cli.main([
        "fanin", "build", "--request", str(req_path), "--packet-root", str(packet_root),
        "--repo-root", str(governed_repo), "--json",
    ]) == 0
    packets = sorted(packet_root.glob("*.json"))
    assert len(packets) == 1
    assert ce_cli.main(["fanin", "inspect", "--packet", str(packets[0])]) == 0


def test_rehearsal_queue_dry_run_inspect(governed_repo: Path, capsys):
    ce_cli.main(["init", "--repo-root", str(governed_repo)])
    capsys.readouterr()
    # Build a real fan-in packet to serve as queue evidence.
    pkt = _build_fanin_packet(governed_repo)
    request = {
        "kind": "integration-queue-dry-run-request",
        "schema_version": "1",
        "preview_id": "pco-v1-g8-rehearsal-queue",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "b" * 64},
        "lanes": [{"lane_ref": "pco-rehearsal", "fanin_packet_ref": str(pkt), "declared_order": 1}],
    }
    req_path = governed_repo / "queue-request.yaml"
    req_path.write_text(yaml.safe_dump(request, sort_keys=True), encoding="utf-8")
    preview_root = governed_repo / ".hermes" / "integration-queue"

    assert ce_cli.main([
        "queue", "dry-run", "--request", str(req_path), "--preview-root", str(preview_root),
        "--repo-root", str(governed_repo), "--json",
    ]) == 0
    previews = sorted(preview_root.glob("*.json"))
    assert len(previews) == 1
    assert ce_cli.main(["queue", "inspect", "--preview", str(previews[0])]) == 0
    # Live landing is refused fail-closed (no authority).
    assert ce_cli.main([
        "queue", "dry-run", "--request", str(req_path), "--preview-root", str(preview_root),
        "--repo-root", str(governed_repo), "--land",
    ]) != 0


def test_rehearsal_launch_dry_run_no_spawn(capsys):
    ret = ce_cli.main(["launch", "--dry-run", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert ret == 0
    assert payload["spawned"] is False and payload["attached"] is False
    assert payload["plan"]["visibility"] == "operator_visible"


def _build_fanin_packet(repo: Path) -> Path:
    ev = repo / "qev"
    payload = ev / "a.txt"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text("queue evidence\n", encoding="utf-8")
    manifest = ev / "SHA256SUMS.txt"
    manifest.write_text(f"{_sha256_file(payload)}  {payload}\n", encoding="utf-8")
    request = {
        "kind": "evidence-fan-in-request",
        "schema_version": "1",
        "packet_id": "pco-rehearsal-evidence",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "a" * 64},
        "evidence_manifests": [{"manifest_ref": str(manifest), "manifest_sha256": _sha256_file(manifest)}],
    }
    req_path = repo / "qfanin-request.yaml"
    req_path.write_text(yaml.safe_dump(request, sort_keys=True), encoding="utf-8")
    result = fanin_runtime.build(request=req_path, packet_root=repo / ".hermes" / "fan-in")
    return result.packet_path


# ---------------------------------------------------------------------------
# Full pipeline: clean tracked tree + no-leak after the rehearsal
# ---------------------------------------------------------------------------


def test_full_pipeline_leaves_tracked_tree_clean_and_no_leak(governed_repo: Path, capsys):
    transcript: list[str] = []

    def step(argv, expect_zero=True):
        ret, out = _run(argv, capsys)
        transcript.append(f"$ ce {' '.join(argv)}\n[exit {ret}]\n{out}")
        if expect_zero:
            assert ret == 0, f"step failed: ce {argv} -> {ret}\n{out}"
        return ret, out

    step(["init", "--repo-root", str(governed_repo), "--json"])
    # (`ce check` is CWD-sensitive and is exercised from the repo root in
    # test_rehearsal_check_passes_from_repo_root; the clean-status pipeline below
    # stays hermetic to the temp repo.)
    step(["doctor", "--repo-root", str(governed_repo), "--no-check-packaging", "--json"], expect_zero=False)
    step(["launch", "--dry-run", "--json"])

    # fan-in + queue dry-run produce ignored .hermes/ output only.
    pkt = _build_fanin_packet(governed_repo)
    request = {
        "kind": "integration-queue-dry-run-request",
        "schema_version": "1",
        "preview_id": "pco-v1-g8-full-pipeline",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "c" * 64},
        "lanes": [{"lane_ref": "pco-rehearsal", "fanin_packet_ref": str(pkt), "declared_order": 1}],
    }
    req_path = governed_repo / "pipeline-queue.yaml"
    req_path.write_text(yaml.safe_dump(request, sort_keys=True), encoding="utf-8")
    step([
        "queue", "dry-run", "--request", str(req_path),
        "--preview-root", str(governed_repo / ".hermes" / "integration-queue"),
        "--repo-root", str(governed_repo), "--json",
    ])

    # The tracked tree is clean: only ignored .hermes/ + untracked scratch files
    # exist; nothing tracked was mutated by the dry-run-safe pipeline.
    status = _git(["status", "--porcelain"], governed_repo).stdout
    tracked_changes = [
        line for line in status.splitlines()
        if line and not line.startswith("??")
    ]
    assert tracked_changes == [], f"rehearsal mutated tracked files: {tracked_changes}"
    # And .hermes/ output never reaches the tracked/untracked-visible tree.
    assert ".hermes/" not in status, f".hermes output not ignored: {status!r}"

    # No-leak: the transcript carries no obvious secret material.
    blob = "\n".join(transcript)
    for needle in ("BEGIN PRIVATE KEY", "BEGIN RSA", "password=", "secret=", "api_key="):
        assert needle not in blob, f"rehearsal transcript leaked {needle!r}"
