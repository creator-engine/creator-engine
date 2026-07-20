"""Unit tests for the dispatch-receipt library — transport-agnostic activation receipts.

Covers:
  - Schema validation: happy path and sad paths
  - Each activation-gap classification
  - Write/read round-trip
  - CLI: ``ce dispatch-receipt emit`` and ``ce dispatch-receipt verify``
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import dispatch_receipt as dr
from creator_engine_validator import ce_cli


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_SHA256_A = "a" * 64  # valid 64-char lowercase hex
_SHA256_B = "b" * 64
_TIMESTAMP = "2026-07-19T12:00:00Z"
_TIMESTAMP_2 = "2026-07-19T12:01:00Z"


def _minimal_receipt(**overrides) -> dict:
    """Return a minimal valid receipt dict (all required fields populated)."""
    base = dict(
        brief_path=".ce/briefs/ce-615-brief.md",
        brief_sha256=_SHA256_A,
        transport_kind="tmux",
        transport_target="ce-dev1-orchestrator:0.0",
        activation_method="send-keys",
        separate_enter=True,
        model_effort_line="claude-sonnet-4-5 / effort:normal",
        dispatcher="controller-1",
        work_unit="wu-615",
        post_check_kind="working-state",
        post_check_verified_at=_TIMESTAMP_2,
        post_check_result="working",
        emitted_at=_TIMESTAMP,
    )
    base.update(overrides)
    return dr.build_receipt(**base)


def _bare_receipt(**overrides) -> dict:
    """Return a receipt with only required fields (no optional verification data)."""
    base = dict(
        brief_path=".ce/briefs/ce-615-brief.md",
        brief_sha256=_SHA256_A,
        transport_kind="tmux",
        transport_target="ce-dev1-orchestrator:0.0",
        activation_method="send-keys",
        separate_enter=True,
        model_effort_line="claude-sonnet-4-5 / effort:normal",
        dispatcher="controller-1",
        work_unit="wu-615",
        emitted_at=_TIMESTAMP,
    )
    base.update(overrides)
    return dr.build_receipt(**base)


# ---------------------------------------------------------------------------
# Schema validation — happy paths
# ---------------------------------------------------------------------------


class TestBuildReceiptHappy:
    def test_minimal_required_fields(self):
        """build_receipt with only required fields produces a valid receipt."""
        receipt = _bare_receipt()
        assert receipt["kind"] == "ce.dispatch-receipt"
        assert receipt["schema_version"] == "1"
        assert receipt["brief_sha256"] == _SHA256_A
        assert receipt["activation"]["separate_enter"] is True
        assert "post_check" not in receipt
        assert "transport_verified_at" not in receipt
        assert "claim_path" not in receipt

    def test_full_receipt_with_all_optional_fields(self):
        receipt = _minimal_receipt(
            claim_path=".ce/claims/ce-615.md",
            claim_sha256=_SHA256_B,
            transport_verified_at=_TIMESTAMP_2,
        )
        assert receipt["claim_path"] == ".ce/claims/ce-615.md"
        assert receipt["claim_sha256"] == _SHA256_B
        assert receipt["transport_verified_at"] == _TIMESTAMP_2
        assert receipt["post_check"]["kind"] == "working-state"
        assert receipt["post_check"]["result"] == "working"

    def test_herdr_transport_kind(self):
        receipt = _bare_receipt(
            transport_kind="herdr",
            transport_target="w1:p1",
            activation_method="herdr-send-keys",
        )
        assert receipt["transport"]["kind"] == "herdr"
        assert receipt["transport"]["target"] == "w1:p1"

    def test_scrollback_match_post_check(self):
        receipt = _bare_receipt(
            post_check_kind="scrollback-match",
            post_check_verified_at=_TIMESTAMP_2,
            post_check_result=">>> starting task",
        )
        assert receipt["post_check"]["kind"] == "scrollback-match"

    def test_emitted_at_defaults_to_now(self):
        receipt = dr.build_receipt(
            brief_path=".ce/briefs/x.md",
            brief_sha256=_SHA256_A,
            transport_kind="tmux",
            transport_target="s:0.0",
            activation_method="send-keys",
            separate_enter=True,
            model_effort_line="model/effort",
            dispatcher="controller-1",
            work_unit="wu-1",
        )
        # emitted_at is auto-set and matches the timestamp pattern
        import re
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", receipt["emitted_at"])


# ---------------------------------------------------------------------------
# Schema validation — sad paths
# ---------------------------------------------------------------------------


class TestBuildReceiptSadPaths:
    def test_missing_brief_path_raises(self):
        with pytest.raises(dr.ReceiptBuildError, match="brief_path"):
            dr.build_receipt(
                brief_path="",
                brief_sha256=_SHA256_A,
                transport_kind="tmux",
                transport_target="s:0.0",
                activation_method="send-keys",
                separate_enter=True,
                model_effort_line="m/e",
                dispatcher="controller-1",
                work_unit="wu-1",
            )

    def test_bad_brief_sha256_raises(self):
        with pytest.raises(dr.ReceiptBuildError, match="brief_sha256"):
            dr.build_receipt(
                brief_path=".ce/briefs/x.md",
                brief_sha256="not-a-hex-digest",
                transport_kind="tmux",
                transport_target="s:0.0",
                activation_method="send-keys",
                separate_enter=True,
                model_effort_line="m/e",
                dispatcher="controller-1",
                work_unit="wu-1",
            )

    def test_claim_path_without_sha256_raises(self):
        with pytest.raises(dr.ReceiptBuildError, match="claim_path and claim_sha256"):
            dr.build_receipt(
                brief_path=".ce/briefs/x.md",
                brief_sha256=_SHA256_A,
                transport_kind="tmux",
                transport_target="s:0.0",
                activation_method="send-keys",
                separate_enter=True,
                model_effort_line="m/e",
                dispatcher="controller-1",
                work_unit="wu-1",
                claim_path=".ce/claims/c.md",
                # claim_sha256 omitted intentionally
            )

    def test_partial_post_check_raises(self):
        with pytest.raises(dr.ReceiptBuildError, match="post_check"):
            dr.build_receipt(
                brief_path=".ce/briefs/x.md",
                brief_sha256=_SHA256_A,
                transport_kind="tmux",
                transport_target="s:0.0",
                activation_method="send-keys",
                separate_enter=True,
                model_effort_line="m/e",
                dispatcher="controller-1",
                work_unit="wu-1",
                post_check_kind="working-state",
                # post_check_verified_at and result omitted
            )

    def test_missing_model_effort_line_raises(self):
        with pytest.raises(dr.ReceiptBuildError, match="model_effort_line"):
            dr.build_receipt(
                brief_path=".ce/briefs/x.md",
                brief_sha256=_SHA256_A,
                transport_kind="tmux",
                transport_target="s:0.0",
                activation_method="send-keys",
                separate_enter=True,
                model_effort_line="",
                dispatcher="controller-1",
                work_unit="wu-1",
            )

    def test_invalid_transport_kind_fails_schema(self):
        """An invalid transport_kind passes build-time checks but fails schema."""
        # We have to go through a raw dict because build_receipt catches this
        # earlier via schema validation (not a separate guard).
        with pytest.raises((dr.ReceiptSchemaError, dr.ReceiptBuildError)):
            dr.build_receipt(
                brief_path=".ce/briefs/x.md",
                brief_sha256=_SHA256_A,
                transport_kind="signal",  # not in enum
                transport_target="s:0.0",
                activation_method="send-keys",
                separate_enter=True,
                model_effort_line="m/e",
                dispatcher="controller-1",
                work_unit="wu-1",
            )


# ---------------------------------------------------------------------------
# Gap classification — verify_receipt
# ---------------------------------------------------------------------------


class TestVerifyReceiptGapClasses:
    def test_clean_receipt_no_failures(self):
        """A receipt with transport_verified_at + separate_enter + post_check passes."""
        receipt = _minimal_receipt(transport_verified_at=_TIMESTAMP_2)
        failures = dr.verify_receipt(receipt)
        assert failures == []

    def test_dispatch_without_transport_gap(self):
        """Missing transport_verified_at → dispatch-without-transport."""
        receipt = _bare_receipt(separate_enter=True)
        # No transport_verified_at
        failures = dr.verify_receipt(receipt)
        gap_classes = {f.gap_class for f in failures}
        assert dr.GAP_DISPATCH_WITHOUT_TRANSPORT in gap_classes

    def test_receipt_without_activation_separate_enter_false(self):
        """separate_enter=False → receipt-without-activation."""
        receipt = _bare_receipt(separate_enter=False)
        failures = dr.verify_receipt(receipt)
        gap_classes = [f.gap_class for f in failures]
        assert dr.GAP_RECEIPT_WITHOUT_ACTIVATION in gap_classes
        # Check the specific field name is reported
        enter_failures = [
            f for f in failures
            if f.gap_class == dr.GAP_RECEIPT_WITHOUT_ACTIVATION
            and f.field == "activation.separate_enter"
        ]
        assert len(enter_failures) == 1

    def test_receipt_without_activation_no_post_check(self):
        """Missing post_check → receipt-without-activation."""
        receipt = _bare_receipt(separate_enter=True)
        # separate_enter=True but no post_check
        failures = dr.verify_receipt(receipt)
        gap_classes = [f.gap_class for f in failures]
        assert dr.GAP_RECEIPT_WITHOUT_ACTIVATION in gap_classes
        post_check_failures = [
            f for f in failures
            if f.gap_class == dr.GAP_RECEIPT_WITHOUT_ACTIVATION
            and f.field == "post_check"
        ]
        assert len(post_check_failures) == 1

    def test_all_three_gaps_at_once(self):
        """Receipt with no transport_verified_at, separate_enter=False, and no post_check."""
        receipt = _bare_receipt(separate_enter=False)
        failures = dr.verify_receipt(receipt)
        gap_classes = {f.gap_class for f in failures}
        # Should have BOTH gap classes
        assert dr.GAP_DISPATCH_WITHOUT_TRANSPORT in gap_classes
        assert dr.GAP_RECEIPT_WITHOUT_ACTIVATION in gap_classes
        # And multiple receipt-without-activation failures
        rwoa = [f for f in failures if f.gap_class == dr.GAP_RECEIPT_WITHOUT_ACTIVATION]
        assert len(rwoa) == 2  # separate_enter=False AND no post_check

    def test_only_separate_enter_gap(self):
        """separate_enter=False with post_check present → only that sub-gap."""
        receipt = _bare_receipt(
            separate_enter=False,
            transport_verified_at=_TIMESTAMP_2,
            post_check_kind="working-state",
            post_check_verified_at=_TIMESTAMP_2,
            post_check_result="working",
        )
        failures = dr.verify_receipt(receipt)
        gap_classes = {f.gap_class for f in failures}
        # transport verified → no dispatch-without-transport
        assert dr.GAP_DISPATCH_WITHOUT_TRANSPORT not in gap_classes
        assert dr.GAP_RECEIPT_WITHOUT_ACTIVATION in gap_classes

    def test_only_missing_post_check_gap(self):
        """separate_enter=True but no post_check, transport verified."""
        receipt = _bare_receipt(
            separate_enter=True,
            transport_verified_at=_TIMESTAMP_2,
        )
        failures = dr.verify_receipt(receipt)
        gap_classes = {f.gap_class for f in failures}
        assert dr.GAP_DISPATCH_WITHOUT_TRANSPORT not in gap_classes
        assert dr.GAP_RECEIPT_WITHOUT_ACTIVATION in gap_classes

    def test_verify_receipt_is_pure_no_io(self):
        """verify_receipt must not touch the filesystem."""
        import io as _io
        import unittest.mock as mock

        receipt = _bare_receipt(separate_enter=True)
        with mock.patch("builtins.open", side_effect=AssertionError("I/O forbidden")):
            failures = dr.verify_receipt(receipt)
        # Failures may or may not be present but no I/O was performed
        assert isinstance(failures, list)


# ---------------------------------------------------------------------------
# Write / read round-trip
# ---------------------------------------------------------------------------


class TestWriteReadRoundTrip:
    def test_write_creates_file(self, tmp_path: Path):
        receipt = _bare_receipt(separate_enter=True)
        dest = dr.write_receipt(receipt, state_root=tmp_path / "state")
        assert dest.exists()
        assert dest.suffix == ".json"
        # Verify parent directory is correct
        assert dest.parent.name == dr.RECEIPTS_SUBDIR

    def test_read_round_trips_content(self, tmp_path: Path):
        receipt = _bare_receipt(separate_enter=True)
        dest = dr.write_receipt(receipt, state_root=tmp_path / "state")
        loaded = dr.read_receipt(dest)
        assert loaded["kind"] == receipt["kind"]
        assert loaded["brief_sha256"] == receipt["brief_sha256"]
        assert loaded["work_unit"] == receipt["work_unit"]

    def test_write_multiple_receipts_no_collision(self, tmp_path: Path):
        """Two write calls must produce distinct files."""
        r1 = _bare_receipt(emitted_at="2026-07-19T12:00:00Z", separate_enter=True)
        r2 = _bare_receipt(emitted_at="2026-07-19T12:00:01Z", separate_enter=True)
        d1 = dr.write_receipt(r1, state_root=tmp_path / "state")
        d2 = dr.write_receipt(r2, state_root=tmp_path / "state")
        assert d1 != d2

    def test_read_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            dr.read_receipt(tmp_path / "nonexistent.json")

    def test_read_invalid_schema_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"kind": "wrong", "schema_version": "1"}), encoding="utf-8")
        with pytest.raises(dr.ReceiptSchemaError):
            dr.read_receipt(bad)

    def test_write_with_custom_filename(self, tmp_path: Path):
        receipt = _bare_receipt(separate_enter=True)
        dest = dr.write_receipt(
            receipt,
            state_root=tmp_path / "state",
            filename="custom-name.json",
        )
        assert dest.name == "custom-name.json"

    def test_full_receipt_round_trips(self, tmp_path: Path):
        receipt = _minimal_receipt(
            transport_verified_at=_TIMESTAMP_2,
            claim_path=".ce/claims/ce-615.md",
            claim_sha256=_SHA256_B,
        )
        dest = dr.write_receipt(receipt, state_root=tmp_path / "state")
        loaded = dr.read_receipt(dest)
        assert loaded["transport_verified_at"] == _TIMESTAMP_2
        assert loaded["claim_sha256"] == _SHA256_B
        assert loaded["post_check"]["kind"] == "working-state"


# ---------------------------------------------------------------------------
# patch_receipt
# ---------------------------------------------------------------------------


class TestPatchReceipt:
    def test_patch_adds_transport_verified_at(self):
        base = _bare_receipt(separate_enter=True)
        patched = dr.patch_receipt(base, transport_verified_at=_TIMESTAMP_2)
        assert patched["transport_verified_at"] == _TIMESTAMP_2
        # Original is untouched
        assert "transport_verified_at" not in base

    def test_patch_adds_post_check(self):
        base = _bare_receipt(separate_enter=True)
        patched = dr.patch_receipt(
            base,
            post_check_kind="working-state",
            post_check_verified_at=_TIMESTAMP_2,
            post_check_result="working",
        )
        assert patched["post_check"]["kind"] == "working-state"

    def test_patch_partial_post_check_raises(self):
        base = _bare_receipt(separate_enter=True)
        with pytest.raises(dr.ReceiptBuildError, match="post_check"):
            dr.patch_receipt(base, post_check_kind="working-state")


# ---------------------------------------------------------------------------
# SHA256 helpers
# ---------------------------------------------------------------------------


class TestSha256Helpers:
    def test_sha256_bytes(self):
        digest = dr.sha256_bytes(b"hello")
        assert len(digest) == 64
        assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_sha256_file(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello")
        assert dr.sha256_file(f) == dr.sha256_bytes(b"hello")


# ---------------------------------------------------------------------------
# CLI integration — emit
# ---------------------------------------------------------------------------


class TestCliEmit:
    def test_emit_writes_file_and_reports_gaps(self, tmp_path: Path):
        brief = tmp_path / "brief.md"
        brief.write_text("# Brief content\n", encoding="utf-8")

        rc = ce_cli.main([
            "dispatch-receipt", "emit",
            "--brief-path", str(brief),
            "--transport-kind", "tmux",
            "--transport-target", "ce-dev1-orchestrator:0.0",
            "--activation-method", "send-keys",
            # NOTE: --separate-enter NOT passed → defaults to False
            "--model-effort-line", "claude-sonnet-4-5 / effort:normal",
            "--dispatcher", "controller-1",
            "--work-unit", "wu-615",
            "--state-root", str(tmp_path / "state"),
        ])
        # CLI exits 0 even when gaps exist (gaps are warnings, not hard errors)
        assert rc == 0
        receipts_dir = tmp_path / "state" / dr.RECEIPTS_SUBDIR
        assert receipts_dir.exists()
        files = list(receipts_dir.glob("*.json"))
        assert len(files) == 1

    def test_emit_json_output(self, tmp_path: Path, capsys):
        brief = tmp_path / "brief.md"
        brief.write_text("# Brief\n", encoding="utf-8")

        ce_cli.main([
            "dispatch-receipt", "emit",
            "--brief-path", str(brief),
            "--transport-kind", "tmux",
            "--transport-target", "s:0.0",
            "--activation-method", "send-keys",
            "--separate-enter",
            "--model-effort-line", "m/e",
            "--dispatcher", "controller-1",
            "--work-unit", "wu-615",
            "--state-root", str(tmp_path / "state"),
            "--json",
        ])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["ok"] is True
        assert "receipt_path" in payload
        assert "gap_classes" in payload

    def test_emit_missing_brief_returns_error(self, tmp_path: Path):
        rc = ce_cli.main([
            "dispatch-receipt", "emit",
            "--brief-path", str(tmp_path / "nonexistent.md"),
            "--transport-kind", "tmux",
            "--transport-target", "s:0.0",
            "--activation-method", "send-keys",
            "--model-effort-line", "m/e",
            "--dispatcher", "controller-1",
            "--work-unit", "wu-615",
            "--state-root", str(tmp_path / "state"),
        ])
        assert rc == 1


# ---------------------------------------------------------------------------
# CLI integration — verify
# ---------------------------------------------------------------------------


class TestCliVerify:
    def _write_receipt(self, tmp_path: Path, **overrides) -> Path:
        receipt = _bare_receipt(**overrides)
        return dr.write_receipt(receipt, state_root=tmp_path / "state")

    def test_verify_clean_receipt_exits_0(self, tmp_path: Path):
        dest = dr.write_receipt(
            _minimal_receipt(transport_verified_at=_TIMESTAMP_2),
            state_root=tmp_path / "state",
        )
        rc = ce_cli.main([
            "dispatch-receipt", "verify", str(dest),
        ])
        assert rc == 0

    def test_verify_gapped_receipt_exits_1(self, tmp_path: Path):
        dest = self._write_receipt(tmp_path, separate_enter=False)
        rc = ce_cli.main([
            "dispatch-receipt", "verify", str(dest),
        ])
        assert rc == 1

    def test_verify_json_output_has_gap_classes(self, tmp_path: Path, capsys):
        dest = self._write_receipt(tmp_path, separate_enter=False)
        ce_cli.main([
            "dispatch-receipt", "verify", str(dest), "--json",
        ])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert dr.GAP_RECEIPT_WITHOUT_ACTIVATION in payload["gap_classes"]

    def test_verify_missing_file_exits_1(self, tmp_path: Path):
        rc = ce_cli.main([
            "dispatch-receipt", "verify", str(tmp_path / "nope.json"),
        ])
        assert rc == 1

    def test_verify_json_clean_receipt(self, tmp_path: Path, capsys):
        dest = dr.write_receipt(
            _minimal_receipt(transport_verified_at=_TIMESTAMP_2),
            state_root=tmp_path / "state",
        )
        ce_cli.main([
            "dispatch-receipt", "verify", str(dest), "--json",
        ])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["ok"] is True
        assert payload["gap_classes"] == []
        assert payload["failures"] == []
