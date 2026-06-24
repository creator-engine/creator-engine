"""RV1-082 — Integration Queue **dry-run** seam contract tests.

Gate 8 authors a *local serialized landing preview only*. The dry-run seam:

* reconstructs a deterministic, content-hashed serialized canonical-branch
  landing order across lanes from **verified fan-in packet evidence** (not lane
  self-report);
* carries **no authority** (``has_authority`` is schema ``const false``);
* refuses any live ``enqueue`` / ``land`` / ``merge`` action **fail-closed
  before any write**, leaving the output root byte-identical;
* records CE-event / PCL / distributed-identity as **deferred-not-rejected**
  seam stubs, never as active integrations.

These tests drive both the ``integration_queue_dry_run`` runtime directly and
the ``ce queue`` CLI surface, and assert determinism + every refusal. They use
real fan-in packets built by the landed Gate 7 ``fanin_runtime`` so the
evidence chain is genuine (no mocks).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli, fanin_runtime, integration_queue_dry_run as iq


# ---------------------------------------------------------------------------
# Helpers — build genuine fan-in packets as the queue dry-run's evidence inputs
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _build_fanin_packet(tmp_path: Path, slug: str) -> Path:
    """Build a real, content-hashed fan-in packet and return its path."""
    payload = _write(tmp_path / slug / "ev" / "a.txt", f"{slug}\n")
    manifest = _write(
        tmp_path / slug / "ev" / "SHA256SUMS.txt",
        f"{_sha256_file(payload)}  {payload}\n",
    )
    request = {
        "kind": "evidence-fan-in-request",
        "schema_version": "1",
        "packet_id": f"pkt-{slug}",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "a" * 64},
        "evidence_manifests": [
            {"manifest_ref": str(manifest), "manifest_sha256": _sha256_file(manifest)}
        ],
    }
    request_path = _write(tmp_path / slug / "request.yaml", yaml.safe_dump(request, sort_keys=True))
    packet_root = tmp_path / slug / "fan-in"
    result = fanin_runtime.build(request=request_path, packet_root=packet_root)
    return result.packet_path


def _make_request(tmp_path: Path, **override) -> tuple[Path, Path]:
    pkt_a = _build_fanin_packet(tmp_path, "lane-a")
    pkt_b = _build_fanin_packet(tmp_path, "lane-b")
    req = {
        "kind": "integration-queue-dry-run-request",
        "schema_version": "1",
        "preview_id": "pco-v1-g8-queue-dry-run",
        "source_ratification": {"prompt_ref": ".hermes/x/G8_PROMPT.md", "sha256": "b" * 64},
        "lanes": [
            {"lane_ref": "pco-lane-alpha", "fanin_packet_ref": str(pkt_a), "declared_order": 2},
            {"lane_ref": "pco-lane-beta", "fanin_packet_ref": str(pkt_b), "declared_order": 1},
        ],
    }
    req.update(override)
    request_path = _write(tmp_path / "queue-request.yaml", yaml.safe_dump(req, sort_keys=True))
    preview_root = tmp_path / ".hermes" / "integration-queue"
    preview_root.mkdir(parents=True, exist_ok=True)
    return request_path, preview_root


def _previews(root: Path) -> list[Path]:
    return sorted(Path(root).glob("*.json"))


# ---------------------------------------------------------------------------
# build — happy path: deterministic, content-hashed serialized landing preview
# ---------------------------------------------------------------------------


def test_build_writes_deterministic_content_hashed_preview(tmp_path):
    request, root = _make_request(tmp_path)
    result = iq.build(request=request, preview_root=root)
    assert result.preview_path.is_file()
    # content-addressed filename carries the content hash
    assert result.content_hash in result.preview_path.name
    assert result.preview["has_authority"] is False
    assert result.preview["mode"] == "dry-run"


def test_landing_order_is_serialized_by_declared_order(tmp_path):
    request, root = _make_request(tmp_path)
    result = iq.build(request=request, preview_root=root)
    order = result.preview["landing_order"]
    # beta (declared_order=1) lands before alpha (declared_order=2); positions are 1..N
    assert [e["lane_ref"] for e in order] == ["pco-lane-beta", "pco-lane-alpha"]
    assert [e["position"] for e in order] == [1, 2]
    # each entry pins the verified fan-in packet content hash
    for entry in order:
        assert len(entry["fanin_content_hash"]) == 64


def test_build_is_idempotent_same_bytes_same_path(tmp_path):
    request, root = _make_request(tmp_path)
    first = iq.build(request=request, preview_root=root)
    second = iq.build(request=request, preview_root=root)
    assert first.content_hash == second.content_hash
    assert first.preview_path == second.preview_path
    assert _previews(root) == [first.preview_path]


def test_seam_stubs_are_deferred_not_rejected(tmp_path):
    request, root = _make_request(tmp_path)
    result = iq.build(request=request, preview_root=root)
    stubs = result.preview["seam_stubs"]
    for name in ("ce_event", "pcl", "distributed_identity"):
        assert stubs[name]["status"] == "deferred-not-rejected"


# ---------------------------------------------------------------------------
# build — refusals (every refusal raises before any write)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["enqueue", "land", "merge"])
def test_build_refuses_live_action_before_any_write(tmp_path, action):
    request, root = _make_request(tmp_path)
    with pytest.raises(iq.AuthorityRefused):
        iq.build(request=request, preview_root=root, live_action=action)
    assert _previews(root) == []


def test_build_refuses_missing_source_ratification(tmp_path):
    request, root = _make_request(tmp_path, source_ratification=None)
    with pytest.raises(iq.MissingSourceRatification):
        iq.build(request=request, preview_root=root)
    assert _previews(root) == []


def test_build_refuses_duplicate_landing_position(tmp_path):
    pkt_a = _build_fanin_packet(tmp_path, "dup-a")
    pkt_b = _build_fanin_packet(tmp_path, "dup-b")
    req = {
        "kind": "integration-queue-dry-run-request",
        "schema_version": "1",
        "preview_id": "pco-v1-g8-dup",
        "source_ratification": {"prompt_ref": ".hermes/x/P.md", "sha256": "c" * 64},
        "lanes": [
            {"lane_ref": "lane-x", "fanin_packet_ref": str(pkt_a), "declared_order": 1},
            {"lane_ref": "lane-y", "fanin_packet_ref": str(pkt_b), "declared_order": 1},
        ],
    }
    request_path = _write(tmp_path / "dup.yaml", yaml.safe_dump(req, sort_keys=True))
    root = tmp_path / ".hermes" / "iq"
    root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(iq.LandingConflict):
        iq.build(request=request_path, preview_root=root)
    assert _previews(root) == []


def test_build_refuses_tampered_fanin_evidence(tmp_path):
    request, root = _make_request(tmp_path)
    # Tamper a referenced fan-in packet on disk so its content hash no longer matches.
    data = yaml.safe_load(Path(request).read_text())
    packet_path = Path(data["lanes"][0]["fanin_packet_ref"])
    packet = json.loads(packet_path.read_text())
    packet["packet_id"] = "tampered-packet-id"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(iq.FaninEvidenceError):
        iq.build(request=request, preview_root=root)
    assert _previews(root) == []


def test_build_refuses_missing_fanin_packet(tmp_path):
    request, root = _make_request(tmp_path)
    data = yaml.safe_load(Path(request).read_text())
    Path(data["lanes"][0]["fanin_packet_ref"]).unlink()
    with pytest.raises(iq.FaninEvidenceError):
        iq.build(request=request, preview_root=root)
    assert _previews(root) == []


def test_build_refuses_empty_lane_set(tmp_path):
    request, root = _make_request(tmp_path, lanes=[])
    with pytest.raises(iq.RequestError):
        iq.build(request=request, preview_root=root)
    assert _previews(root) == []


# ---------------------------------------------------------------------------
# inspect — read-only content-hash + shape verification
# ---------------------------------------------------------------------------


def test_inspect_ok_on_built_preview(tmp_path):
    request, root = _make_request(tmp_path)
    built = iq.build(request=request, preview_root=root)
    result = iq.inspect(preview=built.preview_path)
    assert result.ok
    assert result.issues == ()


def test_inspect_flags_tampered_preview(tmp_path):
    request, root = _make_request(tmp_path)
    built = iq.build(request=request, preview_root=root)
    packet = json.loads(built.preview_path.read_text())
    packet["preview_id"] = "mutated"  # breaks the content hash
    built.preview_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = iq.inspect(preview=built.preview_path)
    assert not result.ok
    assert any("content_hash" in issue for issue in result.issues)


# ---------------------------------------------------------------------------
# schema — the preview document validates against its own schema; authority fails
# ---------------------------------------------------------------------------


def test_schema_rejects_authority_assertion(tmp_path):
    from creator_engine_validator.schema import validate_with_schema

    request, root = _make_request(tmp_path)
    built = iq.build(request=request, preview_root=root)
    bad = dict(built.preview)
    bad["has_authority"] = True
    errors = validate_with_schema(
        bad, iq.SCHEMA_PATH, "<preview>", code="RV1-082", contract=iq.PROSE_CONTRACT
    )
    assert errors  # has_authority: const false -> asserting True must fail schema


def test_schema_rejects_non_dry_run_mode(tmp_path):
    from creator_engine_validator.schema import validate_with_schema

    request, root = _make_request(tmp_path)
    built = iq.build(request=request, preview_root=root)
    bad = dict(built.preview)
    bad["mode"] = "live"
    errors = validate_with_schema(
        bad, iq.SCHEMA_PATH, "<preview>", code="RV1-082", contract=iq.PROSE_CONTRACT
    )
    assert errors  # mode: const dry-run -> "live" must fail schema


# ---------------------------------------------------------------------------
# ce queue CLI surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["queue", "--help"],
    ["queue", "dry-run", "--help"],
    ["queue", "inspect", "--help"],
])
def test_queue_help_is_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


def test_ce_queue_dry_run_writes_preview(tmp_path):
    request, root = _make_request(tmp_path)
    ret = ce_cli.main([
        "queue", "dry-run",
        "--request", str(request),
        "--preview-root", str(root),
    ])
    assert ret == 0
    assert len(_previews(root)) == 1


def test_ce_queue_dry_run_json_reports_hash_and_path(tmp_path, capsys):
    request, root = _make_request(tmp_path)
    ret = ce_cli.main([
        "queue", "dry-run",
        "--request", str(request),
        "--preview-root", str(root),
        "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["has_authority"] is False
    assert payload["mode"] == "dry-run"
    assert payload["content_hash"] in payload["preview_path"]


# ce-ops#218: the v1 `ce queue dry-run --enqueue/--land/--merge` live-tick wiring was
# removed (it imported the v3 forge belt from the v1 CLI → v1⊥v3 boundary violation).
# Live belt actions now run via `cev3 queue-poll` (v3, fail-closed; covered by
# test_integrator_belt). The v1 build's INJECTED live-action-runner contract is unchanged
# and still covered by the two callback tests below.


def test_live_action_callback_accepts_only_runner_accepted_result(tmp_path):
    request, root = _make_request(tmp_path)
    calls = []

    def runner(action_request: iq.LiveActionRequest) -> iq.LiveActionResult:
        calls.append(action_request)
        return iq.LiveActionResult(
            accepted=True,
            action=action_request.action,
            evidence=("approved=true", "all_green=true", "mechanical=true"),
        )

    result = iq.build(
        request=request,
        preview_root=root,
        live_action="enqueue",
        live_action_runner=runner,
    )

    assert result.preview_path.is_file()
    assert len(calls) == 1
    assert calls[0].action == "enqueue"
    assert calls[0].preview_id == "pco-v1-g8-queue-dry-run"


def test_live_action_callback_refusal_fails_closed_before_preview_write(tmp_path):
    request, root = _make_request(tmp_path)

    def runner(action_request: iq.LiveActionRequest) -> iq.LiveActionResult:
        return iq.LiveActionResult(
            accepted=False,
            action=action_request.action,
            refusal_reason="event_not_approved_green",
            evidence=("approved=false",),
        )

    with pytest.raises(iq.AuthorityRefused, match="event_not_approved_green"):
        iq.build(
            request=request,
            preview_root=root,
            live_action="land",
            live_action_runner=runner,
        )
    assert _previews(root) == []


def test_ce_queue_inspect_ok(tmp_path):
    request, root = _make_request(tmp_path)
    built = iq.build(request=request, preview_root=root)
    ret = ce_cli.main(["queue", "inspect", "--preview", str(built.preview_path)])
    assert ret == 0


def test_existing_ce_groups_intact():
    # The new queue group must not displace the prior gate surfaces.
    for argv in (["fanin", "--help"], ["ledger", "--help"], ["worker", "--help"], ["lane", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# Committed example fixtures (examples/{well-formed,malformed}/integration-queue-dry-run)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WELL_FORMED = _REPO_ROOT / "examples" / "well-formed" / "integration-queue-dry-run"
_MALFORMED = _REPO_ROOT / "examples" / "malformed" / "integration-queue-dry-run"


def test_committed_well_formed_preview_inspects_ok():
    result = iq.inspect(preview=_WELL_FORMED / "landing-preview.json")
    assert result.ok, result.issues
    assert result.preview["has_authority"] is False
    assert result.preview["mode"] == "dry-run"


def test_committed_well_formed_request_rebuilds_to_same_hash(tmp_path):
    # Rebuilding from the committed request must reproduce the committed preview's hash.
    committed = json.loads((_WELL_FORMED / "landing-preview.json").read_text())
    result = iq.build(request=_WELL_FORMED / "request.yaml", preview_root=tmp_path / "out")
    assert result.content_hash == committed["content_hash"]


@pytest.mark.parametrize("name", [
    "asserts-authority.json",
    "non-dry-run-mode.json",
    "tampered-content-hash.json",
])
def test_committed_malformed_previews_fail_inspection(name):
    result = iq.inspect(preview=_MALFORMED / name)
    assert not result.ok
    assert result.issues
